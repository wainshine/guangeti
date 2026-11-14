# 发布说明：GuanGe Kai C v1.3.0

> 2026-11-02。真迹 5,257；合成字由 90 轮 **ep090** 生成。
> 日期口径：`release_date = artifacts_built_at = 2026-11-02`；`AGENTS.md` 的 11-12 是共享文档更新日，待 A 线归一（C4）。
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

CPU 300 字 holdout：**0.470 / 6.38 / 8.3%**（`work-c/eval_v130_unseen_c2.json`，c_ep090，n=300，`--close 2`）；仅作参考，不作为视觉选点的唯一依据。
旧值 0.4666 与旧产物 0.469/6.26/7.0 在当前 `pairs_holdout` 上都不能精确复现；以本次可复跑产物为准（C1）。
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

## 证据口径更正（2026-11-14，C1/C2/C3/C9）

- 300 字 unseen：0.470 / 6.38 / 8.3%，来源 `work-c/eval_v130_unseen_c2.json`（c_ep090，n=300，`--close 2`）；旧值 0.4666 与旧产物 0.469/6.26/7.0 在当前数据上不能精确复现；
- clean 0.471 / 6.19 / 12.0%：与 `work-c/eval_v121_ep090.json`（c_ep090，n=200）同组，属 v1.2.1 继承值；`release-c.json` 保留 `clean_n=3210` 为数据集规模，新增 `clean_eval_n=200` 与 `clean_eval_source`，v1.3.0 未重测；
- `fallback_share_of_block=0.0712` 是 v1.2.1 的 1,495/20,992 旧值，已删除；双口径为 8.34%（合成字）/ 6.25%（基本区）；
- `weight_bias` 以 `work-c/accept_c.json` 实测 1.009 为准；0.998 为旧值；
- 日期：`release_date = 2026-11-02`（签核/构建日），`artifacts_built_at = 2026-11-02`；`AGENTS.md` 的 11-12 是文档更新日，待 A 线共享文档归一（C4）。

## 两套验收标准（C7）

| 标准 | 内容 | 结果 | 证据 |
|---|---|---|---|
| 发布 QA | 覆盖/真迹子集/空字形/孔洞/打包 | 已通过 | 本文 §验收、`work-c/qa/` |
| 冻结四级门 | 门 1 WRONG_LABEL precision ≥90% | **未过**：23/27=85.2% | `docs/AUDIT-2026-10-31.md:442` |
| 冻结四级门 | 门 2 AGREE 二次盲审内容错 ≤2/100 | **未过**：5/94 可读中有 5 错 | `docs/AUDIT-2026-10-31.md:464-468` |
| 冻结四级门 | 门 3 格级覆盖终态 ≥97% | **未执行/无签字** | `docs/AUDIT-2026-10-31.md:195-215` |
| 冻结四级门 | 门 4 chosen 错标率相对下降 ≥50% | **未执行/无签字** | 同上 |

> 结论：v1.3.0 是“发布 QA 通过”，**不是“四级冻结门通过”**；两套标准不能混写。


## golden repro（C6，2026-11-14）

命令：

```bash
python3 scripts/76_build_real_c.py --close 3 --hole-repair
python3 scripts/79_build_full_c.py
shasum -a 256 build/GuanGeKai-C-Real.ttf build/GuanGeKai-C-Regular.ttf
```

结果（`work-c/logs-v1.3/golden_c_v13.log`）：

```
76: glyphs 5257 (counter repair: 2159)
    Real  = 6caf9d82d71ad716eb5cbcf7a8c2947245756141a24b53f061130783752f359d
79: real 5257 gen 15735 total 20992 (basic block 20992/20992) missing 0
    Regular = 765d08486b75da52e196cbe81570efd29226cea26d4f4198d6acd62dbf440f48
```

与 v1.3.0 制品哈希一致；这是字形数据路径，不重建/不重发 release-c。
