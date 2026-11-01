# OCR 分层方案实施计划（v1.1 / 决策 A）

> 依据 `docs/PLAN-OCR-PIPELINE.md` §11 与 `docs/AUDIT-2026-10-31.md` §18。
> 目标：先把 **拒贴+冲突从 34% 压到 ≤10%**，并把 verified 精度做到 ≥99%；
> 不训练、不重切全量、不跑全量 55.5k 行。

---

## 0. 冻结与基线

| 项 | 值 |
|---|---|
| 发布版 | C v1.2.1 冻结 |
| 切图基线 | v3d2，1,187,881 格 |
| 真值 | content_oracle 100（94 可读）+ calib28 27 + canary 4 |
| 当前 99zf | 128 格；verified 81/84=96.4%；拒贴 25；冲突 16 |
| 当前人工量 | 34% × 5,302 ≈ 1,800 格 |
| 目标人工量 | ≤10% ≈ 530 格 |
| 禁止 | 全量 55.5k 行 VLM；百万格逐格 OCR；重跑 90 轮 |

---

## 1. 阶段 G1：几何守卫（只读，先量化）

### 目的

把 99zf 的 25 个“无对齐字符”分类，而不是直接归因 DP：

```
A. 格内有 v6 框，中心通过          → 正常
B. 格内无 v6 框，最近框在邻格      → 渗漏/漂移
C. 格 bbox 高度 < 0.75×中位        → 行尾/碎片
D. 格 bbox 与最近框中心偏移 >0.5cp → 漂移
E. 一格多个框                      → 并格/渗漏
```

### 新脚本

`scripts/99zg_geometry_guard_c.py`

输入：

```
work-c/cells.jsonl
work-c/ocr_v6.jsonl            # 行文本已有；字符框用 99zf 的缓存或定向重跑
work-c/preview/99zf_charboxes.json
work-c/preview/99zf_report.json
```

输出：

```
work-c/preview/geom_guard.jsonl   # 每格：status, nearest_dist, h_ratio, dy, n_boxes
work-c/preview/geom_guard_summary.json
```

### 门

- 只读，不改标签、不改 mask；
- 先报 A–E 分布；
- 若 B+C+D > 10%，先修几何（G2），不允许直接进 99zf 调参。

### 时间

2–3 小时（含 4–5k 行字符框补跑，约 15 分钟）。

---

## 2. 阶段 G2：行尾/漂移修复（局部，不全量重切）

### 目的

R004 的 cell bbox 只有 103px、正常约 160px，且与 v6 框错位约 120px；这不是匹配问题，是格框问题。

### 新脚本

`scripts/99zh_lineend_repair_c.py`

只处理 G1 中 B/C/D 的行：

1. 用该行 v6 字符框的 y 序列估计正常 pitch、行首、行尾；
2. 对格 bbox 高度 <0.75×中位或中心偏移 >0.5cp 的格，按最近的 v6 框重定 bbox；
3. 只重裁这些格的 `cell/mask`，文件名沿用；
4. 不动未涉及行；产出 patch manifest。

### 门

- 受影响行 ≤10%；
- 修复后 `无框格/偏移格` 降到 ≤5%；
- 不改变任何标签；
- 任何一行无法安全重定 → 标 `unaligned`，不进自动路径。

### 时间

半天到一天；取决于受影响行数。

---

## 3. 阶段 G3：99zf 加守卫，重跑 128 格

### 修改

`scripts/99zf_dp_align_gate_c.py` 增加：

```
--guard geom
```

规则：

```
最近框中心不在格内（含 0.5cp 边界） → unaligned
一格多个框 / 邻框距离 <0.5 字高     → leak_suspect → unaligned
bbox 高 <0.75×中位                   → unaligned
```

### 门（128 格）

| 指标 | 要求 |
|---|---:|
| DP 单调违例 | 0 |
| verified 精度 | ≥99% |
| 拒贴+冲突 | ≤10%（≤13/128） |
| canary | R003/R028/R069 修正或人工；R072 隔离 |
| 回归 | 0 |

如果 verified 精度不升：先看 3 个渗漏（C006/C018/R061）是否都被守卫拦下。
如果拒贴仍 >10%：回 G2，不准用“最近框”硬贴。

### 时间

1 小时（本地 Paddle 缓存重打分）。

---

## 4. 阶段 G4：572 cut-pass 扩展

### 输入

