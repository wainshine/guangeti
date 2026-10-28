# 发布说明：GuanGe Kai C v1.0.0（含 A/B 同步发版）

> 2026-10-28。三条线同批发布：
> **A 四书 v1.6.5**（不变）、**B 史记 v1.2.1**（不变）、**C 永乐大典 v1.0.0**（新增）。
> 逐字来源、覆盖表、校验和见 `release-c/` 与本文 §6。

---

## 1. 一句话

C 线把《永乐大典》美国藏本 41 册 3,538 页做成第三套馆阁体字体：
真迹 **5,310 字**（基本区 25.30%），其余由 GAN 补齐，覆盖 20,992 字，OFL 1.1。

## 2. 交付物

| 文件 | 内容 | 大小 |
|---|---|---|
| `GuanGeKai-C-Regular.ttf` | 20,992 字（5,310 真迹 + 15,382 GAN + 300 回退） | 20.6 MB |
| `GuanGeKai-C-Real.ttf` | 仅 5,310 真迹 | 6.16 MB |
| `GuanGeKai-C-v1.0.0.zip` | 上述 + OFL + 覆盖表 + 逐字来源 + 校验和 | 18 MB |

## 3. 资料与方法（摘要）

- 来源：明嘉靖隆庆间内府重写本，美国国会图书馆藏，41 个 LOC item；PDF 由书格整理发布。
- 页面：3,538 页（3,428 页可用；104 页地图/衬页、6 页封面），全部 300 dpi。
- 切字：OCR 行框定行（大字行≈整栏、小字双行≈半栏），逐行 DP 切格，共 **1,214,431 格**。
- 标签：**两个独立 OCR 见证**（PP-OCRv6 彩色 / PP-OCRv5 去红+拉伸），行级对齐后
  逐字一致率 **91.1%**，一致才给标签；冲突（约 9%）丢弃。
- 篆/隶/草页（222 页）整页排除；依使用者要求只做楷体。
- 真迹：5,310 字；干净集按**页**留出（207 页，6%），只用留出页上的多见证字。
- 生成：GAN（zi2zi U-Net + 5 层 PatchGAN + hinge + 增强），训练 30 轮；
  守卫不通过的字回落带状扫掠。

## 4. 质量数字

| 指标 | 值 | 说明 |
|---|---|---|
| 覆盖率 | **20,992 / 20,992** | `80_qa_c.py` |
| 真迹字数 | **5,310**（25.30%） | `chosen.jsonl` |
| 真迹子集 | 5,310 / 5,310 | `GuanGeKai-C-Real.ttf` |
| 合成/真迹字重比 | 1.108（+10.8%） | `84_accept_c.py`，目标 1.00±0.10 |
| 孔洞丢失率 | 5.6% | `71_holes.py`，基线 A 1.9% |
| 干净集 Dice / chamfer | 0.459 / 6.82 | 留出页 3,213 字，检查点 c_ep030.pt |
| 真迹互比 chamfer 地板 | 6.98 | 同字两真迹样本 |

## 5. 已知限制

1. **标签来自双引擎一致，未经逐字人工校对。** 这是与 A/B 最大的差别；
   两引擎同错的形近字（曰/日、己/已）无法自动发现。
2. 合成字不是真迹；严格字形请用 `GuanGeKai-C-Real.ttf`。
3. 篆、隶、草书不收。
4. 无 hinting。
5. 异体/简化码位政策见 `README-C.md` §5。

## 6. 校验和与 A/B 完整性

```
8881a0208c75ba4e033529b9d4e5beb920bb9504fb263e2dc7207b62158c4c1f  build/GuanGeKai-C-Regular.ttf
2d9abb207ff1b44e444a28d7a8947fd74d99216fca8d7365a4d2f4aaf8c3ace1  build/GuanGeKai-C-Real.ttf
016154dacb5daa6d835b8eefb9f4d10953449f992a0966b6a25910593a5af340  GuanGeKai-C-v1.0.0.zip
```

`scripts/83_verify_ab_c.py` 的结果：

```
OK  GuanGeKai-Regular.ttf     d10ecf00bdb01b53  (== A v1.6.5 release/SHA256SUMS)
OK  GuanGeKai-Real.ttf        b0a706b90701ff8b  (== A v1.6.5)
OK  GuanGeKai-B-Regular.ttf   a0cf0912e1a8eb77  (== B v1.2.1 release-b/SHA256SUMS)
OK  GuanGeKai-B-Real.ttf      7e9d70862f9341e3  (== B v1.2.1)
OK  A coverage 20992 / A real 1675 / A chosen 1675 / A provenance real 1675
OK  B coverage 20992 / B real 4078 / B chosen 4078 / B provenance real 4078
RESULT: A/B INTACT
```

**A、B 两线未被本次 C 线工作改动**：四份 TTF 与各自 `release*/SHA256SUMS` 逐位元组一致，
A `chosen.jsonl` 1,675、B 4,078、两者覆盖 20,992 均保持不变。

## 7. 发版顺序

1. `76_build_real_c.py` → `79_build_full_c.py`
2. `80_qa_c.py`（硬闸；C 线预设 `--max-lost-frac 0.18`，白名单已去掉 `园`）
   → `71_holes.py --font build/GuanGeKai-C-Regular.ttf --n 300 --json work-c/holes_c.json`（记录）
3. `84_accept_c.py`（字重比）
4. `72_specimen_c.py`、`71_book_vs_font_c.py`
5. `81_package_c.py` → zip
6. `83_verify_ab_c.py`（必须 `A/B INTACT`）
7. 校验和写回 `DATA-C.md` / 本文
