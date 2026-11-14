# 三线任务板 v1.1（主会话维护，2026-11-14 09:40 修订）

> 规则：见 `audit/OPERATING.md` v1.1。主会话不代写；三线执行并回报；所有者裁定优先级。
> 修订依据：A/B/C 三线对 v1.0 的审查（快照已随所有者提交 `27eab26` 更新；B golden repro 需补标点；
> `31 --check-release` 不存在；A5 会误伤 97 历史白名单；83/README 所有权会阻塞 B/C；主会话跑闸门会写项目文件）。
> 状态：`待办` / `进行中` / `待复核` / `完成` / `阻塞` / `已关闭`。
> 回报格式：命令 + 输出摘要 + 产物哈希 + 快照（HEAD / git status）。

## 0. 所有者决策

| ID | 事项 | 状态/建议 |
|---|---|---|
| O1 | A 两处修复是否提交 | **已关闭**：所有者已提交 `27eab26`（AGENTS 步 2.5、release-a res 256；工作区干净） |
| O2 | 共享资产 owner 正式化 | **降级为现状记录**：按所有者 2026-11-14 说明「共享东西由 A 维护」执行，主会话不接管；不阻塞 |
| O3 | 各线自签发布、主会话复核不代签 | 待所有者确认一句 |
| O4 | zip 是否承诺字节可复现 | 建议不承诺（记录为发布快照）；如需，另立确定性打包任务 |
| O5 | 三线是否必须同步发版 | 建议不强制；`main_version` 只是对齐标记 |
| O6 | `release_date` 语义 | 建议统一为：`release_date` = 签核日；`artifacts_built_at` = 打包日（B2 执行） |

## 1. A 线（A 会话；共享技术 owner）

| ID | 任务 | 验收标准 | 状态 |
|---|---|---|---|
| A1 | `docs/DATA.md:176/181` 的 `--res 512` 改为 256（与已提交的 `release-a.json` 对齐） | `grep -n 'res 512' docs/DATA.md` 无输出（历史 ribbon 注释行如保留须标注"旧方法"） | 待办 |
| A2a | 跑 `31_ckpt_manifest.py`（无代码改动）；`m2wt_*` 4 个入册；`m2wt_ep090` SHA-256 写进 `release-a.json`；补 `DATA §6.5.1` | MANIFEST **24/24**；`release-a.json` 含 ckpt sha256；`DATA §6.5.1` 有 m2wt 行 | 待办 |
| A2b | （可选，共享脚本）给 `31_ckpt_manifest.py` 加只读 `--check`（不是不存在的 `--check-release`） | 变更前登记影响面；跑三线回归 + 83/97；A 核准 | 待办 |
| A3 | floor 5.16 产物：A 线地板脚本 + `work/chamfer_floor.json`（seed 7、800 对、中位/CI/KS/MW）+ EXPERIMENTS E32 命令 | JSON + 命令 + 与 5.16 的一致性说明 | 待办 |
| A4 | 钉死 A golden repro 并修文档：Regular = 11+13 → `e6d8a104`；Real = **retrace** → `bf278ab1`；`--reuse-contours`=`5733ca42` 标注为"非发布路径/恢复用"；同步 `AGENTS.md` 步骤 1 的措辞 | 两条命令 + 哈希进 A 发布清单；AGENTS 不再暗示 reuse 是发布路径 | 待办 |
| A5a | 97 扫描面**只加** `docs/index.html`；收紧非历史文档的「44 码位」正则；`docs/releases/`、`docs/REPORTS/` 继续白名单/不扫（历史不改写） | `--help` 说明 + 仅 index.html 新命中；历史文件零新增误报 | 待办 |
| A5b | 发布闸另加**法律来源声明**检查（不是术语闸）：`OFL.txt`/`LICENSE`/包内 README 不得再写 `woodblock print` /「刻本」描述《四书白文》 | 独立只读脚本或发布检查单一行；OFL.txt 措辞修正或 ERRATA 登记 | 待办 |
| A6 | 文档口径收口（随下次发版）：`holes lost` 全量或固定 seed/n；`0.549→0.539` 注明 n；PROJECT_STATE/README 作废口径；DATA §4.9/§5 台账 | 审计报告对应 P1 项逐条关闭，主会话复核 | 待办 |
| A7 | 根 README 的 B/C 版本/链接行：建立「B/C 提交单行 diff + A review」的落地方式（不阻塞 B/C） | 流程写进 §2 例外或 README 维护约定 | 待办 |
| A8 | `67_verify_a.py` 的快照写 `work-b/verify_a_snapshot.json`：现状登记为例外；如需改路径，按 §3 处理（可选） | 现状已在 OPERATING §7 登记 | 已关闭（现状） |

