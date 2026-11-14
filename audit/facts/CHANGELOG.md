# 协调层更正记录（CHANGELOG）

> 记录 `audit/` 协调产物的每次修订：谁、何时、改了什么、为什么。
> 目的：外部冻结台账本身不能变成"不可追溯"的东西（A 线 2026-11-14 的建议）。

## 2026-11-14 09:14 CST — 台账 v0 / OPERATING v1.0 / TASKS v1.0

- 创建者：主会话。
- 基线：`HEAD e308ad5`；工作区有 A 的两处未提交修复（AGENTS 步 2.5、release-a res 256）。
- 产物：`audit/OPERATING.md`、`audit/TASKS.md`、`audit/facts/2026-11-14.md`、
  `audit/facts/frozen-hashes-2026-11-14.json`、`docs/AUDIT-2026-11-14.md §9`。
- 问题（A/B/C 审查指出，成立）：**v0 快照在发布那一刻就过期**——所有者已于 09:16 前提交 `27eab26`，
  台账仍记 `M AGENTS.md` / `M data/release-a.json`；O1 也仍写"待提交"。

## 2026-11-14 09:16 CST — 所有者提交 `27eab26`

- commit 主题：`增加主会话`。
- 内容：A 两处修复（AGENTS 步 2.5、release-a `res=256` + 实测备注）+ `audit/` 全部产物 +
  `docs/AUDIT-2026-11-14.md`。
- 结果：v0 快照正式过期；工作区干净。

## 2026-11-14 09:40 CST — v1 修订（本文件对应的修订）

修订者：主会话。触发：A/B/C 三线对 v1.0 的对抗性审查。逐项如下。

### OPERATING v1.0 → v1.1

1. §1：明确主会话**不直接运行会写项目文件的闸门**（83/67/73），改为线自跑或 `/tmp` 只读等价复算；
   不做重活（不重建制品、不跑训练/生成）。
2. §2：A 的 `build/GuanGeKai-*.ttf` 通配改为**枚举**（Regular/Real 两个文件），修掉把 B/C 字体划给 A 的歧义；
   A 的脚本范围写明 01–42（17–20 归 A）；补"2026-11-14 前共享改动不回滚"的 historical clause；
   共享归属措辞降级为"现状事实（所有者说明）"，不再写成新增授权（C 的 P0-1）；
   增加 README/83 自线条目的**单行例外**（A review，不阻塞 B/C）。
3. §3：新增两条硬规则——共享改动若改到**已发布哈希**由所有者决定重发/回滚；受影响线有 **3 个工作日**
   要求回归复跑的窗口；补 2026-11-14 前改动的追溯登记。
4. §4：golden repro 修正 —— B Regular 必须 `62 → 13_extend_punct` 两步；B Real 补 `--drop-outside-basic`；
   C 路径钉死（`79` 内含标点；`76 --close 3 --hole-repair`）；明确**执行主体 = 各线自跑**，主会话只比对。
5. §5：冻结台账版本化 + 更正记录；以 v0 过期事件为例。
6. §6：发布门禁第 5/6 步改为线自跑交输出或 `/tmp` 等价复算；主会话不写仓库。
7. §7：登记 `67 → work-b/verify_a_snapshot.json` 为已知跨线写入（B 同意保留现状）。

### TASKS v1.0 → v1.1

- O1 关闭（`27eab26` 已提交）；O2 降级为现状记录；新增 O6（`release_date`/`artifacts_built_at` 语义）。
- A1–A8：A2 拆为 A2a（无代码跑 31）/A2b（可选加 `--check`）；A5 拆为 A5a（97 只加 `docs/index.html`）/
  A5b（OFL/LICENSE 独立法律来源检查）；A4 补"reuse 非发布路径"文档对齐；A7/A8 增补。
- B1 关闭（62 的 VERSION 1.2.4 解释中间态，非漂移）；B4 golden 路径改两步；B5/B6 增补。
- C1–C11：C3 注明 1,495 是 v1.2.1 的 ribbon 数；C5 统一为一组数字；C6 路径钉死；C7 补审计行号；
  C9 `weight_bias`；C10/C11 C-big 状态。
