"""99zn: 572 cut-pass 全量收集管线（PLAN-OCR-PIPELINE §15 的数据侧）。

S1  pages300 渲染（缺页补齐，4 workers）
S2  v6 字符框（return_single_char_box，缺页补齐）
S3  PaddleOCR-VL 单格读数（ollama，缺格补齐）
S4  PaddleOCR-VL 行级转写（ollama，缺行补齐）
全部落盘缓存，重跑只补缺。只读 cells/probe，不改任何现有产物。
"""
from __future__ import annotations
import json, base64, urllib.request
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
W = ROOT / 'work-c'
CORPUS = ROOT / '永乐大典美国藏本'
OLLAMA = 'http://localhost:11434'
PADDLE = 'enaval/PaddleOCR-VL-1.6-0.9B-Backup'
CJK = lambda ch: '\u3400' <= ch <= '\u9fff' or '\uf900' <= ch <= '\ufaff'
SINGLE_PROMPT = ('Read the single Chinese character in the center of the image. '
                 'Return only that character, or ? if unreadable.')
LINE_PROMPT = ('Transcribe every Chinese character in this vertical line of a Ming manuscript, '
               'in reading order (top to bottom). Return ONLY JSON: {"chars":["字"]}. '
               'Traditional forms as written; do not skip characters.')

def load_jsonl(p):
    return [json.loads(l) for l in open(p)]

def dump_jsonl(p, rows):
    open(p, 'w').write(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows))

# ---------------------------------------------------------------- 基础数据
probe_rows = json.load(open(W / 'cellbox_probe.json'))['rows']
cut_pass = [r for r in probe_rows if r.get('cut_status') == 'pass']
print(f'572 cut-pass cells: {len(cut_pass)}', flush=True)
cells = {}
for l in open(W / 'cells.jsonl'):
    d = json.loads(l); cells[d['file']] = d
stats = {json.loads(l)['key']: json.loads(l) for l in open(W / 'page_stats.jsonl')}

# ---------------------------------------------------------------- S1 pages300
def s1_render():
    out = W / 'pages300'
    keys = sorted({r['key'] for r in cut_pass})
    missing = [k for k in keys if not (out / f'{k}.jpg').exists() and k in stats and stats[k]['content'] == 'text']
    print(f'S1 pages300: {len(keys)} 需要, 缺 {len(missing)}', flush=True)
    if not missing: return
    by_book = {}
    for k in missing:
        s = stats[k]; by_book.setdefault(s['book'], []).append(k)
    def work(item):
        book, tasks = item
        pdfs = list(CORPUS.glob(book))
        if not pdfs: return f'S1 PDF missing {book}'
        doc = pymupdf.open(pdfs[0])
        for k in tasks:
            s = stats[k]
            page = doc[s['page']]
            pix = page.get_pixmap(dpi=300)
            rgb = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)[:, :, :3].copy()
            ang = s['angle']
            if abs(ang) >= 0.03:
                h, w = rgb.shape[:2]
                M = cv2.getRotationMatrix2D((w/2, h/2), ang, 1.0)
                rgb = cv2.warpAffine(rgb, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
            cv2.imwrite(str(out / f'{k}.jpg'), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 95])
        doc.close()
    with ThreadPoolExecutor(max_workers=4) as ex:
        for r in ex.map(work, list(by_book.items())):
            if r: print(r, flush=True)
    print(f'S1 done: {len(list(out.glob("*.jpg")))} pages on disk', flush=True)

# ---------------------------------------------------------------- S2 v6 char boxes
def s2_boxes():
    cache_p = W / 'preview' / '99zn_charboxes.json'
    cache = json.load(open(cache_p)) if cache_p.exists() else {}
    from rapidocr import RapidOCR
    e = RapidOCR(params={'EngineConfig.onnxruntime.intra_op_num_threads': 2})
    keys = sorted({r['key'] for r in cut_pass} - set(cache))
    print(f'S2 v6 boxes: {len(keys)} pages to run', flush=True)
    for ki, key in enumerate(keys):
        im = cv2.imread(str(W / 'pages150' / f'{key}.jpg'))
        if im is None: cache[key] = []; continue
        r = e(im, return_word_box=True, return_single_char_box=True)
        bx = []
        if r is not None and getattr(r, 'word_results', None) is not None:
            for line in r.word_results:
                for item in line:
                    ch, sc, box = item[0], item[1], item[2]
                    if not ch or not CJK(ch): continue
                    xs = [p[0] for p in box]; ys = [p[1] for p in box]
                    bx.append(dict(ch=ch, conf=float(sc), x0=min(xs)*2, y0=min(ys)*2,
                                   x1=max(xs)*2, y1=max(ys)*2))
        cache[key] = bx
        if (ki+1) % 25 == 0: print(f'  {ki+1}/{len(keys)}', flush=True)
    json.dump(cache, open(cache_p, 'w'), ensure_ascii=False)
    print(f'S2 done: {len(cache)} pages cached', flush=True)