- 572 个 cut-pass 格；
- 4–5k verified 行；
- 本地 PaddleOCR-VL（DeepSeek 已触发 governor，不依赖线上）。

### 流程

```
行裁剪 300dpi → 本地 Paddle 行转写 → v6 字符框 → DP → 守卫
→ 三方一致 verified_auto
→ 冲突/拒贴/回归 → 人工队列
```

### 门

- verified 抽检 ≥99%（n≥500）；
- 拒贴+冲突 ≤10%；
- canary 3/3；
- 回归 0；
- 人工队列 ≤530 格。

### 时间

2–3 小时机器 + 1 天人工。

---

## 5. 阶段 G5：数据链与测量修复

只在 G4 过门后：

1. `05_select` 在 verified 池上重跑；
2. `08_make_pairs` 用 verified 目标；
3. `75_build_clean_c` 重建 clean/unseen；
4. `21_train_gan` val 从 8 个样本改为 **≥300 固定字、每轮一算**；
5. 产出 `val_fixed` 和 `verified_manifest`。

### 门

- chosen 只来自 verified；
- clean/unseen 无污染；
- 逐字 AGREE 覆盖 ≥97%（含人工）；
- 回归 0。

### 时间

半天。

---

## 6. 阶段 G6：v1.3 重训（最后）

- 只在 G5 全过后启动；
- 先短跑 5 轮探针，val 固定 300；
- 有提升再续到 40–50 轮，不默认 90；
- 不发版直到 300 格盲审 + clean/unseen 双门通过。

---

## 7. 决策点

### G2 后仍 >10% 拒贴

- 不硬调匹配；
- 选：
  - A1：再修一轮行尾几何；
  - A2：把无框格全部送人工/GAN（人工量上升）；
  - B：退回 exact-length + 全人工（约 2,100 格）。

### G3 verified 精度仍 <99%

- 先查渗漏是否全部拦下；
- 若仍有“三方一致但错”，该字类进人工，不扩大自动池；
- 不重训。

---

## 8. 时间表

| 阶段 | 机器 | 人工 |
|---|---:|---:|
| G1 几何守卫 | 2–3 h | — |
| G2 行尾修复 | 4–8 h | — |
| G3 99zf + 守卫 128 | 1 h | — |
| G4 572 + 4–5k 行 | 2–3 h | 1 天 |
| G5 数据链/val | 半天 | — |
| G6 重训探针 | 1 h | — |
| **合计** | **约 2 天** | **约 1–2 天** |

---

## 9. 一句话

**先把“无框/漂移/渗漏”从 34% 压到 ≤10%，再谈 verified ≥99%；几何修复是主线，DP 调参不是。**

---

## 10. G1/G2 实测结果（2026-10-31）

### G1 几何守卫

```
A_normal        93
B_no_box        25
C_short_bbox     9
no_cell          1
offset_suspect  26
```

几何异常 **34/128 = 26.6%**；R004 bbox 103px（正常 ~160），错位 ~120px。

### G2 互 nearest 分配（只读）

`99zh_geom_assign_c.py`：

```
assigned_mutual   123/127
unassigned_ambiguous 4
```

分配能补回大部分无框格，但不能解决“框是邻字”的渗漏。

### G3 预演（分配 + 守卫）

在分配结果上：

```
verified 73/121，precision 100%
但覆盖率只有 60.3%
reject/conflict ≈ 40%
```

- 加“label != assigned box char”守卫后，6 个已知渗漏被拦下；
- 但 26 个 label/box 不一致格全部进人工，覆盖率掉到 60%；
- **A 的“拒贴+冲突 ≤10%”在现有几何下达不到**。

### 结论

A 不是“再调一版”，而是“几何问题比预期大”：

- 25 无框 + 9 短框可以靠 bbox 修复改善；
- 26 个 label/box 不一致是内容/切格混合，不能靠 guard 自动放行；
- B 兜底（exact-length + 全人工）约 2,100 格，不是 530。

下一步必须选：

1. **A+**：真正重裁 34 个几何格 + 26 个 label/box 冲突进人工；目标人工 600–800，机器 1–2 天；
2. **B**：直接 exact-length + 全人工，约 2,100 格，1–2 周；
3. 不再拿“最近框”硬贴，不扩大自动池。

v1.2.1 冻结，训练不动。

---

## 11. G3 守卫固化后的实测（修正 §10 的口径）

`99zh_rescore_c.py` 已固化守卫，并重算 `correct_vlm/correct_verified`，不再继承旧 flag：

