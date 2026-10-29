# AGENTS.md — 给接手的 agent

本项目：从明代写本《四书白文》扫描本出发，做一套覆盖 CJK 基本区 20,992 字的 **馆阁体** 开源字体（OFL 1.1）。

**先读这三个文件，再动手：**

1. [`docs/PROJECT_STATE.md`](docs/PROJECT_STATE.md) —— 现状、决策、已知缺陷、未决问题、审计方法
2. [`docs/EXPERIMENTS.md`](docs/EXPERIMENTS.md) —— 40 组实验（E1–E40）的配置/指标/复现命令（含"第几轮训练"）
3. [`docs/DATA.md`](docs/DATA.md) —— 数据来源、许可、校验和、重建步骤

## 硬性约束

- **不要执行任何 git 写操作**（add/commit/reset/checkout）。仓库由用户本人管理。
- **不要修改** `data/vendor/zi2zi-JiT/`（第三方克隆 + 本地 MPS 补丁，见 PROJECT_STATE §7.3）。
- **不要**把 `史记...pdf` 的字形并入本字体：用户明确要求《史记》另立项目、单独训练。
  该任务已另立会话，交接提示词在 `docs/PROMPT-SHIJI.md`；
  产物固定为 `build/GuanGeKai-B-Regular.ttf` / `GuanGeKai-B-Real.ttf`（家族名 `GuanGe Kai B`），
  工作目录 `work-b/`，文档 `*-B.md`。**本会话（四书）不要碰这些路径。**
- **不要**引入任何与 OFL 不兼容的授权数据（商业字库衍生的部件表、笔画表、字形数据）——
  这类数据只能做实验，不可进入发布字体；发布前逐一核对来源许可。
- **禁止使用任何专有/商业字体**（含操作系统自带的中文字体）——即使只做测量或对照。
  只允许 OFL / Apache-2.0 / UFL 等自由许可字体；基于专有字体测出的数字也不得作为决策依据。
- 大文件（PDF、`work/`、`data/models/`）不要加入版本库。
- **并发上限（所有者明令）**：同时最多 **10 线程 / 20 核**。跑任何多进程脚本前必须做三件事：
  `torch.set_num_threads(1)`、`cv2.setNumThreads(1)`、环境变量
  `OMP_NUM_THREADS=MKL_NUM_THREADS=OPENBLAS_NUM_THREADS=1`；worker 数按 20 核反推
  （单 worker 实测约 2 核，故 `--workers ≤ 8`），**启动后用 `ps` 核对总 CPU ≤ 2000%**。
  2026-10-25 曾用 16 worker 把 32 核吃满，被所有者叫停。
- **训练检查点（所有者 2026-10-25 定的规则）**：
  - 训练时**每 10 轮存一个快照**（`--save-every 10`，已是默认值）；
  - 清理过程文件时保留三类：**最终一轮**、**验证最佳一轮**、
    **核心轮次 50 / 100 / 150 / 200 / 300 / 400 / 500…**；其余中间轮次可删。
    核心轮次是将来换配置重训时的对照锚点，别当垃圾清掉；
  - 正在推进的路线（当前 `m2_*`）在推进期间保留全部；
  - 任何删除先看 `work/ckpt/MANIFEST.json`，并在 `docs/DATA.md` §6.5.1 登记；
    **删完必须立刻重跑 `scripts/31_ckpt_manifest.py`**——这一步单独做已经漏过三次。

## 当前状态（v1.7.0）

- `build/GuanGeKai-Regular.ttf`：20,992 字 = 1,675 真迹 + 19,317 合成
  （**GAN 18,518 字 = 95.9%（ep90 17,790 + ep80 补位 728），ribbon 回退 799 字 = 4.1%**，
  见 E39/E40；发布口径见 `data/release-a.json`）
- `build/GuanGeKai-Real.ttf`：仅 1,675 真迹
- 真字覆盖率 8% 是全局瓶颈。v1.3.x 的合成字骨架取自文楷（结构=文楷结构）；
  **v1.5.0 起合成字由 GAN 生成**，笔画级结构更接近写本：干净集 Dice 0.414→0.549、
  骨架 chamfer 8.76→5.92（真迹互比地板 5.16，仍差 15%）。
- 已知偏差：合成字比真迹重约 17%（E34）。拆开是：**5–7% 字集构成**（生僻字本来墨多）+
  **约 5% 来自模型输出的字面偏小**（GAN 包围盒是真迹的 0.949，归一化放大后墨量跟着涨，E37）。
  模型逐字输出本身是准的（0.995）。
  **不要再做"轮廓层面积补偿"**：E37 已证明 potrace 不膨胀（轮廓/掩膜 = 0.9997），
  没有可补的对象；要修只能从模型侧（尺寸一致性）或归一化策略入手。

### C 线（《永乐大典》，v1.2.0）

