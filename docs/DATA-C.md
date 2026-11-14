# C 线数据、许可与校验和

> 本文件回答三个问题：**每个文件从哪来、能不能用、怎么复现**。
> 数字均为 2026-10-27 实测；未完成项标「待补」。

---

## 1. 输入数据

| 文件 | 体积 | 来源 | 许可 | 是否入库 |
|---|---|---|---|---|
| `永乐大典美国藏本/*.pdf`（41 册） | 20 GB | 美国国会图书馆（LOC）藏明嘉靖隆庆间内府重写本；41 个 LOC item（`2018421651`–`2018421670`、`2018433742`–`2018433762`）；PDF 由书格 shuge.org 整理发布（PDF 元数据 `subject` 字段） | 原书为公有领域（明代写本）；扫描件为公版二维作品的忠实再现（见 §3） | ❌ 不入库 |
| `data/base/LXGWWenKai-Regular.ttf` | 25 MB | LXGW WenKai v1.530 | OFL 1.1，含 Reserved Font Name | ❌ 不入库（可自行下载） |
| `work-c/models/*.onnx` | 52 MB | RapidOCR 3.10 的 PP-OCRv6 small / PP-OCRv5 mobile（Apache-2.0） | Apache-2.0 | ❌ 不入库（脚本自动下载） |

**41 册清单**：卷 10934–10935（楚）、10949–10950（抚）、10998–10999 / 11000–11001（府）、
11076–11077（蜼等）、11618–11619（老）、11951–11952 / 11953–11955（顶）、
11956–11957 / 11958–11959 / 11960（鼎）、11980–11981（岭）、12013–12014（有）、
12015–12016 / 12017–12018（友）、12043–12044 / 12071–12072（酒）、12148（叟等）、
12269 / 12270–12271 / 12272–12274 / 12275–12276 / 12306–12308 / 12399–12400 / 12428–12429 /
12506–12507 / 12960–12962 / 12963–12965 / 12966–12968 / 12969–12971（宋）、
13344–13345（示諡）、13589–13590（誓）、14055–14056（祭）、14131（第）、
15142 / 15143（兑等）、15950–15951（运）、19742–19743（录）、19785–19786 / 19792（服）、
6831–6832（王）。

## 1.1 A 线语料性质更正（避免沿用旧说法）

A 线《四书白文》是**明代精写本**（手书墨迹），不是刻本。早期文档写作「明刻本」「刻刀笔锋」，<!-- term-ok -->
2026-10-28 已更正；一手证据是 `docs/images/manuscript-evidence.jpg`（第 11 页 600 dpi：
**版心空白**——无书名、卷次、叶码、刻工、牌记；笔锋浓淡与飞白；字径不匀、基线起伏），
书格著录（原站文件名含「明钞本」）为旁证。判读细则见 `docs/ERRATA.md` E1。

三条线**都是写本**：A 名家精写本 / B 旧抄本 / C 嘉靖内府录副本。差异在书写者与场合，不在刻还是写。
术语以 `docs/GLOSSARY.md` 为准；历史勘误见 `docs/ERRATA.md`。本线文档提到 A 线时统一写
「写本 / 精写本 / 墨笔笔锋」，不要写「刻本 / 刻刀 / 刀刻」。<!-- term-ok -->
**指标不受影响**（Dice、墨量、chamfer、孔洞都是对图像测的）。

## 2. 语料实测（`work-c/page_stats.jsonl`）

| 指标 | 值 |
|---|---|
| PDF | 41 |
| 总页数 | **3,538** |
| 有可用红栏的文字页 | **3,428**（96.9%） |
| 无栏/地图/衬页 | 104 |
| 封面 | 6 |
| 内嵌图分辨率 | 全部 **300 dpi**（3,428 页 `eff_dpi` 均为 300） |
| 页面尺寸 | 每册、每页不同；150 dpi 渲染高度 3,900–6,100 px |
| 红栏宽（pitch）@150dpi | 中位 **268.5 px**，p10 216 / p90 327.5；折算 300 dpi 中位 537 px |
| 纠偏角 | 中位绝对值 0.158°，最大 1.2°（搜索上限） |
| 墨迹占比 | 中位 6.4% |
| 严格红像素占比 | 中位 3.4% |

