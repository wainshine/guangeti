# 《康熙字典》项目可借鉴点 v2（2026-11-14，三线反馈后）

> 只读调研 + 三线对抗复核。对象：`/Users/wainshine/newAI/kangxizidian`，v2.6.3。
> **结论不变：借测量/闸门/流程，不借字形数据。**
> 三线一致修正：**D21 是刻本结论，A/B/C 都是写本/抄本**，不能把“不数孔洞”绝对化；
> 但“不拿文楷拓扑判孔洞”适用于三线，孔洞只做 source-mask 两栏诊断。
> 康熙当前字头数引用写“≈17,006”（其 README/RELEASE-METRICS 与 ARCHITECTURE/BACKLOG 有 17,006/17,005 不一致）。

## 1. 已落地，不用再“借”

- **复核包已三线接入**：`scripts/review_sheet.py`（共享库）+ `45_review_a.py` + `79_singleton_sheet_b.py` + `99qa_review_sheet_c.py`；
  A 第一张表已抓出 `攖/望` 错标。**不要再写“Q1 借用/移植版式”**。
- 遗留两件小事：
  1. `_draw_fit` 与康熙版高度同构，**建议加 MIT 署名**（B 已指出；若确为独立实现，也补一句“版式思想来源”即可）；
  2. 三线都缺**固定 100 字回归表**：当前是分层抽样/确定性前 100，不是固定字表。固定表才能做逐字版本 diff。

## 2. 最高价值（P0，修正后）

| # | 内容 | 正确表述 | 用在哪 |
|---|---|---|---|
| 1 | **版本对版本内容闸** | `content_loss_gate.py` 比较 **old.ttf vs new.ttf**（ink_ratio + 配准 IoU；新增/删除单列；字符宇宙=两侧 cmap 交集；sidecar 绑定）。**不是“vs 源墨”** | A v1.7.2→v1.7.3 期望 0 changed；B/C 版本回归；先证明“重建没漂移” |
| 2 | **精确 glyf 轮廓 diff** | 康熙自己踩过“阈值筛集 617 changed、精确轮廓 3,351”的坑，v2.6.3 起只用精确 diff | A/B/C 版本变化字；质量卡 per-version |
| 3 | **固定 100 字回归表** | 康熙是固定种子随机 100；三线应入库固定 `chars_100.txt`（real/GAN/ribbon 分层），每版同表重出 | A-Q1/B-Q1/C-Q7；否则每版样本不同，回归结论不成立 |
| 4 | **输入绑定 sidecar** | `<out>.sha256` JSON：inputs/script/argv/git；复用前校验，fail-closed。**我们已有部分**（71 font/n/seed/cmd、31 sha/epoch、83 baseline path），缺的是单一 digest + 校验 | 71/83/73/accept/quality card；防换字体后静默复用旧结果 |
| 5 | **源 mask 两栏孔洞** | 不拿文楷拓扑当判据；`源 mask 有孔、成品没有=候选真损失` vs `源 mask 同样开口=风格`。**只对 real 层**；合成层没有源块 | A 1,675 / B 4,073 / C 5,257；不删 holes，但降为诊断 |
| 6 | **缺件扫描** | 源块中未被成品覆盖的部件（面积≥1%、最短边≥8px、覆盖率<0.45）；只对 real 层 | B 473,847 masks 条件最好；C real+holdout；A real |
| 7 | **版本/发布指标表** | 字形数、覆盖、内容 damaged、缺件、框线逃逸、精确变化字，每版同口径 | 三线质量卡 |
| 8 | **标签证据链 + 精度披露** | 自动证据通道、可复算、留产物；不宣称“映射已验收” | B/C 标签审计；A 对照回对 |

## 3. 按线裁剪（三线反馈后的结论）

### A
- **借**：版本对版本内容闸、精确轮廓 diff、固定 100 字表、71 两栏（real）、83/71 sidecar。
- **不借/不优先**：框线逃逸（A 页面无边栏/界行，已抽查）；provenance 拷贝闸（A 无 overlay 通道）；
  F/C/R 三层与 `release_gate.py` 框架（A 打包 2 分钟，流程成本大于收益）。
