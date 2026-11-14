# 三线任务板 v1.2（主会话维护，2026-11-14 09:52 修订）

> 规则：见 `audit/OPERATING.md` v1.2。主会话不代写；三线执行并回报；所有者裁定优先级。
> 修订依据：三线对 v1.1 的审查（快照自指、已发布 OFL 错误、83 跨线写、门禁漏 accept、`/tmp` 通道、
> 共享归属原文、B1/X8 状态矛盾等）。
> 状态：`待办` / `进行中` / `待复核` / `完成` / `阻塞` / `已关闭`。
> 回报格式：命令 + 输出摘要 + 产物哈希 + 快照（`head_at_capture` / status）。

## 0. 所有者决策

| ID | 事项 | 状态/建议 |
|---|---|---|
| O1 | A 两处修复是否提交 | **完成**：`27eab26` 已含（AGENTS 步 2.5、release-a res 256） |
| O2 | 共享资产归属原文 | **记录现状**（不是待授权）：所有者 2026-11-14 说明"共享东西由 A 维护"；缺时间/渠道/原话。确认前 A 按"现状维护 + 事后登记"，不作排他授权，不阻塞 |
| O3 | 各线自签发布、主会话复核不代签 | **待所有者确认**；当前按"各线自签、主会话复核"试运行（B 已确认，A/C 未正式确认） |
| O4 | zip 是否承诺字节可复现 | 建议不承诺（记录为发布快照） |
| O5 | 三线是否必须同步发版 | 建议不强制；`main_version` 只是对齐标记 |
| **O6** | `release_date` / `artifacts_built_at` 语义 | **三线同义**：`release_date` = 签核日；`artifacts_built_at` = 打包日。**同时覆盖 C（C4）**；B2 执行 |
| **O7** | 已发布包内 `OFL.txt` 的 "woodblock print" 如何修 | **已裁决（所有者 2026-11-14）：不改、不单独 patch 重发**。理由：不是许可条款/原则性错误，只是来源描述的轻微事实偏差；重打包成本高。处理：ERRATA E8 登记为已接受 drift；将来若因其他原因重打包，可顺带修正（可选） |

## 1. A 线（A 会话；共享技术 owner 现状）

| ID | 任务 | 验收标准 | 状态 |
|---|---|---|---|
| A1 | `docs/DATA.md:176/181` 的 `--res 512` 改为 256（与已提交的 `release-a.json` 对齐） | `grep -n 'res 512' docs/DATA.md` 无输出（历史 ribbon 注释如需保留须标"旧方法"） | 待办 |
| A2a | 跑 `31_ckpt_manifest.py`（无代码改动）；`m2wt_*` 入册；`m2wt_ep090` SHA-256 写进 `release-a.json`；补 `DATA §6.5.1` | **磁盘 .pt = 24；MANIFEST items = 24；`m2wt_ep090` 有 release 标记 + SHA-256**（三者都写清） | 待办 |
| A2b | （可选，共享脚本）给 `31` 加只读 `--check` | 变更前登记；三线回归 + 83/97；A review | 待办 |
| A3 | floor 5.16 产物：脚本 + `work/chamfer_floor.json`（seed 7、800 对、中位/CI/KS/MW）+ E32 命令 | JSON + 命令 + 与 5.16 一致性说明 | 待办 |
| A4 | 钉死 A golden repro 并修文档：Regular = 11+13 → `e6d8a104`；Real = **retrace** → `bf278ab1`；`--reuse-contours`=`5733ca42` 标注"非发布路径/恢复用"；同步 `AGENTS.md` 步骤 1 措辞；**按新规 A 自跑一次金样交日志** | 命令 + 哈希 + 日志；AGENTS 不再暗示 reuse 是发布路径 | 待办 |
| A5a | 97 扫描面**只加** `docs/index.html`；**保留**规则，只排除历史目录（`docs/releases/`、`docs/REPORTS/` 继续白名单/不扫）；收紧非历史文档的「44 码位」正则（规则不删） | `--help` 说明；仅 index.html 新命中；历史文件零新增误报 | 待办 |
| **A5b** | **已接受 drift**：E8 已由 A 写入 `docs/ERRATA.md`（未提交，`git status = M docs/ERRATA.md`）；**建议 E8 末句从"可选"改为"如重打包则必须顺带修正（改为 manuscript 或删句）"**；不修当前 `OFL.txt`、不 patch；不新增失败当前包的闸门 | E8 提交 + 提交后由主会话建 v3 快照；发布说明无需改动 | **完成（E8 已写，待提交）** |
| A6a | 指标口径收口：`holes lost` 全量或固定 seed/n；`0.549→0.539` 注明 n=150/617 | 文档口径与落盘一致 | 待办 |
| A6b | PROJECT_STATE/README 作废口径清理；DATA §4.9/§5 台账 | 审计报告对应 P1 项逐条关闭，主会话复核 | 待办 |
| A7 | 根 README 的 B/C 版本/链接行维护方式落地（单行例外） | 流程写进 §2 例外 | 待办 |
| A8 | `67` 写 `work-b/verify_a_snapshot.json`：现状登记（B 同意） | 已在 OPERATING §7 | 已关闭 |

