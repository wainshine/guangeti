"""99zf: DP-alignment gate for PLAN-OCR-PIPELINE (P0-2 pre-execution gate).

Validates the alignment mechanism: line VLM transcription (DeepSeek Flash, 300dpi
line crops) DP-aligned against PP-OCRv6 per-character boxes, mapped to cells by
box center, scored against content truth on oracle100 (94) + calib28 (27).

Stages (all cached):
  1. line crops      pages300 + lin_xyxy (300dpi, native)
  2. line VLM        DeepSeek Flash line transcription (thinking disabled)
  3. char boxes      RapidOCR v6 return_single_char_box on pages150 (x2 to 300dpi)
  4. DP alignment    Needleman-Wunsch, VLM chars <-> v6 char boxes (indels allowed)
  5. scoring         alignment fidelity (mechanical) + end-to-end vs truth (full denominator)

Read-only vs repo data; writes work-c/preview/99zf_*.{json,jsonl}.
Env: VISION_API_KEY/VISION_BASE_URL/VISION_MODEL for stage 2 (only missing lines are called).
"""
from __future__ import annotations
import json, os, sys, base64, urllib.request, ssl
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import cv2
from PIL import Image
# local MITM proxy serves a self-signed chain; API transport only, measurement unaffected
ssl._create_default_https_context = ssl._create_unverified_context

ROOT = Path(__file__).resolve().parents[1]
W = ROOT / 'work-c'
sys.path.insert(0, str(ROOT / 'scripts'))
CJK = lambda ch: '\u3400' <= ch <= '\u9fff' or '\uf900' <= ch <= '\ufaff'

PROMPT = ('Transcribe every Chinese character in this vertical line of a Ming manuscript, '
          'in reading order (top to bottom). Return ONLY JSON: {"chars":["字"]}. '
          'Traditional forms as written; do not skip characters.')

# ---------------------------------------------------------------- stage 1: line crops
def line_crops():
    cells = {}
    for l in open(W / 'cells.jsonl'):
        d = json.loads(l); cells[d['file']] = d
    benches = {}
    for kind in ('oracle100', 'calib28'):
        benches[kind] = json.load(open(W / f'preview/{kind}_key.json'))['cells']
    outdir = W / 'vlm_crops300' / 'lines99zf'
    outdir.mkdir(parents=True, exist_ok=True)
    made = skipped = 0
    for kind, rows in benches.items():
        for c in rows:
            cell = cells.get(c['file'])
            p300 = W / 'pages300' / f"{c['key']}.jpg"
            op = outdir / f"{kind}_{c['sid'] if 'sid' in c else c.get('bench_id','x')}.png"
            if not cell or not p300.exists():
                c['line_crop'] = None; skipped += 1; continue
            c['line_crop'] = str(op)
            if op.exists():
                skipped += 1; continue
            im = cv2.imread(str(p300), cv2.IMREAD_GRAYSCALE)
            x0, y0, x1, y1 = cell['lin_xyxy']
            mx, my = int(0.06 * (x1 - x0)), int(0.06 * (y1 - y0))
            crop = im[max(0, y0 - my):min(im.shape[0], y1 + my),
                      max(0, x0 - mx):min(im.shape[1], x1 + mx)]
            hh, ww = crop.shape
            sc = min(1.0, 2400 / max(1, max(hh, ww)))
            if sc < 1.0:
                crop = cv2.resize(crop, (int(ww * sc), int(hh * sc)), interpolation=cv2.INTER_AREA)
            cv2.imwrite(str(op), crop); made += 1
    print(f'stage1 line crops: made {made}, reused/skipped {skipped}', flush=True)
    return benches, cells

