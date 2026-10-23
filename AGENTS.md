# AGENTS.md — 给接手的 agent

本项目：从明代刻本《四书白文》扫描本出发，做一套覆盖 CJK 基本区 20,992 字的 **馆阁体** 开源字体（OFL 1.1）。

**先读这三个文件，再动手：**

1. [`docs/PROJECT_STATE.md`](docs/PROJECT_STATE.md) —— 现状、决策、已知缺陷、未决问题、审计方法
2. [`docs/EXPERIMENTS.md`](docs/EXPERIMENTS.md) —— 21 组实验（E1–E21）的配置/指标/复现命令（含"第几轮训练"）
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

## 当前状态（v1.3.4）

- `build/GuanGeKai-Regular.ttf`：20,992 字 = 1,675 真迹 + 19,317 合成（90.0% 经 ribbon 风格化，10.0% 回退裸文楷）
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

- A（v1.3.4）：掩膜级 Dice 0.414 / 墨量 1.068 / 端帽 KS 0.063；90.0% 合成字经风格化。
  待做 —— **转折（横折方角，建议 miter join）**、高分辨率矢量化（512px 可把 potrace 税从 +10% 降到 +5%）、小字号回归。
- B（ep150 已完成）：见过的字 Dice 0.803 / 墨量 0.997 / 端帽 KS 0.048；
  没见过的字 0.552 / 0.993 / 0.039；书中没有的字拓扑一致 116/150（ribbon 145/150）。
  **拓扑闸门已试（E20）**：混合方案 Dice 0.490、拓扑 147/150，但因依赖 390 MB 检查点与三个经验门限，**未发布**。
- C：上游权重不可用（LICENSE 只覆盖 "Software"）；计划用 MIT 代码 + 自有数据从头训练（`main_jit.py` 已验证可跑）。
- 换数据源（楷书字典刻本）是唯一能根本改变 8% 覆盖率的路线。

> 字重与风格结论以五项指标同时报告为准：Dice、墨量比、端帽 cap_mid、端帽 KS、笔内 std。
> Dice 单独会奖励加粗；`18_eval.py` 的 `width_ratio` 对细笔画不稳，不得用于字重结论。

## 发布流程（顺序固定，勿跳步）

改文档 / 改代码之后，**必须按这个顺序走完才算发布完成**：

```bash
python3 scripts/07_build_real.py            # 1. 真字子集
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
| `ls -lh build/*.ttf` | Regular ~22 MB、**Real ~3.1 MB**（若是 KB 级，说明真字没建出来） |

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