- 交叉：X2 改为"先检查项清单、不复用 73 代码"；新增 X7（追溯共享改动）、X9（文档数字持久对账）、
  X10（83 ZIPS 读 release json）、X11（主会话闸门写法）。

### 台账 v0 → v1

- 快照更新为 `HEAD 27eab26`、工作区干净；O1 关闭。
- A `--reuse-contours` 从"缺陷/待复核"改为"已解释的路径定义（A4 仅文档对齐）"。
- B golden repro 修正；B1 关闭；31 `--check-release` 不存在（A2 拆分）。
- C-big 体量 5.5 GB；7.12% 分母溯源为 v1.2.1 的 1,495/20,992。
- 新增冻结台账 v1：`audit/facts/frozen-hashes-2026-11-14T0940.json`。

### 报告

- `docs/AUDIT-2026-11-14.md` 追加 §9.5：快照更新说明（HEAD `27eab26`、O1 关闭、golden 路径修正、
  83/67/73 禁直接跑、更正记录指针）。

## 待办（截至 2026-11-14 09:40）

- 所有者：O3（签核模型确认）、O6（`release_date` 语义确认）；把任务板转给三线。
- 三线：按 `audit/TASKS.md` v1.1 执行；golden repro 由各线自跑交哈希+日志。
- 主会话：X2/X9 清单落地；X8 每次提交后重跑快照；X7/X10 跟踪。

## 2026-11-14 09:44 CST — 所有者提交 `6d20782`

- commit 主题：`更新`。内容：`audit/OPERATING.md`、`audit/TASKS.md`、`audit/facts/2026-11-14.md`、
  `audit/facts/CHANGELOG.md`、`audit/facts/frozen-hashes-2026-11-14T0940.json`、`docs/AUDIT-2026-11-14.md §9.5`。
- 性质：**audit-only 提交**。按 OPERATING v1.2 §5，这类提交不构成基线漂移；但它导致
  `T0940` 快照的 `HEAD 27eab26` 与仓库 HEAD 不一致（A/B/C 三线同时指出，成立）。

## 2026-11-14 09:52 CST — v1.2 修订（v2 快照）

修订者：主会话。触发：三线对 v1.1 的审查。逐项：

### 快照自指（A/B/C 的共同 P0）

- 采用 A 建议的漂移口径：**基线漂移 = 制品哈希变化 或 非 audit 提交**；`audit/**` 与 `docs/AUDIT-*`
  的提交（如 `6d20782`）不算漂移。
- 采用 B 建议的 `committed_in` 回填字段：快照自身所在提交由下一次快照/CHANGELOG 回填。
- 新建 `audit/facts/frozen-hashes-2026-11-14T0950.json`：
  `head_at_capture = 6d20782`、`last_non_audit_commit = 27eab26`、`git_status_at_capture = []`、
  `committed_in = pending`。v0/v1 均标 superseded（不删除）。

### 已发布制品错误（A 的 P0-2，升级）

- `OFL.txt:8` 的 `Ming-dynasty woodblock print` 存在于仓库根、`release*/OFL.txt` 与**三个已发布 zip**内
  （同哈希 `51aae3b7…`）。升级为 **P0**：A5b = 修 `OFL.txt` + ERRATA E8 + 由所有者决定 patch 重发（O7）；
  在新构建前，发布说明/README 必须声明该行已过期；许可来源检查只对**新构建**生效（不会一上线就红）。
- 写入 `audit/facts/2026-11-14.md §3` 与冻结台账 `known_released_defect`。

### 83 跨线写（B 的 P0-4 + C 的 P0-2 延续）

- `83` 写 `work-c/ab_baseline.json`、`verify_ab.json`，且**没有 `--help`/`--no-write`**。
- 规则：B 不跑 83（B6 改为 63/68/97）；83 由 C（work-c owner）或 A 经 C 同意执行；主会话不运行。
- X10 扩大：给 83 加 `--no-write`/`--baseline-out` 与真正 `--help`，并把 `ZIPS` 改为读 `data/release-*.json`。
- **事故自记**：2026-11-14 09:50 主会话为核 83 的 `--help` 实际执行了脚本，重写
  `work-c/ab_baseline.json`、`work-c/verify_ab.json`；内容与原先一致（A/B 字体哈希未变），制品未变。
  此事故作为 X10 的直接证据，不影响发布基线。

