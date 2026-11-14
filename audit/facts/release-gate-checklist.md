# 跨线发布检查项清单 v0（X2 初稿，2026-11-14）

> 用途：三线发布前由**各线自跑**、主会话**只读复核**的公共检查项。不是新脚本，是检查单。
> 依据：`audit/OPERATING.md` v1.2.1 §4/§6；每线可增补本线特有项，但不得删公共项。
> 状态：初稿，待 A/B/C 各线 review；主会话不代跑任何写盘脚本。

## A. 快照（每次发版第一步）

| # | 检查 | 方法 | 通过标准 | 执行者 |
|---|---|---|---|---|
| A1 | 记录 `HEAD`、`git status`、制品 SHA-256 | `git rev-parse HEAD`、`git status --porcelain`、`shasum -a 256 build/*.ttf release*/*.ttf *.zip` | 有快照；非 audit 脏文件已说明 | 线 |
| A2 | 与当前冻结台账（v4：`audit/facts/frozen-hashes-2026-11-14T1015.json`）比对 | 制品哈希 / `last_non_audit_commit` | 制品哈希一致；不一致须说明原因 | 主会话 |
| A3 | `release*/SHA256SUMS` 自校验 | `cd release && shasum -a 256 -c SHA256SUMS`（B/C 同理） | 全 OK | 线 |

## B. golden repro（每线钉死路径；线自跑交命令+哈希+日志）

| 线 | 产物 | 路径 | 期望哈希 | 通过标准 |
|---|---|---|---|---|
| A | Regular | `11_build_full` → `13_extend_punct --line A --inplace` | `e6d8a104…` | 哈希一致 + 日志 |
| A | Real | `07_build_real`（masks retrace） | `bf278ab1…` | 哈希一致 + 日志 |
| B | Regular | `62 --drop-outside-basic` → `13_extend_punct --line B --inplace` | `aa19d6d2…` | 哈希一致 + 日志 |
| B | Real | `57 --reuse-contours --drop-outside-basic` | `7d10e460…` | 哈希一致 + 日志 |
| C | Regular | `79_build_full_c`（默认含 42 标点） | `765d0848…` | 哈希一致 + 日志 |
| C | Real | `76_build_real_c --close 3 --hole-repair` | `6caf9d82…` | 哈希一致 + 日志 |

**硬规则**：A 的 `--reuse-contours`（`5733ca42…`）不是发布路径；B 的 retrace（`f82ea61a…`）不是发布路径。
主会话只比对哈希与日志，不亲自构建。

## C. 发布 manifest 与制品对账

| # | 检查 | 通过标准 |
|---|---|---|
| C1 | 该线 `data/release-*.json` 的 `version` / `counts` / `sha256` 与制品一致 | 逐字段一致 |
| C2 | `release_date`（签核日）与 `artifacts_built_at`（打包日，ISO 日期字符串）已按 O6 填写 | 三线同义 |
| C3 | `zip_sha256` 与磁盘 zip 一致（zip 是 recorded snapshot，不承诺字节可复现） | 一致 |
| C4 | 字体 name 表版本串与 release 版本一致 | 一致 |

## D. provenance / 数据一致性

| # | 检查 | 通过标准 |
|---|---|---|
| D1 | `release*/provenance.json` ↔ `chosen`/`generated` 逐字对账 | 零失配 |
| D2 | `stats.json` 的 counts（real/gan/ribbon/punct/codepoints）与 manifest 一致 | 一致 |
| D3 | `-Real.ttf` 只含真迹、无标点；cmap 与 provenance 的 `real` 集合相同 | 一致 |

## E. QA / accept / 孔洞

| 线 | QA | accept | 孔洞 |
|---|---|---|---|
| A | `13_qa.py`（coverage 20,992；real-subset 1,675；empty/tiny/huge 0；punct OK） | 无独立 accept | `71_holes --n 300`，记录 lost（固定 seed；基线 1.9%） |
| B | `63_qa_b.py` | `68_accept_b.py`（字重/包围盒/回退率） | `63` 内置 / `71_holes --font B` 记录 |
| C | `80_qa_c.py` | `84_accept_c.py`（字重/包围盒/回退率） | `80` 内置（holes lost 3/214=1.4%） |

**通过标准**：QA 通过；accept 无 FAIL；孔洞数字记录并与上一版比较（不升高或说明原因）。

## F. 跨线闸（线自跑交输出；主会话只读复核）

| # | 检查 | 通过标准 | 备注 |
|---|---|---|---|
| F1 | `83_verify_ab_c.py` | 打印 `A/B INTACT` + 三个 `21,034`；zip 基线一致 | **写 `work-c/`；只由 C 或 A 经 C 同意运行；B 不跑** |
| F2 | `97_check_terms.py` | `TERMS OK` | 白名单/历史遗留不计；已知盲区见报告 |
| F3 | `95_compare_lines.py --check` | build ↔ release SHA 一致 | 若本轮更新三线图，跑不带 `--check` 的版本并提交图 |
| F4 | `73_selfaudit_b.py`（B 线） | `SELF-AUDIT OK` | 由 B 自跑（经 67 写 `work-b/`） |

## G. 文档数字与发布说明

| # | 检查 | 通过标准 |
|---|---|---|
| G1 | 发布说明的数字可由 `release-*.json`/落盘 json 导出（Dice/chamfer/holes/回退率/体积/哈希/日期） | 每个数字有来源；不写无落盘产物 |
| G2 | 文档术语/字集口径 | 不出现已作废写法；`97` 通过；包内许可文本按 E8 处理（不追溯） |
| G3 | 发布说明由该线负责人签核 | 有签核记录（O3） |

## H. 主会话复核单（不代签）

- 主会话输出：`可发 / 不可发` + 快照 + 逐项证据（哈希/日志/JSON 路径）。
- 主会话**不运行** 83/67/73/QA/accept/生成/打包；不重建；不 git 写；只读复核。
- 所有者提交/发版；发布说明由各线自签。
