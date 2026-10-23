# GuanGe Kai v1.3.3

> 当前发布版。合成字使用**带状扫掠渲染器**（`--method ribbon`），构建可复现（字节一致）。

**Version 1.3.3** — 20,992 字全覆盖：1,675 真迹 + 19,317 合成。

## 相对 v1.3.2 的变更

- **逐笔宽度分布重拟合**：从 45,042 条笔画（2,292 个字）估计，取代原来的 2,490 条（约 120 字）；
  掩膜级端帽 KS 从 0.084 降到 0.050。
- **potrace `alphamax` 改为 0.4**（原 1.0），保留更多尖角。
- **`scale` 改为 0.78**（原 0.82），按字体级墨量校准。
- 字体级（矢量化后）：Dice 0.432、墨量 1.146、端帽 KS 0.124；体积 22.8 MB。
- **构建可复现**：`head.created/modified` 固定为 `SOURCE_DATE_EPOCH`（默认 2026-10-23），
  两次构建字节完全一致。

## 档案

| 档案 | 说明 |
|---|---|
| `GuanGeKai-Regular.ttf` | 20,992 字（1,675 真迹 + 19,317 合成），22.8 MB |
| `GuanGeKai-Real.ttf` | 仅 1,675 真迹，3.2 MB |
| `OFL.txt` / `LICENSE` | 字体 OFL 1.1 / 代码 MIT |
| `provenance.json` | 逐字 real / gen |
| `coverage.txt` | 覆盖码位清单 |
| `specimen.png` / `book-vs-font.png` | 样张与刻本对照 |
| `SHA256SUMS` | 校验和 |

## 校验和

```
SHA-256 见 release/SHA256SUMS
```

## 已知限制

- 合成字的骨架取自霞鹜文楷，拓扑与其一致（97%），但与刻本真迹仅 47%——这部分差异继承自内容字体。
- 墨量 1.146（字体级），比真迹重 14.6%。
- 横折（转折）仍是圆角，尚未专门处理。
- 未做 hinting。

## 重建

见 `docs/DATA.md` §6 与 `AGENTS.md` 的发布流程。字体重建需先跑 `01_segment.py`（若 `work/cells` 不存在）。
