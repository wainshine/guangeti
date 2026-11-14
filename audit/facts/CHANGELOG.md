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

## 2026-11-14 10:19 CST — 所有者提交 `56edd05`（audit-only：v4 + checklist）

- 内容：v4 快照、`release-gate-checklist.md` v0、audit 修订；**audit-only**，不触发漂移。
- v4 的 `committed_in` 回填为 `56edd05`（在 v5 中记录）。

## 2026-11-14 10:34 CST — 所有者提交 `beaa524`（A/B/C 三线合并交付）

- 16 文件：AGENTS、README、DATA、PROJECT_STATE、EXPERIMENTS、ERRATA E9、DATA-B/C、RELEASE-C、
  EXPERIMENTS-C、index.html、`scripts/43_chamfer_floor.py`（新）、`scripts/97_check_terms.py`（A5a）、
  `data/release-a/b/c.json`。
- 性质：**非 audit-only** → 触发 v5。

## 2026-11-14 10:36 CST — v5 交付基线 + 合并交付核验

- 新建 `audit/facts/frozen-hashes-2026-11-14T1035.json`：`head_at_capture = beaa524`、
  `previous_snapshot.committed_in = 56edd05`、`committed_in = pending`、`delivery_status = delivery-baseline (v5)`；
  v4 的 `committed_in=56edd05` 已回填。
- **核验结论**（详见 facts §6.13 / TASKS §5 / 报告 §9.12）：
  - A：A1/A3/A5a/A7 完成；A2a 部分（MANIFEST 24/24 + SHA 已核，`release` 标记未实现）；
    A4 文档完成但**自跑金样日志缺失**（A build 未重建）；A6a/A6b 未清。
  - B：B2/B4/B6 完成；golden 日志 `work-b/golden_repro_2026-11-14.log` 哈希一致、QA/accept/selfaudit 全过；
    仅 DATA-B「C v1.2.0」一句 P3。
  - C：C1/C2/C3/C5/C6/C7/C8/C9/C10/C11 完成；golden 日志 `work-c/logs-v1.3/golden_c_v13.log` 哈希一致；
    C4 待 A 改 AGENTS 日期一行；README-C 旧值待更新（C12）。
  - 制品：六 TTF/三 zip 哈希未变；B/C build 2026-11-14 重建后字节一致；A build 未重建；三线 SHA 自检 OK；97 OK。
- 更新 OPERATING §7（v5）、facts v5、TASKS v1.3、报告 §9.12。
- v5 写入后主会话只改 `audit/`（audit-only，不构成漂移）；下轮三线提交时按 X8 建 v6。

## 2026-11-14 10:39 CST — 所有者提交 `6858c08`（audit-only：v5 + 核验）

- 内容：v5 快照、TASKS v1.3、facts v5、报告 §9.12；**audit-only**，不触发漂移。
- v5 的 `committed_in` 回填为 `6858c08`（在 v6 中记录）。

## 2026-11-14 10:48 CST — 所有者提交 `0e22ade`（A4/A2a/C4/C12/B8/A6a 收口）

- 5 文件：`AGENTS.md`（C 日期归一 + holes n=300 基线）、`README-C.md`（unseen 0.470/6.38/8.3%）、
  `README.md`（Dice 0.549→0.539）、`docs/DATA-B.md`（C v1.3.0）、`scripts/31_ckpt_manifest.py`
  （`release_ckpts.json` → `kind=release`）。
- 性质：**非 audit-only** → 触发 v6。
- A4 金样已在 `work/logs/golden_repro_a_2026-11-14.log`（07 retrace `bf278ab1`、11→13 `e6d8a104`、13_qa OK）；
  A build 10:40–10:41 重建后字节一致。

## 2026-11-14 10:52 CST — v6 交付基线 / 收口复核

- 新建 `audit/facts/frozen-hashes-2026-11-14T1050.json`：`head_at_capture = 0e22ade`、
  `previous_snapshot.committed_in = 6858c08`、`committed_in = pending`、`delivery_status = delivery-baseline (v6)`；
  v5 的 `committed_in=6858c08` 已回填。
- 核验：A4/A2a（release 标记）/C4/C12/B8 完成；A6a 部分；A6b 未动；制品六 TTF/三 zip 未变；
  三线 SHA 自检 OK；97 OK；MANIFEST A 24（`m2wt_ep090`/`m2_ep080` 均 `kind=release`）。
- 新增 P3/P2 备注：release 标记依赖 `work/ckpt/release_ckpts.json`（gitignore，work 重建会丢；
  31 的 `CK` 硬编码 A 的 work/ckpt；DATA §6.5.1 未登记该文件）；AGENTS C 段仍写 `unseen 0.4666`（与 0.470 不一致）；
  n=200 0.7% 无落盘产物；EXPERIMENTS 历史表未标口径；A6b 旧口径未清。