- `build/GuanGeKai-C-Regular.ttf`：20,992 字 = **5,299 真迹 + 14,758 GAN + 935 带状回退（6.0%）**；
  `build/GuanGeKai-C-Real.ttf`：仅 5,299 真迹（基本区 **25.24%**，三条线里最高）。
- **v1.2.0 质量修复**（2026-10-29）：v3c 全量重切（两列墨迹中缝 + 每行白廊校验、`merged/tiny/full`；
  碎片过滤默认关闭），`05 --prefer-ab`；把 v1.1.0 的 ep30 在 v3c pairs 上以 lr 1e-4 微调到 **ep34**；
  页留出 **0.451 / 6.63 / 14.1%**，300 字 **0.584 / 5.38 / 1.3%**，ribbon **6.0%**。
- **v1.1.0 质量修复**（2026-10-28，回应「字重忽粗忽细/边缘毛糙/简体字怪」）：
  逐字墨量标定（真迹逐字墨量/文楷比从 0.42–0.98 收窄到 0.85–1.14，字体级 16/24/48px
  偏差 0.974/0.969/1.025/0.995）、追踪前去噪（`turdsize 3`）、
  `repair_counters` 移到字重标定之前（全字体孔洞丢失 5.6%→**1.4%** 全量，300 抽样 0.9%）、
  清理 10 个「简体码位 + 繁体字形」标签，再剔除碎片/错标（罎、讞、串），真迹 5,310→**5,299**（v1.2.0）；`05 --prefer-ab` 把 a_only 从 12.7% 降到 **5.04%**；墨量 gain 1.25（真迹/文楷 0.703，B 0.730）。
  简体码位加**结构守卫**（`--struct-guard`：GAN 输出组件数与文楷差 >2 时回落 ribbon），
  ribbon 占比 1.9%→6.0%（v1.2.0）。清理后从零重训（计划 80 轮，训到 **ep52** 停止；ep20–50 结构指标单调变差）。
- 发布包 `release-c/`、`GuanGeKai-C-v1.2.0.zip`（15 MB）；口径 `data/release-c.json`
  与 `work-c/accept_c.json`；文档 `README-C.md`、`docs/{PLAN,DATA,EXPERIMENTS,RELEASE-v1.2.0}-C.md`。
- **与 A/B 的根本差别：没有对照文本。** 标签靠 **PP-OCRv6 + PP-OCRv5 双见证**
  （全量 1,297,735 字，双见证一致率 **93.0%**；含单见证 90.3%），冲突（约 9%）丢弃；干净集按**页**留出
  （207 页 / 6%），不用“只出现一次的字”。**标签未经逐字人工校对**，发布说明已披露。
- 版面：朱丝栏 + 小字双行/大字字头混排，切字用 OCR 行框定行 + DP 切格（1,214,431 格，组件归属）；
  篆/隶页按 OCR 含「篆」或「隸+書」整页排除（222 页）。
- **v1.1.0 的发布检查点是 ep30**；v1.2.0 在 v3c 上微调到 **ep34**（页 0.451 / 300 字 0.584）。207 页留出集 n=800 上 ep20/30/40/50 的
  Dice 0.464/0.444/0.444/0.436、崩坏率 11.5/15.4/15.4/17.4%。ep20 结构最好，
  但字体级字重 1.19 过不了 0.90–1.15 的闸；ep30 字重 0.974/0.969/1.025/0.995，全项过闸。
  生成工作点 **thr +0.30 / close 1 / blend 0.8 / --struct-guard**。
- 共用脚本（`05_select`/`06_norm`/`08_make_pairs`）的 C 兼容改动已用 A 数据复跑验证：
  chosen 1,675 逐项一致、norm 与 HEAD 版一致、pairs 逐元素一致。
  **发版前必须跑 `python3 scripts/83_verify_ab_c.py`，必须打印 `A/B INTACT`。**
- 已知缺陷：`园`、`四` 的「囗」按写本风格开口，拓扑上无闭合孔（已从 C 线白名单移除并登记）。

## 最短验证命令

```bash
python3 scripts/13_qa.py --font build/GuanGeKai-Regular.ttf   # 覆盖率/空字形
wc -l work/chosen.jsonl                                       # 应为 1675
python3 -c "import json;d=json.load(open('release/provenance.json'));print(sum(v=='real' for v in d.values()))"
```

## 技术路线（v1.5.0 现状）

> **命名规范**（见 `docs/GLOSSARY.md`）：A/B/C 只指**字形线**（四书/史记/永乐大典）；
> 技术路线一律写方法名 `ribbon` / `zi2zi-GAN` / `zi2zi-JiT`（表格内可用短码 RT1–RT3）。
> `R0–R7` 保留给闸门判据（`30_gate_rules.py`），技术路线不得使用。**禁止再写「路线 A/B/C」。** <!-- term-ok -->

