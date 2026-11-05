# C 线数据清理建议（2026-11-02，只读盘点）

> 当前 `work-c/` 约 **120 GB**。发布必需资产不足 1 GB；大头是检查点和历史实验。
> **本文件只是建议，未删除任何文件。**

## 0. 检查点保留原则（所有者 2026-11-02 明确）

**当前版本与刚训练完准备发布的版本，必须保留：best + ep030/050/060/070/080/090
（有 100 的也保留 100）。** 目的是任何一段都能继续训练/回滚，不是只留发布点。
本文件不得把上述检查点列为可删；v1.2.1/v1.3 的 `.pt` 不在清理建议范围内。

## A. 必须保留（发布/复现/审计）

| 路径 | 体积 | 原因 |
|---|---:|---|
| `build/GuanGeKai-C-Regular.ttf`、`-Real.ttf` | 19 MB | v1.3.0 成品 |
| `release-c/` | 20 MB | v1.3.0 发布包 |
| `GuanGeKai-C-v1.3.0.zip` | 14 MB | v1.3.0 分发件 |
| `GuanGeKai-C-v1.2.1.zip` | 14 MB | 上一版分发件 |
| `work-c/v121_backup/` | 1.0 GB | v1.2.1 回滚（字体、release-c、generated） |
| `work-c/chosen.jsonl` | 3.7 MB | 5,257 真迹选点 |
| `work-c/labeled.jsonl` | 697 MB | 标签主数据 |
| `work-c/real_contours.jsonl` | 80 MB | 5,257 真迹轮廓 |
| `work-c/pairs/pairs.npz` | 84 MB | v1.3 训练对 |
| `work-c/pairs_clean.npz`、`pairs_holdout.npz` | 35 MB | 干净集/300 字评估 |
| `work-c/generated.jsonl` | 170 MB | v1.3 生成源；发布包 provenance 依据 |
| `work-c/cells.jsonl` | 616 MB | 格元数据，重建必需 |
| `work-c/cells/`、`masks/` | 13.8 GB | 真迹重切输入；可重建但需 ~40 min |
| `work-c/pages150/` | 12 GB | OCR/重切原始底图 |
| `work-c/ckpt/v1.3/` 的 `best(ep085)` + `ep020/030/050/060/070/080/090` | 3.4 GB | 续训/回滚锚点 |
| `work-c/ckpt/v1.2.1/` 的 `best` + `ep030/050/060/070/080/090` | 2.7 GB | 续训/回滚锚点 |
| `work-c/ckpt/v1.2.0/` 的发布点 + 保留锚点 | 3.7 GB | v1.2.0 回滚 |
| `work-c/ckpt/MANIFEST.json` | 24 KB | 检查点清单 |
| `work-c/qa/`、`accept_c_v130.json` | 33 MB | v1.3 QA 证据 |
| `work-c/preview/{v13_ep20_30_80_85_90_real,no_real}.png` | ~2 MB | v1.3 视觉选点 |
| `docs/RELEASE-v1.3.0-C.md`、`docs/DATA-C.md` | 小 | 发布说明/校验和 |

## B. 可删除（先审批，建议归档后再删）

