# GuanGe Kai B v1.2.2

> 随主版本 **GuanGeKai v1.7.0** 发布。同一项目、三个字形来源：
> A = 四书精写本《四書白文》（`GuanGe Kai`，v1.7.0）、
> B = 史记旧抄本（`GuanGe Kai B`，本包 v1.2.2）、
> C = 永乐大典嘉靖内府录副本（`GuanGe Kai C`，v1.0.1）。

---

## 1. 一句话

**v1.2.2 是文档与元数据版：模型、工作点、字形都没有变化。**
改的是三件事：README 的载体术语（「刻本」→「写本」）、一批过期数字、
以及 Real 子集的构建来源（让它与 Regular 中的同一字轮廓一致）。

## 2. 交付物

| 文件 | 内容 | 大小 |
|---|---|---|
| `GuanGeKai-B-Regular.ttf` | 20,992 字（4,073 区内真迹 + 5 扩展 A + 16,919 生成） | **15.39 MB** |
| `GuanGeKai-B-Real.ttf` | 仅 4,078 真迹 | **3.82 MB** |
| `GuanGeKai-B-v1.2.2.zip` | 上述 + OFL + 覆盖表 + 逐字来源 + 校验和 | **14.3 MB** |

字体名表版本串 `Version 1.2.2`；家族名、PostScript 名不变。

## 3. 改了什么

### 3.1 术语：A 线是写本，不是刻本

本项目早期把《四书白文》写成「刻本」，实为**明代精写本**（手书墨迹）。
本包对比表里的「明刻本 / 刀刻刻本 / 刻本有刀口」全部更正，
「載體」一行改为「性質」（名家精写本 / 旧抄本），按书写者与场合区分而不是按载体。
规范见 `docs/GLOSSARY.md`，检查器 `scripts/97_check_terms.py` 已全库通过。

### 3.2 数字更正（旧值都是在 v1.2.1 打包前写的，比最终验收早 17 分钟）

| 项 | 原写法 | 更正为 | 依据 |
|---|---|---|---|
| 生成字数 | 16,927 | **16,919** = 15,784 + 544 + 591 | `release-b/stats.json` |
| GAN 轮数 | 50 轮 | **80 轮** | `data/release-b.json`、发版检查点 `b_ep080.pt` |
| 合成字字重 | 重 12.5%（1.125） | **重 8.2%（1.082）** | `work-b/accept_b.json` |
| 12px 字重偏移 | ×1.04 | **×1.008** | 同上 |
| 小字号偏移 | 12px 1.003 / 16px 1.014 / 48px 1.024 | **12px 1.008 / 16px 1.026 / 24px 1.053 / 48px 1.033** | 同上（原值漏了最差的 24px 一档） |
| 孔洞：完全丢孔 | 0.5% | **1.0%**（全字集 157/15,265） | `71_holes.py --n 0`；0.5% 是 300 字抽样的点估计 |
| 孔洞：少孔 | 13.6% | **12.2%**（全字集） | 同上 |
| Regular 体积 | 15.46 MB | **15.39 MB** | 15,390,716 B |

「干净集 Dice / 墨量 / chamfer = 0.523 / 1.009 / 5.60」本来就与
`work-b/eval_v120.json` 一致，未改。

### 3.3 Real 子集的构建来源（本次唯一的实质改动）

v1.2.1 的两个字体里，**同一个字在 Regular 与 Real 中的轮廓并不相同**：

| 字体 | 来源 | `一` 的轮廓点数 |
|---|---|---|
| v1.2.1 Regular | `work-b/real_contours.jsonl` | 52 |
| v1.2.1 Real | `57_build_real_b.py` 现场重新描摹 | 51 |

差一个闭合点，256 px 渲染下看不出差别，但它违反「Real 是 Regular 真迹子集」这个定义。

v1.2.2 起 `57_build_real_b.py` 增加 `--reuse-contours`，直接从
`work-b/real_contours.jsonl` 重建 Real，两个字体的真迹轮廓首次完全一致（都是 52 点）。

**影响评估**：抽 200 个真迹字，在 256 px 下逐像素比较 v1.2.1 与 v1.2.2 的 Real，
Dice = **1.000**（完全重合）。即轮廓字节不同、渲染无差异。

## 4. 质量数字（与 v1.2.1 相同）

| 指标 | 值 | 说明 |
|---|---|---|
| 覆盖率 | **20,992 / 20,992** | `63_qa_b.py` → QA OK |
| 真迹子集 | 4,078 字形 · 4,078 cmap | OK |
| 逐字来源 | real 4,078 · gan 15,784 · gan_ht 544 · ribbon_fb 591 · missing 0 | `stats.json` |
| 字重比（合成/真迹） | **1.082** | `68_accept_b.py` → ACCEPTANCE OK |
| 包围盒比 | 1.031 | 同上 |
| ribbon 回退占比 | **3.5%** | 同上 |
| 孔洞：完全丢孔 / 少孔 | **1.0% / 12.2%**（全字集） | `71_holes.py --n 0` |

> `63_qa_b.py` 的孔洞闸门用 300 字抽样（本次抽到 1/214 = 0.5%），
> 发布口径一律引用全字集的 1.0%，不用抽样值。

## 5. 已知限制

与 v1.2.1 相同，未变：

- **孔洞**：全字集完全丢孔 1.0%、少孔 12.2%，根因是抄本断笔与细接缝（B/E9、A 线 E38），不是分辨率。
- **困难字的 GAN 输出仍不如主体**：544 个救回字是模型最吃力的一档（局部粘连率 4.68%，主体 3.9%），
  但仍优于 ribbon（6.40%）。
- chamfer 5.60 相对真迹地板 3.57 差 57%，是 150 dpi 扫描的结构性天花板（`docs/DATA-B.md` §5.8）。
- 未做 hinting。

## 6. 校验和

```
682a1c2295d9b108b930e2f6cbcbc47a01b981c2c6f2c9e3a2c56aa433978971  build/GuanGeKai-B-Real.ttf
1367082fd0fffba7b6e8245736cbf200699594ccca3deb86202f7689405ceece  build/GuanGeKai-B-Regular.ttf
d9da537640fbac12003ea2d1a13323cdda9187ff9f5bce49fb5e10095ff4b491  GuanGeKai-B-v1.2.2.zip
```

包内 `release-b/SHA256SUMS` 逐文件自校验。

## 7. 复现

```bash
python3 scripts/57_build_real_b.py --reuse-contours   # 从 real_contours.jsonl 重建 Real
python3 scripts/62_build_full_b.py                    # 从 real_contours + generated 重建 Regular
python3 scripts/63_qa_b.py                            # 硬闸
python3 scripts/68_accept_b.py                        # 硬闸（字重比 / 包围盒 / 回退率）
rm -rf release-b && python3 scripts/64_package_b.py
```

工作点未变：`b_ep080.pt`、thr −0.10、close 7、hole-repair、`--ckpt-hardtail b_wt_ep090.pt`，
见 `data/release-b.json`。