- 更新 OPERATING §7（v6）、facts v6、TASKS v1.4、报告 §9.13。
- v6 写入后主会话只改 `audit/`（audit-only）；下轮三线提交时按 X8 建 v7。

## 2026-11-14 11:03 CST — 所有者提交 `2f523d1`（A6a/A6b + release 标记入库，混合提交）

- 14 文件：`AGENTS.md`、`README.md`、`docs/{PROJECT_STATE,DATA,EXPERIMENTS}.md`、
  `data/release_ckpts_a.json`（新）、`scripts/31_ckpt_manifest.py`、`audit/*`（v6）。
- 性质：**混合提交**（非 audit-only 文档/脚本 + audit）→ 触发 v7。
- 要点：C unseen 改 0.470；holes n=200 1.4% + `work/holes_a_n200.json`；EXPERIMENTS 口径脚注；
  README/PROJECT_STATE/DATA 旧口径清理；release_ckpts 入库 + `31 --release-file` + DATA §6.5.1 登记。

## 2026-11-14 11:06 CST — v7 交付基线 / 文档收尾复核

- 新建 `audit/facts/frozen-hashes-2026-11-14T1103.json`：`head_at_capture = 2f523d1`、
  `previous_snapshot.committed_in = 2f523d1`、`committed_in = pending`、`delivery_status = delivery-baseline (v7)`；
  v6 的 `committed_in=2f523d1` 已回填。
- 核验：
  - A6a 完成（AGENTS C 0.470 / holes 双 n / EXPERIMENTS 脚注）；
  - A6b 大部分完成（README 拓扑/程序化/C 指针/去色；PROJECT_STATE 118/139/211；DATA 36 步标注）；
  - release 标记 P3 修复（`data/release_ckpts_a.json` + `31 --release-file` + DATA 登记）；
  - 制品未变；三线 SHA 自检 OK；97 OK；MANIFEST A 24（release 2 项）。
- **A6b 残余 4 处**：README 已知限制「9.5% 觸發守衛」（现 4.1% ribbon）；`docs/method.md §5.0` 仍 9.5%/0.549/5.92/5.16；
  DATA §5 校验和仍列 v1.5.0–v1.5.2 / B v1.0.1；DATA §4.9 称 build ID0 仍 `Ming woodblock print`（实测已是 `Ming manuscript`）。
- 跨线未做：X7（97/31/21/100 登记）、X9（数字对账）、X10（83 `--no-write`）、X2（checklist review）。
- 更新 OPERATING §7（v7）、facts v7、TASKS v1.5、报告 §9.14。v7 写入后主会话只改 `audit/`（audit-only）；下轮按 X8 建 v8。

## 2026-11-14 11:26 CST — 所有者提交 `bcdeb10`（A6b 收尾，混合提交）

- 10 文件：`README.md`（已知限制 4.1%）、`docs/method.md`（4.1%/0.539/6.13/5.42）、`docs/DATA.md`（§4.9 ID0 已修复、§5 A/B/C 当前校验和）、`audit/*`（v7）。
- 性质：**混合提交** → 触发 v8。
- **新发现（P2）**：DATA §5 历史版本段落（`docs/DATA.md:130-138`）残留 3 行旧 B v1.0.1 哈希 + 错位 code fence，
  导致 `release-b/SHA256SUMS` 与 `release/SHA256SUMS` 段落被吞进代码块；交 A6b-follow（A 清理）。

## 2026-11-14 11:28 CST — v8 交付基线 / A6b 收尾复核

- 新建 `audit/facts/frozen-hashes-2026-11-14T1126.json`：`head_at_capture = bcdeb10`、
  `previous_snapshot.committed_in = bcdeb10`、`committed_in = pending`、`delivery_status = delivery-baseline (v8)`；
  v7 的 `committed_in=bcdeb10` 已回填。
- 核验：A6b 四项残余全部修复（README 4.1% / method.md / DATA §4.9 ID0 / DATA §5 当前校验和）；
  制品未变；三线 SHA 自检 OK；97 OK；MANIFEST A 24（release 2 项）。
- 新待办：`A6b-follow`（DATA §5 排版回归，P2）；X7/X9/X10/X2 仍未做；A2b 可选；A5b-follow P3。
- 更新 OPERATING §7（v8）、facts v8、TASKS v1.6、报告 §9.15。v8 写入后主会话只改 `audit/`（audit-only）；下轮按 X8 建 v9。

## 2026-11-14 11:48 CST — 所有者提交 `8b810f3`（DATA §5 修复 + E8 措辞，混合提交）

- 9 文件：`docs/DATA.md`（删残留 3 行旧 B v1.0.1 + 错位 fence，统一 release*/SHA256SUMS 说明）、
  `docs/ERRATA.md`（E8 末句改为「若重打包，必须顺带改为 Ming manuscript」）、`audit/*`（v8）。
