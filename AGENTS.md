# AGENTS.md — 给接手的 agent

本项目：从明代刻本《四书白文》扫描本出发，做一套覆盖 CJK 基本区 20,992 字的 **馆阁体** 开源字体（OFL 1.1）。

**先读这三个文件，再动手：**

1. [`docs/PROJECT_STATE.md`](docs/PROJECT_STATE.md) —— 现状、决策、已知缺陷、未决问题、审计方法
2. [`docs/EXPERIMENTS.md`](docs/EXPERIMENTS.md) —— 32 组实验（E1–E32）的配置/指标/复现命令（含"第几轮训练"）
3. [`docs/DATA.md`](docs/DATA.md) —— 数据来源、许可、校验和、重建步骤

## 硬性约束

- **不要执行任何 git 写操作**（add/commit/reset/checkout）。仓库由用户本人管理。
- **不要修改** `data/vendor/zi2zi-JiT/`（第三方克隆 + 本地 MPS 补丁，见 PROJECT_STATE §7.3）。
- **不要**把 `史记...pdf` 的字形并入本字体：用户明确要求《史记》另立项目、单独训练。
- **不要**引入任何与 OFL 不兼容的授权数据（商业字库衍生的部件表、笔画表、字形数据）——
  这类数据只能做实验，不可进入发布字体；发布前逐一核对来源许可。
- **禁止使用任何专有/商业字体**（含操作系统自带的中文字体）——即使只做测量或对照。
  只允许 OFL / Apache-2.0 / UFL 等自由许可字体；基于专有字体测出的数字也不得作为决策依据。
- 大文件（PDF、`work/`、`data/models/`）不要加入版本库。
- **训练检查点不删**：`work/*.pt` 与 `work/ckpt/*` 是几小时算力的结果。真需要清理时先看
  `work/ckpt/MANIFEST.json`，并在 `docs/DATA.md` §6.5.1 记录删了什么、为什么。

## 当前状态（v1.3.5）

- `build/GuanGeKai-Regular.ttf`：20,992 字 = 1,675 真迹 + 19,317 合成（88.3% 经 ribbon 风格化，11.7% 回退裸文楷）
- `build/GuanGeKai-Real.ttf`：仅 1,675 真迹
- 真字覆盖率 8% 是全局瓶颈；合成字的笔画骨架取自霞鹜文楷，**拓扑与文楷一致（97%），但与刻本真迹仅 47%**——
  这部分差异继承自内容字体，不是渲染器引入的。笔锋为程序化近似（v1.3 起有斜切端头与逐笔波动）

## 最短验证命令

```bash
python3 scripts/13_qa.py --font build/GuanGeKai-Regular.ttf   # 覆盖率/空字形
wc -l work/chosen.jsonl                                       # 应为 1675
python3 -c "import json;d=json.load(open('release/provenance.json'));print(sum(v=='real' for v in d.values()))"
```

## 下一步（v1.4.0 起三线并行，详见 docs/PLAN-v1.4.md）

三条线各自保留产物：**A 带状扫掠**（`--method ribbon`）/ **B zi2zi-GAN** / **C zi2zi-JiT 自训练权重**。

- A（v1.3.5）：512 渲染+矢量化（potrace 税 +6.2%→0）、轮廓简化（23.3→14.9 MB）；88.3% 合成字经风格化。
  待做 —— **转折（横折方角，建议 miter join）**、小字号回归。
- B（E25/E26 干净集结论）：**最佳配置是「单实例 + PatchGAN + 约 15 轮」= 0.543**
  （旧单实例+全局D 150 轮是 0.526）。多实例是拖累：+全局D 0.523、+PatchGAN 峰值 0.520。
  E23 的"0.675"作废——`bench_unseen` 91/91 全在多实例训练集里。
  **泛化只认 `work/pairs_single.npz`（617 个只出现一次的字，从未训练）**：
  `python3 scripts/32_eval_clean.py --gan work/ckpt/attr_single_patch_ep015.pt`。
- **闸门不可用（E24）**：现行判据（连通域+字碗全等）在 B 类回退 79/91，其中 **78 字是误回退**，
  Dice 0.675 → 0.455。8 种候选判据里没有一种能同时保住风格与结构：IoU 类判据全拒
  （风格化后与文楷 IoU 只有 0.245），墨量判据几乎不保护结构。
  **不要再调这个闸门**（E24）。
