# 实验记录（可复现）

> 本文件记录本项目所有"生成 19,317 个缺字"的尝试、配置与客观指标。
> 指标统一为：**二值化 Dice**（预测墨迹 ∩ 真跡 / 并集×2），在留出字上计算；越高越好。
> 参考基线：**直接拿霞鹜文楷当输出 = 0.431**（即"什么都不做"的分数）。

---

## 训练轮次一览（回答"这是第几轮"）

| 轮次 | 模型 | 脚本 | 状态 | 指标 |
|---|---|---|---|---|
| 第 1 轮 | 自训 U-Net v1（256²，脏目标） | `09_train.py`（旧） | 停于 ep16 | val L1 0.202 |
| 第 2 轮 | 自训 U-Net v2（2 通道 + GroupNorm） | `09_train.py` | 跑完 45 ep | val L1 0.210 |
| 第 3 轮 | 自训 U-Net v3（128² patch + Dice） | `09_train_b.py` | 停于 ep107 | **Dice 0.441** |
| 第 4 轮 | zi2zi-JiT **LoRA 微调**（第一个外部预训练模型） | `lora_single_gpu_finetune_jit.py` | 跑完 40 ep / 1,240 步 | Dice 0.514 |

> 另有一次 **zi2zi-JiT 零样本**推理（E5），不涉及训练。
> 所以：**自训模型到第 3 轮为止；算上 LoRA，一共进行了 4 轮训练。**

---

## 指标口径

```python
def dice(pred_mask, target_mask):
    a, b = pred_mask > 127, target_mask > 127   # 或 <128，取决于图片极性
    return 2 * (a & b).sum() / (a.sum() + b.sum())
```

留出集：`data/zi2zi_ds2/test.npz` 的 8 字（zi2zi 系列），或 `work/pairs/pairs.npz` 的
120 字验证集（自训 U-Net）。**注意：8 字样本太小，zi2zi 的 0.528 有 ±0.05 的波动。**

---

## 总表

| # | 方案 | 配置摘要 | 指标 | 判定 |
|---|---|---|---|---|
| E0 | 笔墨滤波（发布版） | 横膨+竖蚀+闭运算 | 未测（结构 100%） | 保底方案 |
| E1 | 自训 U-Net v1 | 256², 1ch, BatchNorm+残差, 脏目标 | val L1 0.202（零输出 0.235） | ❌ 鬼影 |
| E2 | 自训 U-Net v2 | 256², 2ch, GroupNorm, 干净二值目标 | val L1 0.210 | ❌ 鬼影 |
| E3 | 自训 U-Net v3 | 128² patch, 2ch, BCE+Dice, 干净掩膜 | **Dice 0.441**（基线 0.431） | ❌ 无提升 |
| E4 | IDS 部件拼字 | cjkvi-ids + 真字部件 | 覆盖率 **6.0%**（1,166/19,317） | ❌ 不可全量 |
| E5 | zi2zi-JiT 零样本 | B/16, heun 25 步, cfg 2.6 | **Dice 0.528**（基线 0.309） | ✅ 风格最佳，结构有幻觉 |
| E6 | zi2zi-JiT + LoRA | 500 字, 40 ep, 1,240 步, 5:52 | Dice 0.514 | ❌ 欠训，无提升 |
| E7 | 骨架+笔刷原型 | skimage skeleton + 变宽圆盘 | 未量化 | 🚧 方向可行，工程量大 |

---

## E1 — 自训 U-Net v1（像素级风格迁移）

- 脚本：`scripts/09_train.py`（旧版）
- 数据：`work/pairs/pairs.npz`，2,185 组（霞鹜文楷 256² → 刻本裁剪 256²）
- 问题：目标来自灰度裁剪的二值化，**含印刷圈点、被截断的撇捺**；模型学到的是噪声
- 配置：U-Net base32 depth4，BatchNorm，残差连接，BCE + 0.5·L1 + 2·边缘梯度，80 epoch（实际到 ep16）
- 结果：val L1 0.202（"全零"基线 0.235，恒等 0.259）
- 目测：笔画发虚、粘连，阈值化后破碎
- 结论：**失败**。根因判断为训练目标脏 + 欠拟合。

## E2 — 自训 U-Net v2

- 脚本：`scripts/09_train.py`（2 通道版）
- 改进：输入加距离变换通道；GroupNorm 取代 BatchNorm；目标换成干净二值（但还是旧提取）
- 配置：256²，batch 16，lr 8e-4，45 epoch（1,171 s）
- 结果：val L1 0.210，best 0.2103
- 目测：仍是"鬼影"
- 结论：**失败**。此时意识到目标本身有问题（圈点/断笔），转向先修数据。

## E3 — 自训 U-Net v3（patch 训练 + Dice）

