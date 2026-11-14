# 三线任务板 v1（主会话维护，2026-11-14）

> 规则：见 `audit/OPERATING.md`。主会话不代写；三线执行并回报；所有者裁定优先级。
> 状态：`待办` / `进行中` / `待复核` / `完成` / `阻塞`。
> 回报格式：命令 + 输出摘要 + 产物哈希 + 快照（HEAD / git status）。

## 0. 所有者决策（阻塞项，优先）

| ID | 事项 | 建议 |
|---|---|---|
| O1 | A 两处未提交修复（AGENTS 步 2.5、release-a res 256）是否现在提交 | 建议提交；提交后主会话按新 HEAD 重跑快照 |
| O2 | 共享资产 owner 正式化（A 继续维护共享 docs/scripts；主会话不接管） | 建议按 2026-11-14 确认执行，写入 AGENTS 或 owner 口头规则即可，不必重构 |
| O3 | 各线发布签核人：A/B/C 各自签，主会话只复核不代签 | 建议确认 |
| O4 | zip 是否承诺字节可复现 | 建议不承诺（记录为发布快照）；若要，改为确定性打包需另立任务 |
| O5 | 三线是否必须同步发版 | 建议不强制；`main_version` 只是对齐标记 |

## 1. A 线（A 会话；共享 owner）

| ID | 任务 | 验收标准 | 状态 |
|---|---|---|---|
| A1 | `docs/DATA.md:176/181` 的 `--res 512` 改为 256，重建链与 `release-a.json` 对齐 | `grep -n 'res 512' docs/DATA.md` 无输出；reproduce 链可执行 | 待办 |
| A2 | 跑 `31_ckpt_manifest.py`；`m2wt_*` 4 个入册；`m2wt_ep090` SHA-256 写入 `release-a.json`；`kind=release` / `--check-release`；补 `DATA §6.5.1` | MANIFEST 24/24；`31 --check-release` 通过；`release-a.json` 有 ckpt sha | 待办 |
| A3 | floor 5.16 产物：A 线地板脚本 + `work/chamfer_floor.json`（seed 7、800 对、中位/CI/KS/MW）+ EXPERIMENTS E32 命令 | JSON + 命令 + 与 5.16 的一致性说明 | 待办 |
| A4 | 钉死 A golden repro：Regular = 11+13 → `e6d8a104`；Real = retrace → `bf278ab1`；`--reuse-contours` = `5733ca42` 标注非发布；复核后回复 | 两条命令 + 哈希写进 A 发布清单 | 待办 |
| A5 | 97 扫描面扩容：`OFL.txt`、`LICENSE`、`docs/index.html`、`docs/REPORTS/*.md`、`docs/releases/` 摘要；正则覆盖「44 码位」 | `--help` 说明 + 新命中清单 | 待办 |
| A6 | 文档口径收口（随下次发版）：`holes lost` 全量或固定 seed/n；`0.549→0.539` 注明 n；PROJECT_STATE/README 作废口径；DATA §4.9/§5 台账 | `docs/AUDIT-2026-11-14.md` 对应 P1 项逐条关闭，主会话复核 | 待办 |

## 2. B 线（B 会话）

| ID | 任务 | 验收标准 | 状态 |
|---|---|---|---|
| B1 | E15 的「中间态无法归因」改为「待定位」或给出定位；说明 `drop_duplicate_last_point`（默认关）不足以解释 62 的中间态漂移 | 文档句可复核；62 改动前后各一次中间产物哈希 | 待办 |
| B2 | `release_date=2026-10-30` vs zip mtime `2026-11-13`：定义 `release_date` 与 `artifacts_built_at` | 两字段语义写入 DATA-B 或 release-b.json | 待办 |
| B3 | 撤回/改写「21 个未提交文件」；提供 `73_selfaudit_b` 最近一次输出（注意它经 `67_verify_a` 写 `work-b/verify_a_snapshot.json`） | 输出贴出 + 副作用说明 | 待办 |
| B4 | 提供 B 的 golden repro 金样一次（Regular `aa19d6d2`、Real `7d10e460`，cache 路径） | 命令 + 哈希 + 与台账一致 | 待办 |

