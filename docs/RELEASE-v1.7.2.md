# GuanGe Kai v1.7.2（A 四书）

> **字集口径定稿 + 工作点固化。** 基本区字形与 v1.7.1 相同；码位从 v1.7.1 的 44 个（含 `U+201C/U+201D` 两个弯引号）收紧为 42 个，变的是「补进来的标点到底算多少、从哪来、怎么复现」。

## 本版变更

| # | 项 | 内容 |
|---|---|---|
| 1 | **字集定稿** | `cmap` **21,034** = CJK 基本区 20,992 + 标点/数字/空格 **42**。删除半角弯引号 `U+201C/U+201D`（文楷里是 350/1000 em，中文正文会贴字），中文引号用 `「」『』` |
| 2 | **唯一定义源** | 新增 `scripts/punct_set.py`；`13_extend_punct`、`13_qa`、`83_verify_ab_c` 全部引用它，禁止硬编码数量 |
| 3 | **字节可复现** | `13_extend_punct` 设 `recalcTimestamp=False`，同一输入两次输出哈希一致 |
| 4 | **工作点固化** | `10_generate.py` 默认改为主 `m2wt_ep090.pt` + 补位 `m2_ep080.pt` + 阈值 `−0.05/−0.45`，与 `data/release-a.json` 一致；完整复现命令见该文件 `reproduce` 行（含 `--simplify 2.0` 与 hardtail 阈值），不要按“无参数默认”理解 |
| 5 | **记录补齐** | `release/provenance.json` 增 42 条 `punct`（20,992 → 21,034）；`stats.json` 增 `codepoints_total` |

## 指标（发布时记录；口径见下注）

> **口径更正（2026-11-14 复核）**：孔洞 n=200 重测为 **1.4%（2/145）**（`work/holes_a_n200.json`）；
> 干净集以 clean617 **Dice 0.539 / chamfer 6.13（n=617）** 为准（旧 0.549/5.92 为 n=150 抽样，见 ERRATA E9）。

| 项 | 值 |
|---|---|
| 覆盖 | 基本区 20,992 / 20,992；总码位 21,034 |
| 真迹 / GAN / 回退 | 1,675 / 18,518 / 799（4.1%） |
| 孔洞 | `holes lost` 0.7%（200 字抽样）**（已更正，见上注）** |
| 干净集 | Dice 0.549、chamfer 5.92**（已更正，见上注）** |

## 已知限制

1. 标点与数字取自霞鹜文楷（OFL 1.1，1:1 不缩放），**笔意偏印刷体**，与馆阁体并排时略轻；
2. 孔洞缺陷无工程解法（E38）；
3. 合成字比真迹重约 17%（E34/E37）；
4. 补位字与主模型字墨量差 3.8%（E40）。

## 檔案

`GuanGeKai-Regular.ttf`（21,034 / Version 1.7.2）、`GuanGeKai-Real.ttf`（1,675，不含标点）、
`provenance.json`、`stats.json`、`SHA256SUMS`、`OFL.txt`、`LICENSE`、`coverage.txt`、`specimen.png`、`book-vs-font.png`

校验和见 `docs/DATA.md`。三线字集口径一致，跨线闸 `83_verify_ab_c.py` 必须打印三个 `OK 字集 21034`。
