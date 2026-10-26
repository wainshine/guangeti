# GuanGe Kai v1.6.1（项目级发布：A v1.6.1 + B v1.0.1）

> 本项目同时维护两套馆阁体：**A 四书白文**（本页，`GuanGe Kai`）与
> **B 史记抄本**（`GuanGe Kai B`）。两者独立训练、独立评估、互不复用字形。
> 本文件是**项目级**发布说明；B 线的细节见 [`README-B.md`](../README-B.md) 与
> [`docs/RELEASE-v1.1.0-B.md`](RELEASE-v1.1.0-B.md)。

## 本版做了什么（A 线）

| 项 | 内容 |
|---|---|
| **回退字墨量修正落到制品** | 1,833 个 ribbon 回退字用修正后的 256px 口径重画：ink/文楷 **0.714 → 0.852**（拟合目标 0.824）。上一版只改了代码、没重生成数据，本版把制品补齐 |
| **质检硬闸** | `13_qa` 现在会中止：覆盖率必须 20,992、`empty/tiny/huge > 0` 即停、真迹子集断言**精确 1675/1675**、`Real.ttf` 缺失即停 |
| 字形 | 沿用 v1.6.0 的源码重建结果（`_orient` 曲线采样、`turdsize 8→2`） |
| 样张 | `specimen.png` 按本版字体重出；包内 README 的图片路径由打包脚本改写，安装包内可直接显示 |

## A 线指标（617 干净字，参照刻本真迹）

| 指标 | 值 |
|---|---|
| Dice | 0.549 |
| 骨架 chamfer | 5.92 px（真迹互比地板 5.16 px，仍差 15%） |
| 崩坏率（Dice<0.30） | 0.7% |
| 合成字构成 | 17,484 GAN + 1,833 ribbon 回退（9.5%） |

## B 线概要（史记抄本 v1.0.1）

| 项 | 值 |
|---|---|
| 真迹 | **4,078 字**（A 为 1,675） |
| 覆盖 | 20,992 / 20,992 |
| 干净集 | 墨量比 1.057 / Dice 0.528 / chamfer 5.63 |
| 常见带孔字失孔 | **0 个**（v1.0.0 曾有个别字失孔） |
| 完整失孔率（可比字） | **1.9%**（v1.0.0 为 5.6%） |
| 质检 | 三道硬闸（QA / 打包新鲜度 / 验收），不过即中止 |

**入口**：安装 `GuanGeKai-B-Regular.ttf`，家族名 `GuanGe Kai B`，可与 `GuanGe Kai` 并存；
数据与许可见 [`docs/DATA-B.md`](DATA-B.md)，实验记录见 [`docs/EXPERIMENTS-B.md`](EXPERIMENTS-B.md)。

## 已知限制

1. **孔洞缺陷（P0，未根治）**：`四/国/目/自/年` 等字在 A、B 两套字体里仍有实心形态。
   绕向与 turdsize 两层已修（A 严重缺孔字 10→3），剩下的根因是**掩膜里孔与外部连通**，
   需要 450–600 dpi 重渲染全链路重跑才能根治，属下一里程碑。
2. A 线合成字比真迹重约 17%（5–7% 为字集构成，约 5% 来自模型输出字面偏小）。
3. 未做 hinting。

## 檔案

**A**：`GuanGeKai-Regular.ttf`（15 MB）、`GuanGeKai-Real.ttf`（3.1 MB）、`provenance.json`（三态）、
`stats.json`、`SHA256SUMS`、`OFL.txt`、`LICENSE`、`coverage.txt`、`specimen.png`、`book-vs-font.png`

**B**：`GuanGeKai-B-Regular.ttf`（15.45 MB）、`GuanGeKai-B-Real.ttf`（3.76 MB）、
`GuanGeKai-B-v1.0.1.zip`（14.33 MB，`SHA256SUMS` 10/10 通过）

校验和统一记在 [`docs/DATA.md`](DATA.md)。