### 门禁与执行方式

- OPERATING §6 第 5 步补 **accept 脚本**：B `68_accept_b`、C `84_accept_c`（A 无独立 accept）。
- 删除 `/tmp` 镜像通道；主会话"只读等价复算"限定为：`shasum`、`fontTools` 读取、`release-*.json`、
  `punct_set.verify()`、`provenance` 对账；不运行 83/67/73、不复制 work 目录（B 的 P1-7）。
- 共享改动"3 个工作日回归窗口"改为"**下一个发版前、且不超过 24 小时**"（A 的措辞建议）。

### 归属与状态

- 共享归属措辞改为"现状描述，待所有者原文"（C 的 P1）；O2 不阻塞。
- A5a 保留规则、只加 `docs/index.html`（A 的建议）；A6 拆 A6a/A6b；A2a 验收写明磁盘 24/MANIFEST 24/
  ckpt SHA（C 的建议）；B1 状态改"已解释，文档待改"；B5 关闭；C4 与 O6 绑定；O6 覆盖三线；
  X8 状态改为"规则已定、v2 已建"。

### 报告

- `docs/AUDIT-2026-11-14.md` 追加 §9.6：OFL 已发布错误升级、v2 快照规则、83 事故、accept 门禁、
  `/tmp` 通道删除、待所有者决策。

## 待办（截至 2026-11-14 09:52）

- 所有者：**O7（OFL patch 重发决定，P0）**、O3（签核模型）、O6（日期语义）；把任务板转给三线；提交 v1.2 文件。
- 三线：按 `audit/TASKS.md` v1.2 执行；A5b 优先；golden repro 由各线自跑交哈希+日志。
- 主会话：X2/X7/X9/X10 跟踪；下一次**非 audit 提交或发版**后重建快照并回填 `committed_in`。

## 2026-11-14 09:56 CST — 所有者裁决：OFL.txt 不改、不 patch（O7 关闭）

- 所有者判断：`OFL.txt` 的 "woodblock print" 不是原则性/许可条款错误，只是来源描述的轻微偏差；
  协议性质文件改动成本高、收益低，**决定不改、不单独 patch 重发**。
- 主会话核对并同意该判断：OFL 1.1 许可正文与版权行完整，字体的 OFL 分发不受影响；
  该句属来源描述，非许可条款。残留影响仅为项目内部一致性（与"写本不是刻本"的表述不一致），
  通过 ERRATA E8 登记即可，不必重打包。
- 调整：
  - `TASKS O7` 关闭；`A5b` 从 P0 降为 **P3（仅 ERRATA E8 一段）**；不做许可来源追溯闸门；
  - `facts §3` 改为"已接受 drift"；`frozen v2` 的 `known_released_defect` 改为 `accepted-drift`；
  - `OPERATING §6` 改为"已发布 drift 不追溯；仅新构建可做提示性检查"；
  - 将来若因其他原因重打包，可顺带修正（可选，不强制）。
- 仍待所有者：O3（签核模型）、O6（日期语义）；提交本批 v1.2/v1.2.1 文件。

## 2026-11-14 09:57 CST — 所有者提交 `3336143`（v1.2 文件）

- commit 主题：`更新`；内容：`audit/OPERATING.md`、`audit/TASKS.md`、`audit/facts/2026-11-14.md`、
  `audit/facts/CHANGELOG.md`、`audit/facts/frozen-hashes-2026-11-14T0950.json`、`docs/AUDIT-2026-11-14.md`。
- 性质：**audit-only 提交**，不构成基线漂移。v2 快照的 `committed_in` 回填为 `3336143`。
- 同时：A 已完成 A5b 的 `docs/ERRATA.md` E8（内容见下），但**尚未提交**（工作区 `M docs/ERRATA.md`）。

