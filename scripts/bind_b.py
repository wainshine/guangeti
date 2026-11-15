#!/usr/bin/env python3
"""Input-binding sidecar for B-line gate outputs (B-Q10).

A measurement is only valid for the exact inputs it was computed from.  Writing the font
path alone is not enough: swapping the font, the provenance or the chosen set silently
reuses a stale gate result.  Ported *idea* (not code) from the kangxizidian project's
`gate_binding.py` (MIT): every gate output gets `<out>.sha256` recording the sha256 of the
output and of every input, plus argv and the git head; reuse verifies all of them and
fails closed.

  from bind_b import write_sidecar, verify_sidecar
  write_sidecar("work-b/accept_b.json", {"font": "build/GuanGeKai-B-Regular.ttf", ...})
  ok, why = verify_sidecar("work-b/accept_b.json")
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: str | Path) -> str | None:
    p = Path(path)
    if not p.is_absolute():
        p = ROOT / p
    if not p.exists():
        return None
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_head() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                              text=True).stdout.strip()
    except Exception:
        return ""


def write_sidecar(out: str | Path, inputs: dict[str, str]) -> Path:
    """Write `<out>.sha256` next to the gate output."""
    out_p = Path(out) if Path(out).is_absolute() else ROOT / out
    side = out_p.with_suffix(out_p.suffix + ".sha256")
    payload = {
        "out": str(out_p.relative_to(ROOT)) if out_p.is_relative_to(ROOT) else str(out_p),
        "out_sha256": sha256(out_p),
        "inputs": {k: {"path": str(v), "sha256": sha256(v)} for k, v in inputs.items()},
        "script": str(Path(sys.argv[0]).name),
        "argv": sys.argv[1:],
        "git_head": _git_head(),
        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    side.write_text(json.dumps(payload, ensure_ascii=False, indent=1))
    return side


def verify_sidecar(out: str | Path) -> tuple[bool, str]:
    """True when the output and every bound input still match the recorded hashes."""
    out_p = Path(out) if Path(out).is_absolute() else ROOT / out
    side = out_p.with_suffix(out_p.suffix + ".sha256")
    if not side.exists():
        return False, f"missing sidecar {side.name}"
    try:
        d = json.loads(side.read_text())
    except Exception as e:  # noqa: BLE001
        return False, f"sidecar unreadable: {e}"
    if sha256(out_p) != d.get("out_sha256"):
        return False, "output changed since measurement"
    for name, rec in (d.get("inputs") or {}).items():
        if sha256(rec["path"]) != rec.get("sha256"):
            return False, f"input changed since measurement: {name}"
    return True, "ok"
