"""Single source of truth for the non-CJK codepoints every GuanGeKai line ships.

Why a module: A/B/C each build the font through a different path (A/C via
13_extend_punct.py, B via 62_build_full_b.py), and until now the list lived in
those files.  If one line edits it, the others silently diverge.  Import this
instead; `verify()` is what 83-style cross-line checks call.

Dropped on purpose: U+201C/U+201D (curly double quotes).  WenKai's are 350/1000
em wide, so they glue to the neighbouring hanzi in CJK text; the corner quotes
「」『』 (already in the set) are the ones Chinese body text actually uses.
"""
from __future__ import annotations

SPACE = [0x0020, 0x3000]
DIGITS_HALF = list(range(0x30, 0x3A))
DIGITS_FULL = list(range(0xFF10, 0xFF1A))
PUNCT = [
    0x3001, 0x3002,                    # 、。
    0xFF0C, 0xFF1B, 0xFF1A, 0xFF1F, 0xFF01,   # ，；：？！
    0x300C, 0x300D, 0x300E, 0x300F,    # 「」『』
    0xFF08, 0xFF09, 0x300A, 0x300B, 0x3008, 0x3009,  # （）《》〈〉
    0x2014, 0x2026, 0x00B7,            # — … ·
]

CHARS = SPACE + DIGITS_HALF + DIGITS_FULL + PUNCT
CHARSET = frozenset(CHARS)
REMOVED = (0x201C, 0x201D)             # legacy: half-width curly quotes
EXPECTED_CMAP = 20992 + len(CHARS)     # 20,992 CJK + this set


def verify(cmap) -> list[str]:
    """Return a list of human-readable problems; empty means OK."""
    problems = [f"缺 U+{cp:04X}" for cp in CHARS if cp not in cmap]
    for cp in REMOVED:
        if cp in cmap:
            problems.append(f"残留 U+{cp:04X}（半角弯引号，应删）")
    if len(cmap) != EXPECTED_CMAP:
        problems.append(f"cmap {len(cmap)} != {EXPECTED_CMAP}")
    return problems
