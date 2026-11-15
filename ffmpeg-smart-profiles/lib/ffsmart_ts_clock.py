"""Conservative MPEG-TS PCR timeline, implemented for FFmpeg Smart (MIT).

TSClock.feed(data) accepts arbitrarily split bytes and returns *only new* ordered
(offset, epoch, seconds) events; seconds is None for invalidation. Offset is the zero-based absolute byte offset
of the packet carrying PCR; seconds are unwrapped 27 MHz ticks within epoch.
known indicates that a validated single-program PAT and PMT select a PCR PID;
reason explains unknown state. Epoch changes invalidate all older markers. No
markers are retained by this object. Caller must bound its own marker queue.

This intentionally rejects multi-program/multi-section tables, malformed PSI,
transport errors and ambiguous alignment rather than guessing a clock. After a
fault, fresh valid PAT and PMT are required. An input discontinuity or changed
program/PMT/PCR identity starts a new epoch. PCR discontinuity_indicator and
backward jumps other than a plausible wrap start a new epoch as well.
"""

PACKET = 188
PCR_MOD = (1 << 33) * 300
# Bound stale timing in the byte domain; this is not a wall-clock timeout.
MAX_PCR_GAP_BYTES = 4 * 1024 * 1024


def _crc32(data):
    crc = 0xffffffff
    for byte in data:
        crc ^= byte << 24
        for _ in range(8):
            crc = ((crc << 1) ^ (0x04c11db7 if crc & 0x80000000 else 0)) & 0xffffffff
    return crc