- 前置：v1.1 切字修复完成（黑圈点剔除、两遍归属、掩膜直出）
- 脚本：`scripts/09_train_b.py`
- 数据：1,675 组干净配对；128² 随机 patch；2 通道（raster + DT）
- 配置：U-Net base32，GroupNorm，BCE + Dice，batch 32，lr 3e-4，OneCycle，120 epoch（实际到 107）
- 结果：soft valDice 0.487（ep5 曾达 0.564，之后过拟合下降）；**二值化 Dice 0.441 vs 恒等 0.431**
- 目测：结构对、笔画软；阈值化后缺口多
- 结论：**失败**（+0.010，无实用价值）。

## E4 — IDS 部件拼字

- 脚本：`scripts/ids_build.py`（解析器 + 12 个算子的排版引擎）
- 数据：`data/ids/ids.txt`（cjkvi-ids，88,937 条）
- 覆盖率（对 19,317 缺字）：
  - 完全可用真字拼出：**1,166（6.0%）**
  - 部分真字 + 基底部件：16,810（87.0%）
  - 无法分解：1,506（7.8%）
- 目测：`只` 的口过小、`企` 上部错位、`吉` 的口位置错；比例规则是瓶颈
- 结论：**不用于全量**。规则体系（约 120 条比例规则）是数天级工程，且 87% 混拼仍会风格打架。

## E5 — zi2zi-JiT 零样本

- 仓库：https://github.com/kaonashi-tyc/zi2zi-JiT （MIT，权重在作者 Google Drive）
- 权重：`data/models/zi2zi/zi2zi-JiT-B-16.pth`（2.1 GB）
- 数据构建：`scripts/generate_font_dataset.py`（用 `build/GuangeKai-Real.ttf` 作为目标字体、思源宋体 Light 作为源字体）→ `data/zi2zi_ds2/`
- 推理：`generate_chars.py --device mps --num_sampling_steps 25`（cfg 2.6，heun）
- 结果（8 字）：**Dice 0.528**，基线 0.309（+71%）
- 视觉：字重与笔锋明显接近刻本；但偏粗、偏匀
- 结构问题：400 字上有约 1/4 出现粘连/缺笔（孔洞数不一致）
- 结论：**目前最好的风格来源**，但必须加结构闸门。

## E6 — zi2zi-JiT LoRA 微调（第一轮）

- 脚本：`lora_single_gpu_finetune_jit.py`
- 配置：500 字、40 epoch、batch 16、LoRA r=32、0.28 s/it、总耗时 **5:52**
- 推理：cfg 2.6 → Dice **0.514**（低于零样本 0.528）
- 结论：**欠训**（仅 1,240 步）。建议用全部 1,675 字、20,000+ 步重跑（约 1.5 小时）。

## E7 — 骨架 + 笔刷原型

- 背景：研究 [LingDong-/computer-grass](https://github.com/LingDong-/computer-grass)（参数化毛笔物理 + MMAH 骨架）
- 障碍：其字形数据是 **Arphic Public License**（copyleft），与 OFL 不兼容；且默认风格是细线楷，不是馆阁体
- 我方原型：`work/preview/brush_demo2.png`（skimage skeleton + 方向相关半径 + 端点收锋）
- 现状：能跑，但半径标定/收锋曲线粗糙
- 结论：**方向可行**，需要 1–2 天工程化。

---

## 复现命令

```bash
# E3 自训 U-Net（干净 patch 训练）
python3 scripts/09_train_b.py --epochs 120 --batch 32 --base 32

# E5 zi2zi 零样本
python3 scripts/zi2zi_make_npz.py --train_dir data/zi2zi_ds2/train \
    --source_font data/base/NotoSerifSC-Light.otf --output data/zi2zi_ds2/inference.npz
cd data/vendor/zi2zi-JiT && PYTHONPATH=. python3 generate_chars.py \
    --device mps --checkpoint ../../models/zi2zi/zi2zi-JiT-B-16.pth \
    --test_npz ../../zi2zi_ds2/inference.npz --output_dir ../../zi2zi_out3

# E6 LoRA
cd data/vendor/zi2zi-JiT && PYTHONPATH=. python3 lora_single_gpu_finetune_jit.py \
    --data_path ../../zi2zi_ds2/train/ --test_npz_path ../../zi2zi_ds2/test.npz \
    --output_dir ../../lora_run --base_checkpoint ../../models/zi2zi/zi2zi-JiT-B-16.pth \
    --model JiT-B/16 --num_fonts 1000 --num_chars 20000 --max_chars_per_font 500 \
    --img_size 256 --lora_r 32 --lora_alpha 32 --batch_size 16 --epochs 40 \
    --num_workers 0 --device mps
```

> 复现 zi2zi 需要在 `data/vendor/zi2zi-JiT` 打 MPS 补丁（见 `PROJECT_STATE.md` §7.3）；
> 直接 `git clone` 上游代码在 Apple Silicon 上会因硬编码 `.cuda()` 失败。
