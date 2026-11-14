# 主会话运行规则 v1.2.1（2026-11-14 10:15 修订）

> 本文件是协调层规则，放在 `audit/`，不改变项目现有结构。
> 修订依据：A/B/C 三线对 v1.1 的对抗性审查（快照自指、已发布 OFL 错误、83 被 B 跑会写 C 工作区、
> 门禁漏 accept、`/tmp` 通道未定义、共享归属无原文等），以及所有者对收口文件自指问题的终审。
> **当前交付基线 v3**：`audit/facts/frozen-hashes-2026-11-14T1007.json`
> （`head_at_capture = 6bbcf3c`，含 `docs/ERRATA.md` E8；`previous_snapshot.committed_in = 3336143`）。
> v2 `...T0950.json` 为历史规则快照（`committed_in = 3336143`）。
> 更正记录：`audit/facts/CHANGELOG.md`。**audit 自身提交不构成基线漂移**（§5）。

## 1. 主会话定位与边界

主会话不是第 4 个写者。职责：协调任务、维护任务板与事实台账、只读复核发布闸门、发布编排、
审计跟进、冲突裁决建议、向所有者上报。

不做的：

- 不写项目代码、共享文档、`work*/`、`build/`、`release*/`、`data/`；
- 不做 git 写操作（仓库由所有者管理）；
- **不重构**：不移动/重命名现有文件与目录，不新建 docs 层级；
- 不替三线写发布说明，不单方面宣布跨线技术规则；
- **不运行任何会写项目目录的脚本**。已知写盘者（不完全列表）：
  `83`（`work-c/ab_baseline.json`、`verify_ab.json`）、`67`/`73`（`work-b/verify_a_snapshot.json`）、
  `63_qa_b`（`work-b/qa/`、`holes.json`）、`68_accept_b`（`work-b/accept_b.json`）、
  `13_qa`（`work/qa/`）、`80_qa_c`（`work-c/qa/`）、`84_accept_c`（`work-c/accept_c.json`）、
  `71_holes --json`、`12/23/95/98`（`docs/images/` 或 `work/`）、`07/11/14`（`build/`/`release/`）。
  **主会话只允许只读动作**：`shasum`、`fontTools` 读取、`release-*.json`/`provenance` 读取与逐字对账、
  `punct_set.verify()`、`git` 只读命令、`97_check_terms.py`（只读）、`95_compare_lines.py --check`（只读）。
  注意 `83` **没有实现 --help/--no-write**：传 `--help` 也会执行并写盘
  （2026-11-14 09:50 主会话误跑一次，内容未变、已登记 CHANGELOG）。闸门只能由各线自跑交输出（§6）。

## 2. 写作用域矩阵

| 角色 | 可写 | 不可写 |
|---|---|---|
| 所有者 | 全部；git；发布签核；角色与规则裁决 | — |
| A 会话 | A 线产物：`work/`、`build/GuanGeKai-Regular.ttf`、`build/GuanGeKai-Real.ttf`、`release/`、`data/release-a.json`、A 的 `RELEASE/README`；**共享 docs**：`AGENTS.md`、`PROJECT_STATE`、`DATA`、`EXPERIMENTS`、`GLOSSARY`、`CONVENTIONS`、`method`、`README`、`PLAN`；**共享脚本**：`scripts/` 中非 `_b`/`_c` 脚本（01–42；17–20 归 A）+ 共享库 | B/C 的 `work*/build/release*/doc/data`；不重构 |
| B 会话 | `work-b/`、`build/GuanGeKai-B-*.ttf`、`release-b/`、`scripts/*_b.py`、`*-B.md`、`data/release-b.json` | A/C 的同上 |
| C 会话 | `work-c/`、`work-c-big/`、`build/GuanGeKai-C-*`、`release-c/`、`scripts/*_c.py`、`*-C.md`、`data/release-c.json` | A/B 的同上 |
| 主会话 | `audit/**`（findings / facts / TASKS / OPERATING）、自己创建的 `docs/AUDIT-*` | 其余全部；只读验证 |

**共享资产归属（暂定，待所有者原文）**：项目 README 与共享文档/脚本目前由 A 维护，这是**现状描述**，
不是排他授权。所有者原话/时间/渠道尚缺，`TASKS O2` 记为待确认；确认前：