# ---------------------------------------------------------------- S3/S4 Paddle ollama
def paddle_call(prompt, img_b64, is_line):
    if is_line:
        body = {"model": PADDLE, "messages": [{"role": "user", "content": prompt, "images": [img_b64]}],
                "stream": False, "options": {"temperature": 0, "num_predict": 1000}}
        url = OLLAMA + '/api/chat'
    else:
        body = {"model": PADDLE, "messages": [{"role": "user", "content": prompt, "images": [img_b64]}],
                "stream": False, "options": {"temperature": 0, "num_predict": 40}}
        url = OLLAMA + '/v1/chat/completions'
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=300) as r: d = json.load(r)
    txt = (d['choices'][0]['message']['content'] if 'choices' in d else d['message']['content']).strip()
    return txt

def s3_single():
    out_p = W / 'preview' / '99zn_single.jsonl'
    done = {json.loads(l)['file'] for l in open(out_p)} if out_p.exists() else set()
    todo = [r for r in cut_pass if r['file'] not in done and r['file'] in cells
            and (W / 'pages150' / f"{r['key']}.jpg").exists()]
    print(f'S3 Paddle single: {len(todo)} cells to run', flush=True)
    from PIL import Image as PImage
    def work(r):
        c = cells[r['file']]
        im = cv2.imread(str(W / 'pages150' / f"{r['key']}.jpg"), cv2.IMREAD_GRAYSCALE)
        x0, y0, x1, y1 = c['x0']//2, c['y0']//2, c['x1']//2, c['y1']//2
        mx, my = int(0.28*(x1-x0)), int(0.28*(y1-y0))
        crop = im[max(0, y0-my):min(im.shape[0], y1+my), max(0, x0-mx):min(im.shape[1], x1+mx)]
        sc = min(2.0, 384/max(1, min(crop.shape)))
        if sc > 1: crop = cv2.resize(crop, (int(crop.shape[1]*sc), int(crop.shape[0]*sc)), interpolation=cv2.INTER_CUBIC)
        ok, tmp = cv2.imencode('.png', crop)
        b64 = base64.b64encode(tmp.tobytes()).decode()
        try:
            txt = paddle_call(SINGLE_PROMPT, b64, is_line=False)
            m = CJK.search(txt) if (CJK := __import__('re').compile(r'[\u3400-\u9fff\uf900-\ufaff]')) else None
            ch = m.group(0) if m else '?'
            return dict(file=r['file'], sid=r.get('bench_id',''), vlm_char=ch, raw=txt[:80], model=PADDLE)
        except Exception as e:
            return dict(file=r['file'], sid=r.get('bench_id',''), vlm_char='', error=str(e)[:200], model=PADDLE)
    with ThreadPoolExecutor(max_workers=2) as ex, open(out_p, 'a') as f:
        for rec in ex.map(work, todo): f.write(json.dumps(rec, ensure_ascii=False) + '\n')
    print(f'S3 done -> {out_p}', flush=True)

def s4_line():
    out_p = W / 'preview' / '99zn_line.jsonl'
    done = {json.loads(l)['file'] for l in open(out_p)} if out_p.exists() else set()
    todo = [r for r in cut_pass if r['file'] not in done and r['file'] in cells
            and (W / 'pages300' / f"{r['key']}.jpg").exists()]
    print(f'S4 Paddle line: {len(todo)} lines to run', flush=True)
    def work(r):
        c = cells[r['file']]
        im = cv2.imread(str(W / 'pages300' / f"{c['key']}.jpg"), cv2.IMREAD_GRAYSCALE)
        x0, y0, x1, y1 = c['lin_xyxy']
        mx, my = int(0.06*(x1-x0)), int(0.06*(y1-y0))
        crop = im[max(0, y0-my):min(im.shape[0], y1+my), max(0, x0-mx):min(im.shape[1], x1+mx)]
        sc = min(1.0, 2400/max(1, max(crop.shape)))
        if sc < 1: crop = cv2.resize(crop, (int(crop.shape[1]*sc), int(crop.shape[0]*sc)), interpolation=cv2.INTER_AREA)
        ok, tmp = cv2.imencode('.png', crop)
        b64 = base64.b64encode(tmp.tobytes()).decode()
        try:
            txt = paddle_call(LINE_PROMPT, b64, is_line=True)
            chars = [c2 for c2 in txt if CJK(c2)]
            return dict(file=r['file'], sid=r.get('bench_id',''), chars=chars, raw=txt[:100], model=PADDLE)
        except Exception as e:
            return dict(file=r['file'], sid=r.get('bench_id',''), error=str(e)[:200], model=PADDLE)
    with ThreadPoolExecutor(max_workers=2) as ex, open(out_p, 'a') as f:
        for rec in ex.map(work, todo): f.write(json.dumps(rec, ensure_ascii=False) + '\n')
    print(f'S4 done -> {out_p}', flush=True)

if __name__ == '__main__':
    import pymupdf, re
    import importlib
    s1_render()
    s2_boxes()
    s3_single()
    s4_line()
    print('ALL STAGES DONE', flush=True)
