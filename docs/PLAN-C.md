# C 线计划：用《永乐大典》美国藏本做 GuanGeKai-C

> 状态：**v1.2.0 已发版**（2026-10-29）。本线产物 `build/GuanGeKai-C-*`、`work-c/`、`release-c/`，
> 文档 `README-C.md`、`docs/*-C.md`。A 线（`build/GuanGeKai-*`、`work/`、`release/`）与
> B 线（`build/GuanGeKai-B-*`、`work-b/`、`release-b/`）的路径**一律不写**。

## 1. 目标与产物

| 项 | 内容 |
|---|---|
| 源数据 | `永乐大典美国藏本/` 41 册 PDF，3,538 页；明嘉靖隆庆间内府重写本；美国国会图书馆藏，书格整理发布 |
| 产物 | `build/GuanGeKai-C-Regular.ttf`（全字集）、`build/GuanGeKai-C-Real.ttf`（仅真迹） |
| 家族名 | `GuanGe Kai C` / PS 名 `GuanGeKai-C-Regular`、`GuanGeKai-C-Real` |
| 发布包 | `release-c/` + `GuanGeKai-C-v1.2.0.zip` |
| 工作目录 | `work-c/` |
| 覆盖目标 | CJK 基本区 20,992 字 |

## 2. 语料事实（实测）

| 项 | 实测值 |
|---|---|
| PDF / 页数 | 41 / 3,538 页（其中 **3,428 页**有可用红栏，104 页无栏或为地图/衬页，6 页封面） |
| 内嵌图 | 全部 **300 dpi**（`page_stats.jsonl` 的 `eff_dpi` 全为 300；此前“部分 245 dpi”的说法不成立） |
| 版面 | 单叶一页；朱丝栏；**正文多为小字双行**（每红栏两行），字头/标题为大字单行（占满一栏） |
| 字距 | 红栏宽 430–1100 px@150dpi（中位 269），折算 300 dpi 中位 **538 px**；小字单字前进约其一半 |
| 红色 | 朱丝栏 + 句读 + 少量红笔标注；`r−g` 可达 90；严格红掩膜占 3–4% |
| OCR 规模 | 58,771 行 / **1,297,735 字**（v6，3428 页）；v5 为 58,732 行 / 1,265,711 字 |
| 双见证一致率 | **91.1%**（全量，行级对齐后逐字比较） |
| 卷首/篆隶页 | **222 页**（按 OCR 文本含「篆」或「隸+書」整页排除，占 6.5%） |
| 多抄手 | 嘉靖录副由多人分抄，风格有差异；本版先单模型混合，按册报告指标 |
| 破损 | 虫蛀、水渍、撕裂、边缘残缺；切字阶段按质量标记，不指望模型扛 |

## 3. 与 A/B 的三处根本差别

1. **没有对照文本**。识典古籍最多到卷 7,602，本批是 6,831–19,792，41 册里只有卷 6831–6832
   落在其覆盖内且未确认有录文。所以标签不能靠“OCR + 对齐”，只能靠**多见证 + 视觉一致性**。
2. **双字号混排**。同一栏里既有占满整栏的大字，也有两行并排的小字，固定字距必然切错一半。
   本线用 **OCR 行框**确定行结构（大字行框≈整栏宽、小字行框≈半栏宽），再按 OCR 字数沿 y 切格。
3. **篆/隶/草集中在“六書/字源”页**。注意：**不能用“永樂大典卷之…”判卷首**——这个书名
   也印在正文叶的版心边栏上（前 1,040 页里 73 页命中，绝大多数是正文）。可用的标记是
   页面 OCR 文本含「篆」，或同时含「隸/隷」与「書」；整页排除（222 页，6.5%），正文只收楷书。

## 4. 流水线（脚本 → 产物）