## 2026-11-14 10:05 CST — v1.2.1 收口修订（三方终审后）

触发：A/B/C 对 v1.2 的终审。修订：

1. **主会话禁跑清单补全**（B 的要求）：除 83/67/73 外，`63_qa_b`、`68_accept_b`、`13_qa`、`80_qa_c`、
   `84_accept_c`、`71_holes --json`、`12/23/95/98`、`07/11/14` 均会写项目目录，全部列入"不直接跑"；
   只读白名单：shasum、fontTools 读取、JSON/`provenance` 对账、`punct_set.verify`、git 只读、
   `97`（只读）、`95 --check`。
2. **`committed_in` 回填验收**（B/C 的要求）：写进 OPERATING §5 与 X8；v2 实证回填 `3336143`；
   v3（E8 提交后）必须带 `previous_snapshot.committed_in=3336143`；不允许连续两版 pending。
3. **O2/O3 措辞**：O2 = "记录现状"（非待授权）；O3 = "待所有者确认，当前试运行"。
4. **A5b 收口**：E8 已写（未提交）；建议末句"可选"改为"如重打包则必须顺带修正（改 manuscript 或删句）"。
5. **B1**：等 E8 提交、v3 重拍后与 B2/B4/B6 一批做，避免弄脏快照。
6. **快照 schema**：v2 增加 `delivery_status`、`state_after_capture`、`schema_note`（无旧版 `head` 键，
   以 `head_at_capture` 为准），回填 `committed_in=3336143`。
7. **OFL 判断最终措辞**（C 的要求）：不是许可条款错误，是已分发制品中的**来源描述 drift**；
   不影响授权与使用，但影响项目内部事实一致性；接受 drift、不 patch，是因为重打包成本高于收益。
8. 当前工作区：`HEAD 3336143`（audit-only）+ `M docs/ERRATA.md`（E8）；制品哈希未变。
9. **v3 交付快照待 E8 提交后建立**；在 v3 落盘前，v2 不得作为最终交付基线。

## 待办（截至 2026-11-14 10:05）

- 所有者/A：提交 `docs/ERRATA.md`（E8；建议把"可选"改为"重打包则必须修正"）。
- 所有者：O3（签核模型）、O6（日期语义，含字段类型 ISO 字符串）确认；提交本批 v1.2.1 文件。
- 主会话：E8 提交后建 v3（含 `previous_snapshot.committed_in=3336143`）；此后按 X8 规则维护。
- 三线：A1/A2a/A3/A4 → C1/C2/C3/C6/C7 → B1/B2/B4/B6。

## 2026-11-14 10:07 CST — 所有者提交 `6bbcf3c`（v1.2.1 + E8）

- commit 主题：`更新`。内容：`audit/{OPERATING,TASKS,facts/2026-11-14,facts/CHANGELOG,facts/frozen-hashes-…T0950}.md|json`、
  `docs/AUDIT-2026-11-14.md`、**`docs/ERRATA.md`（E8）**。
- 性质：**非 audit-only**（含 `docs/ERRATA.md`）→ 按漂移规则触发新快照。
- E8 已提交，末句保留"可选，不强制"（A 建议的"重打包则必须"未应用；记录为可选后续，不阻断）。
- 工作区在提交后干净。

## 2026-11-14 10:10 CST — v3 交付快照建立（协调层收口）

- 新建 `audit/facts/frozen-hashes-2026-11-14T1007.json`：
  `head_at_capture = 6bbcf3c`、`last_non_audit_commit = 6bbcf3c`、`git_status_at_capture = []`、
  `previous_snapshot.committed_in = 3336143`、v3 `committed_in = pending`、
  `delivery_status = delivery-baseline (v3)`。
- 更新 OPERATING §7（当前基线 v3）、facts §1（v3/历史快照）、TASKS X1/X8/A5b（完成）、报告 §9.9。
- v3 写入后主会话对 `audit/` 的修订待所有者提交（audit-only，不构成漂移）；**协调层到此收口**。
- 仍待所有者：O3（签核模型）、O6（日期语义，ISO 日期类型）。此后转入三线任务执行。