**发布版 = 真迹 1,675 + GAN 18,518（ep90 17,790 + ep80 补位 728）+ 带状扫掠回退 799。**
历史三条路线：**`ribbon` 带状扫掠**（v1.3.x 发布方案，现降级为回退兜底）/
**`zi2zi-GAN`**（v1.5.0 起主线）/ **`zi2zi-JiT`**（未启动）。`docs/PLAN-v1.4.md` 的"三线并行"已作废，当前计划见 `docs/PLAN-v1.5.md`。

- `ribbon`（v1.3.5，**已被 v1.5.0 取代**）：512 渲染+矢量化、轮廓简化；当年 88.3% 合成字经风格化。
  待做 —— **转折（横折方角，建议 miter join）**、小字号回归。
- `zi2zi-GAN`（**v1.5.0 采用**）：单实例 + 5 层 PatchGAN + hinge + 数据增强，80 轮 = 干净集 Dice 0.549 /
  chamfer 5.92。多实例是拖累（0.520），已被排除。
  **泛化只认 `work/pairs_single.npz`（617 个只出现一次的字，从未训练）**：
  `python3 scripts/32_eval_clean.py --gan work/ckpt/m2_ep080.pt`。
- **闸门不可用（E24）**：现行判据（连通域+字碗全等）在 B 类回退 79/91，其中 **78 字是误回退**，
  Dice 0.675 → 0.455。8 种候选判据里没有一种能同时保住风格与结构：IoU 类判据全拒
  （风格化后与文楷 IoU 只有 0.245），墨量判据几乎不保护结构。
  **不要再调这个闸门**（E24）。
- **E29 反转了 E27 的否决策**：E27 用「与文楷拓扑全等」判 GAN 结构崩坏，而那把尺子对 A 线循环
  （E28 实测：vs 真迹时 ribbon/GAN/文楷全是 ~11%，无区分度）。改用**以真迹为参照的分级骨架度量**
  （`scripts/34_struct_score.py`）后，GAN 的 chamfer 6.68→5.92、崩坏率 5.7%→0.7%。
- **M2（E32）是转折点**：5 层 hinge 判别器 + 首次数据增强 + 80 轮。
  真迹互比的同口径地板是 **5.16**，GAN **5.92**——**同一量级但未打平（差 0.77px / 15%，KS p<0.001）**。
  **加训到 150 轮已实测（E36）：与 80 轮完全持平**（Dice 0.543–0.548、chamfer 5.87–5.94），
  「欠训」假设被否证，模型在 ep60–80 就到顶。**不要再靠加轮数提升**，余量只在数据/容量/分辨率。
- `zi2zi-JiT`：上游权重不可用（LICENSE 只覆盖 "Software"）；计划用 MIT 代码 + 自有数据从头训练（`main_jit.py` 已验证可跑）。
- 换数据源（楷书字典类刻本）是唯一能根本改变 8% 覆盖率的路线。 <!-- term-ok -->
  **《史记》不在本项目内**（用户已决定另立项目），要用须先取得所有者明确同意并更新本文件。

> 字重与风格结论以五项指标同时报告为准：Dice、墨量比、端帽 cap_mid、端帽 KS、笔内 std。
> Dice 单独会奖励加粗；`18_eval.py` 的 `width_ratio` 对细笔画不稳，不得用于字重结论。

> **结构指标不作"与文楷拓扑全等"**（E28）：换真迹参照后 ribbon 17/150、GAN 16/150、文楷自己 17/150，
> 全员 ~11%，没有区分度；对 A 线还是循环论证（骨架本就取自文楷）。
> 结构评估用 `scripts/33_struct_metrics.py` 的维度化指标（重心/宽高比/横画角 KS/字碗差），
> 参照一律是真迹。

## 当前计划

**`docs/PLAN-v1.5.md`** —— 把 `zi2zi-GAN` 推到可验收，四个里程碑：
M0 墨量校准（0.5h）→ M1 目标图去模糊（1h）→ M2 5 层 hinge 判别器 + 数据增强 + 80 轮（5h）
→ M3 全量生成与字体级验收（2h）→ M4 512 重训（条件触发）。
每个里程碑只改一个变量，评估一律用 617 干净集 + 骨架分级度量，结果必须落盘。

## 发布流程（顺序固定，勿跳步）

改文档 / 改代码之后，**必须按这个顺序走完才算发布完成**：