```
verified_strict  75/121
strict precision 100.0%
verified_variant 73/73
conflict          47/121
guard_reasons:
  label_box_mismatch 28
  v5_conflict        15
  unassigned          4
  no_cell             1
```

- 6 个已知渗漏全部被 `label_box_mismatch` 拦下；
- 4 个 canary（R003/R028/R069/R072）全部在冲突/人工桶；
- 但冲突率 **38.8%**，仍远高于 A+ 的 ≤15% / ≤800 格目标；
- 几何分配能补框，不能补“标签和框内容不一致”的 28 格；这些必须人工或修标签。

结论：**A+ 仍未达成**；下一步不是继续调匹配，而是做 34 格几何重裁 + 28 格 label/box 人工，再重跑。

---

## 12. 守卫漏 `label↔vlm` 的修复与政策裁决（2026-10-31）

审计指出 R003/R028 在旧守卫下 `verified=True`，确认属实：旧守卫只比 `label↔box`，漏了 `label↔vlm`。

修复后的严格路由：

```
auto_strict     78
human_label_fix 26
human (其余)    24
verified        73/121
precision       100%
conflict        49/121 = 38.3%
```

### 不采纳“双证 label_fix 自动入池”

`human_label_fix` 的 26 格里，至少 6 格是已知**标签正确、box/vlm 同时指到邻字**的误报
（C006/C014/C018/C019/R034/R061）。双证不是独立见证：v6 框和 Paddle 行读都在同一张
漂移的行图/格框上工作，会一起错。

若自动修：

- 6/26 会被改成错字；
- 10% 抽检期望只抽到 2.6 格，发现不了 6 个错误；
- 直接违反“宁缺毋滥”。

### 裁决

**保守**：只有 `label == box == vlm`（且 v5 不反对）才自动；所有 `label_fix` 必须人盖确认章。
代价：49/121 = 38.3% 人工，放大到 5,302 约 **2,000 格**。A+ 的 ≤800 不成立。

### canary

R003/R028/R069/R072 现在全部 human；canary 4/4 拦截。

---

## 13. 目标格框读实验（读者模式，已跑）

`scripts/99zi_targetbox_read_c.py`：在 300 dpi 行图上用白框标出**当前 cell bbox**，
只让本地 PaddleOCR-VL 读框内字；48 个 label_fix/仲裁格。

```
target_char == truth: 3/48 = 6.2%
```

结论：

- 框住的是**旧 cell bbox**；当 bbox 本身是 off-by-one 邻字时，模型读到的就是邻字；
- 所以“目标格框读”在几何未修前**不构成独立见证**；
- 不能靠它自动修 label_fix；保守路由不变；
- 若要做，必须先重裁 bbox，再用框读做独立复核。

v1.2.1 冻结，训练不动。

---

## 14. A++ 几何重裁 + 框读复测（2026-10-31）

### 几何重裁

`99zj_geomfix_c.py`：

- 只对 G1 的 B/C 格；
- 用 G2 已分配的 v6 box 从 `pages300` 重裁；
- 输出 `work-c/geomfix/{cells,masks}` + `geomfix_map.json`；
- canonical cells/masks 未动。

结果：

```
repaired 30
skipped   4（G2 unassigned）
```

### 修后框读

`99zi` 用 `geomfix_map` 的 bbox 重画框：

```
target==truth 3/48 = 6.2%
repaired 子集 1/10 = 10.0%
```

仍失败。原因不是框没修，是模型会忽略白框、继续按行文读；框读在当前读者上不构成独立见证。

### 结论

- 几何重裁只解决 30/34 的 bbox，不解决 28 个 label/box 内容冲突；
- 框读实验失败，不能靠它自动修 label_fix；
- A++ 的人工量仍是 ~2,000 格，B 兜底不变；
- v1.2.1 冻结，训练不动。

---

## 15. 读者实验复核与选型（2026-10-31）

### 99zi 框读实验无效

`99zi_targetbox_read_c.py` 用 `CJK.search` 取响应第一个汉字；PaddleOCR-VL 实际返回整行转写，
所以“目标读数”= 行首字。3/48 的“正确”只是目标恰在行首。

**撤销 §14 的框读结论**：它没有测试 grounding，只测试了“行首字比例”。
target-box 仍是一个未测设计，不是“已被证伪”。

### 新增本地读者