| 阶段 | 脚本 | 产物 | 说明 |
|---|---|---|---|
| 0 普查 | `90_survey_c.py` | `work-c/page_survey.jsonl` | 早期试验；正式普查已并入 91 |
| 1 渲染+纠偏 | `91_render_c.py` | `work-c/pages150/*.jpg`、`page_stats.jsonl` | 150 dpi 纠偏副本供 OCR；300 dpi 在阶段 3 重渲染 |
| 1b 复算 | `91b_recensus_c.py` | 更新 `page_stats.jsonl` | 红栏检测改进后不必重渲染 |
| 2 双引擎 OCR | `92_ocr_c.py` | `work-c/ocr_v6.jsonl`、`ocr_v5.jsonl` | v6=PP-OCRv6 彩色；v5=PP-OCRv5 去红+拉伸+1.3× |
| 3 切字 | `93_segment_c.py` | `work-c/cells/`、`masks/`、`cells.jsonl` | OCR 行框 + 逐行 DP 切字；记录 `cpitch`/`slot`/质​量标记 |
| 4 标签 | `94_label_c.py` | `work-c/labeled.jsonl`、`label_report.json` | 行级对齐；一致才给标签，冲突置空并记录原因；篆隶页整页置空 |
| 4b 留出页 | `74_make_holdout_c.py` | `work-c/holdout_pages.json` | 按册分层抽 6%，整页留出 |
| 5 选优 | `05_select.py --work work-c --workers 6 --holdout-pages … --prefer-clean bad --drop-if-all-flagged` | `work-c/chosen.jsonl` | 每字一个 medoid；留出页不参与；全样本都坏的字直接丢弃（碎片不能进真迹字体） |
| 6 归一 | `06_norm.py --work work-c --pitch-floor 180` | `work-c/norm.json` | 用 `cpitch`，不是栏距 |
| 7 真迹字体 | `76_build_real_c.py --close 3 --hole-repair` | `build/GuanGeKai-C-Real.ttf` | 300 dpi，counter 修复 |
| 8 配对 | `08_make_pairs.py --work work-c --out work-c/pairs/pairs.npz` | 训练对 | 必须显式 `--out` |
| 8b 宽度/墨量拟合 | `73_fit_width_c.py` | `work-c/stroke_rel_width.npy`、`ribbon_fit.json` | C 自己的曲线，不复用 A/B |
| 9 干净集 | `75_build_clean_c.py` | `work-c/pairs_clean.npz` | 留出页上的多见证字，一处一字 |
| 10 训练 | `21_train_gan.py --data work-c/pairs/pairs.npz --out work-c/ckpt/c.pt --ckpt-dir work-c/ckpt --patchgan --hinge --aug` | `work-c/ckpt/c_ep*.pt` | 单实例 + 5 层 PatchGAN + hinge + 增强，实际 30 轮（ep20–30 平台） |
| 11 评估 | `82_eval_c.py` | `work-c/eval_c.json` | 五项指标 + chamfer + 崩坏率 |
| 12 全量生成 | `77_generate_c.py --method gan … --out work-c/generated_gan.jsonl` | 16k+ 字 | 守卫回退 ribbon |
| 13 补位 | `78_fill_fallback_c.py` | `work-c/generated.jsonl` | |
| 14 合字 | `79_build_full_c.py` | `build/GuanGeKai-C-Regular.ttf` | |
| 15 质检/验收/打包 | `80_qa_c.py`、`84_accept_c.py`、`81_package_c.py` | `release-c/` | 硬闸同 A/B |
| 16 A/B 校验 | `83_verify_ab_c.py` | `work-c/verify_ab.json` | 发版前必须 `A/B INTACT` |

## 5. 标签体系（本线核心）

```
每页：PP-OCRv6 行框 ──┐
                      ├─ 行级文本对齐 → 逐字一致才给 silver 标签
      PP-OCRv5 行框 ──┘
      （不同引擎 + 不同预处理，错误不完全相关）

筛选：同页同栏的字框宽度 → 大字/小字（不靠固定字距）
      OCR 字数 = 硬约束 → DP 在低墨行切格
      切格质量（edge/fill/宽高）→ bad 标记，选优时降权

干净集：整页留出（6%），不是“只出现一次的字”
```

**为什么不把“只出现一次的字”当测试集**：没有参照文本时，单次字 = 只有一个见证的标签，
是全库最不可信的一批；拿它当测试集会同时低估质量、又不可解释。

## 6. 已知风险与对策

| 风险 | 现状 | 对策 |
|---|---|---|
| OCR 系统性误读（曰/日、己/已、刺/剌） | 两引擎同错时无法发现 | 抽样人工核（见 §8）；字形一致性抽检；发布说明如实披露 |
| 双行小注切错半字 | 行框宽度可区分大小字，DP 切格 | `bad` 标记 + medoid 选优；抽样复核 |
| 卷首篆/隶混入 | 卷首有“永樂大典卷之…”标题 | 按页排除；正文抽检 |
| 破损/污渍格 | 少量 | `bad` + 选优；不专门修复 |
| 真迹字量未知 | 预计 4,000–7,000 | 覆盖率如实报告；不足时以 GAN 补 |

## 7. 发布口径（v1.2.0）

- 版本 **v1.2.0**；`data/release-c.json` 记录 checkpoint（v1.1.0 ep30 在 v3c pairs 上 lr 1e-4 微调到 **ep34**）、
  阈值 0.30、close 1、blend 0.8、hole_repair、`--struct-guard`、逐字墨量标定、留出页比例。
- v1.2.0 的 v3c 重切、中缝校验、ep34 微调见 `EXPERIMENTS-C.md` C/E15–C/E30 与 `work-c/logs-v1.2.0/`。
- 发版前硬闸（2026-10-28 全部通过）：
  - `80_qa_c.py`：覆盖率 20,992；无空/过小/过大字形；真迹子集数量与 `chosen.jsonl` 一致；孔洞审计达标；
  - `83_verify_ab_c.py`：`A/B INTACT`；
  - `84_accept_c.py`：合成/真迹字重比 1.00±0.10。
- A/B 同步发版：见 `docs/RELEASE-v1.2.0-C.md`。

## 8. 人工核的边界

执行本任务的 AI 会话**不能替代所有者做最终人工核**。本线提供：
1. `work-c/clean_sheet.png` 等接触表（字 + 标签并排），供所有者抽查；
2. 抽样清单（页码、格坐标、裁切图、标签），格式与 B 线一致；
3. 自动闸门（多见证一致率、崩坏率、孔洞率）。

**发布说明中必须写明：标签来自双引擎一致，未经逐字人工校对。**