**与旧交接文档的差异**：`docs/PROMPT-YONGLE.md` 写「532 页大页只有约 245 dpi」。逐页核对
`eff_dpi` 后**不成立**：41 册 3,538 页的内嵌图相对页面框都是 300 dpi（大页的内嵌图也
按比例更大，例如 7,215×12,070 px 对应 1,731×2,897 pt）。工作分辨率因此统一用 300 dpi。

## 3. 许可论证

### 3.1 原书

明嘉靖隆庆间内府重写本《永乐大典》，成书于 1562 年前后，作者逝世逾 400 年，
**在世界主要法域均属公有领域**。本线只使用其字形，不复制其文本内容。

### 3.2 扫描件

LOC 的数字化影像是对公版二维作品的**忠实再现**：

1. 按 *Bridgeman Art Library v. Corel Corp.*（S.D.N.Y. 1999）的通行观点，对二维公版作品的
   纯复制性拍摄不产生新的独创性；
2. 美国 *Feist Publications v. Rural Telephone Service*（1991）确立的独创性门槛同样排除
   「辛苦采集」本身；
3. 中国《著作权法》对复制品的独创性要求亦不覆盖纯扫描。

**本项目立场**：不对扫描图像主张任何权利；字形经切分、去噪、矢量化、归一化，是加工作品，
底层书法字形本身为公有领域。

### 3.3 未能取得的锚点原文

LOC 条目页（`https://www.loc.gov/item/2018421652/` 等）在本执行环境返回 **HTTP 403**
（Cloudflare 挑战），**未能取得 Rights & Access 声明的原文摘录**。因此本文不引用未核实的
LOC 原文，只记录条目 URL 与访问日期（2026-10-27）。若发布前需要逐字引用，请在可正常访问的
网络环境中补录。

书格（shuge.org）为分发渠道而非权利方；本线不依赖其授权主张（与 A/B 线一致）。

### 3.4 工具与模型

| 组件 | 许可 | 用途 |
|---|---|---|
| RapidOCR 3.10 | Apache-2.0 | OCR 运行时 |
| PP-OCRv6 small / PP-OCRv5 mobile | Apache-2.0（PaddlePaddle 模型） | 两个 OCR 见证 |
| LXGW WenKai | OFL 1.1（含 RFN） | 骨架先验与 GAN 输入 |
| potrace / potracer | GPL-2.0（工具，不链接进字体） | 位图矢量化 |

**未使用任何专有/商业字体**（含系统字体）做对照或测量。

## 4. 生成物（`work-c/`，全部不入库）

| 文件/目录 | 体积（实测/估计） | 内容 |
|---|---|---|
| `pages150/` | **12 GB** | 3,538 页 150 dpi 纠偏 JPEG（OCR 输入） |
| `cells/` | **9.7 GB**（1,214,431 个） | 单字灰度裁剪（只保留本格组件的墨） |
| `masks/` | **4.8 GB**（1,214,431 个） | 二值掩膜 |
| `cells.jsonl` | **614 MB** | 每格元数据（页/栏/行/坐标/字距/质量） |
| `ocr_v6.jsonl`、`ocr_v5.jsonl` | 待补 | 两套行级 OCR 结果（58,771 / 58,732 行） |
| `labeled.jsonl` | **697 MB** | 每格标签与见证一致性（1,044,983 格有标签，训练池；全量 1,187,881 格） |
| `chosen.jsonl` | **5,302 行** | 每字一个 medoid 样本（v1.2.1：沿用 v3d2 重切 + `--prefer-ab`） |
| `norm.json` | 待补 | 字面框归一化参数 |
| `pairs/pairs.npz` | **94 MB** | GAN 训练对（**5,002 对**；排除 300 个按字留出后） |
| `pairs_clean.npz` | **32 MB**（3,210 字） | 留出页干净集 |
| `pairs_clean_second.npz` | **25 MB**（2,445 字） | 同字第二样本，用于 chamfer 地板 |
| `ocr_bench.json` | **0.3 MB** | 700 个唯一人工审计格：**128 切格失败 + 572 切格通过**；其中 100 格已有 `content_oracle` 真值：90 正确 / 3 确认错标 / 1 存疑 / 6 不可读。原始 1,272 条见 `ocr_bench_raw.json`（572 条为锚点重复） |
| `content_oracle.json` | **27 KB** | oracle100 的 100 格盲读真值：94 可读（90 正确 + 3 错标 + R072 存疑），6 格不可读；含 file→label/verdict |
| `calib28_verdicts.json` | **8.4 KB** | calib28 构成：23 真错标 + 4 匹配器误报 + 1 无图；`ink_truth` 已按 owner csheet 红字补齐 27/28（C009=skip） |
| `ckpt/` | 每 10 轮约 400 MB | 快照 + best |

