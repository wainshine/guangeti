# v1.3 数据链独立复核（2026-11-01）

## 已确认

- `labeled.jsonl`：1,187,881 行，24 条 `label_correct` 全部写入；
- `chosen.jsonl`：**5,277**；
- `v121_backup/chosen.jsonl`：5,302；
- 无 `ckpt/v1.3`、无训练进程、无 `val_fixed`；
- 数据链文件 `pairs.npz` / `pairs_clean.npz` 已生成。

## 账目不符

5,302 → 5,277 的实际字集变化：

```
丢失 labels 44
新增 labels 19
5,302 − 44 + 19 = 5,277
```

不是对方报告的 **−47 +22**（两者各差 3）。

44 个丢失 label 中，只有 **24** 个的旧 chosen 格位于 207 个 holdout 页；
其余 20 个不能由 holdout 解释，需补账。

19 个新增 label 是 `侂/倭/哽/喋/婬/淝/矍/筴/簸/耋/蚩/貔/蹂/鄄/鏘/顱/餕/黠/齬`
等新字，不是“22 演化”。

## 修正与隔离

`human_stamp_verdicts_final.json`：

```
label_correct 24
confirm       22
quality_reject 2
quarantine     1
```

24 条修正已全部落 `labeled`；但“12 隔离格排除”未在 selected/chosen 账目中独立复现，需单独给 manifest。

## 结论

数据链**已跑完**，但：
- 字集账目 44/19 ≠ 47/22；
- 44 个丢失字只有 24 个能归因 holdout；
- v1.3 **未训练**；
- 572 门仍未按我们的复核通过。

因此“数据侧完成、重训解锁”只能算**部分成立**，不能作为最终账目。

## 补记：44 字归因复核通过

独立按 `labeled.jsonl` 全量重算 44 个丢失 label 的非 holdout 样本数：

```
non-holdout 样本数 = 1：42 字
non-holdout 样本数 = 0：2 字（蕢、岍）
合计 44/44 < min-samples 2
```

- 42+2=44，零未解释；
- 与“旧 chosen 格在 holdout 页 24/44”不矛盾：前者是**计数不足**，后者是**被选格位置**；
- 账目闭合：`5,302 − 44 + 19 = 5,277`。

**更正**：此前笔记中的“20 个不能由 holdout 解释”撤回；归因表以本节为准。