## 2. B 线（B 会话）

| ID | 任务 | 验收标准 | 状态 |
|---|---|---|---|
| B1 | E15「中间态无法归因」改为「已解释」：62 的中间态变化来自 `62_build_full_b.py:19 VERSION="1.2.4"`（`bcb74b4`），62 连跑确定性（`446cc896…`） | E15 一句说明 + 两次同哈希记录；**等 E8 提交、v3 重拍后与 B2/B4/B6 一批做**（避免弄脏快照） | **已解释，文档待改** |
| B2 | `release_date` / `artifacts_built_at` 语义落地（O6，三线同义） | 两字段写入 DATA-B 或 release-b.json | 待办 |
| B3 | 澄清「21 个未提交文件」为当时状态；当前 git status 不成立 | 一句更正 | 已关闭（澄清） |
| B4 | golden repro 两步金样：Regular = `62 --drop-outside-basic` → `13_extend_punct --line B --inplace` → `aa19d6d2`；Real = `57 --reuse-contours --drop-outside-basic` → `7d10e460` | 命令 + 哈希 + 日志；主会话比对 | 待办 |
| B5 | 83 中 B v1.2.4 zip 条目 | 已在 `27eab26` 前存在（historical clause），无需 review | 已关闭 |
| B6 | 交付 `63_qa_b` / `68_accept_b` / `97` 最近输出；**83 不跑**（83 写 C 的 `work-c/`；由 C 或 A-with-C-consent 交付） | 三项输出 + 快照 | 待办 |
| B7 | `release-b.json` 顶层 clean 字段保持"不存在/嵌套单一源"（不复制顶层） | 文档一句 | 已关闭（裁决） |

## 3. C 线（C 会话）

| ID | 任务 | 验收标准 | 状态 |
|---|---|---|---|
| C1 | 0.4666 / 0.469 对齐：重跑落盘并改数，或给出 0.4666 的产物 | `release-c.json` 与唯一产物一致；附命令 | 待办 |
| C2 | clean 0.471/6.19/12.0% 来源：确认 v1.2.1 继承或重测 v1.3.0 | 字段注明来源版本；或重测 JSON | 待办 |
| C3 | 删除/重算 `fallback_share_of_block`（0.0712 = **v1.2.1** 的 1,495/20,992）；只留 8.34%（合成）/6.25%（区块） | release-c 无 0.0712；JSON diff 可核 | 待办 |
| C4 | 日期 11-02 vs `AGENTS.md:62` 11-12 归一；并按 **O6** 给 `release-c` 补 `release_date`/`artifacts_built_at` 语义 | 两处一致 + 字段语义与 B 相同 | 待办 |
| C5 | 未记录修复运行：用**一组**数字核（主日志 `15,715 / fallback 836` vs 出厂 `15,735 行 / gan_fallback 17 项`）确认或否认 | 结论 + 三条证据路径 | 待办 |
| C6 | golden repro：路径已定义（Regular = `79_build_full_c` 内含 42 标点 → `765d0848`；Real = `76_build_real_c --close 3 --hole-repair` → `6caf9d82`）；**金样待自跑** | 命令 + 哈希 + 日志 | 待办（路径已确认，金样待跑） |
| C7 | RELEASE-C 补「两套验收标准」表：发布 QA vs 冻结四级门（`AUDIT-2026-10-31.md:442`、`:464-468`、`:195-215`） | 表 + 行号 + 无签字说明 | 待办 |
| C8 | C-big 体量 5.5 GB（apparent 5.93 GB） | 文档更正 | 待办 |
| C9 | `release-c.json weight_bias 0.998` vs `work-c/accept_c.json 1.009` | 字段与产物一致 | 待办 |
| C10 | C-big 训练污染：代码已修（21 的 val-data 重算 tr）、`cbig_ep100` 未重训 | 在 DATA-C/EXPERIMENTS-C 登记状态 | 待办 |
| C11 | C-big 旧 MPS 面板作废、CPU 面板待重生成；`104_eval_big_c.py` 已改 CPU | 登记 + 重生成计划 | 待办 |

