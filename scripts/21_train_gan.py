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


class Pairs(Dataset):
    def __init__(self, idx):
        d = np.load(ROOT / "work/pairs/pairs.npz", allow_pickle=True)
        self.X = d["X"][idx].astype(np.float32) / 127.5 - 1.0
        self.Y = d["Y"][idx].astype(np.float32) / 127.5 - 1.0

    def __len__(self):
        return len(self.X)

    def __getitem__(self, i):
        a = np.repeat(self.X[i][None], 3, 0)
        b = np.repeat(self.Y[i][None], 3, 0)
        return torch.from_numpy(a), torch.from_numpy(b)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=200)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--out", default=str(ROOT / "work" / "zi2zi_gan.pt"))
    ap.add_argument("--sample", default=str(ROOT / "work" / "preview" / "gan_sample.png"))
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    dev = "mps" if torch.backends.mps.is_available() else "cpu"
    d = np.load(ROOT / "work/pairs/pairs.npz", allow_pickle=True)
    n = len(d["chars"])
    rng = np.random.RandomState(0)
    perm = rng.permutation(n)
    val = perm[:120]
    tr = perm[120:]
    if args.limit:
        tr = tr[:args.limit]
    dl = DataLoader(Pairs(tr), batch_size=args.batch, shuffle=True, drop_last=True, num_workers=0)
    print(f"train {len(tr)} val {len(val)} device {dev}", flush=True)

    G = Generator().to(dev)
    D = Discriminator().to(dev)
    optG = torch.optim.Adam(G.parameters(), lr=args.lr, betas=(0.5, 0.999))
    optD = torch.optim.Adam(D.parameters(), lr=args.lr, betas=(0.5, 0.999))
    bce = nn.BCEWithLogitsLoss()

    for ep in range(args.epochs):
        t0 = time.time()
        gl = dls = 0.0
        nb = 0
        for a, b in dl:
            a, b = a.to(dev), b.to(dev)
            # ---- D
            with torch.no_grad():
                fake = G(a)
            real_logit = D(b)
            fake_logit = D(fake.detach())
            d_loss = bce(real_logit, torch.ones_like(real_logit)) + \
                     bce(fake_logit, torch.zeros_like(fake_logit))
            optD.zero_grad(); d_loss.backward(); optD.step()
            # ---- G
            fake = G(a)
            fake_logit = D(fake)
            adv = bce(fake_logit, torch.ones_like(fake_logit))
            l1 = F.l1_loss(fake, b) * 100.0
            enc_real, _ = G.encode(b)
            enc_fake, _ = G.encode(fake)
            const = F.mse_loss(enc_fake, enc_real.detach()) * 15.0
            g_loss = adv + l1 + const
            optG.zero_grad(); g_loss.backward(); optG.step()
            gl += float(g_loss); dls += float(d_loss); nb += 1
        msg = f"ep {ep+1}/{args.epochs} G {gl/max(1,nb):.2f} D {dls/max(1,nb):.2f} {time.time()-t0:.0f}s"
        if (ep + 1) % 5 == 0 or ep == 0:
            G.eval()
            with torch.no_grad():
                vb = Pairs(val[:8])
                xa = torch.stack([vb[i][0] for i in range(8)]).to(dev)
                yb = torch.stack([vb[i][1] for i in range(8)]).cpu().numpy()
                ya = xa.cpu().numpy()
                gen = G(xa).cpu().numpy()
                dice = []
                for k in range(8):
                    p = gen[k, 0] > 0; t = yb[k, 0] > 0
                    dice.append(2 * (p & t).sum() / max(1, p.sum() + t.sum()))
                msg += f" valDice {np.mean(dice):.3f}"
                sheet = np.zeros((3 * 256, 8 * 256), np.uint8)
                for k in range(8):
                    sheet[0:256, k*256:(k+1)*256] = ((ya[k, 0] + 1) * 127.5).astype(np.uint8)
                    sheet[256:512, k*256:(k+1)*256] = ((gen[k, 0] + 1) * 127.5).astype(np.uint8)
                    sheet[512:768, k*256:(k+1)*256] = ((yb[k, 0] + 1) * 127.5).astype(np.uint8)
                from PIL import Image
                Image.fromarray(sheet).resize((8*128, 3*128)).save(args.sample)
            G.train()
        print(msg, flush=True)
        torch.save({"G": G.state_dict(), "D": D.state_dict()}, args.out)
    print("done", flush=True)


if __name__ == "__main__":
    main()