**磁盘**：`work-c/` 实测约 **28 GB**（含 `pages150` 12 GB、`cells` 9.7 GB、`masks` 4.8 GB）；
全流程含检查点预计 35–45 GB。清理策略：`cells/` 与 `masks/` 在发布后可按需重建
（重跑 `93_segment_c.py`，约 40 分钟 / 6 worker）。

**语料规模**：OCR 得到 58,771 行 / **1,297,735 字**；唯一汉字 **6,864**；双见证逐字一致率
**93.0%**（双见证格之间；含 a_only 90.3%）；最终真迹 **5,302 字**（基本区 25.26%，a_only 5.0%）；
另补 **42** 个标点/数字/空格（文楷 1.00），cmap **21,034**，CJK 基本区仍 20,992。

## 5. 校验和

```
68fd1aeb633c92cda954fcbbd7e0a65f2ec9bf921d65e9758276de17e37f5796  build/GuanGeKai-C-Regular.ttf
0cbb7cb17f4b02689e2d23f9c83d67bd9b3913cc5fc49646a5943e24b8089680  build/GuanGeKai-C-Real.ttf
9acc6463eb6bdcb9ad8852d08586a2bb7bddf5db81bdf40228453c2d3f4a713b  GuanGeKai-C-v1.2.1.zip
```

`release-c/SHA256SUMS` 是发布包的逐文件校验和（10 个文件，不含自身）。
**包内 README**：联合发版时已按当前 `README-C.md` 重打包（A v1.7.2 / B v1.2.4 / C v1.3.0 同步），
不再有术语 drift。`specimen-c.png` / `book-vs-font-c.jpg` 的图注本来就是「重寫本」，无旧词。
体积：Regular **15.20 MB**（15,201,924 B）、Real **4.61 MB**（4,608,864 B）、zip **14.75 MB**（14,751,732 B）。

## 6. 重建步骤