- qwen3.5:27b（Ollama，视觉）：
  - 行转写连贯，R003 读出「肩」；
  - 位置对齐 85.7%，29/128 字数不齐；
  - 可作独立第二意见，不作主读。

### 门拆分（采纳）

四项分开判：

```
verified precision ≥99%（n≥500）
arbitration 预算：N_arb / N_eval ≤15%（超过先修几何/DP）
label_fix 确认章：不计入 15% 门；全量人章，数量/修正率单列
canary 3/3
regression 0
全分母准确率只报告，不当作唯一 release gate
```

### 主读选型

**Paddle 本地为主，DeepSeek 行级为可选第二读。**

理由：

- Paddle 96.3%，¥0、离线、无 governor；
- DeepSeek 98.7%（可对齐子集），但有 governor、要 API；
- 双读一致 → 自动；分歧 → 人工；
- qwen 只作第二意见，不主读。

v1.2.1 冻结，训练不动。

---

## 16. 门定义钉死：双队列（2026-10-31）

### 定义

```
N_eval    = 有真值、进入评估的格
N_auto    = label == box == vlm（且 v5 不反对）
N_fix     = label != box，且 vlm == box（标签错误被发现，需人章）
N_arb     = 无框 / 孤议 / 三方相异 / canary 冲突
N_eval    = N_auto + N_fix + N_arb
```

### 两个队列，两个门

| 队列 | 是否设失败门 | 今日实测 | 规模/成本 |
|---|---|---|---|
| `N_fix` 确认章 | **不设**；只报数量、修正率、人章耗时 | 28/121 = 23.1% | 5,302 × 23.1% ≈ **1,225 格**；10–15 s/格 ≈ **4–6 h** |
| `N_arb` 真仲裁 | **N_arb / N_eval ≤15%** | 19/121 = 15.7% | 5,302 × 15.7% ≈ **830 格**；60–90 s/格 ≈ **14–21 h** |
| 合计人工 | — | — | **≈2,055 格，3–4 个工作日** |

- `label_fix` 是**流水线的产出**，不是失败；把它计入 15% 会让门永远不可通过；
- `label_fix` 仍必须 **100% 人章**（保守路由），不能自动；
- `N_arb` 超过 15% 时先修几何/DP，不硬压；
- 如果 `N_fix` 异常升高（>30%），触发 review，但不算失败门。

### 口径备注

- Paddle 96.3% 是**可对齐子集**；行级全分母约 84%。选型不变：本地/免费/可复现优先。
- qwen3.5:27b 的 R072「遵」是语料先验替代墨迹；作第二意见时标注。

v1.2.1 冻结，训练不动。

---

## 17. DP/几何迭代结果：N_arb 未达 15%（2026-10-31）

用 `cells_geomfix.jsonl`（30 个重裁 bbox）重新分配，并用 fresh PP-OCRv5 字符框
替换旧 v5：

```
assigned_mutual        123
unassigned_ambiguous     4
auto_strict              78
human_label_fix         26
human (N_arb)           24
verified_strict         73/121
strict precision       100%
N_arb / N_eval          24/121 = 19.8%
```

`N_arb` 构成：

```
v5_conflict          12
label_vlm_mismatch    5
label_box_mismatch    2
unassigned            4
no_cell               1
```

结论：

- 30 个 bbox 重裁和 fresh v5 框都没有改变分配结果；
- `N_arb` 仍是 **19.8%**，高于 15% 门；
- 差值不是调参能补的：4 个 unassigned 是真几何/无框，5 个 label-vlm 是真错标，
  12 个 v5 冲突是独立见证不同意；
- 继续自动化的唯一路径是新增真正独立的读者；当前 qwen/DeepSeek 都未证明独立且位置对齐足够。

v1.2.1 冻结，训练不动。

---

## 18. 人工确认章试点结果（2026-10-31）

26 个 `label_fix` 做成“图 + 机器读数 + 原标签”小页，所有者只标 `❌`（读错）或划线（图差）。
结果：

```
accept_candidate   20   （20/20 == truth）
keep_original       3   （3/3 == truth）
drop_real           3   （F001/F015/F019，图质量差）
```

- **0 个假接受**；
- 6 个已知 false positive 全部被 `❌/划线` 拦住；
- 20 个真 label_fix 全部自动接受；
- 人工成本约 3–5 分钟/26 格。

结论：这套“不写字、只打 ❌/划线”的确认章可扩展；label_fix 的真值问题可以用它清掉，
不需要逐格输入正确字。
