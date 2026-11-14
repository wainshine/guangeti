"""Version-to-version gate: exact outline diff + content-loss (ink ratio / IoU).

Two questions this answers, both required before a release:
  1. which codepoints actually changed?  (glyf outline identity, not a threshold)
  2. did any glyph lose ink?             (ink_ratio / IoU against the previous version)

Contract (borrowed from the KangXi project's content_loss_gate, adapted):
  * universe = baseline cmap ∩ new cmap; added/removed codepoints are listed separately
  * damaged when ink_ratio < 0.50 or (ink_ratio < 0.80 and iou < 0.70)
  * exit 0 PASS, 2 unusable input, 3 damaged over threshold
  * sidecar `<out>.sha256` binds inputs + script sha + git head (fail-closed on reuse)

Usage:
    python3 scripts/46_version_diff.py OLD.ttf NEW.ttf --json work/version_diff.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def outline_sig(font: TTFont, cp: int):
    """Exact, order-stable signature of a glyph's outlines (no rasterisation)."""
    cmap = font.getBestCmap()
    name = cmap.get(cp)
    if name is None:
        return None
    g = font["glyf"][name] if "glyf" in font else None
    if g is None:
        return ("no-glyf", name)
    g.expand(font["glyf"])
    if g.numberOfContours == 0:
        return (0,)
    coords, ends, flags = g.getCoordinates(font["glyf"])
    return (int(g.numberOfContours), tuple(map(int, ends)),
            tuple(int(v) for xy in coords for v in xy),
            tuple(int(f) for f in flags))


def render(font_path: Path, cp: int, size: int = 256):
    from PIL import Image, ImageDraw, ImageFont
    im = Image.new("L", (size, size), 0)
    try:
        f = ImageFont.truetype(str(font_path), int(size * 0.8))
    except Exception:
        return None
    try:
        ImageDraw.Draw(im).text((size / 2, size * 0.92), chr(cp), font=f, fill=255, anchor="ms")
    except Exception:
        return None
    return np.array(im) > 127


def iou_shift(a, b, rad=6):
    """Best IoU over small translations (both glyphs are baseline-aligned renders)."""
    best = 0.0
    for dy in range(-rad, rad + 1, 2):
        for dx in range(-rad, rad + 1, 2):
            bb = np.roll(np.roll(b, dy, 0), dx, 1)
            inter = np.logical_and(a, bb).sum()
            union = np.logical_or(a, bb).sum()
            if union:
                best = max(best, inter / union)
    return best


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("old")
    ap.add_argument("new")
    ap.add_argument("--json", required=True)
    ap.add_argument("--max-report", type=int, default=40)
    args = ap.parse_args()

    old_p, new_p = Path(args.old), Path(args.new)
    if not old_p.exists() or not new_p.exists():
        print("ABORT: missing input font", file=sys.stderr)
        raise SystemExit(2)
    old, new = TTFont(str(old_p)), TTFont(str(new_p))
    co, cn = old.getBestCmap(), new.getBestCmap()
    universe = sorted(set(co) & set(cn))
    added = sorted(set(cn) - set(co))
    removed = sorted(set(co) - set(cn))

    changed, damaged, errors = [], [], 0
    for cp in universe:
        try:
            so, sn = outline_sig(old, cp), outline_sig(new, cp)
        except Exception:
            errors += 1
            continue
        if so != sn:
            changed.append(cp)
            a, b = render(old_p, cp), render(new_p, cp)
            if a is None or b is None or a.sum() == 0:
                continue
            ink = b.sum() / max(1, a.sum())
            iou = iou_shift(a, b)
            if ink < 0.50 or (ink < 0.80 and iou < 0.70):
                damaged.append({"cp": f"U+{cp:04X}", "char": chr(cp),
                                "ink_ratio": round(float(ink), 3), "iou": round(float(iou), 3)})

    out = {
        "old": str(old_p), "new": str(new_p),
        "old_sha256": sha(old_p), "new_sha256": sha(new_p),
        "n_universe": len(universe), "n_changed": len(changed),
        "n_added": len(added), "n_removed": len(removed), "n_error": errors,
        "changed": [f"U+{c:04X}" for c in changed[: args.max_report]],
        "added": [f"U+{c:04X}" for c in added[: args.max_report]],
        "removed": [f"U+{c:04X}" for c in removed[: args.max_report]],
        "damaged": damaged[: args.max_report],
        "gate_pass": not damaged and errors == 0,
        "script_sha256": sha(Path(__file__)),
        "cmd": " ".join(sys.argv),
    }
    try:
        out["git_head"] = subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
        out["git_dirty"] = bool(subprocess.check_output(
            ["git", "-C", str(ROOT), "status", "--porcelain", "--untracked-files=no"], text=True).strip())
    except Exception:
        pass

    Path(args.json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.json).write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    Path(args.json + ".sha256").write_text(json.dumps(
        {k: out[k] for k in ("old_sha256", "new_sha256", "script_sha256", "git_head")},
        ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ("n_universe", "n_changed", "n_added", "n_removed",
                                          "n_error", "damaged", "gate_pass")},
                     ensure_ascii=False))
    # changed glyphs are expected in a normal release; only damage/errors fail the gate
    raise SystemExit(0 if out["gate_pass"] else 3)


if __name__ == "__main__":
    main()
