"""99zo: 572 cut-pass 路由 + 门判定 + 标注图生成（99zn 收集之后）。

对齐设计（PLAN-OCR-PIPELINE §4.2 的完整实现）：
  DP1: v6 框字符序列 <-> 该行全部切格的标签序列（顺序对齐，允许增删；
       格栅与 OCR 框的行内漂移不影响顺序对齐）
  DP2: 行级 VLM 字符序列 <-> v6 框字符序列 → 每框的 VLM 读数
  路由（所有者 §12 保守规则）:
    auto        label==box==行VLM 且 v5 不反对
    label_fix   label≠box 但 box==行VLM（双证同向 → 人盖确认章）
    arbitration 其余（无框/孤议/三方相异）
门（121 真值格）：verified precision ≥99%（strict）、仲裁类占比、canary 3/3、回归 0。
"""
from __future__ import annotations
import json, csv, sys
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
W = ROOT / 'work-c'
CJK = lambda ch: '\u3400' <= ch <= '\u9fff' or '\uf900' <= ch <= '\ufaff'
VAR = {'来': '來', '剑': '劍'}
canon = lambda c: VAR.get(c, c)

def dp_align(seq_a, seq_b):
    n, m = len(seq_a), len(seq_b)
    GAP = -2.0
    S = [[0.0] * (m + 1) for _ in range(n + 1)]
    P = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1): S[i][0] = S[i-1][0] + GAP; P[i][0] = 2
    for j in range(1, m + 1): S[0][j] = S[0][j-1] + GAP; P[0][j] = 3
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            sub = S[i-1][j-1] + (2.0 if seq_a[i-1] == seq_b[j-1] else -1.0)
            up, left = S[i-1][j] + GAP, S[i][j-1] + GAP
            best = max(sub, up, left); S[i][j] = best
            P[i][j] = 1 if best == sub else (2 if best == up else 3)
    pairs = []; i, j = n, m
    while i > 0 or j > 0:
        p = P[i][j] if i > 0 and j > 0 else (2 if i > 0 else 3)
        if p == 1: pairs.append((i-1, j-1)); i -= 1; j -= 1
        elif p == 2: pairs.append((i-1, None)); i -= 1
        else: pairs.append((None, j-1)); j -= 1
    return pairs[::-1]