- 性质：**混合提交** → 触发 v9。
- 两个 follow-up 均闭环：A6b-follow（DATA §5 排版）、A5b-follow（E8「必须」）。

## 2026-11-14 11:50 CST — v9 交付基线 / A 线收尾复核

- 新建 `audit/facts/frozen-hashes-2026-11-14T1148.json`：`head_at_capture = 8b810f3`、
  `previous_snapshot.committed_in = 8b810f3`、`committed_in = pending`、`delivery_status = delivery-baseline (v9)`；
  v8 的 `committed_in=8b810f3` 已回填。
- 核验：DATA §5 排版已修（97 OK）；E8「必须」已落；制品未变；三线 SHA 自检 OK；MANIFEST A 24（release 2 项）。
- **A 线闭环**（A1–A7 + A5b/A6a/A6b follow-up 全完成；A2b 可选未做）。
- 剩余仅跨线：X7（97/31/21/100 登记）、X9（文档数字对账）、X10（83 `--no-write/--help` + ZIPS 读 json）、
  X2（checklist review）。
- 更新 OPERATING §7（v9）、facts v9、TASKS v1.7、报告 §9.16。v9 写入后主会话只改 `audit/`（audit-only）；下轮按 X8 建 v10。

## 2026-11-14 11:52 CST — 所有者授权：文字错误直改；纯文档提交不重建快照；X7 完成

所有者反馈「反复更新太费劲」，决定：

1. **文字性/文档错误由主会话直接改**，不再排 A 等下一轮。范围：typo、过期措辞/数字、格式、链接、CJK 用字；
   不改代码/脚本/data/制品；每次修正在本 CHANGELOG 记录（文件 + 提交号）；git 仍由所有者执行。
   已写入 OPERATING v1.2.2 §1/§2。
2. **纯文档修正提交不重建快照**：基线只由 ①制品哈希变化 ②脚本或 data 变化 ③发版 触发；
   README/DATA/method/ERRATA 等纯文字/数字/格式修正只记 `docs_commits`，不新建 vN。
   当前 **v9（`8b810f3`）继续作为交付基线**，直到下次制品/脚本/data 变化或发版再建 v10。
3. **X7 追溯登记完成**（历史共享改动，不回滚）：
   - `scripts/97_check_terms.py`：`beaa524`（A5a 加 docs/index.html 扫描）、`83d01d9`（+1 行）；
     影响：仅术语闸；验证：97 OK、index.html 已改「寫本」；A 为作者。
   - `scripts/31_ckpt_manifest.py`：`0e22ade`（release kind）、`2f523d1`（--release-file + data 文件）；
     影响：仅 A 的 MANIFEST；验证：A 24/24、B 14、C 43 不变；97 不受影响；A 为作者。
   - `scripts/21_train_gan.py`：`83d01d9`（C 的 val-data 重算 tr 修复）、`ef6e3f8`（C-big）；
     影响：仅 C-big 实验（未重训），不进发布；83/97 不受影响；已登记 EXPERIMENTS-C。
   - `scripts/100_review.py`：`ef6e3f8`（C 新增）、`83d01d9`（CPU 相关）；影响：仅审阅图/文档生成；不进制成品。
4. TASKS v1.8：X7 完成；X9（主会话只读检查器 + 直改文字）、X2（主会话定稿 advisory）、
   X10（主会话出 patch，A 共享 owner review，C 跑 83 回归）进行中。

## 2026-11-14 11:53 CST — 所有者提交 `f2fc6ed`（audit-only：v9 台账）

- 内容：v9 快照 + facts v9 + TASKS v1.7 + 报告 §9.16；**audit-only**，不触发漂移。
- v9 的 `committed_in` 回填为 `f2fc6ed`（已写入 OPERATING/facts/TASKS 与快照文件）。
- 依新规则：**v9 保持当前交付基线**，纯文档/audit 提交不再新建 v10；下一次快照只看制品/脚本/data 变化或发版。

## 2026-11-14 12:05 CST — X10 实施：83 改造（所有者授权 A：主会话直改，A review）

- 所有者选择「A」：主会话直接改 `scripts/83_verify_ab_c.py`，A 做共享 owner review，C 跑回归，B 不跑。
- 改动：真 `--help`/argparse；**默认只读**，`--write`/`--out-dir` 才写；`ZIPS` 读
  `data/release-{a,b,c}.json`（A 嵌套 `artifacts`、B 推导文件名、C 顶层）；写盘移到字集检查后（修 P1-8）；
  docstring 纠正。patch 存 `audit/proposals/X10-83.patch`，review 单 `audit/proposals/X10-83-review.md`。
