import sys, json, numpy as np, torch
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
ROOT=Path('/Users/wainshine/newAI/guangeti'); W=ROOT/'work-c'
sys.path.insert(0,str(ROOT/'scripts'))
import importlib.util
spec=importlib.util.spec_from_file_location('gan',ROOT/'scripts/21_train_gan.py'); gan=importlib.util.module_from_spec(spec); spec.loader.exec_module(gan)
d=np.load(W/'pairs_holdout.npz',allow_pickle=True); chars=[str(c) for c in d['chars']]
idx=np.linspace(0,len(chars)-1,16).round().astype(int).tolist()
X=torch.from_numpy(d['X'][idx].astype(np.float32)/127.5-1).unsqueeze(1).repeat(1,3,1,1)
Y=d['Y'][idx]>127
base=d['X'][idx]
# full 300 metrics
allX=torch.from_numpy(d['X'].astype(np.float32)/127.5-1).unsqueeze(1).repeat(1,3,1,1)
allY=d['Y']>127
res=[]
ckpts=[('v121',W/'ckpt/v1.2.1/c_ep090.pt'),('ep10',W/'ckpt/v1.3/c_ep010.pt'),('ep20',W/'ckpt/v1.3/c_ep020.pt'),('ep30',W/'ckpt/v1.3/c_ep030.pt'),('ep40',W/'ckpt/v1.3/c_ep040.pt'),('ep50',W/'ckpt/v1.3/c_ep050.pt'),('ep60',W/'ckpt/v1.3/c_ep060.pt'),('ep70',W/'ckpt/v1.3/c_ep070.pt'),('ep80',W/'ckpt/v1.3/c_ep080.pt')]
if (W/'ckpt/v1.3/c_best.pt').exists(): ckpts.append(('best',W/'ckpt/v1.3/c_best.pt'))
dev='mps' if torch.backends.mps.is_available() else 'cpu'
outs={}
for name,p in ckpts:
 ck=torch.load(p,map_location='cpu'); G=gan.Generator(); G.load_state_dict(ck['G']); G.to(dev); G.eval()
 with torch.no_grad():
  y=G(X.to(dev)).cpu().numpy()[:,0]
  ya=[]
  for i in range(0,len(allX),32):
   ya.append(G(allX[i:i+32].to(dev)).cpu().numpy()[:,0])
  ya=np.concatenate(ya)
 outs[name]=y
 del G
 dice=[]
 for k in range(len(ya)):
  pr=ya[k]>0; tr=allY[k]>0; dice.append(2*(pr&tr).sum()/max(1,pr.sum()+tr.sum()))
 ink=float((ya>0).sum()/max(1,(allY>0).sum()))
 res.append({'name':name,'epoch':int(ck.get('epoch',0)),'valDice':float(np.mean(dice)),'ink_ratio':ink})
 print(name,res[-1],flush=True)
# draw
S=100; left=62; top=26; ncol=len(idx); nrow=2+len(ckpts)
im=Image.new('RGB',(left+ncol*S, top+nrow*(S+22)+130),(255,255,255)); dr=ImageDraw.Draw(im)
font=ImageFont.truetype(str(ROOT/'data/base/LXGWWenKai-Regular.ttf'),14); small=ImageFont.truetype(str(ROOT/'data/base/LXGWWenKai-Regular.ttf'),11)
def put(a,x,y): im.paste(Image.fromarray(np.clip((a+1)*127.5,0,255).astype(np.uint8)).convert('L').resize((S,S)),(x,y))
for j,i in enumerate(idx):
 dr.text((left+j*S+S//2-8,4),chars[i],font=font,fill='black')
put(base[0] if False else (d['X'][idx][0].astype(np.float32)/127.5-1),left,top)
for j,i in enumerate(idx): put(d['X'][i].astype(np.float32)/127.5-1,left+j*S,top)
dr.text((2,top+S//2-6),'input',font=small,fill='black')
for r,(name,p) in enumerate(ckpts):
 y=top+(r+1)*(S+22); 
 for j in range(ncol): put(outs[name][j],left+j*S,y)
 dr.text((2,y+S//2-6),name,font=small,fill='black')
y=top+(len(ckpts)+1)*(S+22)
for j,i in enumerate(idx): put(Y[j].astype(np.float32)*2-1,left+j*S,y)
dr.text((2,y+S//2-6),'real',font=small,fill='black')
yy=y+S+30
for k,r in enumerate(res):
 dr.text((left,yy+k*18),f"{r['name']:4s} ep{r['epoch']:03d}  Dice {r['valDice']:.3f}  ink {r['ink_ratio']:.3f}",font=small,fill='black')
out=W/'preview/v13_ep_compare.png'; im.save(out); print('saved',out,im.size)
json.dump({'chars':[chars[i] for i in idx],'metrics':res},open(W/'preview/v13_ep_metrics.json','w'),ensure_ascii=False,indent=1)