- A 对共享脚本/共享 docs 的改动按「现状维护 + 事后登记（X7）」处理，**不视为排他写权限**；
- 其他线对共享文件的改动仍按 §3 协议（先登记、跨线回归、A review、主会话记录）。

**Historical clause**：2026-11-14 前已发生的共享改动（如 `21_train_gan.py`、`100_review.py`、83 的 B zip 行）
视为既成事实，不回滚；此后按 §3。

**发布元信息单行例外**：根 `README.md` 的 B/C 版本/链接行、83 的 `ZIPS` 中本线条目，允许该线提交
**单行 diff**，A review；X10 落地后 83 条目改为读 `release-*.json`。此例外不扩大写作用域。
（B v1.2.4 的 83 条目已在 historical clause 内，无需再 review —— B5 已关闭。）

## 3. 共享资产变更协议

适用：`punct_set`、`05/06/08/10/13/14/83/97`、其他被两条以上线引用的脚本或文档口径。

1. **变更前**：在 `audit/TASKS.md` 登记，说明影响面（哪几条线、哪类产物）。
2. **变更后**：跑三线回归——成品哈希 + 中间产物哈希；跑 `83`、`97`；涉及发布口径的跑对应 QA；
   **`83` 会写 `work-c/`，由 C（work-c owner）执行，或 A 经 C 同意执行**；B 不跑 83。
3. **A（共享技术 owner，待原文确认）review** 语义变化；主会话记录证据，不代改。
4. **已发布哈希停手规则**：共享改动若使任一**已发布制品**哈希变化，由**所有者**决定「重发」或「回滚」。
5. **回归窗口**：受影响线可在**下一个发版前、且不超过 24 小时**要求回归复跑；未复跑前不进发布签核。
6. **追溯登记**：2026-11-14 前共享改动在 X7 补登记。
7. 未按协议改共享脚本：主会话在下次闸门中列为「未验证变更」，不签发布复核。

## 4. golden repro（路径定义 + 金样验收分开；执行主体=各线自跑）

> 路径定义已按代码核对（A/B/C 三线 2026-11-14 确认）。**金样验收**由各线自跑交「命令 + 哈希 + 日志」，
> 主会话只比对，不亲自构建。

| 线 | 产物 | 路径（钉死） | 期望哈希 | 状态 |
|---|---|---|---|---|
| A | Regular | `11_build_full` → `13_extend_punct --line A --inplace` | `e6d8a104…` | v1.0 时主会话实测；按新规由 A 复跑确认（A4） |
| A | Real | `07_build_real` **retrace**（masks） | `bf278ab1…` | 同上；`--reuse-contours`=`5733ca42…` 非发布路径 |
| B | Regular | `62_build_full_b --drop-outside-basic` → `13_extend_punct --line B --inplace` | `aa19d6d2…` | 路径已确认；金样待 B 自跑（B4） |
| B | Real | `57_build_real_b --reuse-contours --drop-outside-basic` | `7d10e460…` | 路径已确认；金样待 B 自跑（B4） |
| C | Regular | `79_build_full_c`（默认内含 42 标点） | `765d0848…` | 路径已确认；金样待 C 自跑（C6） |
| C | Real | `76_build_real_c --close 3 --hole-repair` | `6caf9d82…` | 路径已确认；金样待 C 自跑（C6） |

**A 的路径定义**：A 发布 Real = retrace；cache 路径哈希不同属已解释的路径差异，不是字体缺陷；
剩余工作是把 `AGENTS.md` 步骤 1 与发布清单对齐（A4）。

## 5. 状态快照协议（修快照自指）

任何审计、闸门、发布复核结论必须同时记录：

- `head_at_capture`（抓取时 HEAD）、`last_non_audit_commit`（最近一次含非 audit 路径的提交）
- `git_status_at_capture`（用 `[]` 表示干净，不使用 null）
- 未提交修改清单 + 文件哈希；相关制品 SHA-256；采样时间
- `committed_in`：本快照文件自身所在提交（由所有者提交后由下一次快照/CHANGELOG **回填**；
  未提交时写 `"pending"`）。**回填验收**：下一次快照必须把上一版的实际提交号写进
  `previous_snapshot.committed_in`，并在 CHANGELOG 记录；不允许连续两版都停在 pending。
  快照 schema 只使用 `head_at_capture`，不设旧版 `head` 键；下游解析以 `head_at_capture` 为准。