def main():
    probe_all = {r['file']: r for r in json.load(open(W / 'cellbox_probe.json'))['rows']}
    cut_pass = [r for r in probe_all.values() if r.get('cut_status') == 'pass']
    cells = {}
    for l in open(W / 'cells.jsonl'):
        d = json.loads(l); cells[d['file']] = d
    single = {json.loads(l)['file']: json.loads(l) for l in open(W / 'preview/99zn_single.jsonl')}
    linev = {json.loads(l)['file']: json.loads(l) for l in open(W / 'preview/99zn_line.jsonl')}
    v6boxes = json.load(open(W / 'preview/99zn_charboxes.json'))
    # 真值与 qwen 均按 file 索引
    truth = {}
    tr = {r['sid']: r['owner_reading'] for r in csv.DictReader(open(W / 'preview/oracle100_owner_transcript.csv'))}
    for kind, src in (('oracle100', 'oracle100_key.json'), ('calib28', 'calib28_key.json')):
        for c in json.load(open(W / 'preview' / src))['cells']:
            t = tr.get(c['sid'])
            if t: truth[c['file']] = t
    for c in json.load(open(W / 'calib28_verdicts.json'))['cells']:
        if c.get('ink_truth'): truth[c['file']] = c['ink_truth']
    qwen_raw = {json.loads(l)['sid']: json.loads(l) for l in open(W / 'preview/oracle_calib_qwen_line.jsonl')}
    qwen = {}
    for kind, src in (('oracle100', 'oracle100_key.json'), ('calib28', 'calib28_key.json')):
        for c in json.load(open(W / 'preview' / src))['cells']:
            if f'{kind}:{c["sid"]}' in qwen_raw: qwen[c['file']] = qwen_raw[f'{kind}:{c["sid"]}']

    # 行集合：572 覆盖的 (key, col, li)
    line_keys = set()
    for r in cut_pass:
        c = cells.get(r['file'])
        if c: line_keys.add((c['key'], c['col'], c['li']))
    # 该行全部切格（cells.jsonl 全量一遍扫描）
    lines = defaultdict(list)
    for l in open(W / 'cells.jsonl'):
        d = json.loads(l)
        lk = (d.get('key'), d.get('col'), d.get('li'))
        if lk in line_keys: lines[lk].append(d)
    for lk in lines: lines[lk].sort(key=lambda d: d['sub'])
    print(f'lines: {len(lines)}  cells in lines: {sum(len(v) for v in lines.values())}', flush=True)

    rows = []
    for lk, group in sorted(lines.items()):
        c0 = group[0]
        lx = c0['lin_xyxy']
        pb = [b2 for b2 in v6boxes.get(lk[0], [])
              if lx[1]-24 <= (b2['y0']+b2['y1'])/2 <= lx[3]+24 and lx[0]-24 <= (b2['x0']+b2['x1'])/2 <= lx[2]+24]
        pb.sort(key=lambda b2: b2['y0'])
        box_chars = [b2['ch'] for b2 in pb]
        cell_labels = [(d.get('label') or '?') for d in group]
        pairs_bc = dp_align(box_chars, cell_labels)
        box2cell = {bi: ci for bi, ci in pairs_bc if bi is not None and ci is not None}
        # 行级 VLM（任一 probe 格的 99zn 行转写即代表本行）
        vlm_seq = []
        for d in group:
            lv = linev.get(d['file'])
            if lv and lv.get('chars'): vlm_seq = lv['chars']; break
        vlm_seq = [c2 for c2 in vlm_seq if CJK(c2)]
        pairs_vb = dp_align(vlm_seq, box_chars) if vlm_seq else []
        vlm_for_box = {}
        for vi, bi in pairs_vb:
            if vi is not None and bi is not None: vlm_for_box[bi] = vlm_seq[vi]
        # qwen 行（同法）
        qwen_seq = []
        for d in group:
            q = qwen.get(d['file'])
            if q and q.get('chars'): qwen_seq = q['chars']; break
        qwen_seq = [c2 for c2 in qwen_seq if CJK(c2)]
        pairs_qb = dp_align(qwen_seq, box_chars) if qwen_seq else []
        qwen_for_box = {}
        for qi, bi in pairs_qb:
            if qi is not None and bi is not None: qwen_for_box[bi] = qwen_seq[qi]

        for gi, d in enumerate(group):
            f = d['file']; sid = f'572:{f}'
            my_boxes = [bi for bi, ci in pairs_bc if ci == gi]
            box_char = box_chars[my_boxes[0]] if my_boxes else ''
            vlm_char = vlm_for_box.get(my_boxes[0], '') if my_boxes else ''
            qwen_char = qwen_for_box.get(my_boxes[0], '') if my_boxes else ''
            pr = probe_all.get(f)
            rec = dict(sid=sid, file=f, key=lk[0], col=lk[1], li=lk[2], sub=d['sub'],
                       label=d.get('label'), n_boxes=len(pb), n_cells=len(group),
                       n_vlm=len(vlm_seq), box_char=box_char, vlm_char=vlm_char,
                       qwen_char=qwen_char, v5=(pr.get('v5', '') if pr else ''),
                       in_probe=bool(pr), cut_status=(pr.get('cut_status') if pr else ''))
            labN = canon(d.get('label')) if d.get('label') else None
            boxN = canon(box_char) if box_char else None
            lineN = canon(vlm_char) if vlm_char else None
            v5N = canon(rec['v5']) if rec['v5'] else None
            qN = canon(qwen_char) if qwen_char else None
            if labN and boxN and lineN and labN == boxN == lineN and (not v5N or v5N == labN):
                rec['route'] = 'auto'
            elif boxN and lineN and boxN == lineN and labN != boxN:
                rec['route'] = 'label_fix_double_witness'
            elif not my_boxes:
                rec['route'] = 'unassigned_box'
            else:
                rec['route'] = 'arbitration'
            if f in truth:
                rec['truth'] = truth[f]; tN = canon(truth[f])
                final_char = {'auto': d.get('label'), 'auto_qwen_override': d.get('label'),
                              'label_fix_double_witness': box_char}.get(rec['route'], '')
                rec['correct_final'] = bool(final_char) and canon(final_char) == tN
            rows.append(rec)

    json.dump(rows, open(W / 'preview' / '99zn_routed.json', 'w'), ensure_ascii=False, indent=1)
    sr = [r for r in rows if 'truth' in r]
    auto = [r for r in sr if r['route'].startswith('auto')]
    auto_ok = [r for r in auto if r.get('correct_final')]
    lfix = [r for r in rows if r['route'] == 'label_fix_double_witness']
    arb = [r for r in rows if r['route'] in ('arbitration', 'unassigned_box')]
    print(f'== 572 路由 ==  行 {len(lines)}  格 {len(rows)}（真值 {len(sr)}）')
    print(Counter(r['route'] for r in rows))
    if auto:
        print(f'verified precision (strict auto, n={len(auto)}): {len(auto_ok)}/{len(auto)} = {100*len(auto_ok)/len(auto):.1f}%')
    print(f'人工队列: label_fix {len(lfix)} + arbitration {len(arb)} = {len(lfix)+len(arb)} '
          f'({100*(len(lfix)+len(arb))/max(1,len(rows)):.1f}%)')
    canary_files = {c['file']: c['sid'] for kind in ('oracle100', 'calib28')
                    for c in json.load(open(W / f'preview/{kind}_key.json'))['cells']
                    if c['sid'] in ('R003', 'R028', 'R069', 'R072')}
    for f, csid in sorted(canary_files.items()):
        r = next((x for x in rows if x['file'] == f), None)
        if r: print(f'  canary {csid}: route={r["route"]} label={r["label"]} box={r["box_char"]} '
                    f'line={r["vlm_char"]} qwen={r["qwen_char"]}')
    # ---- 标注图（非 auto 的 probe 格）----
    outdir = W / 'preview' / 'stamp572'
    outdir.mkdir(parents=True, exist_ok=True)
    stamp = [r for r in rows if r['route'] != 'auto' and r['file'] in probe_all]
    stamp.sort(key=lambda r: (r['route'], r['file']))
    font_lab = ImageFont.truetype('/System/Library/Fonts/Songti.ttc', 30, index=1)
    font_sid = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 20)
    COLS, TILE, CROP, LBL, per = 3, 320, 280, 46, 24
    meta = []
    for si in range(0, len(stamp), per):
        chunk = stamp[si:si+per]
        rn = (len(chunk)+COLS-1)//COLS
        sheet = Image.new('L', (COLS*TILE, rn*(TILE+LBL)), 255)
        dr = ImageDraw.Draw(sheet)
        for i, r in enumerate(chunk):
            c = cells[r['file']]
            tile = Image.new('L', (CROP, CROP), 255)
            p300 = W / 'pages300' / f"{r['key']}.jpg"
            if p300.exists():
                im = cv2.imread(str(p300), cv2.IMREAD_GRAYSCALE)
                x0, y0, x1, y1 = c['x0'], c['y0'], c['x1'], c['y1']
                mx, my = int(0.25*(x1-x0)), int(0.25*(y1-y0))
                crop = im[max(0, y0-my):min(im.shape[0], y1+my), max(0, x0-mx):min(im.shape[1], x1+mx)]
                hh, ww = crop.shape
                sc = min(CROP/ww, CROP/hh, 3.0)
                crop = cv2.resize(crop, (max(1, int(ww*sc)), max(1, int(hh*sc))), interpolation=cv2.INTER_CUBIC)
                ch2, cw2 = crop.shape
                tile.paste(Image.fromarray(crop), ((CROP-cw2)//2, (CROP-ch2)//2))
            x, y = (i % COLS)*TILE, (i // COLS)*(TILE+LBL)
            sheet.paste(tile, (x+10, y))
            dr.text((x+10, y+CROP+2), f"标签:{r['label']}", fill=160, font=font_lab)
            sid_short = f'S5{si+i+1:03d}'
            dr.text((x+10+150, y+CROP+2), sid_short, fill=0, font=font_sid)
            meta.append(dict(sid_sheet=sid_short, sid=r['sid'], file=r['file'], key=r['key'],
                             label=r['label'], route=r['route']))
        sheet.save(outdir / f'S5_{si//per+1}.png')
    with open(outdir / 'stamp572_answer_template.csv', 'w') as f:
        w = csv.writer(f)
        w.writerow(['sid_sheet', 'file', 'label', 'mark(空=确认/❌=错/划线=质量差)', 'correct_char(可选)', 'note'])
        for m in meta: w.writerow([m['sid_sheet'], m['file'], m['label'], '', '', ''])
    json.dump(meta, open(outdir / 'stamp572_meta.json', 'w'), ensure_ascii=False, indent=1)
    print(f'标注图: {len(meta)} 格 -> {outdir}（{len(list(outdir.glob("*.png")))} 张）')

if __name__ == '__main__':
    main()
