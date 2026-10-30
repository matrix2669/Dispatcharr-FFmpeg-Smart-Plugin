#!/usr/bin/env python3
"""Owned, single-request HTTP MPEG-TS startup reservoir (stdlib only).

Media stays in RAM. Probe clients replay byte zero; the sole playback client
releases retained chunks only after delivery, applying upstream backpressure.
"""

import base64
from collections import deque
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
import secrets
import signal
import socket
import ssl
import subprocess
import sys
import threading
import time
from urllib.parse import unquote, urljoin, urlsplit


class Reservoir:
    def __init__(self, source, agent, cap, idle):
        self.source, self.agent, self.cap, self.idle = source, agent, cap, idle
        self.cv = threading.Condition()
        self.chunks = deque()
        self.start = self.end = self.peak = self.opens = self.requests = 0
        self.eof = self.stopped = self.playback = False
        self.error = None
        self.connection = None
        self.socket = None
        self.began = time.monotonic()
        self.first_byte = self.playback_ms = None
        self.first_output = None
        self.probe_start_ms = {}
        self.probes = 0
        self.reader_started = False

    def fail(self, reason):
        with self.cv:
            if not self.error:
                self.error = reason
            self.cv.notify_all()

    def read(self):
        try:
            url = urlsplit(self.source)
            headers = {"User-Agent": self.agent or "ffmpeg-smart-shared-input", "Accept-Encoding": "identity"}
            if url.username is not None:
                credentials = unquote(url.username) + ":" + unquote(url.password or "")
                headers["Authorization"] = "Basic " + base64.b64encode(credentials.encode()).decode()
            initial_origin = (url.scheme, url.hostname, url.port or (443 if url.scheme == "https" else 80))
            target_url = self.source
            previous_scheme = url.scheme
            for redirect in range(6):
                if self.stopped:
                    return
                url = urlsplit(target_url)
                if url.scheme not in ("http", "https") or not url.hostname:
                    self.fail("unsupported-redirect")
                    return
                if redirect and (url.username is not None or (previous_scheme == "https" and url.scheme != "https")):
                    self.fail("unsafe-redirect")
                    return
                origin = (url.scheme, url.hostname, url.port or (443 if url.scheme == "https" else 80))
                request_headers = dict(headers)
                if origin != initial_origin:
                    request_headers.pop("Authorization", None)
                connection_type = http.client.HTTPSConnection if url.scheme == "https" else http.client.HTTPConnection
                kwargs = {"timeout": self.idle}
                if url.scheme == "https":
                    kwargs["context"] = ssl.create_default_context()
                self.connection = connection_type(url.hostname, url.port, **kwargs)
                self.requests += 1
                target = (url.path or "/") + ("?" + url.query if url.query else "")
                self.connection.request("GET", target, headers=request_headers)
                self.socket = self.connection.sock
                response = self.connection.getresponse()
                if response.status in (301, 302, 303, 307, 308):
                    location = response.getheader("Location")
                    response.close()
                    self.connection.close()
                    if not location or redirect == 5:
                        self.fail("redirect-limit-or-missing-location")
                        return
                    target_url = urljoin(target_url, location)
                    previous_scheme = url.scheme
                    continue
                if response.status != 200:
                    self.fail("http-status")
                    return
                self.opens = 1
                break
            if response.getheader("Content-Encoding", "identity").lower() != "identity":
                self.fail("unsupported-content-encoding")
                return
            prefix = bytearray()
            validated = False
            while not self.stopped:
                with self.cv:
                    while self.end - self.start >= self.cap and not self.stopped:
                        self.cv.wait(.1)
                    if self.stopped:
                        break
                    size = min(65536, self.cap - (self.end - self.start) - len(prefix))
                data = response.read1(size)
                if not data:
                    if response.length:
                        self.fail("upstream-truncated")
                    if not validated:
                        self.fail("early-eof-before-mpegts")
                    with self.cv:
                        self.eof = True
                        self.cv.notify_all()
                    break
                if self.first_byte is None:
                    self.first_byte = round((time.monotonic() - self.began) * 1000)
                if not validated:
                    prefix.extend(data)
                    if len(prefix) < 377:
                        continue
                    if any(prefix[i] != 0x47 for i in (0, 188, 376)):
                        self.fail("unsupported-input-requires-188-byte-mpegts")
                        return
                    validated = True
                    data = bytes(prefix)
                    prefix.clear()
                with self.cv:
                    # Coalesce short socket reads without delaying delivery.
                    # Queue object overhead must not scale with one-byte reads.
                    offset = self.end
                    remaining = data
                    if self.chunks and len(self.chunks[-1][1]) < 65536:
                        tail = self.chunks[-1][1]
                        amount = min(65536 - len(tail), len(remaining))
                        tail.extend(remaining[:amount])
                        remaining = remaining[amount:]
                        offset += amount
                    if remaining:
                        self.chunks.append((offset, bytearray(remaining)))
                    self.end += len(data)
                    self.peak = max(self.peak, self.end - self.start)
                    self.cv.notify_all()
        except (OSError, ValueError, http.client.HTTPException):
            if not self.stopped:
                self.fail("upstream-read")
        finally:
            if self.connection:
                self.connection.close()

    def stream(self, handler, playback):
        with self.cv:
            if playback:
                if self.playback:
                    handler.send_error(409)
                    return
                self.playback = True
            else:
                if self.playback:
                    handler.send_error(409)
                    return
                self.probes += 1
                self.probe_start_ms[handler.path.rsplit('/', 1)[-1]] = round((time.monotonic() - self.began) * 1000)
        handler.send_response(200)
        handler.send_header("Content-Type", "video/mp2t")
        handler.send_header("Connection", "close")
        handler.end_headers()
        cursor = 0
        try:
            while not self.stopped:
                with self.cv:
                    while cursor >= self.end and not (self.eof or self.error or self.stopped):
                        self.cv.wait(.1)
                    if self.error or self.stopped:
                        return
                    if cursor >= self.end and self.eof:
                        return
                    data = next((bytes(chunk[cursor - offset:]) for offset, chunk in self.chunks
                                 if offset <= cursor < offset + len(chunk)), None)
                    if data is None:
                        return  # An old probe may finish after playback releases its prefix.
                handler.wfile.write(data)
                cursor += len(data)
                if playback:
                    with self.cv:
                        if self.playback_ms is None:
                            self.playback_ms = round((time.monotonic() - self.began) * 1000)
                        while self.chunks and self.chunks[0][0] + len(self.chunks[0][1]) <= cursor:
                            offset, chunk = self.chunks.popleft()
                            self.start = offset + len(chunk)
                        self.cv.notify_all()
        except (BrokenPipeError, ConnectionResetError, socket.timeout):
            pass

    def close(self):
        with self.cv:
            self.stopped = True
            self.cv.notify_all()
        if self.connection:
            # Closing alone does not interrupt a blocked read on every platform.
            sock = self.socket
            if sock:
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
            self.connection.close()


