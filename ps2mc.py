"""PS2 メモリーカードイメージ (PCSX2 の .ps2 / .bin) の読み書き。

- 512byte ページ + 16byte スペア(ECC) の 528byte 形式と、スペア無し 512byte 形式の両方に対応
- ファイルの「同じサイズでの上書き」のみ対応 (FAT / ディレクトリ構造は変更しない)
- 書き込んだページの ECC は再計算する (実カードのスペア領域から逆算したアルゴリズム)
"""
import struct

PAGE = 512

# ---- ECC ----
_PAR = [bin(i).count("1") & 1 for i in range(256)]
_COLV = [0x07, 0x16, 0x25, 0x34, 0x43, 0x52, 0x61, 0x70]
_COL = []
for _b in range(256):
    _v = 0
    for _k in range(8):
        if _b >> _k & 1:
            _v ^= _COLV[_k]
    _COL.append(_v)


def ecc128(chunk):
    col, l0, l1 = 0x77, 0x7F, 0x7F
    for i, b in enumerate(chunk):
        col ^= _COL[b]
        if _PAR[b]:
            l0 ^= ~i
            l1 ^= i
    return bytes([col & 0xFF, l0 & 0x7F, l1 & 0x7F])


class Entry:
    def __init__(self, raw, parent):
        self.raw = raw
        self.parent = parent
        self.mode, _, self.length, = struct.unpack_from("<HHI", raw, 0)
        self.cluster = struct.unpack_from("<I", raw, 0x10)[0]
        self.name = raw[0x40:0x60].split(b"\0")[0].decode("latin1")

    @property
    def is_dir(self):
        return bool(self.mode & 0x20)

    @property
    def is_file(self):
        return bool(self.mode & 0x10)


class Card:
    def __init__(self, path):
        self.path = path
        self.data = bytearray(open(path, "rb").read())
        n = len(self.data)
        if n % 528 == 0 and (n // 528) in (8192 * 2, 16384, 4096 * 2):
            self.stride = 528
        elif n % 512 == 0:
            self.stride = 512
        else:
            raise ValueError("メモリーカードイメージとして認識できません")
        sb = self._page(0)
        if not sb.startswith(b"Sony PS2 Memory Card Format"):
            raise ValueError("PS2 メモリーカードではありません")
        self.page_size, self.ppc, self.ppb = struct.unpack_from("<HHH", sb, 0x28)
        (self.clusters, self.alloc_off, self.alloc_end,
         self.root) = struct.unpack_from("<IIII", sb, 0x30)
        self.ifc = struct.unpack_from("<32I", sb, 0x50)
        self.csize = self.page_size * self.ppc
        self.dirty_pages = set()
        self._load_fat()

    # --- 低レベル ---
    def _page(self, n):
        o = n * self.stride
        return bytes(self.data[o:o + PAGE])

    def _cluster(self, n):
        return b"".join(self._page(n * self.ppc + i) for i in range(self.ppc))

    def _write_cluster(self, n, buf):
        for i in range(self.ppc):
            p = n * self.ppc + i
            o = p * self.stride
            self.data[o:o + PAGE] = buf[i * PAGE:(i + 1) * PAGE]
            self.dirty_pages.add(p)

    def _load_fat(self):
        epc = self.csize // 4
        fat = []
        for i in self.ifc:
            if i == 0xFFFFFFFF:
                break
            for j in struct.unpack(f"<{epc}I", self._cluster(i)):
                if j == 0xFFFFFFFF or len(fat) >= self.clusters:
                    break
                fat += struct.unpack(f"<{epc}I", self._cluster(j))
        self.fat = fat

    def chain(self, start):
        out, c = [], start
        while True:
            out.append(c)
            n = self.fat[c]
            if n == 0xFFFFFFFF or not n & 0x80000000:
                break
            c = n & 0x7FFFFFFF
        return out

    def _read_chain(self, start):
        return b"".join(self._cluster(self.alloc_off + c) for c in self.chain(start))

    # --- ディレクトリ ---
    def listdir(self, entry=None):
        start = self.root if entry is None else entry.cluster
        raw = self._read_chain(start)
        ents = [raw[i:i + 512] for i in range(0, len(raw), 512)]
        n = struct.unpack_from("<I", ents[0], 4)[0] if entry is None else entry.length
        return [Entry(e, entry) for e in ents[:n]]

    def find_dir(self, name):
        for e in self.listdir():
            if e.name == name and e.is_dir:
                return e
        return None

    def find_file(self, dirname, fname):
        d = self.find_dir(dirname)
        if d is None:
            return None
        for e in self.listdir(d):
            if e.name == fname and e.is_file:
                return e
        return None

    def read_file(self, entry):
        return self._read_chain(entry.cluster)[:entry.length]

    def write_file(self, entry, content):
        if len(content) != entry.length:
            raise ValueError("ファイルサイズが変わる書き込みは未対応です")
        pad = content + b"\0" * (-len(content) % self.csize)
        old = self._read_chain(entry.cluster)
        for k, c in enumerate(self.chain(entry.cluster)):
            new = pad[k * self.csize:(k + 1) * self.csize]
            if new != old[k * self.csize:(k + 1) * self.csize]:
                self._write_cluster(self.alloc_off + c, new)

    def save(self, path=None):
        if self.stride == 528:
            for p in self.dirty_pages:
                o = p * 528
                page = self.data[o:o + PAGE]
                self.data[o + PAGE:o + PAGE + 12] = b"".join(
                    ecc128(page[j * 128:(j + 1) * 128]) for j in range(4))
        self.dirty_pages.clear()
        with open(path or self.path, "wb") as f:
            f.write(self.data)