## 2. B 线（B 会话）

| ID | 任务 | 验收标准 | 状态 |
|---|---|---|---|
| B1 | E15「中间态无法归因」改为「已解释」：62 的中间态变化来自 `62_build_full_b.py:19 VERSION="1.2.4"`（`git log -S` 指向 `bcb74b4`），非漂移；62 连跑确定性 | E15 一句说明 + 两次同哈希记录（`446cc896…`） | 待办（小） |
| B2 | `release_date` / `artifacts_built_at` 语义落地（按 O6 建议）；`data/release-b.json` 现 2026-10-30 vs zip 2026-11-13 | 两字段语义写进 DATA-B 或 release-b.json | 待办 |
| B3 | 澄清「21 个未提交文件」为当时状态；当前 `git status` 不成立 | 文档/评议记录更正一句 | 已关闭（澄清） |
| B4 | golden repro 两步钉死：Regular = `62 --drop-outside-basic` → `13_extend_punct --line B --inplace` → `aa19d6d2`；Real = `57 --reuse-contours --drop-outside-basic` → `7d10e460` | 命令 + 哈希 + 日志；主会话比对 | 待办 |
| B5 | 83 中的 B zip 条目：在 X10 落地前可用单行例外（A review）；之后从 `release-b.json` 读取 | 与 A7/X10 同步 | 待办（与 A 协同） |
| B6 | 63/68/83/97 最近输出交付（供主会话复核；73 会经 67 写 `work-b/`，由 B 自跑） | 输出摘要 + 快照 | 待办 |

## 3. C 线（C 会话）

| ID | 任务 | 验收标准 | 状态 |
|---|---|---|---|
| C1 | 0.4666 / 0.469 对齐：重跑落盘并改数，或给出 0.4666 的产物 | `release-c.json` 与唯一产物一致；附命令 | 待办 |
| C2 | clean 0.471/6.19/12.0% 来源：确认 v1.2.1 继承或重测 v1.3.0 | 字段旁注明来源版本；或重测 JSON | 待办 |
| C3 | 删除/重算 `fallback_share_of_block`（0.0712 = **v1.2.1** 的 1,495/20,992）；只留 8.34%（合成）/6.25%（区块）双口径 | release-c 无 0.0712；JSON diff 可核 | 待办 |
| C4 | v1.3.0 日期 11-02（release-c/RELEASE）与 `AGENTS.md:62` 11-12 归一 | 两处一致 | 待办 |
| C5 | 未记录修复运行：用**一组**数字核（主日志 `15,715 / fallback 836` vs 出厂 `15,735 行 / gan_fallback 17 项`）给出确认或否认 | 结论 + 三条证据路径 | 待办 |
| C6 | golden repro 钉死：Regular = `79_build_full_c`（默认含 42 标点）→ `765d0848`；Real = `76_build_real_c --close 3 --hole-repair` → `6caf9d82` | 命令 + 哈希 + 日志 | 待办 |
| C7 | RELEASE-C 补「两套验收标准」表：发布 QA（已过）vs 冻结四级门（`AUDIT-2026-10-31.md:442` 门 1=85.2%<90%、`:464-468` 门 2=5/94、`:195-215` 门 3/4 无执行记录、无签字） | 表 + 具体行号 | 待办 |
| C8 | C-big 体量 10.9 GB → 5.5 GB（apparent 5.93 GB，75 文件） | 文档更正 | 待办 |
| C9 | `release-c.json weight_bias 0.998` vs `work-c/accept_c.json 实测 1.009`：以实测为准或注明来源 | 字段与产物一致 | 待办 |
| C10 | C-big 训练污染状态：代码已修（21 的 val-data 重算 tr）、`cbig_ep100` **未重训**；在 DATA-C/EXPERIMENTS-C 登记 | 状态句 + 文件路径 | 待办 |
| C11 | C-big 旧 MPS 面板作废、CPU 面板待重生成；`104_eval_big_c.py` 已改 CPU | 登记 + 重生成计划 | 待办 |