- 只需保留一条硬规则：**候选不进 `release/`，`release/` 只放最终包**。

### B
- **借**：输入绑定（`accept_b.json`/`quality_card_b.json` 只记路径，是真漏洞）、缺件扫描（real vs mask）、
  版本内容闸、固定 100 字表；review sheet 补 MIT 署名。
- **修正**：`63_qa_b` 的孔洞门槛现在对**文楷**，应改真迹对 **源 mask**；合成层对文楷只能标“结构代理”。
- **不优先**：框线闸（B 用正确“薄+长”判据实测 0/300；此前 39/200 是判据错）；D19 重定位（B 的 ribbon 不是“没找到字头”，是守卫未过）。

### C
- **借**：review pack ledger + 固定 seed、版本内容闸、输入绑定、候选/正式分层、clean tree（限定 tracked）。
- **修正**：
  - D21 不能推成“删掉 holes”；C 保留 holes 诊断，改 source-mask 两栏（C-Q8）；
  - D19 字典字头逻辑**不适用 C**（C 是正文全文字体，没有正典字头/重定位）；
  - 缺件/框线/源墨闸只覆盖 **real + holdout**；14,422 GAN/ribbon 用 review pack + 分层盲审（C-Q3/C-Q9）；
  - 不要移植康熙版式；继续用共享 `review_sheet.py`，加 `--seed`/固定 100 字（C-Q7）。
- **可借**：C 的 `release-c/` 冻结规则；v1.4 先出候选，owner 通过再进正式包。

## 4. 流程项（P1，按线裁剪）

| 项 | 借法 | 不借法 |
|---|---|---|
| 输入绑定 | sidecar/单一 digest + fail-closed；退出码契约（0 PASS/2 不可复用/3 超阈值/1 fail-closed） | 不要从零重写已有 71/31/83 的字段 |
| clean tree | **只看 tracked 路径**（`git status --porcelain --untracked-files=no`） | 全工作区干净（B/C 大量未跟踪产物，会永久红） |
| 候选/正式 | C 用 `work-c/qa/candidate/`；A/B 只需“候选不进 release” | 全盘搬 F/C/R 三层 |
| 变更集 | 一轮一类问题，写 scope/root_cause/fix/verification | 不混修 |
| provenance 无拷贝 | B/C 需要防 overlay/旧字形；A 价值低 | 不强制三线都上 |
| 留出 | 按字优先、按页降级并披露 | 不把页留出说成字留出 |

## 5. 不借/已驳回

- **不并入康熙 17,006 字头**：刻本 vs 写本/抄本，风格与来源不同；OFL 允许也不行。
- **D21 绝对化**：三线不是刻本；孔洞保留诊断，只用 source mask，不用文楷拓扑。
- **D19 字典字头分桶/重定位**：不适用于 A/B/C 的连续文本。
- **D23 源墨保真**：截至调研仍是“提案·未定稿”（content 闸仍按 18/35 旧口径）；不要当现成闸。
  可作为 B 的试点（B 有 473,847 masks），但先小样本验证，不进正式质量门。
- **完整 `release_gate.py`**：1008 行，依赖康熙 mapping/geometry；只借“绑定+分闸+clean tree+finalize”思想。
- **直接复制代码**：MIT 可借，需署名；优先借设计。

## 6. 给三线的落地优先级

| 顺序 | 动作 | 线 | 成本 |
|---|---|---|---|
| 1 | 固定 100 字表 + review sheet changes/random 两表 | A/B/C | 半天 |
| 2 | 版本对版本内容闸 + 精确轮廓 diff | A/B/C | 1 天 |
| 3 | 71/63 孔洞改 source-mask 两栏（只 real） | A/B/C | 半天 |
| 4 | 缺件扫描（real vs mask） | B/C 优先 | 1 天 |
| 5 | 输入 digest/sidecar + 退出码契约 | A/B/C | 半天 |
| 6 | review_sheet MIT 署名 | 共享 | 5 分钟 |
| — | 框线闸、provenance 拷贝闸、F/C/R 框架 | 仅 C / B/C 按需 | — |