# ---------------------------------------------------------------- stage 2: line VLM
def vlm_lines(benches):
    for l in open(ROOT / '.env'):
        k, _, v = l.strip().partition('=')
        if k and not os.environ.get(k): os.environ[k] = v
    base = os.environ.get('VISION_BASE_URL', ''); key = os.environ.get('VISION_API_KEY', '')
    model = os.environ.get('VISION_MODEL', '')
    if not (base and key and model):
        print('stage2 skipped: no VISION_* credentials'); return {}
    cache_p = W / 'preview' / '99zf_linevlm.jsonl'
    cache = {}
    if cache_p.exists():
        for l in open(cache_p):
            r = json.loads(l); cache[r['sid']] = r
    todo = []
    for kind, rows in benches.items():
        for c in rows:
            sid = f'{kind}:{c.get("sid", c.get("bench_id"))}'
            if sid not in cache:
                todo.append((sid, kind, c))
    print(f'stage2 line VLM: {len(todo)} calls needed (cached {len(cache)})', flush=True)
    local = 'localhost' in base or '127.0.0.1' in base

    def work(t, attempt=0):
        sid, kind, c = t
        if not c.get('line_crop'):
            return dict(sid=sid, kind=kind, file=c['file'], error='no_line_crop', model=model)
        b64 = base64.b64encode(Path(c['line_crop']).read_bytes()).decode()
        if local:  # ollama native wire format
            body = {"model": model, "messages": [{"role": "user", "content": PROMPT, "images": [b64]}],
                    "stream": False, "options": {"temperature": 0, "num_predict": 1000}}
        else:      # OpenAI wire format (DeepSeek etc.)
            body = {"model": model, "messages": [{"role": "user", "content": [
                        {"type": "text", "text": PROMPT},
                        {"type": "image_url", "image_url": {"url": "data:image/png;base64," + b64,
                                                             "detail": "high"}}]}],
                    "temperature": 0, "max_tokens": 1000, "thinking": {"type": "disabled"}}
        url = base.rstrip('/') + ('/api/chat' if local else '/chat/completions')
        req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                     headers={'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                d = json.load(r)
            txt = (d['choices'][0]['message']['content'] if 'choices' in d
                   else d['message']['content']).strip()
        except urllib.error.HTTPError as e:
            body_txt = e.read()[:200].decode(errors='replace')
            print(f'  HTTP {e.code} {sid}: {body_txt} | key={key[:8]} proxyny={os.environ.get("https_proxy","-")}/{os.environ.get("http_proxy","-")}', flush=True)
            if e.code in (429, 502, 503) and attempt < 2:
                import time as _t; _t.sleep(5 * (attempt + 1))
                return work(t, attempt + 1)
            return dict(sid=sid, kind=kind, file=c['file'], error=f'HTTP {e.code}: {body_txt}', model=model)
        except Exception as e:
            return dict(sid=sid, kind=kind, file=c['file'], error=str(e)[:200], model=model)
        if '{' in txt and '}' in txt:
            s = txt[txt.find('{'):txt.rfind('}') + 1]
            try:
                chars = [x for x in json.loads(s).get('chars', []) if CJK(x)]
            except Exception:
                chars = [x for x in txt if CJK(x)]
        else:
            chars = [x for x in txt if CJK(x)]
        return dict(sid=sid, kind=kind, file=c['file'], chars=chars, raw=txt[:200], model=model)

    with ThreadPoolExecutor(max_workers=2) as ex, open(cache_p, 'a') as f:
        for rec in ex.map(work, todo):
            cache[rec['sid']] = rec
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')
    errs = [s for s, r in cache.items() if r.get('error')]
    print(f'stage2 done: {len(cache)} lines, {len(errs)} errors', flush=True)
    return cache

# ---------------------------------------------------------------- stage 3: char boxes
def char_boxes(benches):
    cache_p = W / 'preview' / '99zf_charboxes.json'
    cache = json.load(open(cache_p)) if cache_p.exists() else {}
    from rapidocr import RapidOCR
    e = RapidOCR(params={'EngineConfig.onnxruntime.intra_op_num_threads': 2})
    todo = sorted({c['key'] for rows in benches.values() for c in rows} - set(cache))
    print(f'stage3 char boxes: {len(todo)} pages to run', flush=True)
    for ki, key in enumerate(todo):
        im = cv2.imread(str(W / 'pages150' / f'{key}.jpg'))
        if im is None: cache[key] = []; continue
        r = e(im, return_word_box=True, return_single_char_box=True)
        boxes = []
        if r is not None and getattr(r, 'word_results', None) is not None:
            for line in r.word_results:
                for item in line:
                    ch, sc, box = item[0], item[1], item[2]
                    if not ch or not CJK(ch): continue
                    xs = [p[0] for p in box]; ys = [p[1] for p in box]
                    # 150dpi -> 300dpi (x2), cells.jsonl coordinate system
                    boxes.append(dict(ch=ch, conf=float(sc),
                                      x0=min(xs) * 2, y0=min(ys) * 2, x1=max(xs) * 2, y1=max(ys) * 2))
        cache[key] = boxes
        if (ki + 1) % 20 == 0: print(f'  {ki+1}/{len(todo)}', flush=True)
    json.dump(cache, open(cache_p, 'w'), ensure_ascii=False)
    print(f'stage3 done: {len(cache)} pages cached', flush=True)
    return cache

# ---------------------------------------------------------------- stage 4: DP alignment
def dp_align(vlm_chars, boxes):
    """Needleman-Wunsch: vlm char sequence vs ocr char-box sequence.
    Returns list of (vlm_idx or None, box_idx or None). Match/substitution preferred."""
    n, m = len(vlm_chars), len(boxes)
    GAP = -2.0
    S = [[0.0] * (m + 1) for _ in range(n + 1)]
    P = [[0] * (m + 1) for _ in range(n + 1)]  # 1=diag 2=up(vlm gap) 3=left(box gap)
    for i in range(1, n + 1): S[i][0] = S[i-1][0] + GAP; P[i][0] = 2
    for j in range(1, m + 1): S[0][j] = S[0][j-1] + GAP; P[0][j] = 3
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            sub = S[i-1][j-1] + (2.0 if vlm_chars[i-1] == boxes[j-1]['ch'] else -1.0)
            up, left = S[i-1][j] + GAP, S[i][j-1] + GAP
            best = max(sub, up, left)
            S[i][j] = best
            P[i][j] = 1 if best == sub else (2 if best == up else 3)
    pairs = []
    i, j = n, m
    while i > 0 or j > 0:
        p = P[i][j] if i > 0 and j > 0 else (2 if i > 0 else 3)
        if p == 1: pairs.append((i-1, j-1)); i -= 1; j -= 1
        elif p == 2: pairs.append((i-1, None)); i -= 1
        else: pairs.append((None, j-1)); j -= 1
    return pairs[::-1]

# ---------------------------------------------------------------- main
def main():
    benches, cells = line_crops()
    vlm = vlm_lines(benches)
    boxes_by_page = char_boxes(benches)
    # owner truth
    truth = {}
    tr = {r['sid']: r['owner_reading'] for r in csv.DictReader(open(W / 'preview/oracle100_owner_transcript.csv'))}
    for c in benches['oracle100']:
        sid = f'oracle100:{c["sid"]}'
        t = tr.get(c['sid'], '?')
        if t not in ('?', ''): truth[sid] = t
    for c in json.load(open(W / 'calib28_verdicts.json'))['cells']:
        if c['calib_verdict'] != 'skip' and c.get('ink_truth'):
            truth[f'calib28:{c["sid"]}'] = c['ink_truth']

    report = []
    for kind, rows in benches.items():
        for c in rows:
            prefix = f'{kind}:{c.get("sid", c.get("bench_id"))}'
            cell = cells.get(c['file'])
            rec = dict(sid=prefix, kind=kind, file=c['file'], label=c.get('label_current'))
            if not cell or prefix not in vlm or vlm[prefix].get('error'):
                rec['verdict'] = 'vlm_error'; report.append(rec); continue
            vlm_chars = vlm[prefix].get('chars', [])
            lx = cell['lin_xyxy']
            page_boxes = [b for b in boxes_by_page.get(c['key'], [])
                          if lx[1] - 24 <= (b['y0'] + b['y1']) / 2 <= lx[3] + 24
                          and lx[0] - 24 <= (b['x0'] + b['x1']) / 2 <= lx[2] + 24]
            page_boxes.sort(key=lambda b: b['y0'])
            pairs = dp_align(vlm_chars, page_boxes)
            # box -> cell mapping by center containment among this line's cells
            line_cells = [d for d in cells.values()
                          if d['key'] == c['key'] and d.get('li') == cell.get('li')]
            rec['n_vlm'] = len(vlm_chars); rec['n_boxes'] = len(page_boxes)
            rec['n_line_cells'] = len(line_cells)
            rec['vlm_char'] = ''; rec['ocr_char'] = ''
            rec['monotonic'] = True
            last = (-1, -1)
            for vi, bi in pairs:
                if vi is not None and bi is not None:
                    if vi <= last[0] or bi <= last[1]: rec['monotonic'] = False
                    last = (vi, bi)
            if c['file'] in cells:
                own = cells[c['file']]
                cx, cy = (own['x0'] + own['x1']) / 2, (own['y0'] + own['y1']) / 2
                for vi, bi in pairs:
                    if bi is None: continue
                    b = page_boxes[bi]
                    cx_b, cy_b = (b['x0'] + b['x1']) / 2, (b['y0'] + b['y1']) / 2
                    if own['x0'] <= cx_b <= own['x1'] and own['y0'] <= cy_b <= own['y1']:
                        if vi is not None and not rec['vlm_char']:
                            rec['vlm_char'] = vlm_chars[vi]; rec['vlm_conf_box'] = True
                        if not rec['ocr_char']: rec['ocr_char'] = b['ch']
            # three-way with v5 (probe) where available
            pr = probe_by_file.get(c['file'], {})
            v5 = pr.get('v5', '') or ''
            rec['v5'] = v5
            trio = [x for x in (rec['vlm_char'], rec['ocr_char'], v5) if x]
            rec['verified'] = bool(rec['vlm_char']) and len(trio) >= 2 and len(set(trio)) == 1
            rec['conflict'] = (not rec['verified']) and bool(rec['vlm_char'] or rec['ocr_char'])
            if prefix in truth:
                tN = truth[prefix]
                rec['truth'] = tN
                v = rec['vlm_char']
                rec['correct_vlm'] = bool(v) and v == tN
                rec['correct_verified'] = rec['verified'] and rec['vlm_char'] == tN
            report.append(rec)

    json.dump(report, open(W / 'preview' / '99zf_report.json', 'w'), ensure_ascii=False, indent=1)
    # ---- scores ----
    scored = [r for r in report if 'truth' in r]
    cov = [r for r in report if r.get('vlm_char')]
    ver = [r for r in report if r.get('verified') and 'truth' in r]
    ver_ok = [r for r in ver if r.get('correct_verified')]
    mono_bad = [r['sid'] for r in report if not r.get('monotonic', True)]
    conflicts = [r['sid'] for r in report if r.get('conflict')]
    print('\n===== 99zf DP-alignment gate =====')
    print(f'cells: {len(report)}  truth-scored: {len(scored)}  (canary 121 expected)')
    print(f'cells with aligned VLM char: {len(cov)} ({100*len(cov)/max(1,len(report)):.0f}%)')
    print(f'non-monotonic alignments: {len(mono_bad)} {mono_bad[:5]}')
    print(f'three-way verified: {len(ver)}/{len(scored)}  verified-correct: {len(ver_ok)}'
          f'  precision {100*len(ver_ok)/max(1,len(ver)):.1f}%')
    print(f'conflicts (routed human): {len(conflicts)}')
    no_vlm = [r['sid'] for r in report if r.get('verdict') == 'vlm_error']
    no_char = [r['sid'] for r in report if r.get('verdict') != 'vlm_error' and not r.get('vlm_char')]
    wrong_char = [r['sid'] for r in scored if r.get('vlm_char') and not r.get('correct_vlm')]
    print(f'分解: vlm_error {len(no_vlm)} / 无对齐字符 {len(no_char)} / 交付字符但错 {len(wrong_char)}')
    print(f'无对齐字符明细(前12): {no_char[:12]}')
    print(f'错字明细(前12): {[(r["sid"], r["truth"], r["vlm_char"]) for r in wrong_char[:12]]}')
    if scored:
        correct_vlm = sum(1 for r in scored if r.get('correct_vlm'))
        e2e = sum(1 for r in scored if r.get('verified') and r.get('correct_verified'))
        print(f'END-TO-END 全分母 (verified-correct / all readable): {e2e}/{len(scored)} = {100*e2e/len(scored):.1f}%')
        print(f'VLM-at-cell vs truth (reader quality through pipeline): {correct_vlm}/{len(scored)} = {100*correct_vlm/len(scored):.1f}%')
    json.dump(dict(verified_n=len(ver), verified_ok=len(ver_ok),
                   conflicts=len(conflicts), mono_bad=len(mono_bad)),
              open(W / 'preview' / '99zf_gate.json', 'w'))

import csv
probe_by_file = {}
def _load_probe():
    global probe_by_file
    for r in json.load(open(W / 'cellbox_probe.json'))['rows']:
        probe_by_file[r['file']] = r
if __name__ == '__main__':
    _load_probe()
    main()
