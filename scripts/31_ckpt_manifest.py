"""Regenerate work/ckpt/MANIFEST.json from what is actually on disk.

Run after every training run: checkpoints get overwritten in place, so a manifest
written before a run goes stale and its sha256 entries stop matching.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CK = ROOT / "work" / "ckpt"
INVALID = {"zi2zi_gan_multi_g_best.pt": "训练于 2026-10-24 05:27，用的是坏数据集"
                                       "（多实例配对 71% 目标空白），模型不可用，仅作记录"}


def main():
    items = []
    for p in sorted(CK.glob("*.pt")):
        items.append({
            "file": p.name,
            "size_mb": round(p.stat().st_size / 1e6, 1),
            "sha256_16": hashlib.sha256(p.read_bytes()).hexdigest()[:16],
            "mtime": time.strftime("%Y-%m-%d %H:%M", time.localtime(p.stat().st_mtime)),
            "status": "invalid" if p.name in INVALID else "ok",
        })
    man = {
        "note": "每次训练或覆盖检查点后必须重跑本脚本；sha256 与磁盘失配说明文件已被覆盖",
        "retention": "训练检查点不删；删除前先看这里并在 docs/DATA.md §6.5.1 记录",
        "invalid_reason": INVALID,
        "items": items,
    }
    (CK / "MANIFEST.json").write_text(json.dumps(man, ensure_ascii=False, indent=1))
    print(f"{len(items)} checkpoints -> {CK/'MANIFEST.json'}")


if __name__ == "__main__":
    main()