```bash
# 1. 页面普查 + 150 dpi 纠偏副本（约 6 分钟 / 6 worker）
python3 scripts/91_render_c.py --workers 6
python3 scripts/91b_recensus_c.py --workers 6     # 红栏检测改进后复算

# 2. 两个 OCR 见证（约 40 分钟 / 6 worker）
python3 scripts/92_ocr_c.py --workers 6

# 3. 切字（OCR 行框 + DP；约 1 小时 / 6 worker）
python3 scripts/93_segment_c.py --workers 6

# 4. 标签 + 留出页 + 选优 + 归一
python3 scripts/94_label_c.py
# 4.1 OCR 人工基准（700 唯一格；1,272 原始记录）
python3 scripts/99z_build_ocr_bench_c.py
python3 scripts/96_fix_labels_c.py --work work-c   # 10 个简体/繁体错配标签，必须在 05 之前
python3 scripts/74_make_holdout_c.py --frac 0.06
python3 scripts/99c_char_holdout_c.py --work work-c --n 300
python3 scripts/05_select.py --work work-c --min-samples 2 \
        --holdout-pages work-c/holdout_pages.json --prefer-clean bad --prefer-ab
python3 scripts/06_norm.py --work work-c --pitch-floor 180

> 注：仓库现有的 `work-c/pairs_clean.npz` 建于 2026-10-28 06:45，早于 `96_fix_labels_c.py`
> 的 55 格修复（23 重标 + 32 丢弃）。要逐位复现发布数字请保留该文件；重跑 `75` 会得到
> 同量级但非逐位相同的结果。

# 5. 真迹字体 + 配对 + 拟合
python3 scripts/76_build_real_c.py --close 3 --hole-repair   # 内含去噪 + 逐字墨量标定
python3 scripts/08_make_pairs.py --work work-c --exclude-chars work-c/char_holdout.json \
        --out work-c/pairs/pairs.npz
python3 scripts/73_fit_width_c.py

# 6. 干净集 + 训练（v1.3.0 是两阶段：主训练 80 + 80→90 续训）
python3 scripts/75_build_clean_c.py
# 6.1 主训练 80 轮
python3 scripts/21_train_gan.py --data work-c/pairs/pairs.npz \
        --val-data work-c/pairs_holdout.npz --out work-c/ckpt/v1.3/c.pt \
        --ckpt-dir work-c/ckpt/v1.3 --patchgan --hinge --aug \
        --epochs 80 --batch 16 --lr 2e-4
# 6.2 80→90 续训（v1.3 发布检查点 v1.3/c_ep090.pt；日志 work-c/logs-v1.3/train_v13_90.log）
python3 scripts/21_train_gan.py --data work-c/pairs/pairs.npz \
        --val-data work-c/pairs_holdout.npz --out work-c/ckpt/v1.3/c.pt \
        --ckpt-dir work-c/ckpt/v1.3 --resume work-c/ckpt/v1.3/c_ep080.pt \
        --patchgan --hinge --aug --epochs 90 --batch 16 --lr 1e-4

# 7. 评估 / 生成 / 合字 / 质检 / 打包
python3 scripts/82_eval_c.py --gan work-c/ckpt/v1.3/c_ep090.pt --n 300 --close 2 --sweep
python3 scripts/77_generate_c.py --method gan --workers 6 --res 512 --simplify 2.0 \
        --ckpt work-c/ckpt/v1.3/c_ep090.pt --threshold 0.30 --close 1 --blend 0.8 --struct-guard \
        --ink-lo 0.42 --ink-hi 1.20 --comp-tol 6 --out work-c/generated_gan.jsonl
mv work-c/generated_gan.jsonl work-c/generated.jsonl
python3 scripts/78_fill_fallback_c.py --work work-c
python3 scripts/79_build_full_c.py          # 写出 work-c/build_manifest.json（输入哈希）
python3 scripts/71_book_vs_font_c.py        # release 图，必须在 81 之前
python3 scripts/72_specimen_c.py
python3 scripts/80_qa_c.py        # C 线默认 --max-lost-frac 0.18、白名单已去掉 四/园
python3 scripts/71_holes.py --font build/GuanGeKai-C-Regular.ttf --n 300 --json work-c/holes_c.json
python3 scripts/84_accept_c.py
python3 scripts/81_package_c.py             # 先校验 build_manifest 的哈希，再打包
python3 scripts/83_verify_ab_c.py --write
python3 scripts/97_check_terms.py           # 术语检查
```

## 7. 检查点保留

沿用 AGENTS.md 的规则：每 10 轮快照；保留最终轮、验证最佳轮、核心轮次
50/100/150/200/300…；删除前先看 `work-c/ckpt/MANIFEST.json`
（`python3 scripts/31_ckpt_manifest.py --ckpt-dir work-c/ckpt`），删完立即重跑清单。

