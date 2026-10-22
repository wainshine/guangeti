"""Train a small U-Net that transfers the 馆阁体 brush style onto base-font rasters."""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

ROOT = Path(__file__).resolve().parents[1]


def distance_channel(x):
    """Normalised distance-to-ink-edge map, a structural prior for the model."""
    import cv2
    outs = []
    for i in range(len(x)):
        a = (x[i, 0].numpy() > 0.5).astype("uint8")
        d = cv2.distanceTransform(1 - a, cv2.DIST_L2, 5)
        d = np.clip(d / 8.0, 0, 1)
        outs.append(d)
    return torch.from_numpy(np.stack(outs)).float().unsqueeze(1)


class DoubleConv(nn.Module):
    def __init__(self, cin, cout):
        super().__init__()
        g = 8 if cout % 8 == 0 else 1
        self.net = nn.Sequential(
            nn.Conv2d(cin, cout, 3, padding=1), nn.GroupNorm(g, cout), nn.SiLU(inplace=True),
            nn.Conv2d(cout, cout, 3, padding=1), nn.GroupNorm(g, cout), nn.SiLU(inplace=True),
        )

    def forward(self, x):
        return self.net(x)


class UNet(nn.Module):
    def __init__(self, base=32, depth=4):
        super().__init__()
        chs = [base * (2 ** i) for i in range(depth)]
        self.down = nn.ModuleList()
        c = 2
        for ch in chs:
            self.down.append(DoubleConv(c, ch))
            c = ch
        self.mid = DoubleConv(c, c * 2)
        self.up = nn.ModuleList()
        c = c * 2
        for ch in reversed(chs):
            self.up.append(nn.ConvTranspose2d(c, ch, 2, stride=2))
            self.up.append(DoubleConv(ch * 2, ch))
            c = ch
        self.out = nn.Conv2d(c, 1, 1)

    def forward(self, x):
        x0 = x
        skips = []
        for d in self.down:
            x = d(x)
            skips.append(x)
            x = F.max_pool2d(x, 2)
        x = self.mid(x)
        for i in range(0, len(self.up), 2):
            x = self.up[i](x)
            s = skips.pop()
            x = torch.cat([x, s], 1)
            x = self.up[i + 1](x)
        return self.out(x) + 0.0 * x0[:, :1]


def augment(x, y, gen):
    B = x.shape[0]
    # random affine, same for input and target
    ang = (torch.rand(B, generator=gen) - 0.5) * (6 * np.pi / 180)
    scale = 1.0 + (torch.rand(B, generator=gen) - 0.5) * 0.16
    tx = (torch.rand(B, generator=gen) - 0.5) * 10
    ty = (torch.rand(B, generator=gen) - 0.5) * 10
    cos = torch.cos(ang) / scale
    sin = torch.sin(ang) / scale
    theta = torch.zeros(B, 2, 3, device=x.device)
    theta[:, 0, 0] = cos
    theta[:, 0, 1] = -sin
    theta[:, 1, 0] = sin
    theta[:, 1, 1] = cos
    theta[:, 0, 2] = tx / (x.shape[-1] / 2)
    theta[:, 1, 2] = ty / (x.shape[-2] / 2)
    grid = F.affine_grid(theta, x.shape, align_corners=False).to(x.device)
    x = F.grid_sample(x, grid, align_corners=False, padding_mode="zeros")
    y = F.grid_sample(y, grid, align_corners=False, padding_mode="zeros")
    return x, y


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=120)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--base", type=int, default=32)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--size", type=int, default=256)
    ap.add_argument("--out", default=str(ROOT / "work" / "style_unet.pt"))
    ap.add_argument("--resume", default="")
    args = ap.parse_args()

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    print("device", device, flush=True)
    d = np.load(ROOT / "work" / "pairs" / "pairs.npz", allow_pickle=True)
    X0 = torch.from_numpy(d["X"]).float().unsqueeze(1) / 255.0
    Y = torch.from_numpy(d["Y"]).float().unsqueeze(1) / 255.0
    X = torch.cat([X0, distance_channel(X0)], 1)
    N = len(X)
    perm = torch.randperm(N, generator=torch.Generator().manual_seed(0))
    val = perm[: max(32, N // 20)]
    tr = perm[max(32, N // 20):]
    print("train", len(tr), "val", len(val), flush=True)

    model = UNet(base=args.base).to(device)
    if args.resume:
        model.load_state_dict(torch.load(args.resume, map_location=device))
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-5)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=args.lr,
                                                total_steps=args.epochs * (len(tr) // args.batch + 1))
    gen = torch.Generator().manual_seed(1)

    def loss_fn(out, tgt):
        bce = F.binary_cross_entropy_with_logits(out, tgt)
        p = torch.sigmoid(out)
        l1 = F.l1_loss(p, tgt)
        # edge loss keeps stroke terminals crisp
        def grad(z):
            return torch.abs(z[:, :, 1:, :] - z[:, :, :-1, :]).mean() + \
                   torch.abs(z[:, :, :, 1:] - z[:, :, :, :-1]).mean()
        edge = (grad(p) - grad(tgt)).abs()
        return bce + 0.5 * l1 + 2.0 * edge

    best = 1e9
    t0 = time.time()
    for ep in range(args.epochs):
        model.train()
        idx = tr[torch.randperm(len(tr), generator=gen)]
        tot = 0.0
        nb = 0
        for i in range(0, len(idx) - args.batch + 1, args.batch):
            b = idx[i:i + args.batch]
            x = X[b].to(device)
            y = Y[b].to(device)
            x, y = augment(x, y, gen)
            out = model(x)
            loss = loss_fn(out, y)
            opt.zero_grad(set_to_none=True)
            loss.backward()
            opt.step()
            sched.step()
            tot += float(loss.detach())
            nb += 1
        model.eval()
        with torch.no_grad():
            vb = X[val[:128]].to(device)
            vl = float(F.l1_loss(torch.sigmoid(model(vb)), Y[val[:128]].to(device)).detach())
        print(f"ep {ep+1}/{args.epochs} loss {tot/max(1,nb):.4f} valL1 {vl:.4f} "
              f"{time.time()-t0:.0f}s", flush=True)
        if vl < best:
            best = vl
            torch.save(model.state_dict(), args.out)
        if (ep + 1) % 20 == 0:
            torch.save(model.state_dict(), str(args.out).replace(".pt", f"_ep{ep+1}.pt"))
    print("best val", best, "saved", args.out)


if __name__ == "__main__":
    main()