def main():
    source = os.environ.pop("FFSMART_SHARED_SOURCE")
    agent = os.environ.pop("FFSMART_SHARED_AGENT", "")
    cap = int(os.environ["FFMPEG_SMART_SHARED_INPUT_BYTES"])
    deadline = int(os.environ["FFMPEG_SMART_SHARED_INPUT_DEADLINE"])
    idle = int(os.environ["FFMPEG_SMART_SHARED_INPUT_IDLE"])
    reservoir = Reservoir(source, agent, cap, idle)
    token = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_GET(self):
            route = self.path.removeprefix("/" + token + "/")
            if self.path != "/" + token + "/" + route or route not in ("fast", "expanded", "default", "playback"):
                self.send_error(403)
                return
            self.connection.settimeout(idle)
            with reservoir.cv:
                if not reservoir.reader_started:
                    reservoir.reader_started = True
                    threading.Thread(target=reservoir.read, daemon=True).start()
            reservoir.stream(self, route == "playback")

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    endpoint = "http://127.0.0.1:%d/%s" % (server.server_port, token)
    env = dict(os.environ, FFSMART_SHARED_ENDPOINT=endpoint)
    cancelled = threading.Event()
    for signum in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(signum, lambda _sig, _frame: cancelled.set())
    child = None
    status = 1
    output_done = threading.Event()

    def forward_output():
        try:
            while True:
                data = os.read(child.stdout.fileno(), 65536)
                if not data:
                    return
                while data:
                    written = os.write(sys.stdout.fileno(), data)
                    data = data[written:]
                    if reservoir.first_output is None:
                        reservoir.first_output = round((time.monotonic() - reservoir.began) * 1000)
        except OSError:
            reservoir.fail("downstream-output")
        finally:
            output_done.set()

    try:
        threading.Thread(target=server.serve_forever, daemon=True).start()
        child = subprocess.Popen(sys.argv[1:], env=env, start_new_session=True, stdout=subprocess.PIPE)
        threading.Thread(target=forward_output, daemon=True).start()
        while child.poll() is None or not output_done.is_set():
            if cancelled.wait(.05):
                status = 130
                break
            if reservoir.error:
                break
            if reservoir.first_output is None and time.monotonic() - reservoir.began > deadline:
                reservoir.fail("startup-deadline")
                break
        else:
            status = child.returncode
        if reservoir.error:
            status = 65
            print("[ffmpeg-smart] ERROR [shared-input]: " + reservoir.error, file=sys.stderr)
    finally:
        reservoir.close()
        if child is not None:
            # Descendants may outlive a shell that exited or received a signal.
            try:
                os.killpg(child.pid, signal.SIGTERM)
                try:
                    child.wait(timeout=.5)
                except subprocess.TimeoutExpired:
                    pass
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            child.wait()
        server.shutdown()
        server.server_close()
        print("[ffmpeg-smart] shared-input upstream_opens=%d upstream_requests=%d first_byte_ms=%s playback_feed_ms=%s first_output_ms=%s probe_requests=%d peak_retained_bytes=%d cap_bytes=%d probe_start_ms=%s" %
              (reservoir.opens, reservoir.requests, reservoir.first_byte, reservoir.playback_ms, reservoir.first_output, reservoir.probes, reservoir.peak, cap, reservoir.probe_start_ms), file=sys.stderr)
    return status if status >= 0 else 128 - status


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError):
        print("[ffmpeg-smart] ERROR [shared-input]: supervisor-configuration-or-startup", file=sys.stderr)
        sys.exit(65)