## 2026-11-14 10:15 CST — 所有者确认 O3/O6 + 收口文件自指修正

所有者确认：

- **O3**：A/B/C 各自签发布说明；主会话只出"可发/不可发"复核单，不代签。
- **O6**：`release_date` = 签核日；`artifacts_built_at` = 打包日；统一 ISO 日期字符串，三线同义。

按所有者终审修正 4 处自指问题：

1. **标题/current snapshot 同步**：OPERATING 标题 → v1.2.1、头部当前基线 → v3（`...T1007.json`，head `6bbcf3c`）；
   TASKS 标题 → v1.2.1；facts 标题已为 v3、§1 HEAD 已为 `6bbcf3c`（本轮复核确认）。
2. **v3 `last_non_audit_subject`** 改为 `6bbcf3c` 的实际主题「更新（v1.2.1 协调修订 + docs/ERRATA.md E8）」。
3. **v3 `audit_only_commits_ignored`** 补 `3336143`（v1.2 audit/report only），并加 `audit_only_commit_notes`。
4. **TASKS O3/O6** 状态改「已确认（所有者 2026-11-14）」；facts §7 同步。

其他：

- facts §3 的影响表述改为所有者口径：不影响授权/分发/安装/cmap/字形，只影响项目内部 provenance/事实一致性。
- 新增 `TASKS A5b-follow`（P3）：E8 末句"可选→必须"（所有者建议），随 A 的下一个非 audit 提交一起做，
  届时按 X8 触发 v4；不单独为一句触发发版/重打包。
- OPERATING §5 漂移示例补 `3336143`。
- HEAD `6bbcf3c`；`docs/ERRATA.md` E8 已提交；制品哈希未变；`97 TERMS OK`。
- **v3 抓取后的非 audit 脏文件**：B 于 10:11 修改 `docs/EXPERIMENTS-B.md`（B1 中间态哈希说明，未提交）；
  该文件是非 audit 路径。主会话 `audit/` 修订 + v3 文件也待提交（audit-only）。
  **两者一起提交时按 X8 建 v4**（`head_at_capture`=该提交、`previous_snapshot.committed_in`=v3 实际提交号）；
  在 v4 落盘前，v3 仍是 `6bbcf3c` 的交付基线，但工作区已不等于抓取时状态（已记入 v3 `state_after_capture`）。
- 本轮 `audit/` 修订待所有者提交（audit-only，不构成漂移）。**协调层 final，转入执行。**

## 2026-11-14 10:15 CST — 所有者提交 `5940a6d`（v1.2.1 + B1）

- commit 主题：`更新`。内容：`audit/{OPERATING,TASKS,facts/2026-11-14,facts/CHANGELOG,facts/frozen-hashes-…T1007}.md|json`、
  `docs/AUDIT-2026-11-14.md`、`docs/EXPERIMENTS-B.md`（B1）。
- 性质：**非 audit-only**（含 `docs/EXPERIMENTS-B.md`）→ 按 X8 触发 v4。
- B1 已提交完成（62 的 VERSION 1.2.4 解释 + 确定性复核）；E8 末句仍是"可选"（A5b-follow 保留 P3）。

## 2026-11-14 10:18 CST — v4 交付快照建立（执行阶段开始）

- 新建 `audit/facts/frozen-hashes-2026-11-14T1015.json`：
  `head_at_capture = 5940a6d`、`last_non_audit_commit = 5940a6d`、`git_status_at_capture = []`、
  `previous_snapshot.committed_in = 5940a6d`（v3 回填）、v4 `committed_in = pending`、
  `delivery_status = delivery-baseline (v4)`。
- 更新 OPERATING §7（当前基线 v4）、facts §1/v4、TASKS X1/X8/B1（完成）、报告 §9.11。
- 抓取时工作区干净；v4 写入后主会话只改 `audit/`（audit-only，不构成漂移）。
- **执行阶段开始**：A1/A2a/A3/A4 → C1/C2/C3/C6/C7 → B2/B4/B6；主会话只读复核，
  等三线提交/交金样后按 OPERATING §6 出「可发/不可发」复核单。
