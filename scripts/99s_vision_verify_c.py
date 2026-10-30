"""Vision-LLM verification for chosen cells (OpenAI-compatible endpoint).

No key is bundled.  Set:
  VISION_API_KEY, VISION_BASE_URL (e.g. https://api.openai.com/v1), VISION_MODEL

Prompt is neutral: the expected label is NOT shown, so the answer can be compared
against our label without anchoring.  Results are cached by crop sha256.
"""
from __future__ import annotations
import argparse, base64, hashlib, json, os, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
PROMPT = """You are a paleography assistant. The image is ONE cell crop from the Ming manuscript 永樂大典.
Return ONLY JSON:
{"char":"<the single Chinese character you actually see, or empty>",
 "cut":"ok|merged|fragment|blank|other",
 "confidence":0.0-1.0,
 "note":"<brief reason>"}
Rules:
- Do not guess from context; read the ink in this crop only.
- If the crop contains two or more characters, cut="merged" and put all seen characters in char.
- If only a fragment/part is present, cut="fragment".
- If blank/no legible ink, cut="blank".
- Do not output anything except the JSON object."""


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


def call(img_b64, base, key, model, timeout=90):
    body = {
        "model": model,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": PROMPT},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64," + img_b64,
                                                  "detail": "low"}},
        ]}],
        "temperature": 0,
        "max_tokens": 80,
        "thinking": {"type": "disabled"},
    }
    req = urllib.request.Request(base.rstrip("/") + "/chat/completions",
                                 data=json.dumps(body).encode(),
                                 headers={"Authorization": "Bearer " + key,
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.load(r)
    txt = d["choices"][0]["message"]["content"].strip()
    s = txt[txt.find("{"): txt.rfind("}") + 1]
    return json.loads(s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chosen", default=str(ROOT / "work-c/exp/v3d2/chosen.jsonl"))
    ap.add_argument("--data", default=str(ROOT / "work-c/exp/v3d2"))
    ap.add_argument("--out", default=str(ROOT / "work-c/exp/v3d2/vision_verify.jsonl"))
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--cache", default=str(ROOT / "work-c/vision_cache.json"))
    args = ap.parse_args()
    key = os.environ.get("VISION_API_KEY", "")
    base = os.environ.get("VISION_BASE_URL", "")
    model = os.environ.get("VISION_MODEL", "")
    if not (key and base and model):
        sys.exit("set VISION_API_KEY / VISION_BASE_URL / VISION_MODEL first")
    cache = json.load(open(args.cache)) if Path(args.cache).exists() else {}
    rows = [json.loads(l) for l in open(args.chosen)]
    if args.limit: rows = rows[:args.limit]
    out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if out.exists():
        for l in open(out):
            try: done.add(json.loads(l)["file"])
            except Exception: pass
    todo = [r for r in rows if r["file"] not in done]
    print("todo", len(todo), "cached", len(cache), flush=True)
    lock = __import__("threading").Lock()
    def work(r):
        cp = Path(args.data) / "cells" / r["file"]
        h = sha(cp)
        if h in cache:
            return {**cache[h], "file": r["file"], "label": r["label"], "cached": True}
        img = base64.b64encode(cp.read_bytes()).decode()
        try:
            v = call(img, base, key, model)
            rec = {"file": r["file"], "label": r["label"], "vision_char": v.get("char", ""),
                   "cut": v.get("cut", ""), "confidence": v.get("confidence"),
                   "note": v.get("note", ""), "cached": False}
        except Exception as e:
            rec = {"file": r["file"], "label": r["label"], "error": str(e)[:200]}
        with lock:
            if "error" not in rec:
                cache[h] = {k: rec[k] for k in ("vision_char", "cut", "confidence", "note") if k in rec}
        return rec
    with ThreadPoolExecutor(max_workers=args.workers) as ex, open(out, "a") as f:
        for i, rec in enumerate(ex.map(work, todo)):
            f.write(json.dumps(rec, ensure_ascii=False) + "\n"); f.flush()
            if i and i % 100 == 0:
                Path(args.cache).write_text(json.dumps(cache, ensure_ascii=False))
                print("done", i, flush=True)
    Path(args.cache).write_text(json.dumps(cache, ensure_ascii=False))
    print("->", out)


if __name__ == "__main__":
    main()
