"""Fresh PP-OCRv5 per-character boxes for 99zf pages (300dpi coords)."""
from __future__ import annotations
import json, collections
from pathlib import Path
import cv2
from importlib.machinery import SourceFileLoader
ROOT=Path(__file__).resolve().parents[1]; W=ROOT/'work-c'
ocr=SourceFileLoader('ocr',str(ROOT/'scripts/92_ocr_c.py')).load_module()

def main():
    e=ocr.get_engine('v5'); rows=json.load(open(W/'preview/99zf_report.json'))
    keys=sorted({r['key'] if 'key' in r else None for r in rows if r.get('file')})
    # report lacks key; derive from file map
    cells={}
    for l in open(W/'cells.jsonl'):
        r=json.loads(l); cells[r['file']]=r
    keys=sorted({cells[r['file']]['key'] for r in rows if r.get('file') in cells})
    cache={}
    for i,k in enumerate(keys):
        p=W/'pages150'/f'{k}.jpg'
        if not p.exists(): continue
        im=cv2.imread(str(p)); rr=e(im,return_word_box=True,return_single_char_box=True)
        out=[]
        for line in (rr.word_results or []):
            for ch,sc,poly in line:
                if not ch: continue
                xs=[a[0] for a in poly]; ys=[a[1] for a in poly]
                out.append({'ch':ch,'conf':float(sc),'x0':min(xs)*2,'y0':min(ys)*2,'x1':max(xs)*2,'y1':max(ys)*2})
        cache[k]=out
        if (i+1)%20==0: print('pages',i+1,'/',len(keys),flush=True)
    json.dump(cache,open(W/'preview/99zf_v5_charboxes.json','w'),ensure_ascii=False)
    print('wrote',len(cache))
if __name__=='__main__': main()
