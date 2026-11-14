# 主会话运行规则 v1.1（2026-11-14 接管；09:40 修订）

> 本文件是协调层规则，放在 `audit/`，不改变项目现有结构。
> 修订依据：A/B/C 三线 2026-11-14 对 v1.0 的对抗性审查（快照过期、A5 误伤术语闸、golden repro 路径、写作用域通配符、
> 83/README 所有权阻塞、主会话跑闸门会写项目文件等）。
> 更正记录：`audit/facts/CHANGELOG.md`。当前快照：`audit/facts/frozen-hashes-2026-11-14T0940.json`（HEAD `27eab26`，工作区干净）。

## 1. 主会话定位与边界

主会话不是第 4 个写者。职责：

1. 协调三线任务、维护任务板与事实台账；
2. 只读运行发布闸门与跨线回归（**不做重活、不重建制品、不跑训练/生成**）；
3. 发布编排与签核前复核（**复核不代签**）；
4. 审计跟进、冲突裁决建议、向所有者上报。

不做的：

- 不写项目代码、共享文档、`work*/`、`build/`、`release*/`、`data/`；
- 不做 git 写操作（仓库由所有者管理）；
- **不重构**：不移动/重命名现有文件与目录，不新建 docs 层级（协调产物一律放 `audit/`）；
- 不替三线写发布说明，不单方面宣布跨线技术规则；
- **不直接运行会写项目文件的闸门**：`83_verify_ab_c.py`（写 `work-c/`）、`67_verify_a.py`（写 `work-b/`）、
  `73_selfaudit_b.py`（经 67 写 `work-b/`）。这些由各线自跑并交输出，或主会话用临时镜像做只读等价复算
  （写入仅限 `/tmp`，且在复核单中注明）。

## 2. 写作用域矩阵（现状事实 + 本次约定）

| 角色 | 可写 | 不可写 |
|---|---|---|
| 所有者 | 全部；git；发布签核；角色与规则裁决 | — |
| A 会话 | A 线产物：`work/`、`build/GuanGeKai-Regular.ttf`、`build/GuanGeKai-Real.ttf`、`release/`、`data/release-a.json`、A 的 `RELEASE/README`；**共享 docs**：`AGENTS.md`、`PROJECT_STATE`、`DATA`、`EXPERIMENTS`、`GLOSSARY`、`CONVENTIONS`、`method`、`README`、`PLAN`；**共享脚本**：`scripts/` 中非 `_b`/`_c` 脚本（含 01–42；17–20 为 A 线评估工具，归 A）与共享库 | B/C 的 `work*/build/release*/doc/data`；不重构 |
| B 会话 | `work-b/`、`build/GuanGeKai-B-Regular.ttf`、`build/GuanGeKai-B-Real.ttf`、`release-b/`、`scripts/*_b.py`、`*-B.md`、`data/release-b.json` | A/C 的同上 |
| C 会话 | `work-c/`、`work-c-big/`、`build/GuanGeKai-C-*`、`release-c/`、`scripts/*_c.py`、`*-C.md`、`data/release-c.json` | A/B 的同上 |
| 主会话 | `audit/**`（findings / facts / TASKS / OPERATING）、自己创建的 `docs/AUDIT-*` | 其余全部；只读验证 |

**共享资产归属的现状表述**：所有者 2026-11-14 说明「项目 README 与共享文档框架事实上是 A 的 README
（先 A 后 B、C，沿用框架；没有另设主会话，共享东西由 A 维护）」。因此：

- 这是**现状事实**，不是新增授权；主会话不接管，也不替所有者分配写权限；
- 归属如需正式变更，由所有者另定（`TASKS O2` 只是记录现状，不阻塞任何工作）。

**Historical clause**：2026-11-14 前已发生的共享脚本/文档改动（例如 `21_train_gan.py`、`100_review.py`
被 B/C 改动）视为既成事实，不回滚；此后按 §3 先登记后改。

**发布元信息单行例外（最小化，避免阻塞 B/C）**：

- 根 `README.md` 中 B/C 的版本号/发布说明链接行，允许 B/C 提交**单行 diff**，A review；
- `83_verify_ab_c.py` 的 `ZIPS` 中本线条目，在 `X10`（改为读 `release-*.json`）落地前，允许该线提交**单行 diff**，A review；
- 除此之外的共享文件改动仍按 §3。此例外不构成共享资产归属变更，也不扩大写作用域。

## 3. 共享资产变更协议

适用：`punct_set`、`05/06/08/10/13/14/83/97`、其他被两条以上线引用的脚本或文档口径。

1. **变更前**：在 `audit/TASKS.md` 登记（或经所有者转达），一句话说明影响面（哪几条线、哪类产物）。
2. **变更后**：跑三线回归——成品哈希 + 中间产物哈希；跑 `83`、`97`；涉及发布口径的跑对应 QA。
3. **A（共享技术 owner）核准**语义变化；主会话只记录证据，不代改。
4. **已发布哈希停手规则**：共享改动若使任一**已发布制品**哈希变化，由**所有者**决定「重发」或「回滚」；
   A 的语义核准不能替代所有者决定。