**漂移定义**：基线漂移只由 **① 制品哈希变化** 与 **② 非 audit 路径的提交**触发；
`audit/**` 与 `docs/AUDIT-*` 的提交（如 `6d20782`、`3336143`）**不构成基线漂移**。这样避免
「写台账→提交→台账过期」的循环。快照文件版本化保存，不删除旧版；CHANGELOG 记录每次修订。

## 6. 发布门禁（主会话只读复核）

每次发布前按线执行，全部通过才提交所有者：

1. 快照（`head_at_capture` / status / 制品哈希；按 §5 的漂移定义比对）；
2. golden repro（§4）——线自跑交哈希+日志，主会话比对；
3. 发布 manifest 与制品一致（A `release-a.json` / B `release-b.json` / C `release-c.json`）；
4. `provenance` ↔ `chosen`/`generated` 逐字对账；
5. 该线 QA + 孔洞（固定 seed/n）+ **该线 accept 脚本**：
   A 无独立 accept；B `68_accept_b`；C `84_accept_c`（字重/包围盒/回退率等硬闸）；self-audit 由该线自跑；
6. 跨线 `83`/`97`/`95 --check`：由线自跑交输出；**主会话只做只读等价复算**——
   允许的动作仅限 `shasum` 哈希比对、`fontTools` 读取 cmap/name、读 `release-*.json`、
   `punct_set.verify()`、`provenance` 逐字对账；**不运行 83/67/73，不复制 20 GB work 目录**；
7. 外部冻结台账比对（§7）；83/67 的自更新基线不作漂移证据；
8. 文档数字可由 manifest/落盘文件导出；发布说明由该线负责人签核，主会话复核不代签。

**包内许可文本（已发布 drift 已接受，不追溯）**：当前三个已发布包内 `OFL.txt` 第 8 行仍写
"woodblock print"。所有者 2026-11-14 裁决（O7）：**不改、不单独 patch 重发**——它不是 OFL 条款/版权行错误，
只是来源描述的轻微偏差；ERRATA E8 登记为已接受 drift。若将来因其他原因重打包，可顺带修正（可选）。
**不对已发布包新增会失败的许可来源闸门**；只允许在"新构建"流程里做提示性检查（非阻断）。

zip：只作为**发布快照记录**；字体字节可复现，zip 在现有工具链下不承诺字节可复现（O4）。

## 7. 外部冻结台账

- **当前交付基线 v3**：`audit/facts/frozen-hashes-2026-11-14T1007.json`
  （`head_at_capture = 6bbcf3c`，2026-11-14 10:07；**非 audit-only**，含 `docs/ERRATA.md` E8）。
  `previous_snapshot.committed_in = 3336143`；v3 自身 `committed_in = pending`（由下一次快照/CHANGELOG 回填）。
  抓取时工作区干净；v3 写入后主会话对 `audit/` 的修订待提交（audit-only，不构成漂移）。
- **历史版本**：v2 `...T0950.json`（规则快照，`committed_in = 3336143`）、v1 `...T0940.json`（自指过期）、
  v0 `frozen-hashes-2026-11-14.json`（过期）；均标 superseded，不删除。
- 主会话每次闸门对比 v3；制品哈希不变且**非 audit** 提交未出现时视为无漂移。
- 写盘副作用清单：`83` 写 `work-c/ab_baseline.json`、`work-c/verify_ab.json`（且无 --help/--no-write）；
  `67` 写 `work-b/verify_a_snapshot.json`；`73` 经 67 写同一文件；QA/accept 脚本写各自 `work*/qa/` 与
  `accept_*.json`（§1 已列入主会话禁跑清单）。X10 跟踪 `83 --no-write/--help`。

## 8. 任务与汇报

- 任务板：`audit/TASKS.md`。主会话维护；三线执行并回报；所有者裁定优先级。
- 每个任务必须带验收标准；完成后主会话复核，把证据行写进台账。
- 冲突：主会话给证据与建议，所有者拍板；不投票、不默认多数。
- 节奏：每次闸门/发布后向所有者报一次；无任务不后台改项目。

## 9. 不重构声明

现存目录、文件命名、文档归属、README = 项目 README（A 线）的事实保持不变。
主会话不发起结构迁移；如所有者要求才另议。
