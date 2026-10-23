# AGENTS.md — 给接手的 agent

本项目：从明代刻本《四書白文》扫描本出发，做一套覆盖 CJK 基本区 20,992 字的 **馆阁体** 开源字体（OFL 1.1）。

**先读这三个文件，再动手：**

1. [`docs/PROJECT_STATE.md`](docs/PROJECT_STATE.md) —— 现状、决策、已知缺陷、未决问题、审计方法
2. [`docs/EXPERIMENTS.md`](docs/EXPERIMENTS.md) —— 17 组实验（E1–E17）的配置/指标/复现命令（含"第几轮训练"）
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

## 当前状态（v1.3.2）

- `build/GuanGeKai-Regular.ttf`：20,992 字 = 1,675 真跡 + 19,317 合成
- `build/GuanGeKai-Real.ttf`：仅 1,675 真跡
- 真字覆盖率 8% 是全局瓶颈；合成字结构 100% 正确，笔锋为程序化近似（v1.3 起有斜切端头与逐笔波动）

## 最短验证命令

```bash
python3 scripts/13_qa.py --font build/GuanGeKai-Regular.ttf   # 覆盖率/空字形
wc -l work/chosen.jsonl                                       # 应为 1675
python3 -c "import json;d=json.load(open('release/provenance.json'));print(sum(v=='real' for v in d.values()))"
```

## 下一步（v1.4.0 起三线并行，详见 docs/PLAN-v1.4.md）

三条线各自保留产物：**A 带状扫掠**（`--method ribbon`）/ **B zi2zi-GAN** / **C zi2zi-JiT 自训练权重**。

- A：墨量 1.077、端帽 KS 0.101、std 0.229。待做 —— **转折（横折方角）**、锐角内侧空洞、小字号回归。
- B：40 字无泄漏集 Dice 0.563、墨量 1.013、端帽 KS 0.048（ep100）；训练中（150 ep）。需结构闸门（孔洞/连通域）。
- C：上游权重不可用（LICENSE 只覆盖 "Software"）；计划用 MIT 代码 + 自有数据从头训练（`main_jit.py` 已验证可跑）。
- 换数据源（楷书字典刻本）是唯一能根本改变 8% 覆盖率的路线。

> 字重与风格结论以五项指标同时报告为准：Dice、墨量比、端帽 cap_mid、端帽 KS、笔内 std。
> Dice 单独会奖励加粗；`18_eval.py` 的 `width_ratio` 对细笔画不稳，不得用于字重结论。

## 文档约定

- 正文一律**简体中文**；`README.md` 面向使用者，保留繁体。
- 表格里只对**数字**与**判定**加粗；正文不用 emoji（总表的判定列除外）。
- 少用“也就是说/换句话说”，少用连续破折号；结论直接写，过程记录放进 REPORTS 的尾注。

## 常见坑

- OCR 必须 150 dpi + PP-OCRv6；72 dpi 只有 ~70% 准确率。
- 原书句读圈点是**红色**的；但我们拿到的 PDF **已被去色**（实测 `r−g` 最大仅 9–14，无红色像素），
  颜色分离在这份文件上无效，实际靠「厚度 + 连通域」判据剔除。若换未去色的扫描，`red_mask()` 可直接生效。
- 撇/捺常是独立连通域，必须两遍归属，否则笔画被截断。
- 字体家族名不能包含 LXGW 的 Reserved Font Name。