## 3. C 线（C 会话）

| ID | 任务 | 验收标准 | 状态 |
|---|---|---|---|
| C1 | 0.4666 / 0.469 对齐：重跑落盘并改数，或给出 0.4666 的产物 | `release-c.json` 与产物一致；附命令 | 待办 |
| C2 | clean 0.471/6.19/12.0% 确认是 v1.2.1 遗留还是 v1.3.0 重测 | 字段旁注明来源版本或重测 JSON | 待办 |
| C3 | 删除/重算 `fallback_share_of_block`（0.0712 = 旧 1,495/20,992）；只保留 8.34%（合成）/6.25%（区块）双口径 | release-c 无 0.0712 | 待办 |
| C4 | v1.3.0 发布日期 11-02 与 AGENTS 11-12 归一 | AGENTS 与 release-c 一致 | 待办 |
| C5 | 未记录修复运行：给出 `gen_v13_ep90.log` 首末行、15,735 行 generated、`gan_fallback.json` 17 项对照结论（确认或否认） | 结论 + 证据链 | 待办 |
| C6 | golden repro 路径 + 两字体哈希钉死（C 的 Real/Regular 各走哪条路径） | 命令 + 哈希 | 待办 |
| C7 | RELEASE-C 补「两套验收标准」表：发布 QA（已过）vs 冻结四级门（门 1/2 未过、门 3/4 未执行、无签字） | 表进 RELEASE-C 或 DATA-C | 待办 |
| C8 | C-big 体量改为 5.5 GB（apparent 5.93 GB），保留 47 字/5.96% 事实 | 文档更正 | 待办 |

## 4. 跨线（主会话）

| ID | 任务 | 验收标准 | 状态 |
|---|---|---|---|
| X1 | 外部冻结台账 v0 | `audit/facts/frozen-hashes-2026-11-14.json` | 完成 |
| X2 | 发布清单 v2 模板（以 `73_selfaudit_b` 为骨架） | 模板文件 + A 线跑通一次 | 进行中 |
| X3 | 状态快照协议 | 写入 `OPERATING.md §5`；每份复核带快照 | 完成（规则）/持续执行 |
| X4 | 共享脚本变更协议 | 写入 `OPERATING.md §3`；一次演练（下次共享脚本改动时） | 完成（规则）/待演练 |
| X5 | 三线事实表 v0 | `audit/facts/2026-11-14.md` | 完成 |
| X6 | 审计报告状态更新与更正 | `docs/AUDIT-2026-11-14.md §9` | 完成 |

## 5. 已闭环（2026-11-14）

| 项 | 结论 |
|---|---|
| A 的 release-a res 512 / AGENTS 缺 punct 步 | 工作区已修；待所有者提交（O1） |
| C-big 10.9 GB | 实测 5.5 GB，C 待改文档（C8） |
| `7.12%` 分母 | = 1,495/20,992 旧值，删（C3） |
| 0.4666 vs 0.469 | 裁决：版本已 1.3.0、数值与唯一产物不对齐（C1） |
| floor 5.16 | 有数字无产物（A3） |
| 83/67 自更新基线 | 已确认，不可作漂移监测（X1/§7） |
| B `release-b.json` 顶层 clean 字段 | 不存在（不是 null），保持嵌套单一源 |
| B「21 个未提交文件」 | 当前 git status 不成立（B3） |

## 6. 门禁顺序（每次发布前，主会话只读）

1. 快照（HEAD / git status / artifact hashes）
2. golden repro（OPERATING §4）
3. manifest 对账（release-*.json）
4. provenance 逐字对账
5. 该线 QA + 孔洞（固定 seed/n）
6. 83 + 97 + 95 `--check`（如适用）
7. 外部冻结台账比对
8. 文档数字可导出 + 发布说明由该线负责人签核
9. 主会话向所有者提交「可发/不可发」复核单（不代签）