| 路径 | 体积 | 理由 | 建议 |
|---|---:|---|---|
| — | — | **检查点保护区：不得删除** | v1.2.1 与 v1.3 的 `best` + `ep030/050/060/070/080/090` 必须保留；v1.3 额外保留 `ep085`（c_best 实际轮次）与 `ep020`（选点对比）。删除任何 `.pt` 必须所有者单独批准 |
| 顶层 `work-c/ckpt/c_ep010/020/030/040/050.pt`、`c_ep030_v100.pt` | ~2.3 GB | 旧实验/重复 | 先与 v1.2.0/v1.3 哈希比对；无引用再删 |
| `work-c/ckpt/v1.2.0/ckpt/`、`ft/`，除 `c_ep034_v120.pt` | ~3.7 GB | v1.2.0 历史中间态 | 归档 v1.2.0 最终检查点，其余删 |
| `work-c/exp/v3d/` | **16 GB** | v3d 实验数据；发布用 v3d2 | 若不再复现 v3d 实验，归档后删 |
| `work-c/archive/v1.2.0-v3c/` | **16 GB** | v1.2.0 旧切图实验 | v1.2.0 已发布；归档后删 |
| `work-c/archive/v1.2.0-generated.jsonl` | 172 MB | 旧生成源 | 归档后可删 |
| `work-c/labeled.pre_stamp_backup.jsonl`、`labeled.pre_572fix_backup.jsonl`、`labeled.jsonl.bak_pre_fix`（三选一） | ~1.4 GB | 同一主数据的多份备份 | 保留当前 + 最近一份；其余删 |
| `work-c/generated_v121_on_disk.jsonl`、`generated_v13_ep90_oldchosen.jsonl`、`generated_dropped.jsonl`、`generated_v13_ep90.jsonl`（若与 generated.jsonl 同 hash） | ~500 MB | 生成源重复 | 保留 `generated.jsonl` + v1.2.1 备份；其余去重后删 |
| `work-c/preview/cells_geomfix.jsonl` | **616 MB** | 几何实验中间 JSONL | 可删（geomfix 图/映射保留） |
| `work-c/preview/vlm_crops300/` | 63 MB | 行级 VLM 实验裁剪 | 实验结束后删 |
| `work-c/preview/targetbox_crops*/`、`stale/` | ~19 MB | 旧实验图 | 可删 |
| `work-c/pages300/` | 5.7 GB | 300 dpi 行实验页 | 若不再跑行级 VLM/重裁，可删 |
| `work-c/glyph_store/` | 347 MB | 中间索引/缓存 | 确认无构建引用后删 |
| `work-c/v13_preclean_real_contours.jsonl` | 70 MB | 清理前轮廓 | 可删 |
| `work-c/pairs_clean_second.npz` | 25 MB | 第二样本 chamfer 地板 | 仅保留若还要算地板 |

**预计可回收**：约 **35–45 GB**（不含任何 v1.2.1/v1.3 模型检查点；v3d/v3c 两个 16 GB 实验目录是否删另议）。

## C. 不要删

- `release-c/`、v1.2.1/v1.3 zip、`v121_backup/`；
- `chosen.jsonl`、`labeled.jsonl`、`real_contours.jsonl`、`generated.jsonl`；
- `cells.jsonl`、`cells/`、`masks/`、`pages150/`（除非确认不再重建）；
- `ckpt/v1.3/c_ep090.pt`、`ckpt/v1.2.1/c_ep090.pt`；
- `preview/stamp572/`、所有者标注图、`human_review_*`；
- `ckpt/MANIFEST.json`、`work-c/qa/`、`accept_c_v130.json`。

## D. 删除前流程（硬性）

1. 先 `sha256` 去重，确认不是发布检查点/重复硬链接；
2. 把要删的目录打包到外置盘或 `work-c/archive/retired/`，保留 7 天；
3. 更新 `work-c/ckpt/MANIFEST.json`（`31_ckpt_manifest.py` 已改 `rglob`）；
4. 在 `docs/DATA-C.md` §6.5 登记删除；
5. 删除后重跑 `31_ckpt_manifest.py`，并 `shasum -a 256 -c release-c/SHA256SUMS`；
6. 发布包和 `build/` 不动。

## E. 切图实际有几套（2026-11-02 复核）

不是“最后 2 份”，磁盘上是 **3 套 cells+masks**：

| 套 | 路径 | cells | masks | 用途 |
|---|---|---:|---:|---|
| **v3d2（最终）** | `work-c/cells/`、`work-c/masks/` | 9.2 GB，1,187,881 格 | 4.6 GB | v1.3 真迹/训练/后续方法 |
| v3c（旧） | `work-c/archive/v1.2.0-v3c/{cells,masks}` | 9.6 GB | 4.7 GB | v1.2.0 历史复现 |
| v3d（实验） | `work-c/exp/v3d/{cells,masks}` | 9.1 GB | 4.6 GB | v3d 实验对照 |

保留切图的目的不是只为当前字体，而是保留 **百万级单字图像 + 格元数据**，
后续换训练方法（自监督、patch、OCR、检测）时可直接用；不要按“当前字体只用 5,257 真迹”判断它们无用。

清理优先级：先归档 v3c/v3d 两套历史切图，**v3d2 的 cells/masks 与 cells.jsonl 必须保留**。

## F. 按所有者四条原则重分类（2026-11-02）

### 原则 1：历史版本，至少输出字体用到的版本，保留

**保留**：

- `GuanGeKai-C-v1.0.0.zip` ~ `v1.3.0.zip`（共约 74 MB）；
- `release-c/` 当前 v1.3.0；
- `work-c/v121_backup/release-c-v1.2.1/` 与 v1.2.1 字体；
- v1.2.0 发布包/发布字体（`GuanGeKai-C-v1.2.0.zip`）。