- **E29 推翻了 E27 的否决策**：E27 用「与文楷拓扑全等」判定 GAN 结构崩坏，而该指标对 A 线循环
  （E28）。改用**以真迹为参照的分级骨架度量**（`scripts/34_struct_score.py`）：
  GAN ep15 的 Dice 0.540 vs ribbon 0.413、骨架 chamfer 6.68 vs 8.76、交叉点差 9 vs 13，
  **崩坏率（Dice<0.30）0.7% vs 5.7%**。视觉复核与指标一致。
  **B 线没有收束**：下一步是生成全量候选字体做字体级验收，不是在 91/150 小样本上争论。
- **B 线 M2 已成功（E32）**：5 层 hinge 判别器 + 首次数据增强 + 80 轮 →
  干净集 Dice 0.549（均值；中位 0.599）、骨架 chamfer **5.92**、len_ratio 0.886。
  真迹互比的同口径地板是 **5.16**，**差 0.77px / 15%，KS p<0.001——同一量级但未打平**。
  valDice 到 ep80 仍在涨（0.619），说明增强把过拟合推后了。
  当前最佳检查点：`work/ckpt/m2_ep080.pt`。
- C：上游权重不可用（LICENSE 只覆盖 "Software"）；计划用 MIT 代码 + 自有数据从头训练（`main_jit.py` 已验证可跑）。
- 换数据源（楷书字典刻本）是唯一能根本改变 8% 覆盖率的路线。
  **《史记》不在本项目内**（用户已决定另立项目），要用须先取得所有者明确同意并更新本文件。

> 字重与风格结论以五项指标同时报告为准：Dice、墨量比、端帽 cap_mid、端帽 KS、笔内 std。
> Dice 单独会奖励加粗；`18_eval.py` 的 `width_ratio` 对细笔画不稳，不得用于字重结论。

> **结构指标不作"与文楷拓扑全等"**（E28）：换真迹参照后 ribbon 17/150、GAN 16/150、文楷自己 17/150，
> 全员 ~11%，没有区分度；对 A 线还是循环论证（骨架本就取自文楷）。
> 结构评估用 `scripts/33_struct_metrics.py` 的维度化指标（重心/宽高比/横画角 KS/字碗差），
> 参照一律是真迹。

## 当前计划

**`docs/PLAN-v1.5.md`** —— 把 B 线（GAN）推到可验收，四个里程碑：
M0 墨量校准（0.5h）→ M1 目标图去模糊（1h）→ M2 5 层 hinge 判别器 + 数据增强 + 80 轮（5h）
→ M3 全量生成与字体级验收（2h）→ M4 512 重训（条件触发）。
每个里程碑只改一个变量，评估一律用 617 干净集 + 骨架分级度量，结果必须落盘。

## 发布流程（顺序固定，勿跳步）

改文档 / 改代码之后，**必须按这个顺序走完才算发布完成**：

```bash
python3 scripts/07_build_real.py --reuse-contours   # 1. 真字子集（无 work/masks 时用缓存）
python3 scripts/11_build_full.py            # 2. 完整字体
python3 scripts/13_qa.py --font build/GuanGeKai-Regular.ttf   # 3. 质检（应打印 real-subset ... OK）
python3 scripts/23_compare_all.py --n 120 --set work/eval_clean3.json  # 3.5 重出对比面板（docs/images/eval-panel*.png）
rm -rf release && python3 scripts/14_package.py               # 4. 重新打包（会复制根 README）
cd release && zip -q -r ../GuanGeKai-vX.Y.Z.zip . && cd ..    # 5. 出 zip
shasum -a 256 build/*.ttf GuanGeKai-vX.Y.Z.zip                # 6. 同步校验和到 DATA.md / PROJECT_STATE.md
```

**发布前必须核对三个数字**（任何一项不对就停下）：

| 检查 | 期望 |
|---|---|
| `13_qa` 覆盖率 | `20992/20992` |
| `13_qa` 的 `real-subset` 行 | `glyphs 1675 cmap 1675 -> OK` |
| `ls -lh build/*.ttf` | Regular ~14.9 MB、**Real ~3.3 MB**（若是 KB 级，说明真字没建出来） |

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
- 原书句读圈点是**红色**的；但我们拿到的 PDF **已被去色**（实测 `r−g` 最大仅 9–14，无红色像素），
  颜色分离在这份文件上无效，实际靠「厚度 + 连通域」判据剔除。若换未去色的扫描，`red_mask()` 可直接生效。
- 撇/捺常是独立连通域，必须两遍归属，否则笔画被截断。
- 字体家族名不能包含 LXGW 的 Reserved Font Name。
