# AGENTS.md — 给接手的 agent

本项目：从明代刻本《四書白文》扫描本出发，做一套覆盖 CJK 基本区 20,992 字的 **馆阁体** 开源字体（OFL 1.1）。

**先读这三个文件，再动手：**

1. [`docs/PROJECT_STATE.md`](docs/PROJECT_STATE.md) —— 现状、决策、已知缺陷、未决问题、审计方法
2. [`docs/EXPERIMENTS.md`](docs/EXPERIMENTS.md) —— 7 组实验的配置/指标/复现命令（含"第几轮训练"）
3. [`docs/DATA.md`](docs/DATA.md) —— 数据来源、许可、校验和、重建步骤

## 硬性约束

- **不要执行任何 git 写操作**（add/commit/reset/checkout）。仓库由用户本人管理。
- **不要修改** `data/vendor/zi2zi-JiT/`（第三方克隆 + 本地 MPS 补丁，见 PROJECT_STATE §7.3）。
- **不要**把 `史记...pdf` 的字形并入本字体：用户明确要求《史记》另立项目、单独训练。
- **不要**引入 Arphic Public License 的数据（MakeMeAHanzi `graphics.txt`、computer-grass 字形、AR PL UKai）——
  与 OFL 不兼容。IDS 数据只可用于实验，不可进入发布字体。
- **禁止使用任何专有字体**（华文/方正/汉仪/微软雅黑/苹方等系统字体）——即使只做测量或对照。
  只允许 OFL / Apache-2.0 / UFL 等自由许可字体；基于专有字体测出的数字也不得作为决策依据。
- 大文件（PDF、`work/`、`data/models/`）不要加入版本库。

## 当前状态（v1.2.0）

- `build/GuanGeKai-Regular.ttf`：20,992 字 = 1,675 真跡 + 19,317 合成
- `build/GuanGeKai-Real.ttf`：仅 1,675 真跡
- 真字覆盖率 8% 是全局瓶颈；合成字结构正确但无笔锋

## 最短验证命令

```bash
python3 scripts/13_qa.py --font build/GuanGeKai-Regular.ttf   # 覆盖率/空字形
wc -l work/chosen.jsonl                                       # 应为 1675
python3 -c "import json;d=json.load(open('release/provenance.json'));print(sum(v=='real' for v in d.values()))"
```

## 下一步（已排序，详见 PROJECT_STATE §8）

1. 骨架 + 笔刷引擎（许可干净，1–2 天）
2. zi2zi-JiT LoRA 全量重训 1.5–2 小时（需先确认权重许可）
3. 《史记》独立项目（先做页面去卷曲）

## 常见坑

- OCR 必须 150 dpi + PP-OCRv6；72 dpi 只有 ~70% 准确率。
- 本书的句读圈点是**黑色印刷**，不是朱笔；颜色分离无效，要用厚度判据。
- 撇/捺常是独立连通域，必须两遍归属，否则笔画被截断。
- 字体家族名不能包含 LXGW 的 Reserved Font Name。
