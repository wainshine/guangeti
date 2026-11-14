# 主会话运行规则（2026-11-14 接管）

> 本文件是协调层规则，放在 `audit/`，不进 `docs/`，不改变项目现有结构。
> 生效前提：所有者 2026-11-14 明确「你来接管」，三线（A/B/C）会话与既有文档归属保持不变。

## 1. 主会话定位与边界

主会话不是第 4 个写者。职责只有四类：

1. 协调三线任务、维护任务板与事实台账；
2. 只读运行发布闸门与跨线回归；
3. 发布编排与签核前复核（**复核不代签**）；
4. 审计跟进、冲突裁决建议、向所有者上报。

不做的：

- 不写项目代码、共享文档、`work*/`、`build/`、`release*/`、`data/`；
- 不做 git 写操作（仓库由所有者管理）；
- **不重构**：不移动/重命名现有文件与目录，不新建 docs 层级（协调产物一律放 `audit/`）；
- 不替三线写发布说明，不单方面宣布跨线技术规则。

## 2. 写作用域矩阵（现状事实 + 本次约定）

| 角色 | 可写 | 不可写 |
|---|---|---|
| 所有者 | 全部；git；发布签核；角色与规则裁决 | — |
| A 会话 | A 线产物（`work/`、`build/GuanGeKai-*.ttf`、`release/`、`data/release-a.json`、A 的 `RELEASE/README`）+ **共享 docs**（`AGENTS.md`、`PROJECT_STATE`、`DATA`、`EXPERIMENTS`、`GLOSSARY`、`CONVENTIONS`、`method`、`README`、`PLAN`）+ **共享脚本**（01–16/21–42、`punct_set`、共享库） | B/C 的 `work*/build/release*/doc/data`；不重构 |
| B 会话 | `work-b/`、`build/GuanGeKai-B-*`、`release-b/`、`scripts/*_b.py`、`*-B.md`、`data/release-b.json` | A/C 的同上 |
| C 会话 | `work-c/`、`work-c-big/`、`build/GuanGeKai-C-*`、`release-c/`、`scripts/*_c.py`、`*-C.md`、`data/release-c.json` | A/B 的同上 |
| 主会话 | `audit/**`（findings / facts / TASKS / OPERATING）、自己创建的 `docs/AUDIT-*` | 其余全部；只读验证 |

**A 的共享职责（所有者 2026-11-14 确认）**：项目 README 与共享文档框架事实上是 A 的 README
（最早实现 A，再 B、C，沿用框架；没有另设主会话，共享东西由 A 维护）。
因此 **A 继续维护共享 docs 与共享脚本**；主会话不接管这些写权限。

## 3. 共享资产变更协议

适用对象：`punct_set`、`05/06/08/10/13/14/83/97`、其他被两条以上线引用的脚本或文档口径。

1. **变更前**：在 `audit/TASKS.md` 登记（或经所有者转达），一句话说明影响面（哪几条线、哪类产物）。
2. **变更后**：跑三线回归——成品哈希 + 中间产物哈希；跑 `83`、`97`；涉及发布口径的跑对应 QA。
3. **A（共享技术 owner）核准**语义变化；主会话只记录证据，不代改。
4. 未按协议改共享脚本：主会话在下次闸门中列为「未验证变更」，不签发布复核。

## 4. golden repro（每线钉死路径，不许二义）

| 线 | 产物 | 路径 | 期望哈希 | 状态 |
|---|---|---|---|---|
| A | Regular | `11_build_full` → `13_extend_punct`（从 `work/` 输入） | `e6d8a104…` | 主会话已实测 |
| A | Real | `07_build_real` **重新描摹**（`work/masks`） | `bf278ab1…` | 主会话已实测；`--reuse-contours`=`5733ca42…`，**非发布路径** |
| B | Regular | `62_build_full_b`（从 `work-b/` 输入） | `aa19d6d2…` | B 声明，待金样一次 |
| B | Real | `57_build_real_b --reuse-contours`（缓存） | `7d10e460…` | B 声明；retrace=`f82ea61a…` |
| C | Regular | `79_build_full_c`（从 `work-c/` 输入） | `765d0848…` | **待 C 提供路径** |
| C | Real | `76_build_real_c`（缓存或描摹，待确认） | `6caf9d82…` | **待 C 提供路径** |

## 5. 状态快照协议

任何审计、闸门、发布复核结论必须同时记录：

- `git rev-parse HEAD`
- `git status --porcelain`
- 未提交修改清单 + 文件哈希
- 相关制品 SHA-256
- 采样时间

工作区是「活」的（会出现「审计后有人改了」）。**没有快照的结论不进入发布签核。**
快照样例见 `audit/facts/`。

## 6. 发布门禁（主会话只读执行）

每次发布前按线执行，全部通过才提交所有者：

1. golden repro（§4）哈希一致；
2. 发布 manifest 与制品一致（A `data/release-a.json` / B `release-b.json` / C `release-c.json`）；
3. `provenance` ↔ `chosen`/`generated` 逐字对账；
4. 该线 QA（A `13_qa` / B `63_qa_b` / C `80_qa_c`）+ 孔洞审计固定 seed/n；
5. 跨线 `83`（完整性）+ `97`；`95 --check`（若该线更新三线图）；
6. 外部冻结台账比对（§7）；**83/67 的自更新基线不作漂移证据**；
7. 文档数字可由 manifest/落盘文件导出；发布说明由该线负责人签核，主会话复核不代签。

zip：只作为**发布快照记录**。字体字节可复现；zip 在现有工具链下不承诺字节可复现
（除非改为确定性打包，需所有者决定）。

## 7. 外部冻结台账

- `audit/facts/frozen-hashes-*.json` 记录六款 TTF、三个 zip、共享脚本哈希、HEAD 与工作区状态。
- 主会话每次闸门对比该台账，只读、不写回发布目录。
- 不可用 `83_verify_ab_c.py`（会回写 `work-c/ab_baseline.json`）或 `67_verify_a.py`
  （会写 `work-b/verify_a_snapshot.json`）做漂移监测。

## 8. 任务与汇报

- 任务板：`audit/TASKS.md`。主会话维护；三线执行并回报；所有者裁定优先级。
- 每个任务必须带验收标准；完成后主会话复核，把证据行写进台账。
- 冲突：主会话给证据与建议，所有者拍板；不投票、不默认多数。
- 节奏：每次闸门/发布后向所有者报一次；无任务不后台改项目。

## 9. 不重构声明

现存目录、文件命名、文档归属、README = 项目 README（A 线）的事实保持不变。
主会话不发起结构迁移；如所有者要求才另议。
