"""Patch-based style-transfer training (WenKai -> 館閣楷 manuscript)."""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from generate_lib import UNet

ROOT = Path(__file__).resolve().parents[1]
P = 128


def dist_channel(x):
    import cv2
    outs = []
    for i in range(len(x)):
        a = (x[i, 0].numpy() > 0.5).astype(np.uint8)
        d = cv2.distanceTransform(1 - a, cv2.DIST_L2, 5)
        outs.append(np.clip(d / 8.0, 0, 1))
    return torch.from_numpy(np.stack(outs)).float().unsqueeze(1)


def grad(z):
    return (torch.abs(z[:, :, 1:, :] - z[:, :, :-1, :]).mean()
            + torch.abs(z[:, :, :, 1:] - z[:, :, :, :-1]).mean())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=120)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--base", type=int, default=32)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--out", default=str(ROOT / "work" / "style_b.pt"))
    ap.add_argument("--adv", action="store_true", help="add a PatchGAN discriminator")
    args = ap.parse_args()

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    d = np.load(ROOT / "work" / "pairs" / "pairs.npz", allow_pickle=True)
    X0 = torch.from_numpy(d["X"]).float().unsqueeze(1) / 255.0
    Y = torch.from_numpy(d["Y"]).float().unsqueeze(1) / 255.0
    X = torch.cat([X0, dist_channel(X0)], 1)
    chars = list(d["chars"])
    n = len(X)
    rng = np.random.RandomState(0)
    perm = rng.permutation(n)
    nval = 120
    val_idx = torch.from_numpy(perm[:nval])
    tr_idx = torch.from_numpy(perm[nval:])
    print(f"train {len(tr_idx)} val {len(val_idx)} device {device}", flush=True)

    model = UNet(base=args.base).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    steps = args.epochs * max(1, len(tr_idx) // args.batch + 1)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=args.lr, total_steps=steps)

    disc = None
    optd = None
    if args.adv:
        disc = nn.Sequential(
            nn.Conv2d(1, 32, 4, 2, 1), nn.LeakyReLU(0.2, True),
            nn.Conv2d(32, 64, 4, 2, 1), nn.InstanceNorm2d(64), nn.LeakyReLU(0.2, True),
            nn.Conv2d(64, 1, 3, 1, 1),
        ).to(device)
        optd = torch.optim.AdamW(disc.parameters(), lr=args.lr, weight_decay=1e-4)

    best = 1e9
    t0 = time.time()
    gen = torch.Generator().manual_seed(7)

    for ep in range(args.epochs):
        model.train()
        order = tr_idx[torch.randperm(len(tr_idx), generator=gen)]
        tot = nb = 0
        for i in range(0, len(order) - args.batch + 1, args.batch):
            b = order[i:i + args.batch]
            xs, ys = [], []
            for j in b:
                ox = int(torch.randint(0, 256 - P + 1, (1,), generator=gen))
                oy = int(torch.randint(0, 256 - P + 1, (1,), generator=gen))
                xs.append(X[j, :, oy:oy + P, ox:ox + P])
                ys.append(Y[j, :, oy:oy + P, ox:ox + P])
            x = torch.stack(xs).to(device)
            y = torch.stack(ys).to(device)
            out = model(x)
            p = torch.sigmoid(out)
            bce = F.binary_cross_entropy_with_logits(out, y)
            inter = (p * y).sum(dim=(1, 2, 3))
            dice = 1.0 - (2 * inter + 1.0) / (p.sum(dim=(1, 2, 3)) + y.sum(dim=(1, 2, 3)) + 1.0)
            loss = bce + dice.mean()
            if disc is not None:
                # generator adversarial
                fake = p
                pred = disc(fake)
                loss = loss + 0.02 * F.binary_cross_entropy_with_logits(pred, torch.ones_like(pred))
            opt.zero_grad(set_to_none=True)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            opt.step()
            sched.step()
            if disc is not None:
                optd.zero_grad(set_to_none=True)
                dp = disc(p.detach())
                dz = disc(y)
                dl = 0.5 * (F.binary_cross_entropy_with_logits(dp, torch.zeros_like(dp))
                            + F.binary_cross_entropy_with_logits(dz, torch.ones_like(dz)))
                dl.backward()
                optd.step()
            tot += float(loss.detach())
            nb += 1
        model.eval()
        with torch.no_grad():
            vp = torch.sigmoid(model(X[val_idx].to(device)))
            vy = Y[val_idx].to(device)
            inter = (vp * vy).sum(dim=(1, 2, 3))
            dice_v = 1.0 - (2 * inter + 1.0) / (vp.sum(dim=(1, 2, 3)) + vy.sum(dim=(1, 2, 3)) + 1.0)
            vl = 1.0 - float(dice_v.mean().detach())
        print(f"ep {ep+1}/{args.epochs} loss {tot/max(1,nb):.4f} valDice {1-vl:.4f} {time.time()-t0:.0f}s", flush=True)
        if vl < best:
            best = vl
            torch.save(model.state_dict(), args.out)
        if (ep + 1) % 30 == 0:
            torch.save(model.state_dict(), str(args.out).replace(".pt", f"_ep{ep+1}.pt"))
    print("best", best)


if __name__ == "__main__":
    main()