class TSClock:
    def __init__(self):
        self.epoch = 0
        self.known = False
        self.reason = 'waiting for PAT and PMT'
        self._buf = bytearray()
        self._offset = 0
        self._program = self._pmt = self._pcr = None
        self._tsid = None
        self._pat_version = self._pmt_version = None
        self._sections = {}
        self._cc = {}
        self._last_pcr = None
        self._last_pcr_offset = None
        self._unwrapped = 0
        self._events = None
        self._event_offset = 0

    def _reset(self, reason):
        self.epoch += 1
        if self._events is not None:
            self._events.append((self._event_offset, self.epoch, None))
        self.known = False
        self.reason = reason
        self._program = self._pmt = self._pcr = None
        self._tsid = None
        self._pat_version = self._pmt_version = None
        self._sections.clear()
        self._cc.clear()
        self._last_pcr = None
        self._last_pcr_offset = None
        self._unwrapped = 0

    def _new_clock(self):
        self.epoch += 1
        if self._events is not None:
            self._events.append((self._event_offset, self.epoch, None))
        self._last_pcr = None
        self._last_pcr_offset = None
        self._unwrapped = 0

    @property
    def consumed(self):
        """Absolute position immediately after the last complete packet."""
        return self._offset

    def feed(self, data):
        self._buf.extend(data)
        out = []
        self._events = out
        while len(self._buf) >= PACKET:
            packet = bytes(self._buf[:PACKET])
            del self._buf[:PACKET]
            offset = self._offset
            self._offset += PACKET
            self._event_offset = offset
            if self._last_pcr_offset is not None and offset - self._last_pcr_offset > MAX_PCR_GAP_BYTES:
                self._new_clock()
                self.known = False
                self.reason = 'PCR stale in byte domain'
            if packet[0] != 0x47:
                self._reset('lost TS packet alignment')
                # Never guess a new phase; input must be a packet-aligned TS.
                continue
            self._packet(packet, offset, out)
        self._events = None
        return out

    def _packet(self, p, offset, out):
        pid = ((p[1] & 31) << 8) | p[2]
        if p[1] & 0x80 or p[3] & 0xc0:
            self._reset('transport error or scrambled packet')
            return
        afc = (p[3] >> 4) & 3
        if not afc:
            self._reset('invalid adaptation control')
            return
        pos = 4
        discontinuity = False
        pcr = None
        if afc & 2:
            n = p[pos]
            pos += 1
            if pos + n > PACKET:
                self._reset('invalid adaptation length')
                return
            if n:
                flags = p[pos]
                discontinuity = bool(flags & 0x80)
                if flags & 0x10:
                    if n < 7:
                        self._reset('truncated PCR')
                        return
                    b = p[pos + 1:pos + 7]
                    base = (b[0] << 25) | (b[1] << 17) | (b[2] << 9) | (b[3] << 1) | (b[4] >> 7)
                    ext = ((b[4] & 1) << 8) | b[5]
                    if b[4] & 0x7e != 0x7e or ext >= 300:
                        self._reset('invalid PCR encoding')
                        return
                    pcr = base * 300 + ext
            pos += n
        if pid == self._pcr and discontinuity:
            self._new_clock()
        if self._pcr is not None and pid == self._pcr and pcr is not None:
            self.known = True
            self.reason = 'validated single-program PCR'
            if self._last_pcr is None:
                self._unwrapped = pcr
            else:
                delta = pcr - self._last_pcr
                if delta < 0 and self._last_pcr > PCR_MOD * 3 // 4 and pcr < PCR_MOD // 4:
                    delta += PCR_MOD
                # Large PCR jumps cannot safely be treated as a pacing delay.
                if delta < 0 or delta > 27000000 * 2:
                    self._new_clock()
                    self._unwrapped = pcr
                else:
                    self._unwrapped += delta
            self._last_pcr = pcr
            self._last_pcr_offset = offset
            out.append((offset, self.epoch, self._unwrapped / 27000000))
        if discontinuity and pid in (0, self._pmt):
            self._reset('PSI discontinuity')
            return
        if not afc & 1 or pid not in (0, self._pmt):
            return
        if pos >= PACKET:
            self._reset('missing PSI payload')
            return
        cc = p[3] & 15
        prev = self._cc.get(pid)
        if discontinuity:
            self._sections.pop(pid, None)
            prev = None
        if prev is not None and cc != ((prev + 1) & 15):
            self._reset('PSI continuity error')
            return
        self._cc[pid] = cc
        payload = p[pos:]
        if p[1] & 0x40:
            pointer = payload[0]
            if pointer + 1 > len(payload):
                self._reset('invalid PSI pointer')
                return
            prior = payload[1:1 + pointer]
            if pid in self._sections:
                self._section_bytes(pid, prior, False)
                if pid in self._sections:
                    self._reset('incomplete PSI before pointer')
                    return
            self._section_bytes(pid, payload[1 + pointer:], True)
        elif pid in self._sections:
            self._section_bytes(pid, payload, False)

    def _section_bytes(self, pid, data, starts):
        if starts:
            self._sections[pid] = bytearray()
        buf = self._sections.get(pid)
        if buf is None:
            return
        buf.extend(data)
        while buf:
            if buf[0] == 0xff:
                self._sections.pop(pid, None)
                return
            if len(buf) < 3:
                return
            length = ((buf[1] & 15) << 8) | buf[2]
            if length < 9 or length > 1021 or buf[1] & 0xf0 != 0xb0:
                self._reset('invalid PSI section length or syntax')
                return
            total = 3 + length
            if len(buf) < total:
                return
            section = bytes(buf[:total])
            del buf[:total]
            if _crc32(section) != 0:
                self._reset('PSI CRC error')
                return
            self._table(pid, section)
            if self._sections.get(pid) is not buf:
                return
        self._sections.pop(pid, None)

    def _table(self, pid, s):
        expected = 0 if pid == 0 else 2
        if s[0] != expected or len(s) < (12 if pid == 0 else 16) or s[5] & 0xc0 != 0xc0:
            self._reset('invalid PSI table')
            return
        if not s[5] & 1:
            return
        if s[6] or s[7]:
            self._reset('multi-section PSI is ambiguous')
            return
        version = (s[5] >> 1) & 31
        if pid == 0:
            body = s[8:-4]
            if len(body) % 4:
                self._reset('malformed PAT')
                return
            programs = []
            for i in range(0, len(body), 4):
                number = int.from_bytes(body[i:i+2], 'big')
                if body[i+2] & 0xe0 != 0xe0:
                    self._reset('malformed PAT PID')
                    return
                if number:
                    programs.append((number, ((body[i+2] & 31) << 8) | body[i+3]))
            if len(programs) != 1 or programs[0][1] in (0, 0x1fff):
                self._reset('PAT is not single-program')
                return
            program, pmt = programs[0]
            tsid = int.from_bytes(s[3:5], 'big')
            if self._program is not None and (tsid, program, pmt) != (self._tsid, self._program, self._pmt):
                self._reset('program identity changed')
            elif self._pat_version is not None and version != self._pat_version:
                self._new_clock()
            self._tsid, self._program, self._pmt, self._pat_version = tsid, program, pmt, version
        else:
            if int.from_bytes(s[3:5], 'big') != self._program or s[8] & 0xe0 != 0xe0 or s[10] & 0xf0 != 0xf0:
                self._reset('invalid PMT identity or reserved bits')
                return
            pcr = ((s[8] & 31) << 8) | s[9]
            info = ((s[10] & 15) << 8) | s[11]
            end = len(s) - 4
            pos = 12 + info
            if pcr == 0x1fff or pos > end:
                self._reset('invalid PMT PCR or descriptors')
                return
            while pos < end:
                if pos + 5 > end or s[pos+1] & 0xe0 != 0xe0 or s[pos+3] & 0xf0 != 0xf0:
                    self._reset('malformed PMT stream')
                    return
                pos += 5 + (((s[pos+3] & 15) << 8) | s[pos+4])
                if pos > end:
                    self._reset('malformed PMT descriptors')
                    return
            if self._pcr is not None and (self._pcr != pcr or self._pmt_version != version):
                self._new_clock()
            self._pcr, self._pmt_version = pcr, version
            if self.reason != 'PCR stale in byte domain':
                self.known = True
                self.reason = 'validated single-program PCR'