```bash
python3 scripts/07_build_real.py --reuse-contours   # 1. 真字子集（无 work/masks 时用缓存）
python3 scripts/11_build_full.py            # 2. 完整字体
python3 scripts/13_qa.py --font build/GuanGeKai-Regular.ttf   # 3. 质检（应打印 real-subset ... OK）
python3 scripts/71_holes.py --font build/GuanGeKai-Regular.ttf --n 300 --json work/holes_a.json  # 3.4 孔洞审计（记录，不阻断）
python3 scripts/23_compare_all.py --n 40                              # 3.5 重出对比面板（默认用 617 干净字）
rm -rf release && python3 scripts/14_package.py               # 4. 重新打包（会复制根 README）
python3 scripts/95_compare_lines.py                    # 4.5 三线对照图（A/B/C 同一文字并排，出 docs/images/lines-compare.png）
python3 scripts/98_style_sheet.py --line A             # 4.6 来源分层图（真迹/GAN/回退 分开看，出 docs/images/style-A.png）
cd release && zip -q -r ../GuanGeKai-vX.Y.Z.zip . && cd ..    # 5. 出 zip
shasum -a 256 build/*.ttf GuanGeKai-vX.Y.Z.zip                # 6. 同步校验和到 DATA.md / PROJECT_STATE.md
python3 scripts/97_check_terms.py                            # 7. 术语检查（必须 TERMS OK；标准见 docs/GLOSSARY.md）
```

**发布前必须核对三个数字**（任何一项不对就停下）：

| 检查 | 期望 |
|---|---|
| `13_qa` 覆盖率 | `20992/20992` |
| `13_qa` 的 `real-subset` 行 | `glyphs 1675 cmap 1675 -> OK` |
| `ls -lh build/*.ttf` | Regular ~15 MB、**Real ~3.3 MB**（若是 KB 级，说明真字没建出来） |
| `71_holes` 的 `holes lost` | 不高于上一版（当前基线 **1.9%**，见 `work/holes_a.json`） |
| `95_compare_lines` 出的三线对照图 | 三条线并排看不出「某条线整体偏细/偏粗/缺笔画」；发现即为回归 |
| `98_style_sheet` 出的 `style-A.png` | 真迹行与 GAN 行风格连续；回退行若明显「等宽细笔」属已知，但占比不应升高 |
| `97_check_terms.py` | 打印 `TERMS OK`（白名单与「已知遗留」不算） |

**踩过的坑**：
1. 先打包、后改 README，导致包内说明落后于仓库（改过 README 必须重跑第 4–6 步）。
2. 删掉 `work/masks` 后重跑 `07_build_real.py`，它产出 0 字形却仍写出文件，并把
   `work/real_contours.jsonl` 截断为 0 字节；因为输出被重定向到 /dev/null，没人看到 `glyphs 0`，
   最终打出了只有 1 个字形的 `GuanGeKai-Real.ttf`。**现在 07/11/13 都会在数量异常时中止。**
3. 把人工策展的 `docs/images/book-vs-font.png`（左：原书页面；右：同段文字用本字体排版）
   当成"可自动生成的图"覆盖掉了。**人工资产不在脚本的生成范围内：覆盖任何图片/文档前先看内容，
   能生成的图与手工拼图分开命名（如 `glyph-pairs.png` 与 `book-vs-font.png`）。**

## 文档约定

- **`README.md` 保留繁体**（面向使用者）；**其余文档一律简体中文**。
- 三处例外，保持原样不转换：
  1. 书名《四书白文》在简体文档中写作简体；引用原书原名时可保留繁体；
  2. OFL 保留字体名的正式写法 `霞鹜/霞鶩/落霞孤鹜/落霞孤鶩/LXGW` 原样引用（DATA §3）；
  3. 讨论异体字时的对照形式（如 `爲/为`、`雲/云`）保留繁体一侧。
- 表格里只对**数字**与**判定**加粗；正文不用 emoji（总表的判定列除外）。
- 少用“也就是说/换句话说”，少用连续破折号；结论直接写，过程记录放进 REPORTS 的尾注。

## 常见坑

- OCR 必须 150 dpi + PP-OCRv6；72 dpi 只有 ~70% 准确率。
- 原书句读圈点是**红色**的，**源 PDF 也是彩色的**（`get_pixmap` 出来 `r−g` 最大约 103）。
  `ink_mask()` 的 `red_mask()` **一直在生效**。全库 410 页实测：正文页约 **0.1–0.4%**（中位 0.27%），
  但跨度极大（p95 **19.97%**、最大 **97.99%**，有整页发红的例外，见 `docs/ERRATA.md` E5）。
  四书这份红色标记本来就少，所以收益接近 0。
  **注意**：仓库里 `work/cells`、`work/masks` 是单通道灰度，**不要拿它们测颜色**——
  早期"PDF 已被去色（`r−g` 最大 9–14）"的结论就是这么误测出来的，源文件其实是彩色的。
  《永乐大典》（C 线）红像素占 4.4%（朱丝栏 + 句读），颜色分离在那里才有大用。
- 撇/捺常是独立连通域，必须两遍归属，否则笔画被截断。
- 字体家族名不能包含 LXGW 的 Reserved Font Name。
