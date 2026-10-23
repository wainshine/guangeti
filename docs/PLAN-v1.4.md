# v1.4.0 三线并行计划（2026-10-23 起）

从 v1.4.0 开始，**三条技术路线并行推进，各自的产物独立保留**，不再只保留最后打包的那一个。

## 路线 A —— 带状扫掠（v1.3.x 延续，主推）

- 代码：`scripts/brush_lib.render_ribbon` + `10_generate.py --method ribbon`
- 产物：`build/GuanGeKai-A-ribbon.ttf`
- 现状：墨量 1.077、端帽 KS 0.101、笔内 std 0.229（真迹 1.000 / — / 0.248）
- 参考：[qiji-font](https://github.com/LingDong-/qiji-font) 的取字流程（视觉居中、双阈值保细节）
  —— 实测视觉中心与 bbox 中心相差仅 0.030–0.032 em（p90 0.063），暂不值得改。
- 待做：
  1. **转折（横折方角）**：目前转折是圆角，是与刻本最明显的差异
  2. 锐角内侧的 potrace 空洞（如 `仲`）
  3. 小字号（12–16 px）可读性回归

## 路线 B —— zi2zi-GAN

- 代码：`scripts/21_train_gan.py`（原版 zi2zi 配方的独立 PyTorch 重实现，Apache-2.0 参考、无预训练权重）
- 产物：`build/GuanGeKai-B-gan.ttf`
- 现状：150 epoch 训练中；40 字无泄漏集 Dice 0.554、墨量 0.922、端帽 KS 0.101、std 0.249
- 已知问题：`丂`/`丏` 等字孔洞数错误，需要结构闸门；对训练集外的字（ep52 起）可生成但质量无真值可评
- 待做：
  1. 训练到 150 epoch，按 epoch 20/50/100/150 各评估一次
  2. 结构闸门：孔洞数 / bbox IoU / 连通域数，不通过回退到路线 A
  3. 加粗前后的端帽保持性（E17 已证：均匀加粗会毁掉端帽）

## 路线 C —— zi2zi-JiT（自训练权重）

- 代码：`data/vendor/zi2zi-JiT`（MIT，**只读，不修改**）
- 现状：上游预训练权重**不可用**（LICENSE 写的是 "MIT License (Software)"，权重无许可），
  因此当前只能把 LoRA-600 的输出当作**评价参考**（端帽 KS 0.093），不能进入发布
- 计划：用 **MIT 代码 + 我们自己的数据从头训练**（`main_jit.py`，已验证在 MPS 可跑，45 s/epoch）
- 产物：`build/GuanGeKai-C-jit.ttf`
- 待做：
  1. 先跑 300 epoch（约 4 小时）看趋势
  2. 若可用，与路线 A 组成「C 笔形 + A 结构闸门」

## 产物命名

```
build/GuanGeKai-A-ribbon.ttf   路线 A（当前发布 = v1.3.2 的 build/GuanGeKai-Regular.ttf）
build/GuanGeKai-B-gan.ttf      路线 B
build/GuanGeKai-C-jit.ttf      路线 C
release/                       只放当前被选为“发布”的那一条线
```

## 评估口径（三条线共用）

- 评估集：`work/eval_clean2.json`（91 字，同时不在 GAN/U-Net 与 LoRA 训练集里）
- 指标：Dice、墨量比、端帽 cap_mid、端帽 KS、笔内 std —— **五项必须同时报**，
  Dice 单独没有意义（它奖励加粗）
- 每次评估出一份 `docs/REPORTS/YYYY-MM-DD-*.md`，含两个面板（有真迹 / 无真迹）