- 主会话自测：`--help` 不执行；默认 `A/B INTACT` + 三 zip OK + 三行 21034，`work-c/` mtime 未变；
  `--out-dir /tmp/83test` 正常写；`--write --no-write` 互斥报错。
- 同步文档：`AGENTS.md`、`README-C.md`、`docs/{DATA-C,PLAN-C,CONVENTIONS}.md`、检查单 F1；
  **未改** `release-c/README.md`（包内快照，改则 SHA256SUMS 失配）。
- 待办：A review patch；C 跑 `83 --write` + `97` 回归；B 不跑。脚本已变，提交后需建 v10 快照
  （当前 HEAD f2fc6ed；工作区含本次改动）。

## 2026-11-14 12:10 CST — X9 初版 + 两处文档数字直改

- 新增只读检查器 `audit/tools/check_doc_numbers.py`（X9）：扫 11 份当前文档（2094 行），
  检查过期数字/术语（0.549/5.92/5.16/0.4666/9.5%/0.7%/4,078/21,036/44 码位 等，历史行有上下文豁免）
  与短哈希前缀；不写项目文件。复跑结果：`DOC NUMBERS OK`。
- 按所有者 2026-11-14「文字错误直改」授权，直接修正两处当前文档：
  1. `README-C.md` 分工表 B 真迹 `4,078（19.4%）` → `4,073（19.4%）`；
  2. `docs/RELEASE-v1.7.2.md` 表格前加「口径更正（2026-11-14）」：
     孔洞 n=200 重测 1.4%（2/145）、Dice/chamfer 以 clean617 0.539/6.13 为准（旧 0.549/5.92 为 n=150 抽样，见 E9）。
- X2 清单定稿为 advisory；X10 待 A review + C 回归；本次提交后建 v10（83 脚本哈希已变）。

## 2026-11-14 12:16 CST — 所有者提交 `06fb50d`（X10 83 改造 + X9 + 文档修正）

- 16 文件：`scripts/83_verify_ab_c.py`、`audit/proposals/*`、`audit/tools/check_doc_numbers.py`、
  文档引用（AGENTS/README-C/CONVENTIONS/DATA-C/PLAN-C/RELEASE-v1.7.2）+ audit 台账。
- 性质：**非 audit-only**（脚本变更）→ 触发 v10。
- X10 代码完成：默认只读、`--write`/`--out-dir`、真 `--help`、zip 读 `data/release-{a,b,c}.json`、
  写盘移到字集检查后（P1-8）。X9 初版完成；X7/X2 完成。

## 2026-11-14 12:18 CST — v10 交付基线

- 新建 `audit/facts/frozen-hashes-2026-11-14T1216.json`：`head_at_capture = 06fb50d`、
  `previous_snapshot.committed_in = f2fc6ed`、`committed_in = pending`、`delivery_status = delivery-baseline (v10)；
  v9 的 `committed_in=f2fc6ed` 已回填；83 新哈希 `14b46c7d…`。
- 核验：`83 --help` 只打印；默认 `A/B INTACT` + 三 zip OK + 三行 21034，`work-c/` mtime 未变；
  `--out-dir /tmp` 正常；97 OK；DOC NUMBERS OK；三线 SHA 自检 OK；制品未变。
- 剩余：**C 跑 `83 --write` + `97` 回归**（B 不跑）；A 对 `audit/proposals/X10-83-review.md` 的 review 记录。


## 2026-11-14 12:17–12:19 CST — v10 台账提交（audit-only）+ A review / C 回归通过（X10 闭环）

- `b2346b8`（12:17，audit-only）：v10 快照 + OPERATING/TASKS/facts/报告 §9.17 台账；v10 `committed_in=b2346b8` 已回填。
- **A（共享 owner）review 通过（12:2x）**：X10 patch 可合入；实测 `--help` 无副作用、默认只读、
  `--out-dir` 正常、三线 zip 由 release json 驱动、写盘在字集检查后（P1-8 成立）、互斥参数报错正确。
  非阻断建议：`--write` + 自定义 `--out-dir` 时 baseline 默认读 work-c；登记 `X10-follow`（P3）。
- **C 回归通过（12:19:25）**：`83 --write` → 四字体 OK、A/B 计数 OK、三行 21034 = 20,992+42、
  `RESULT: A/B INTACT`、`WROTE work-c/verify_ab.json + ab_baseline.json`；`97` → `TERMS OK`。
  `work-c/ab_baseline.json` 四哈希与制品一致；`verify_ab.json` `ok=true`、`issues=[]`。
- 主会话复核：`83` 默认只读不再写（work-c mtime 保持 12:19:25）；六 TTF/三 zip 未变；
  三线 SHA 自检 OK；97 OK；DOC NUMBERS OK。
- **跨线 X7/X9/X10/X2 全部闭环**；全项目任务板无未闭合项（仅 A2b、X10-follow 两个可选）。