## 4. 跨线（主会话）

| ID | 任务 | 验收标准 | 状态 |
|---|---|---|---|
| X1 | 外部冻结台账 v1（HEAD `27eab26`，工作区干净） | `audit/facts/frozen-hashes-2026-11-14T0940.json` | 完成 |
| X2 | 发布清单 v2：**先写一页跨线「检查项清单」**，各线自行实现；不复用 73 代码（73 是 B 专属） | 清单 + 一条线试跑 | 进行中 |
| X3 | 状态快照协议（v0 过期教训） | 写入 OPERATING §5；每份复核带快照 | 完成/持续 |
| X4 | 共享变更协议（含已发布哈希停手规则、3 日回归窗口） | 写入 OPERATING §3 | 完成（规则）/待演练 |
| X5 | 三线事实表 v1 | `audit/facts/2026-11-14.md`（rev 2） | 完成 |
| X6 | 审计报告状态更新 | `docs/AUDIT-2026-11-14.md §9`（+09:40 快照注） | 完成 |
| X7 | 追溯登记 2026-11-14 前共享改动（`21_train_gan.py`、`100_review.py` 由 C 改；B/C 其他改动；含 83 中 B v1.2.4 zip 行） | 影响面 + 83/97 结果 + A 核准，登记在 TASKS/CHANGELOG | 待办 |
| X8 | 每次所有者提交/发版后重跑快照 | 新 `frozen-hashes-*.json` + CHANGELOG 条目 | 完成（本次）/持续 |
| X9 | 文档数字 vs `release-*.json` 持久对账闸（只读，主会话提案） | 一小脚本或检查单；覆盖 README/DATA/AGENTS/PROJECT_STATE 关键数字 | 待办 |
| X10 | `83_verify_ab_c.py` 的 `ZIPS` 改为从 `data/release-*.json` 读取（A 执行，共享脚本变更协议） | 去掉硬编码；B/C 不再等 A 改行；三线回归 + 97 | 待办 |
| X11 | 主会话闸门写法：83/67/73 由线自跑或 `/tmp` 镜像只读等价复算；禁止直接写仓库 | 写入 OPERATING §1/§6 | 完成（规则） |

## 5. 已关闭/已裁决

| 项 | 结论 |
|---|---|
| O1 / 快照过期 | 所有者已提交 `27eab26`；v0 台账作废，v1 已建 |
| A reuse-contours 哈希差异 | 已解释：A 发布 Real = retrace；cache 路径非发布；剩余工作只是 A4 文档对齐 |
| B golden repro 只跑 62 | 修正为 62 → 13_extend_punct 两步；B Real 补 `--drop-outside-basic` |
| 31 `--check-release` | 不存在；A2 拆为 A2a（无代码）/A2b（可选加 `--check`） |
| A5 扩 97 扫描面 | 收缩：只加 `docs/index.html`；OFL/LICENSE 走独立法律来源检查（A5b）；历史文件继续白名单 |
| 主会话跑闸门会写项目文件 | 规则修正：不直接跑 83/67/73；线自跑或 /tmp 等价复算 |
| B1 中间态漂移 | 已解释（62 的 VERSION 1.2.4，`bcb74b4`），非缺陷 |
| C-big 10.9 GB | 5.5 GB（apparent 5.93 GB） |
| 7.12% 分母 | v1.2.1 的 1,495/20,992；删 |
| 83/67 自更新基线 | 已确认；漂移监测改用外部冻结台账 |
