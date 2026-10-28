# GuanGe Kai v1.6.2（A 四书）

> 承 v1.6.1（项目级：A v1.6.1 + B v1.0.1）。本版**字形未变**，修的是质量闸门与可复现性。

## 本版变更

| # | 项 | 内容 |
|---|---|---|
| S1 | **`fontRevision` 修正（共用库）** | `fontbuild.py` 原来只取版本号前两段，`head.fontRevision` 恒为 `1.0`。现按 16.16 定点取三段：`1.6.2 → 1.620`。**B 线 v1.1.0 会自动继承** |
| A1 | 打包新鲜度闸 | 字体比 `chosen.jsonl`/`generated.jsonl` 旧 → 中止；`missing>0` → 中止 |
| A2 | A 线孔洞审计 | 复用 `71_holes_b.py`，基线落盘 `work/holes_a.json`：孔数一致 22.9%、偏少 24.8%、完全丢孔 2.8% |
| A3 | 对比面板改用干净字 | 从 617 个从未训练的单次字抽样（原来 120 字里 79 字在训练集） |
| A4 | 评估可复现 | `32_eval_clean`/`34_struct_score` 加 `--seed`（默认 7）/`--n`（默认 150），对齐 E32/E33 口径 |
| A5 | 干净集默认不模糊 | `24_build_singles --sigma` 默认 `1.0 → 0.0`，与发布产物一致 |

## 已知限制（未变）

1. **孔洞缺陷（P0）仍在**：`四/国/目/自/年` 等字仍实心。三层根因中绕向与 turdsize 已修，
   剩下的是**掩膜里孔与外部连通**，需 450–600 dpi 重渲染全链路重跑才能根治。
2. 合成字比真迹重约 17%（5–7% 为字集构成，约 5% 来自模型输出字面偏小）。
3. 未做 hinting。

## 檔案

`GuanGeKai-Regular.ttf`（15.2 MB）、`GuanGeKai-Real.ttf`、`provenance.json`（三态）、
`stats.json`、`SHA256SUMS`、`OFL.txt`、`LICENSE`、`coverage.txt`、`specimen.png`、`book-vs-font.png`

校验和见 `docs/DATA.md`。B 线（史记本 v1.1.0）另行发布，入口见 `README-B.md`。
