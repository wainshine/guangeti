# valDice 0.357 vs 0.470：根因是 MPS/CPU 推理差异

同一 checkpoint（`work-c/ckpt/v1.3/c_ep020.pt`），同一 300 字 `pairs_holdout`：

| 设备 | Dice |
|---|---:|
| CPU | **0.4703** |
| MPS | **0.3569** |

训练日志里的 0.357 是 MPS；离线汇总图里的 0.470 是 CPU。不是 checkpoint、不是 val 数据、不是阈值。

烟测 checkpoint 同样：

| 设备 | Dice |
|---|---:|
| CPU | 0.0449 |
| MPS | 0.0265 |

## 影响

- 训练在 MPS 上跑，日志 valDice 是 MPS 口径；
- `c_best.pt` 按 MPS val 选，可能不是 CPU 发布口径的最佳点；
- `77_generate_c.py` / `82_eval_c.py` 都是 CPU 加载推理；
- 因此发布选点必须用 CPU 评估，训练日志只能看趋势，不能当发布指标。

## CPU 重评（300 字 holdout）

| 检查点 | Dice | ink |
|---|---:|---:|
| v1.2.1 ep090 | 0.466 | 0.972 |
| ep20 | 0.470 | 1.086 |
| ep30 | 0.469 | 1.077 |
| ep35 best | **0.472** | 1.041 |
| ep40 | 0.463 | 0.994 |
| ep50 | 0.454 | 0.954 |
| ep80 | 0.469 | 1.025 |

CPU 口径下 ep35 最佳，ep20/30/80 接近；差距很小，视觉上 ep20/30 更稳。

## 结论

- 训练日志不是错，是 MPS 口径；
- 发布/字体生成是 CPU 口径；
- 选点改 CPU；不要再用训练日志的 valDice 直接选 checkpoint。