## 4. 跨线（主会话）

| ID | 任务 | 验收标准 | 状态 |
|---|---|---|---|
| X1 | 外部冻结台账 v2（`head_at_capture=6d20782`，`last_non_audit_commit=27eab26`） | `audit/facts/frozen-hashes-2026-11-14T0950.json` | 完成（v2） |
| X2 | 发布清单 v2：**先写跨线检查项清单**，各线自行实现；不复用 73 代码 | 清单 + 一条线试跑 | 进行中 |
| X3 | 状态快照协议（含"audit 提交不算漂移"、`committed_in` 回填） | OPERATING §5；本板 X8 | 完成（规则） |
| X4 | 共享变更协议（已发布哈希停手、24h 回归窗口、83 写 C 的归属） | OPERATING §3 | 完成（规则）/待演练 |
| X5 | 三线事实表 v2 | `audit/facts/2026-11-14.md`（rev v2） | 完成（v2） |
| X6 | 审计报告状态更新（§9.5/§9.6） | `docs/AUDIT-2026-11-14.md` | 完成（v2） |
| X7 | 追溯登记 2026-11-14 前共享改动（`21_train_gan`、`100_review`、83 B zip 行等） | 影响面 + 83/97 + A review，登记 CHANGELOG | 待办 |
| **X8** | 快照重建与 `committed_in` 回填：仅非 audit 提交/发版触发；每次新快照必须带 `previous_snapshot.committed_in` = 上一版实际提交号 | **验收**：v2 的 `committed_in` 回填为 `3336143`（已做）；E8 提交后建 v3（`head_at_capture`=E8 提交、`previous_snapshot.committed_in=3336143`、v3 `committed_in=pending`）；CHANGELOG 同步 | **v2 已回填；v3 待 E8 提交** |
| X9 | 文档数字 vs `release-*.json` 持久对账闸（只读，主会话提案） | 小脚本或检查单；覆盖 README/DATA/AGENTS/PROJECT_STATE 关键数字 | 待办 |
| **X10** | `83_verify_ab_c.py` 增加 `--no-write`/`--baseline-out` 与真正的 `--help`；`ZIPS` 改读 `data/release-*.json`（A 执行，共享变更协议） | 默认不回写；B 可安全运行；三线回归 + 97 | 待办（P1） |
| X11 | 主会话闸门写法：只读等价复算（shasum/fontTools/JSON/punct_set），**不运行 83/67/73、不复制 work 目录** | OPERATING §1/§6 | 完成（规则） |

## 5. 已关闭/已裁决

| 项 | 结论 |
|---|---|
| O1 / v0 快照过期 | `27eab26` 已提交；v0 作废 |
| **v1 快照自指过期** | `6d20782` 是 audit-only 提交，不算漂移；v2 已按 `head_at_capture=6d20782` 重建 |
| A reuse-contours | 已解释为路径定义；A4 文档对齐 |
| B golden repro 只跑 62 | 修正为两步 + Real 补 `--drop-outside-basic` |
| 31 `--check-release` 不存在 | A2 拆分（A2a 无代码 / A2b 可选） |
| A5 扩 97 | 收缩：只加 index.html；OFL/LICENSE 不纳入术语闸 |
| **OFL.txt 已发布 drift** | 所有者 2026-11-14 裁决：不改、不 patch；仅 ERRATA E8 登记（A5b，P3）；无许可条款问题 |
| 主会话跑闸门会写项目文件 | 规则修正；83 无 --help/--no-write，已登记事故与 X10 |
| B1 中间态漂移 | 已解释（VERSION 1.2.4）；仅 E15 文档待改 |
| C-big 10.9 GB | 5.5 GB（apparent 5.93 GB） |
| 7.12% 分母 | v1.2.1 的 1,495/20,992；删 |
| 83/67 自更新基线 | 外部冻结台账；83 写 C、67 写 B 已知 |
| B5 / B7 | 已关闭（historical clause / 嵌套单一源） |
| 主会话误跑 83（见 CHANGELOG 09:50） | work-c 两个缓存被重写、内容未变；制品不变 |
