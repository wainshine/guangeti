"""Compare vision-LLM verification against the current chosen labels."""
from __future__ import annotations
import argparse, json, collections, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
def first(s):
    s = "".join(CJK.findall(s or ""))
    return s[:1]
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vision", default=str(ROOT / "work-c/exp/v3d2/vision_verify.jsonl"))
    ap.add_argument("--out", default=str(ROOT / "work-c/exp/v3d2/vision_compare.json"))
    args = ap.parse_args()
    rows = [json.loads(l) for l in open(args.vision)]
    out = collections.Counter(); flagged = []
    for r in rows:
        if "error" in r:
            out["error"] += 1; continue
        got = first(r.get("vision_char", "")); want = first(r.get("label", ""))
        cut = r.get("cut", "")
        if cut in ("merged", "fragment", "blank", "other"):
            out[cut] += 1; flagged.append(r); continue
        if got == want and got:
            out["match"] += 1
        else:
            out["wrong_char"] += 1; flagged.append(r)
    res = {"n": len(rows), "counts": dict(out), "flagged": len(flagged)}
    Path(args.out).write_text(json.dumps({"summary": res, "flagged": flagged}, ensure_ascii=False, indent=1))
    print(json.dumps(res, ensure_ascii=False, indent=1))
if __name__ == "__main__":
    main()
