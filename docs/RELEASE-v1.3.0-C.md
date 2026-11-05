# 发布说明：GuanGe Kai C v1.3.0

> 2026-11-02。真迹 5,257；合成字由 90 轮 **ep090** 生成。
> 三线版本：A **v1.7.2**、B **v1.2.4**、C **v1.3.0**。

## 变更

- v1.3 数据链补 `05 --drop-if-all-flagged`：剔除 **20 个全坏格**（含 `哽`/`筴`/`呀`），真迹 **5,302 → 5,257**；
- `自` 换回 v1.2.1 的完整样本 `p31_0054_c00_l02_s019.png`，修复丢孔；
- 合成字 15,735（GAN 14,422 + ribbon 1,313），覆盖率 20,992 / 20,992；
- 字体：`GuanGeKai-C-Regular.ttf`（21,034 cmap）、`GuanGeKai-C-Real.ttf`（5,257 真迹）。

## 验收

```
coverage        20992/20992
empty           0
huge            0
real-subset     5257/5257 OK
common holes    0
holes lost      3/214 = 1.4%
ribbon fallback 1,313 / 15,735 = 8.3%
weight bias     1.009x
QA OK
```

CPU 300 字 holdout Dice **0.4666**；仅作参考，不作为视觉选点的唯一依据。
ep090 为所有者视觉选点；ep35 权重损失已记录，不再引用。

## 制品

| 文件 | SHA-256 |
|---|---|
| `build/GuanGeKai-C-Regular.ttf` | `765d08486b75da52e196cbe81570efd29226cea26d4f4198d6acd62dbf440f48` |
| `build/GuanGeKai-C-Real.ttf` | `6caf9d82d71ad716eb5cbcf7a8c2947245756141a24b53f061130783752f359d` |
| `GuanGeKai-C-v1.3.0.zip` | `4b4737758a342e8ddc59ac60615e846c760564faadfb87760f08bf70639f5498` |

## 已知边界

- ep090 在清理前 pairs 上训练；字体使用清理后的 chosen 生成，模型未在清理后 pairs 上重训；
- 20 个被剔除字现由 GAN/ribbon 生成，不再作为真迹；
- v1.2.1 制品保留在 `release-c` 备份与 `GuanGeKai-C-v1.2.1.zip`（若存在），不覆盖。
