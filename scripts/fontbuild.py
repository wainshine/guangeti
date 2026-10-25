"""Assemble an OpenType/TTF font from vector glyphs."""
from __future__ import annotations

from pathlib import Path

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.reverseContourPen import ReverseContourPen

EM = 1000
VERSION = "1.5.2"  # single source of truth for the font version
OFL_TEXT = (
    "This Font Software is licensed under the SIL Open Font License, Version 1.1. "
    "This license is available with a FAQ at: https://openfontlicense.org"
)


def _contour_points(c):
    pts = [c["start"]]
    for s in c["segs"]:
        if s[0] == "L":
            pts.append((s[1], s[2]))
        else:
            pts.append((s[1], s[2]))
            pts.append((s[3], s[4]))
            pts.append((s[5], s[6]))
    return pts


def _signed_area(pts):
    a = 0.0
    for i in range(len(pts)):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % len(pts)]
        a += x0 * y1 - x1 * y0
    return a / 2.0


def _inside(pt, pts):
    x, y = pt
    inside = False
    n = len(pts)
    for i in range(n):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % n]
        if ((y0 > y) != (y1 > y)) and (x < (x1 - x0) * (y - y0) / (y1 - y0 + 1e-12) + x0):
            inside = not inside
    return inside


def _orient(contours):
    """TrueType: outer contours clockwise (negative area), holes counter-clockwise."""
    reps = [(_contour_points(c), _signed_area(_contour_points(c))) for c in contours]
    out = []
    for i, c in enumerate(contours):
        pts = reps[i][0]
        depth = 0
        for j, (p2, _) in enumerate(reps):
            if i == j:
                continue
            if _inside(pts[0], p2):
                depth += 1
        want_negative = (depth % 2 == 0)
        area = reps[i][1]
        flip = (area > 0) if want_negative else (area < 0)
        out.append((c, flip))
    return out


def build_font(glyphs: dict[str, list], out_path: Path, family: str = "GuanGe Kai",
               style: str = "Regular", version: str = VERSION,
               copyright_text: str = "", upm: int = EM) -> None:
    """glyphs: {char: [contour, ...]} in font units."""
    chars = sorted(glyphs)
    order = [".notdef"] + [f"uni{ord(ch):04X}" for ch in chars]
    fb = FontBuilder(upm, isTTF=True)
    fb.setupGlyphOrder(order)
    fb.setupCharacterMap({ord(ch): f"uni{ord(ch):04X}" for ch in chars})

    pen = TTGlyphPen(None)
    # TrueType convention: outer clockwise, hole counter-clockwise (y-up).
    outer = [(40, -120), (40, 880), (960, 880), (960, -120)]
    inner = [(100, -60), (900, -60), (900, 820), (100, 820)]
    for pts in (outer, inner):
        pen.moveTo(pts[0])
        for p in pts[1:]:
            pen.lineTo(p)
        pen.closePath()
    glyf = {".notdef": pen.glyph()}
    metrics = {".notdef": (upm, 40)}

    for ch in chars:
        gname = f"uni{ord(ch):04X}"
        contours = glyphs[ch]
        tpen = TTGlyphPen(None)
        pen = Cu2QuPen(tpen, max_err=1.0)
        xmin = ymin = 10 ** 9
        xmax = ymax = -10 ** 9
        for c, flip in _orient(contours):
            rec = RecordingPen()
            rec.moveTo(c["start"])
            for s in c["segs"]:
                if s[0] == "L":
                    rec.lineTo((s[1], s[2]))
                else:
                    rec.curveTo((s[1], s[2]), (s[3], s[4]), (s[5], s[6]))
            rec.closePath()
            if flip:
                rec.replay(ReverseContourPen(pen))
            else:
                rec.replay(pen)
            for p in _contour_points(c):
                xmin, xmax = min(xmin, p[0]), max(xmax, p[0])
                ymin, ymax = min(ymin, p[1]), max(ymax, p[1])
        glyf[gname] = tpen.glyph()
        lsb = int(xmin) if xmin < 10 ** 8 else 0
        metrics[gname] = (upm, lsb)

    fb.setupGlyf(glyf)
    fb.setupHorizontalMetrics(metrics)
    fb.setupHorizontalHeader(ascent=880, descent=-120)
    fb.setupNameTable({
        "familyName": family,
        "styleName": style,
        "uniqueFontIdentifier": f"{family} {style} {version}",
        "fullName": f"{family} {style}",
        "psName": f"{family.replace(' ', '')}-{style}",
        "version": f"Version {version}",
        "copyright": copyright_text,
        "licenseDescription": OFL_TEXT,
        "licenseInfoURL": "https://openfontlicense.org",
    })
    fb.setupOS2(sTypoAscender=880, sTypoDescender=-120, sTypoLineGap=0,
                usWinAscent=880, usWinDescent=120, sxHeight=500, sCapHeight=700,
                usWeightClass=400, usWidthClass=5, fsType=0,
                achVendID="GGKF", fsSelection=64,
                ulUnicodeRange1=1 | (1 << 28), ulCodePageRange1=(1 << 18) | (1 << 20))
    fb.setupPost(keepGlyphNames=False)
    fb.setupMaxp()
    fb.font["head"].macStyle = 0
    try:
        fb.font["head"].fontRevision = float(".".join(version.split(".")[:2]))
    except Exception:
        pass
    fb.font["head"].flags = 0b00000011
    # Reproducible builds: pin the timestamps so two rebuilds are byte-identical.
    import os as _os
    unix = int(_os.environ.get("SOURCE_DATE_EPOCH", "1792713600"))  # 2026-10-23T00:00:00Z
    stamp = unix + 2082844800  # fontTools stores seconds since 1904-01-01
    fb.font["head"].created = stamp
    fb.font["head"].modified = stamp
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fb.save(str(out_path))
