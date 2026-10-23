"""Shared helpers for glyph generation."""
from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image, ImageDraw


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


def render_base(font, ch, S):
    img = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(img)
    baseline = 880 * S / 1000.0
    d.text((0, baseline), ch, fill=255, font=font, anchor="ls")
    return np.array(img, dtype=np.uint8)


def raster_to_em(contours, S, em_top=880.0, em_bot=-120.0):
    """Canvas 256x256 (em x 0..1000, y 880..-120) -> font units."""
    k = 1000.0 / S

    def mx(px):
        return px * k

    def my(py):
        return em_top - py * k

    out = []
    for c in contours:
        sx, sy = c["start"]
        segs = []
        for s in c["segs"]:
            if s[0] == "L":
                segs.append(("L", mx(s[1]), my(s[2])))
            else:
                segs.append(("C", mx(s[1]), my(s[2]), mx(s[3]), my(s[4]), mx(s[5]), my(s[6])))
        out.append(dict(start=(mx(sx), my(sy)), segs=segs))
    return out


def ribbon_scale(comp: float, base: float = 1.06, lo: float = 0.62, hi: float = 1.12) -> float:
    """Per-character ribbon scale.

    The print's ink/WenKai ratio falls with stroke density (fit on the 1,675 pairs):
    ratio = 20.619 * ink^-0.330, and ribbon ink is ~1.06x its scale.
    """
    tgt = 20.619 * max(float(comp), 1.0) ** -0.330
    return float(min(hi, max(lo, tgt / base)))