C 线现状（2026-10-28）：`c.pt` = ep52（训练实际停止轮）、`c_best.pt` = **ep45**（valDice 最佳）、
v1.3.0 发布用 **v1.3/c_ep090.pt**（0.470 / 6.38 / 8.3%）；v1.1.0 的 ep30 与 v1.2.0 的 ep34 是历史选点，见 EXPERIMENTS-C C/E15；`c_ep030_v100.pt` 是 v1.0.0 模型归档。

## 5.1 v1.3.0 校验和（2026-11-02）

v1.3.0 清理了 20 个全坏格，真迹 **5,257**；`自` 换回完整样本。
v1.2.1 的校验和仍保留在 §5，属历史版本，不是当前 `build/`。

```
765d08486b75da52e196cbe81570efd29226cea26d4f4198d6acd62dbf440f48  build/GuanGeKai-C-Regular.ttf
6caf9d82d71ad716eb5cbcf7a8c2947245756141a24b53f061130783752f359d  build/GuanGeKai-C-Real.ttf
4b4737758a342e8ddc59ac60615e846c760564faadfb87760f08bf70639f5498  GuanGeKai-C-v1.3.0.zip
```

`release-c/` 当前为 v1.3.0；v1.2.1 的 `release-c` 备份在
`work-c/v121_backup/release-c-v1.2.1/`。完整发布说明见 `docs/RELEASE-v1.3.0-C.md`。

## 5.2 work-c-big（大字实验，非发布链）

`work-c-big/` 是 C/E32 的大字字头实验工作区，**不属于 v1.2.1/v1.3.0 发布链**，也未纳入 `release-c/`。
体量：`du` 5.5 GB（apparent 5.93 GB，75 文件）；不是 10.9 GB。

主要产物：

```
work-c-big/chosen.jsonl        651
work-c-big/pairs/pairs.npz      651 对
work-c-big/pairs_clean.npz      109（页留出，但与训练同字，非 unseen）
work-c-big/ckpt/               ep10–120 + best + MANIFEST
work-c-big/generated.jsonl     gen 19,090 + base 1,251
work-c-big/report/             大字 vs C 面板、unseen 复跑
```

注意：`pairs_clean.npz` 是页留出，不是字级 unseen；C/E32 的 109 字面板含 62 个训练同字。
被审计确认的污染与回退口径更正见 `docs/EXPERIMENTS-C.md` C/E32。

## 5.3 C1/C2/C5 证据口径（2026-11-14）

**C1 300 字 unseen**：可复跑产物为 `work-c/eval_v130_unseen_c2.json`（c_ep090，n=300，`--close 2`）：
Dice **0.470** / chamfer **6.38** / broken **8.3%**，`_floor_same_char` n=800 chamfer 6.61。
`release-c.json` 旧值 0.4666 与旧产物 `eval_v121_ep090_unseen.json` 的 0.469/6.26/7.0
在当前 `pairs_holdout` 上都不能精确复现；以本次可复跑产物为准。

**C2 clean 0.471/6.19/12.0%**：来源是 `work-c/eval_v121_ep090.json`（c_ep090，n=200），
属 v1.2.1 继承值；v1.3.0 没有重测。`release-c.json` 的 `clean_n=3210` 是 `pairs_clean.npz`
数据集规模，不是评估样本量；已加 `clean_eval_n=200` 与 `clean_eval_source`。

**C5 未记录生成运行**：

```
初始日志 work-c/logs-v1.3/gen_v13_ep90.log
  2026-11-02 01:36:02；15,715 requested；fallback 836
最终 work-c/generated.jsonl
  2026-11-02 08:38:22；15,735 行；gen 14,422 + base 1,313
work-c/gan_fallback.json
  2026-11-02 08:38:15；17 项
```

结论：**确认存在一次晚于日志的最终生成运行**（08:38，未被 `gen_v13_ep90.log` 记录；
`finalize_c.sh` 的 77 步骤是候选命令，但没有对应日志）。15,715→15,735 的 20 行差值与
“v1.3 清理 20 个全坏格后重生成”一致，但不能仅凭计数把它归因为某个 repair 脚本；
以后重生成必须在 `work-c/logs-v1.3/` 留完整日志与命令。
