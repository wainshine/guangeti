"""99zs: 确认章/仲裁标注图生成（human 队列 → 印标签的 contact sheets）。

输入  : work-c/preview/geom_rescore_v5fix.json + work-c/pages300 + cells.jsonl
输出  : work-c/preview/stamp_sheets/{LF,AR}_N.png + stamp_meta_v2.json + stamp_answer_template_v2.csv
字体  : 仓库内自由字体 NotoSerifSC-Light.otf / SourceHanSansCN-Regular.otf（OFL）；
        不再使用 macOS Songti/Helvetica。
语义  : LF=确认章（label≠box，vlm+box 同证）❌=标签错→应用双证字；
        AR=仲裁 ❌=标签错（写 correct_char 或降 GAN/ribbon）；划线=图质量差。
"""

import json, os, csv
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import cv2
W = Path('/Users/wainshine/newAI/guangeti/work-c')
g = json.load(open(W/'preview/geom_rescore_v5fix.json'))
cells = {}
for l in open(W/'cells.jsonl'):
    d = json.loads(l); cells[d['file']] = d
# 人工队列 = route 非 auto 的全部
queue = [r for r in g if r.get('route') not in (None, 'auto_strict') and r.get('file') in cells]
print('human queue:', len(queue))
from collections import Counter
print(Counter(r['route'] for r in queue))
outdir = W/'preview/stamp_sheets_v2'  # 永不覆盖：owner 标注过的目录一律不动
outdir.mkdir(parents=True, exist_ok=True)
font_lab = ImageFont.truetype(str(W.parent / 'data' / 'base' / 'NotoSerifSC-Light.otf'), 30)
def _renders(ff, ch):
    im = Image.new('L', (40, 40), 255)
    ImageDraw.Draw(im).text((5, 2), ch, fill=0, font=ff)
    return sum(1 for p in im.getdata() if p < 128) > 3
font_sid = ImageFont.truetype(str(W.parent / 'data' / 'base' / 'SourceHanSansCN-Regular.otf'), 20)
TILE, CROP, LBL = 320, 280, 46
COLS = 3
def build(kind_name, rows, prefix):
    rows = [r for r in rows if r['file'] in cells]
    ns = 0
    meta = []
    per = 24
    for si in range(0, len(rows), per):
        chunk = rows[si:si+per]
        rn = (len(chunk)+COLS-1)//COLS
        sheet = Image.new('L', (COLS*TILE, rn*(TILE+LBL)), 255)
        dr = ImageDraw.Draw(sheet)
        for i, r in enumerate(chunk):
            c = cells.get(r['file'])
            tile = Image.new('L', (CROP, CROP), 255)
            p300 = W/'pages300'/f"{c['key']}.jpg"
            if c and p300.exists():
                im = cv2.imread(str(p300), cv2.IMREAD_GRAYSCALE)
                x0,y0,x1,y1 = c['x0'], c['y0'], c['x1'], c['y1']
                mx, my = int(0.25*(x1-x0)), int(0.25*(y1-y0))
                crop = im[max(0,y0-my):min(im.shape[0],y1+my), max(0,x0-mx):min(im.shape[1],x1+mx)]
                hh, ww = crop.shape
                sc = min(CROP/ww, CROP/hh, 3.0)
                crop = cv2.resize(crop, (max(1,int(ww*sc)), max(1,int(hh*sc))), interpolation=cv2.INTER_CUBIC)
                ch2, cw2 = crop.shape
                tile.paste(Image.fromarray(crop), ((CROP-cw2)//2, (CROP-ch2)//2))
            sid_short = f"{prefix}{si+i+1:02d}"
            assert _renders(font_lab, r['label']), f'glyph missing: {r["label"]}'
            x, y = (i%COLS)*TILE, (i//COLS)*(TILE+LBL)
            sheet.paste(tile, (x+10, y))
            color = 0
            dr.text((x+10, y+CROP+2), f"标签:{r['label']}", fill=160, font=font_lab)
            dr.text((x+10+140, y+CROP+2), sid_short, fill=0, font=font_sid)
            meta.append(dict(sid_sheet=sid_short, sid=r['sid'], file=r['file'], key=c['key'],
                             label=r['label'], route=r.get('route',''), truth=(r.get('truth') or '')))
        sheet.save(outdir/f'{prefix}_{ns+1}.png')
        ns += 1
    return meta
m1 = build('label_fix', [r for r in queue if r['route']=='human_label_fix'], 'LF')
m2 = build('arbit', [r for r in queue if r['route']!='human_label_fix'], 'AR')
meta = m1 + m2
with open(outdir/'stamp_meta_v2.json','w') as f:
    json.dump(meta, f, ensure_ascii=False, indent=1)
with open(outdir/'stamp_answer_template_v2.csv','w') as f:
    w = csv.writer(f)
    w.writerow(['sid_sheet','file','label','mark(空=确认/❌=错/划线=质量差)','correct_char(可选)','note'])
    for m in meta:
        w.writerow([m['sid_sheet'], m['file'], m['label'], '', '', ''])
print('sheets:', len(list(outdir.glob('*.png'))), 'meta:', len(meta))
print('outdir:', outdir)
