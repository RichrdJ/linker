"""Het Linker-logo in de accentkleur: als SVG voor het tabblad en als PNG voor
telefoons en geïnstalleerde apps.

De PNG's in static/ zijn getekend in drie kleuren: donkere achtergrond, het blauw
van het logo en wit voor de schakel. Elke pixel is een mengsel van donker en blauw
(rand van de tegel) of van blauw en wit (rand van de schakel). Die verhouding
houden we vast en we wisselen blauw en wit om voor de accentkleur en de bijpassende
inktkleur. Zo blijven de randen even glad, zonder extra pakketten zoals Pillow.
"""
import re
import struct
import zlib
from functools import lru_cache

DEFAULT = "#3b7ddd"
DARK = (27, 35, 46)
BLUE = (59, 125, 221)
WHITE = (255, 255, 255)

GLYPH = ("M13.5 18.5l5-5M12 15l-2.5 2.5a3.5 3.5 0 0 0 5 5L17 20"
         "M15 12l2.5-2.5a3.5 3.5 0 0 1 5 5L20 17")


def _rgb(hex_color: str):
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", hex_color or ""):
        hex_color = DEFAULT
    n = int(hex_color[1:], 16)
    return (n >> 16, (n >> 8) & 255, n & 255)


def ink_for(hex_color: str) -> str:
    """Zelfde regel als inkFor() in app.js: donkere inkt op lichte accentkleuren."""
    r, g, b = _rgb(hex_color)
    return "#1a1408" if (0.299 * r + 0.587 * g + 0.114 * b) / 255 > 0.6 else "#ffffff"


def svg(accent: str) -> str:
    r, g, b = _rgb(accent)
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
            f'<rect width="32" height="32" rx="8" fill="#{r:02x}{g:02x}{b:02x}"/>'
            f'<path d="{GLYPH}" fill="none" stroke="{ink_for(accent)}" stroke-width="2.6" stroke-linecap="round"/>'
            '</svg>')


# ---------------------------------------------------------------- PNG lezen en schrijven

def _read_rgb_png(path):
    """Leest een 8-bit RGB PNG zonder interlace (zo zijn de iconen in static/ opgeslagen)."""
    with open(path, "rb") as f:
        data = f.read()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("geen PNG")
    pos, idat, width, height = 8, b"", 0, 0
    while pos < len(data):
        length, kind = struct.unpack(">I4s", data[pos:pos + 8])
        chunk = data[pos + 8:pos + 8 + length]
        pos += 12 + length
        if kind == b"IHDR":
            width, height, depth, ctype, _, _, interlace = struct.unpack(">IIBBBBB", chunk)
            if depth != 8 or ctype != 2 or interlace:
                raise ValueError("alleen 8-bit RGB zonder interlace")
        elif kind == b"IDAT":
            idat += chunk
        elif kind == b"IEND":
            break
    raw = zlib.decompress(idat)
    bpp, stride = 3, width * 3
    rows, prev = [], bytearray(stride)
    for y in range(height):
        start = y * (stride + 1)
        ftype = raw[start]
        line = bytearray(raw[start + 1:start + 1 + stride])
        for i in range(stride):
            a = line[i - bpp] if i >= bpp else 0
            b = prev[i]
            c = prev[i - bpp] if i >= bpp else 0
            if ftype == 1:
                line[i] = (line[i] + a) & 255
            elif ftype == 2:
                line[i] = (line[i] + b) & 255
            elif ftype == 3:
                line[i] = (line[i] + ((a + b) >> 1)) & 255
            elif ftype == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pred = a if pa <= pb and pa <= pc else (b if pb <= pc else c)
                line[i] = (line[i] + pred) & 255
        rows.append(line)
        prev = line
    return width, height, rows


def _write_rgb_png(width, height, rows):
    raw = b"".join(b"\x00" + bytes(r) for r in rows)

    def chunk(kind, body):
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9))
            + chunk(b"IEND", b""))


# ---------------------------------------------------------------- omkleuren

def _blend(p, a, b):
    """Hoe ver ligt p op de lijn van a naar b (0..1), en hoe ver ervandaan."""
    d = [b[i] - a[i] for i in range(3)]
    t = sum((p[i] - a[i]) * d[i] for i in range(3)) / sum(x * x for x in d)
    t = min(1.0, max(0.0, t))
    off = sum((p[i] - (a[i] + d[i] * t)) ** 2 for i in range(3))
    return t, off


def _mix(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


@lru_cache(maxsize=8)
def _recolor(path, accent):
    width, height, rows = _read_rgb_png(path)
    acc, ink = _rgb(accent), _rgb(ink_for(accent))
    if acc == BLUE:
        return _write_rgb_png(width, height, rows)
    cache = {}
    for line in rows:
        for x in range(0, len(line), 3):
            p = (line[x], line[x + 1], line[x + 2])
            new = cache.get(p)
            if new is None:
                t1, off1 = _blend(p, DARK, BLUE)     # rand van de tegel
                t2, off2 = _blend(p, BLUE, WHITE)    # rand van de schakel
                new = _mix(DARK, acc, t1) if off1 <= off2 else _mix(acc, ink, t2)
                cache[p] = new
            line[x:x + 3] = bytes(new)
    return _write_rgb_png(width, height, rows)


def png(path: str, accent: str) -> bytes:
    r, g, b = _rgb(accent)
    return _recolor(path, f"#{r:02x}{g:02x}{b:02x}")
