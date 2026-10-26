"""PyTorch re-implementation of the original zi2zi recipe (kaonashi-tyc/zi2zi, Apache-2.0).

Faithful to model/unet.py:
  generator : U-Net, 64 base filters, 8 downs / 8 ups, 5x5 stride-2, BN, dropout in
              the first three decoder blocks, tanh output
  discriminator : 4 stride-2 convs (64/128/256/512) + two FC heads (real-fake, category)
  losses    : L1 * 100 + BCE(adv) + constant-loss * 15 (feature matching on the encoder)

Category embedding is dropped: we train a single font, so it carries no information.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset

ROOT = Path(__file__).resolve().parents[1]
S = 256


def conv_bn(in_c, out_c, stride=2, bn=True, k=5):
    layers = [nn.Conv2d(in_c, out_c, k, stride, k // 2, bias=not bn)]
    if bn:
        layers.append(nn.BatchNorm2d(out_c))
    return layers


def deconv_bn(in_c, out_c, k=5):
    return [nn.ConvTranspose2d(in_c, out_c, k, 2, k // 2, output_padding=1),
            nn.BatchNorm2d(out_c)]


class Generator(nn.Module):
    """U-Net: 8 stride-2 downs, 7 deconvs with skips, final 5x5 conv, tanh."""

    def __init__(self, base=64):
        super().__init__()
        f = [base, base * 2, base * 4, base * 8, base * 8, base * 8, base * 8, base * 8]
        self.e1 = nn.Sequential(nn.Conv2d(3, f[0], 5, 1, 2), nn.BatchNorm2d(f[0]), nn.LeakyReLU(0.2))
        downs = []
        cin = f[0]
        for c in f[1:]:
            downs.append(nn.Sequential(nn.Conv2d(cin, c, 5, 2, 2, bias=False),
                                       nn.BatchNorm2d(c), nn.LeakyReLU(0.2)))
            cin = c
        self.down = nn.ModuleList(downs)

        ups = []
        skips = [f[6], f[5], f[4], f[3], f[2], f[1], f[0]]     # e7..e1
        outs = [f[7], f[7], f[7], f[7], f[4], f[2], f[1]]
        cin = f[7]
        for i, (skip, oc) in enumerate(zip(skips, outs)):
            blk = [nn.ConvTranspose2d(cin, oc, 5, 2, 2, output_padding=1, bias=False),
                   nn.BatchNorm2d(oc), nn.ReLU(inplace=True)]
            if i < 3:
                blk.append(nn.Dropout(0.5))
            ups.append(nn.Sequential(*blk))
            cin = oc + skip
        self.up = nn.ModuleList(ups)
        self.out = nn.Sequential(nn.Conv2d(cin, 3, 5, 1, 2), nn.Tanh())

    def encode(self, x):
        feats = [self.e1(x)]
        h = feats[0]
        for blk in self.down:
            h = blk(h)
            feats.append(h)
        return h, feats

    def forward(self, x):
        h, feats = self.encode(x)
        skips = feats[:7][::-1]           # e7..e1 (sizes 4,8,16,32,64,128,256)
        for blk, sk in zip(self.up, skips):
            h = torch.cat([blk(h), sk], 1)
        return self.out(h)


class Discriminator(nn.Module):
    def __init__(self, base=64):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(3, base, 5, 2, 2), nn.LeakyReLU(0.2),
            *conv_bn(base, base * 2), nn.LeakyReLU(0.2),
            *conv_bn(base * 2, base * 4), nn.LeakyReLU(0.2),
            *conv_bn(base * 4, base * 8, stride=1), nn.LeakyReLU(0.2),
        )
        self.fc = nn.Linear(base * 8 * 32 * 32, 1)

    def forward(self, x):
        h = self.net(x)
        return self.fc(h.flatten(1))


class PatchDiscriminator(nn.Module):
    """PatchGAN: one score per local patch instead of one score per glyph.

    Four stride-2/1 convs over 256px give a ~46px receptive field, not the 70px of
    the original pix2pix net (which uses five layers). Smaller patches are not
    necessarily worse, but the number in the comment must match the code.
    

    A global FC head is layout-sensitive and gives weak gradients on local texture
    (终端、转折), which is exactly what the print differs in.
    """

    def __init__(self, base=64):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(6, base, 4, 2, 1), nn.LeakyReLU(0.2),
            *conv_bn(base, base * 2, stride=2), nn.LeakyReLU(0.2),
            *conv_bn(base * 2, base * 4, stride=2), nn.LeakyReLU(0.2),
            *conv_bn(base * 4, base * 8, stride=2), nn.LeakyReLU(0.2),
            nn.Conv2d(base * 8, 1, 4, 1, 1),
        )

    def forward(self, x, y):
        return self.net(torch.cat([x, y], 1))


def _augment(a, b, rng):
    """Same geometric jitter for input and target (rotate/shift/scale)."""
    import cv2 as _cv
    ang = rng.uniform(-2, 2)
    tx, ty = rng.uniform(-3, 3), rng.uniform(-3, 3)
    sc = rng.uniform(0.95, 1.05)
    M = _cv.getRotationMatrix2D((a.shape[-1] / 2, a.shape[-2] / 2), ang, sc)
    M[0, 2] += tx; M[1, 2] += ty
    out = []
    for im in (a, b):
        out.append(_cv.warpAffine(im, M, (a.shape[-1], a.shape[-2]),
                                  flags=_cv.INTER_LINEAR, borderMode=_cv.BORDER_REPLICATE))
    return out


class Pairs(Dataset):
    def __init__(self, idx, path=None, aug=False, alpha=0.0):
        d = np.load(path or (ROOT / "work/pairs/pairs.npz"), allow_pickle=True)
        self.X = d["X"][idx].astype(np.float32) / 127.5 - 1.0
        self.Y = d["Y"][idx].astype(np.float32) / 127.5 - 1.0
        self.aug = aug
        self.alpha = alpha
        # per-sample weight by target ink density (B/E10: fallbacks are the complex glyphs)
        if alpha > 0:
            ink = (self.Y > 0).reshape(len(self.Y), -1).mean(axis=1)
            med = float(np.median(ink)) or 1.0
            self.w = np.clip((ink / med) ** alpha, 0.5, 3.0).astype(np.float32)
        else:
            self.w = np.ones(len(self.X), np.float32)

    def __len__(self):
        return len(self.X)

    def __getitem__(self, i):
        a0, b0 = self.X[i], self.Y[i]
        if self.aug:
            a0, b0 = _augment(a0, b0, np.random)
        a = np.repeat(a0[None], 3, 0)
        b = np.repeat(b0[None], 3, 0)
        return (torch.from_numpy(a.copy()), torch.from_numpy(b.copy()),
                torch.tensor(float(self.w[i])))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=200)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--out", default=str(ROOT / "work" / "zi2zi_gan.pt"))
    ap.add_argument("--ckpt-dir", default=str(ROOT / "work" / "ckpt"),
                    help="periodic + best-val snapshots live here; never delete them")
    ap.add_argument("--save-every", type=int, default=10)
    ap.add_argument("--sample", default=str(ROOT / "work" / "preview" / "gan_sample.png"))
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--data", default=str(ROOT / "work" / "pairs" / "pairs.npz"),
                    help="npz with X/Y/chars; work/pairs_multi.npz for multi-instance")
    ap.add_argument("--hinge", action="store_true", help="hinge loss instead of BCE")
    ap.add_argument("--weight-complexity", type=float, default=0.0,
                    help="alpha for per-sample L1 weight by ink density (0 = off; B/E10)")
    ap.add_argument("--aug", action="store_true", help="rotate/shift/scale jitter on X and Y")
    ap.add_argument("--patchgan", action="store_true",
                    help="70x70 PatchGAN (conditioned on the input) instead of the global FC head")
    ap.add_argument("--resume", default="",
                    help="continue training from a checkpoint (loads G/D and the epoch "
                         "counter; Adam state is not stored, so a short transient is normal). "
                         "The character-level split is deterministic, so the same val "
                         "characters are held out")
    args = ap.parse_args()

    dev = "mps" if torch.backends.mps.is_available() else "cpu"
    d = np.load(args.data, allow_pickle=True)
    n = len(d["chars"])
    rng = np.random.RandomState(0)
    # Split by *character*, not by pair: with multi-instance data the same char
    # appears K times, so a pair-wise split leaks the character into training and
    # makes valDice measure memorisation instead of generalisation.
    all_chars = [str(c) for c in d["chars"]]
    uniq = sorted(set(all_chars))
    rng.shuffle(uniq)
    val_chars = set(uniq[:max(1, len(uniq) // 40)])      # ~2.5% of characters
    val = np.array([i for i, c in enumerate(all_chars) if c in val_chars], dtype=int)
    tr = np.array([i for i, c in enumerate(all_chars) if c not in val_chars], dtype=int)
    if args.limit:
        tr = tr[:args.limit]
    _train_ds = Pairs(tr, args.data, aug=args.aug, alpha=args.weight_complexity)
    dl = DataLoader(_train_ds, batch_size=args.batch, shuffle=True, drop_last=True, num_workers=0)
    print(f"train {len(tr)} val {len(val)} device {dev}", flush=True)
    # Record the split so evaluation can tell whether a benchmark class was seen.
    split_path = Path(args.out).with_suffix("")
    split_path = split_path.parent / (split_path.name + "_split.json")
    split_path.parent.mkdir(parents=True, exist_ok=True)
    split_path.write_text(json.dumps({
        "val_chars": sorted(val_chars),
        "train_chars": sorted(set(all_chars) - val_chars),
        "n_train_pairs": int(len(tr)), "n_val_pairs": int(len(val)),
    }, ensure_ascii=False))
    print(f"split -> {split_path.name} (val {len(val_chars)} chars)", flush=True)

    G = Generator().to(dev)
    D = (PatchDiscriminator() if args.patchgan else Discriminator()).to(dev)
    start_ep = 0
    if args.resume:
        ck = torch.load(args.resume, map_location="cpu")
        G.load_state_dict(ck["G"])
        if "D" in ck:
            D.load_state_dict(ck["D"])
        start_ep = int(ck.get("epoch", 0))
        print(f"resumed {args.resume} at epoch {start_ep} -> target {args.epochs}", flush=True)
    optG = torch.optim.Adam(G.parameters(), lr=args.lr, betas=(0.5, 0.999))
    optD = torch.optim.Adam(D.parameters(), lr=args.lr, betas=(0.5, 0.999))
    bce = nn.BCEWithLogitsLoss()
    best_dice = -1.0

    for ep in range(start_ep, args.epochs):
        t0 = time.time()
        gl = dls = 0.0
        nb = 0
        for a, b, wt in dl:
            a, b, wt = a.to(dev), b.to(dev), wt.to(dev)
            # ---- D
            with torch.no_grad():
                fake = G(a)
            if args.patchgan:
                real_logit = D(a, b)
                fake_logit = D(a, fake.detach())
            else:
                real_logit = D(b)
                fake_logit = D(fake.detach())
            if args.hinge:
                d_loss = torch.relu(1.0 - real_logit).mean() + torch.relu(1.0 + fake_logit).mean()
            else:
                d_loss = bce(real_logit, torch.ones_like(real_logit)) + \
                         bce(fake_logit, torch.zeros_like(fake_logit))
            optD.zero_grad(); d_loss.backward(); optD.step()
            # ---- G
            fake = G(a)
            fake_logit = D(a, fake) if args.patchgan else D(fake)
            adv = -fake_logit.mean() if args.hinge else bce(fake_logit, torch.ones_like(fake_logit))
            if args.weight_complexity > 0:
                per = torch.abs(fake - b).mean(dim=(1, 2, 3))
                l1 = (per * wt).mean() * 100.0
            else:
                l1 = F.l1_loss(fake, b) * 100.0
            enc_real, _ = G.encode(b)
            enc_fake, _ = G.encode(fake)
            const = F.mse_loss(enc_fake, enc_real.detach()) * 15.0
            g_loss = adv + l1 + const
            optG.zero_grad(); g_loss.backward(); optG.step()
            gl += float(g_loss); dls += float(d_loss); nb += 1
        msg = f"ep {ep+1}/{args.epochs} G {gl/max(1,nb):.2f} D {dls/max(1,nb):.2f} {time.time()-t0:.0f}s"
        val_dice = None
        if (ep + 1) % 5 == 0 or ep == 0:
            G.eval()
            with torch.no_grad():
                nval = min(8, len(val))
                vb = Pairs(val[:nval], args.data)
                xa = torch.stack([vb[i][0] for i in range(nval)]).to(dev)
                yb = torch.stack([vb[i][1] for i in range(nval)]).cpu().numpy()
                ya = xa.cpu().numpy()
                gen = G(xa).cpu().numpy()
                dice = []
                for k in range(nval):
                    p = gen[k, 0] > 0; t = yb[k, 0] > 0
                    dice.append(2 * (p & t).sum() / max(1, p.sum() + t.sum()))
                val_dice = float(np.mean(dice))
                msg += f" valDice {val_dice:.3f}"
                sheet = np.zeros((3 * 256, 8 * 256), np.uint8)
                for k in range(nval):
                    sheet[0:256, k*256:(k+1)*256] = ((ya[k, 0] + 1) * 127.5).astype(np.uint8)
                    sheet[256:512, k*256:(k+1)*256] = ((gen[k, 0] + 1) * 127.5).astype(np.uint8)
                    sheet[512:768, k*256:(k+1)*256] = ((yb[k, 0] + 1) * 127.5).astype(np.uint8)
                from PIL import Image
                Image.fromarray(sheet).resize((8*128, 3*128)).save(args.sample)
            G.train()
        print(msg, flush=True)
        torch.save({"G": G.state_dict(), "D": D.state_dict(), "epoch": ep + 1},
                   args.out)
        # Periodic snapshot: a 6-hour run must never leave only its last epoch behind.
        ck = Path(args.ckpt_dir)
        ck.mkdir(parents=True, exist_ok=True)
        tag = Path(args.out).stem
        if (ep + 1) % args.save_every == 0 or ep + 1 == args.epochs:
            torch.save({"G": G.state_dict(), "D": D.state_dict(), "epoch": ep + 1},
                       ck / f"{tag}_ep{ep+1:03d}.pt")
            print(f"  snapshot -> {ck.name}/{tag}_ep{ep+1:03d}.pt", flush=True)
        if val_dice is not None and val_dice >= best_dice:
            best_dice = val_dice
            torch.save({"G": G.state_dict(), "D": D.state_dict(), "epoch": ep + 1},
                       ck / f"{tag}_best.pt")
    print("done", flush=True)


if __name__ == "__main__":
    main()