### 原则 2：最近训练核心轮次 + 最后一次正式发布核心轮次

**保留**：

```
v1.3：c_best(ep85) + ep020/030/050/060/070/080/090
v1.2.1：c_best + ep030/050/060/070/080/090
v1.2.0：发布点 c_ep034_v120.pt + 其核心锚点
```

v1.2.1 的 90 个中间态中，非核心轮次是否删，**等所有者单独批准**；
不把“当前版本”按“非发布”处理。

### 原则 3：重训时间成本 vs 留存空间

| 资产 | 空间 | 重做成本 | 决定 |
|---|---:|---|---|
| v3d2 `cells/` + `masks/` | 13.8 GB | 切图 ~40 min×6 + 标签链 | **留** |
| `pages150/` | 12 GB | 重新渲染/对齐 | **留** |
| v3c `archive/v1.2.0-v3c/` | 16 GB | 旧切图/标签链，数天 | 归档外置；不直接删 |
| v3d `exp/v3d/` | 16 GB | v3d 实验重做，数天 | 归档外置；不直接删 |
| `pages300/` | 5.7 GB | 300 dpi 重渲染 ~1 h | 无行级实验后可删 |
| `labeled` 旧备份 | 1.4 GB | 难以重建 | 保留当前 + 最近一份 |
| `ckpt` 锚点 | 数 GB | 训练数小时/天 | **留** |

### 原则 4：错误方向的探索，只留文档

**可删（先确认无引用）**：

- `preview/cells_geomfix.jsonl` 616 MB（A++ 几何虚拟分配，未采用）；
- `preview/targetbox_crops*/`、`preview/targetbox_*`（框读 harness 失败）；
- `preview/stale/`（被 ep85 污染的“ep35”图）；
- `work-c/geomfix/` 与 `geomfix_map.json`（30 格重裁实验，修法未采用）；
- `exp/v3d3_split_probe.json`；
- `preview/vlm_crops300/`（行级 VLM 实验，结论已入档）；
- 重复的 `generated_*`（保留 `generated.jsonl` + v1.2.1 备份）。

**保留文档**：`docs/AUDIT-2026-10-31.md`、`docs/AUDIT-*-VERIFY.md`、
`docs/PLAN-OCR-*`、`docs/CLEANUP-C.md`、`docs/RELEASE-v1.3.0-C.md`。

## G. 结论

- 当前先不动任何 `.pt` 和切图；
- 先清原则 4 的中间产物（约 1–2 GB）；
- v3c/v3d 两套 32 GB 先外置归档，确认不需要再删；
- 检查点只按“核心轮次”保留，具体删哪些等所有者逐项批准。

## H. 2026-11-02 第一轮执行结果

按原则 4 删除（无 `.pt`、无 cells/masks、无发布资产）：

```
preview/cells_geomfix.jsonl              616 MB
preview/targetbox_crops*/                 19 MB
preview/stale/                           924 KB
work-c/geomfix/                          1.3 MB
preview/geomfix_map.json                  10 KB
v13_preclean_real_contours.jsonl          70 MB
exp/v3d3_split_probe.json                 8 KB
generated_v13_ep90.jsonl  (duplicate)    186 MB
generated_v13_ep90_oldchosen.jsonl       170 MB
generated_v121_on_disk.jsonl             165 MB
generated_dropped.jsonl                  0.2 MB
```

`work-c` 约 **120 GB → 115 GB**；`preview` 约 **720 MB → 84 MB**。
`ckpt/MANIFEST.json` 已重跑（124 项）。

仍未动：v1.2.1/v1.3 全部 `.pt`、v3d2 cells/masks、pages150/pages300、v3c/v3d 历史套、release-c、zip。

## I. v3c 核心切图收口（2026-11-02）

按“只留训练/打包/评估所需图片”保留：

- `chosen.jsonl` 5,299
- `pairs_clean.npz` 3,200
- `pairs_clean_second.npz` 2,431
- `pairs_holdout.npz` 300

并集 **10,737 个 cell**，加 masks 共 **21,474 张**，硬链接在
`work-c/archive/v1.2.0-v3c-core/{cells,masks}`（约 140 MB）。

原 `v1.2.0-v3c/{cells,masks}` 的其余约 117 万格已删除；v3c 目录保留
`cells.jsonl`、`labeled.jsonl`、`pairs/*`、`chosen/real_contours/generated` 等元数据。
v3d 与 v3d2 未动。