5. **受影响线回归窗口**：共享变更若影响某线，该线可在 3 个工作日内要求回归复跑；未复跑前不进发布签核。
6. **追溯登记**：2026-11-14 前已发生的共享改动在 `TASKS X7` 补登记（影响面 + 83/97 结果 + A 核准）。
7. 未按协议改共享脚本：主会话在下次闸门中列为「未验证变更」，不签发布复核。

## 4. golden repro（每线钉死路径；执行主体=各线自跑）

> 执行方式：**各线自己跑并交「命令 + 产物哈希 + 日志」；主会话只做哈希比对与日志核对，不亲自构建。**

| 线 | 产物 | 路径（钉死） | 期望哈希 | 状态 |
|---|---|---|---|---|
| A | Regular | `11_build_full` → `13_extend_punct --line A --inplace`（从 `work/` 输入） | `e6d8a104…` | 主会话已实测 |
| A | Real | `07_build_real` **重新描摹**（`work/masks` 路径） | `bf278ab1…` | 主会话已实测；`--reuse-contours`=`5733ca42…`，**非发布路径** |
| B | Regular | `62_build_full_b --drop-outside-basic` → `13_extend_punct --line B --inplace` | `aa19d6d2…` | B 声明；单跑 62 恒为 `446cc896…`（不含标点），必须两步 |
| B | Real | `57_build_real_b --reuse-contours --drop-outside-basic` | `7d10e460…` | B 声明；retrace=`f82ea61a…` 非发布 |
| C | Regular | `79_build_full_c`（默认内部含 42 标点） | `765d0848…` | C 声明路径 |
| C | Real | `76_build_real_c --close 3 --hole-repair` | `6caf9d82…` | C 声明路径 |

**A 的发布路径事实**：A 发布 Real 走 retrace；cache 路径哈希不同是**已解释的路径差异**，不是字体缺陷。
待办只是把 `AGENTS.md` 步骤 1 的 `--reuse-contours` 措辞与发布清单对齐（`A4`）。

## 5. 状态快照协议

任何审计、闸门、发布复核结论必须同时记录：

- `git rev-parse HEAD`
- `git status --porcelain`
- 未提交修改清单 + 文件哈希
- 相关制品 SHA-256
- 采样时间

工作区是「活」的：v0 台账因所有者 2026-11-14 09:16 提交 `27eab26` 而立刻过期（A/B 均指出）。
冻结台账采用**版本化文件**（`frozen-hashes-<date>T<time>.json`）+ `audit/facts/CHANGELOG.md` 记录
「谁、何时、改了什么」；旧版本不删除、只标 superseded。没有快照的结论不进入发布签核。

## 6. 发布门禁（主会话只读复核）

每次发布前按线执行，全部通过才提交所有者：

1. 快照（HEAD / git status / 制品哈希）；
2. golden repro（§4）——**线自跑交哈希+日志**，主会话比对；
3. 发布 manifest 与制品一致（A `release-a.json` / B `release-b.json` / C `release-c.json`）；
4. `provenance` ↔ `chosen`/`generated` 逐字对账；
5. 该线 QA（A `13_qa` / B `63_qa_b` / C `80_qa_c`）+ 孔洞审计固定 seed/n；该线 **self-audit**
   （B `73`；如新增 A/C 版本）由该线自跑交输出；
6. 跨线 `83` / `97` / `95 --check`：由**线自跑交输出**，或主会话用 `/tmp` 临时镜像做只读等价复算；
   **主会话不直接在仓库跑 83/67/73**；
7. 外部冻结台账比对（§7），83/67 的自更新基线不作漂移证据；
8. 文档数字可由 manifest/落盘文件导出；发布说明由该线负责人签核，主会话复核不代签。

zip：只作为**发布快照记录**。字体字节可复现；zip 在现有工具链下不承诺字节可复现
（除非改确定性打包，需所有者决定 O4）。

## 7. 外部冻结台账

- 当前版本：`audit/facts/frozen-hashes-2026-11-14T0940.json`（HEAD `27eab26`，工作区干净）。
- 旧版 `frozen-hashes-2026-11-14.json` 为过期快照（记录于 CHANGELOG，不删除）。
- 主会话每次闸门对比当前版本，只读、不写回发布目录。
- 不可用 `83_verify_ab_c.py`（回写 `work-c/ab_baseline.json`）或 `67_verify_a.py`
  （写 `work-b/verify_a_snapshot.json`）做漂移监测；`67 → work-b` 属已知跨线写入，B 同意保留为现状
  （如需改路径，由 A 按 §3 处理，不阻塞当前流程）。

## 8. 任务与汇报

- 任务板：`audit/TASKS.md`。主会话维护；三线执行并回报；所有者裁定优先级。
- 每个任务必须带验收标准；完成后主会话复核，把证据行写进台账。
- 冲突：主会话给证据与建议，所有者拍板；不投票、不默认多数。
- 节奏：每次闸门/发布后向所有者报一次；无任务不后台改项目。

## 9. 不重构声明

现存目录、文件命名、文档归属、README = 项目 README（A 线）的事实保持不变。
主会话不发起结构迁移；如所有者要求才另议。
