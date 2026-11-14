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
