"""Regenerate work/ckpt/MANIFEST.json from what is actually on disk.

Run after every training run: checkpoints get overwritten in place, so a manifest
written before a run goes stale and its sha256 entries stop matching.
"""
from __future__ import annotations

import hashlib
import json
import re as _re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CKPT_DIR = ROOT / "work" / "ckpt"
CK = ROOT / "work" / "ckpt"
_RELEASE: set[str] = set()
# 该文件已于 2026-10-24 22:05 删除（见 DATA §6.5.1），条目保留用于说明历史
CORE_EPOCHS = {50, 100, 150, 200, 300, 400, 500}


RELEASE_LIST = CK / "release_ckpts.json"   # legacy default; main() prefers <ckpt-dir>/release_ckpts.json


def _release_names(path: Path | None = None) -> set[str]:
    """Release checkpoints are declared in a small tracked file (default: inside the ckpt dir).

    Pass `--release-file` to point at `data/release_ckpts_<line>.json`; keeping it in `data/`
    survives any cleanup of `work/`, and B/C simply pass their own file (or none).
    """
    src = path or RELEASE_LIST
    if not src.exists():
        if path is not None:          # explicit path must not fail silently
            print(f"WARN        release file {src} not found; nothing marked kind=release")
        return set()
    try:
        data = json.loads(src.read_text())
        if isinstance(data, dict):
            data = data.get("release_ckpts", [])
        return {str(x) for x in data}
    except Exception as exc:
        print(f"WARN        release file {src} unreadable ({exc}); nothing marked kind=release")
        return set()


_RELEASE: set[str] = set()   # populated in main(); import must not read disk


def kind_of(name: str, rel: str | None = None) -> str:
    """Classify a checkpoint for the retention rule (owner, 2026-10-25).

    `rel` is the path relative to the checkpoint dir; release lists may name a checkpoint
    either by basename ("c_ep090.pt") or by relative path ("v1.3/c_ep090.pt"), so both match.
    """
    import re as _re
    if name in _RELEASE or (rel is not None and rel in _RELEASE):
        return "release"
    if name.endswith("_best.pt"):
        return "best"
    m = _re.search(r"_ep(\d+)\.pt$", name)
    if m:
        return "core" if int(m.group(1)) in CORE_EPOCHS else "snapshot"
    return "final"


INVALID = {"zi2zi_gan_multi_g_best.pt": "训练于 2026-10-24 05:27，用的是坏数据集"
                                       "（多实例配对 71% 目标空白），模型不可用，仅作记录"}


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt-dir", default=str(CKPT_DIR),
                    help="checkpoint directory (the B line uses work-b/ckpt)")
    ap.add_argument("--out", default="")
    ap.add_argument("--release-file", default="",
                    help="JSON with release checkpoint names (list or {release_ckpts:[...]})")
    args = ap.parse_args()
    global _RELEASE
    ck = Path(args.ckpt_dir)
    rel_path = Path(args.release_file) if args.release_file else ck / "release_ckpts.json"
    # Explicit --release-file must never fall back to the default (that would read the A
    # line's work/ckpt from a B/C run); a missing file simply means "no release marks".
    _RELEASE = _release_names(rel_path)
    out_path = Path(args.out) if args.out else ck / "MANIFEST.json"
    items = []
    for p in sorted(ck.rglob("*.pt")):
        items.append({
            "file": str(p.relative_to(ck)),
            "kind": kind_of(p.name, str(p.relative_to(ck))),
            "epoch": (int(_re.search(r"_ep(\d+)\.pt$", p.name).group(1))
                      if _re.search(r"_ep(\d+)\.pt$", p.name) else None),
            "size_mb": round(p.stat().st_size / 1e6, 1),
            "sha256_16": hashlib.sha256(p.read_bytes()).hexdigest()[:16],
            "mtime": time.strftime("%Y-%m-%d %H:%M", time.localtime(p.stat().st_mtime)),
            "status": "invalid" if p.name in INVALID else "ok",
        })
    man = {
        "note": "每次训练或覆盖检查点后必须重跑本脚本；sha256 与磁盘失配说明文件已被覆盖",
        "retention": ("保留：最终一轮 + 验证最佳轮 + 核心轮次 50/100/150/200/300/400/500…；"
                      "C 线另保留 best + ep030/050/060/070/080/090（有 100 也留）。删除前先看这里，并在 docs/DATA.md §6.5.1"
                      "（B 线：docs/DATA-B.md §6.5）登记；删完立刻重跑本脚本"),
        "invalid_reason": INVALID,
        "items": items,
    }
    tmp = out_path.with_suffix(out_path.suffix + ".tmp")
    tmp.write_text(json.dumps(man, ensure_ascii=False, indent=1))
    tmp.replace(out_path)          # atomic on the same filesystem
    print(f"{len(items)} checkpoints -> {out_path}")


if __name__ == "__main__":
    main()
