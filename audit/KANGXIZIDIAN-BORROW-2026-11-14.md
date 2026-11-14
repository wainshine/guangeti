# 《康熙字典》项目（kangxizidian）可借鉴点（2026-11-14）

> 只读调研。对象：`/Users/wainshine/newAI/kangxizidian`，当前 v2.6.3。
> 结论：**借方法/流程/闸，不借字形数据**。康熙楷是刻本字头真迹（17,006 字、无生成字），
> 与 A 写本、B 史记、C 永乐大典风格/来源不同；数据不可混入三线。

## 1. 最高价值（P0，直接补我们质量计划）

| # | 可借鉴内容 | 来源 | 用在哪 |
|---|---|---|---|
| 1 | **人工复核包格式**：每格“成品字形 + 独立 OFL 参照字形 + 原书裁片”，100 字/页，编号→字/页/框 ledger；固定种子随机 100 字回归 | `scripts/review_sheet.py`、`scripts/make_round_pack.py`、`docs/WORKFLOW.md §6` | A-Q2/B-Q4/C-Q1 盲审；解决“只给成品图、判读者不知道原字”的问题 |
| 2 | **不拿参照字体数孔洞/连通分量**：刻本/写本的断笔、开口是工艺/风格；孔洞、连通分量、碎片不得当质量判据 | `DECISIONS.md D21`、`font_qa.py` 头注 | 修正我们的 `71_holes` 口径；A/B/C 孔洞只做“源 mask 对照”两栏，不做文楷拓扑比对 |
| 3 | **源墨保真/内容缺失闸**：`ink_ratio`、配准 IoU、新增/删除字单列；基线=上一正式版；输入绑定 sidecar | `scripts/content_loss_gate.py`、`RELEASE-METRICS.md` | 替代“孔洞率”作为回归闸；A/B/C 版本对比与 83 扩展 |
| 4 | **缺件扫描**：源块中未被成品字形覆盖的部件（面积≥1%、最短边≥8px、覆盖率<0.45） | `scripts/scan_missing_parts.py` | B/C 缺笔/漏部件；A 回退字与真迹抽检 |
| 5 | **框线逃逸闸**：切前排除后，块内仍有贯穿长直线=FAIL；不做“切后擦线” | `scripts/scan_frame_escape.py`、`scripts/glyph_frame_gate.py`、`D20/D22` | A/B/C 扫描件版框/界行/邻字残线；B/C 尤其需要 |
| 6 | **标签证据链 + 精度披露**：自动证据通道、留产物、可复算；精度如实披露（康熙的 D16 明确“不宣称映射已验收”） | `DECISIONS.md D16`、`WORKFLOW.md §3` | B/C 标签审计与发布措辞；A 的对照回对也可照此披露 |

## 2. 流程/治理可借鉴（P1）

| # | 内容 | 来源 | 适配 |
|---|---|---|---|
| 7 | **候选/正式分层**：`F` 构建 → `C` 候选（字体+闸+复核包）→ owner 通过 → `R` 发布；`release/` 只放正式包 | `docs/WORKFLOW.md §1` | A/B/C 现在“改完即发”风险高；可借用候选制，减少“发完即失效” |
| 8 | **变更集（Change Set）**：一轮只解决一类问题，写 scope/root_cause/fix/verification；发现新问题进 backlog 不混修 | `WORKFLOW.md §2`、`§10bis` | A/B/C 下一版按“标签/几何/生成/材料”拆变更集，禁止混修 |
| 9 | **闸输入绑定 sidecar**：font/manifest/mapping/geometry/参考字体/脚本 sha + argv + git；复用前校验，失败 fail-closed | `scripts/gate_binding.py`、`WORKFLOW.md §5` | 我们的 83/71/31/验收报告目前没有绑定输入；旧结果可能静默复用 |
| 10 | **clean tree + finalize 原子写**：打包前强制 clean git tree；未全 PASS 不改包；FINALIZE/SHA 原子替换 | `scripts/release_gate.py`、`WORKFLOW.md §5` | `14_package` 已有部分；可补 clean-tree 闸与 finalize 记录 |
| 11 | **按版本指标表**：字形数/覆盖/内容 damaged/缺件/框线逃逸/页几何/变化字；每版同口径可复算 | `docs/reference/RELEASE-METRICS.md` | A/B/C 质量卡与版本对比；变化字用精确轮廓 diff，不用阈值筛集 |
| 12 | **provenance 无拷贝闸**：manifest/mapping/stats 三者自洽；禁止 overlay/repair_overlay 等拷贝通道 | `scripts/provenance_gate.py`、`D4` | A/B/C 的 provenance 已有，但可补“无旧字形拷贝”检查；B/C 的 `real` 尤其需要 |
| 13 | **留出口径按字优先、按页降级并披露泄漏** | `DECISIONS.md D5` | C-Q2 split manifest 可直接采用；A/B 的 val 也按字优先 |

## 3. 有选择借鉴（P2）

- **D15 headword-only / 不承诺假覆盖**：只收字头真迹，缺口交 GAN，不拿小字顶替；对应我们 Real-only vs Full-coverage 两级披露。
- **D19 缺口分桶 + 重定位优先于 GAN**：缺口先分桶、先找真迹候选，再交 GAN；适用于 B/C 的缺口与 C 的标签审计，不适用于 A（已无更多字源）。
- **D20 破坏性清理开关默认禁用**：删组件/去框线类开关默认关，启用需双回归；适用于我们的 `10/07/05` 类脚本。
- **D17 发布材料数字自动生成、随包披露、冻结后不改**：我们的 release/ 已有，但可补“数字由脚本产出”的硬检查。
- **页面几何/pre-cut**：`09`/`font_qa` 类思路可用于 A/B/C 的切格质量；但三线数据版式不同，需单独适配，不作为首批。

## 4. 不建议借的

1. **不把康熙楷 17,006 个字头并入 A/B/C**：刻本 vs 写本/史记/永乐大典，风格与历史来源不同；混入会污染 `real` 语义与发布 provenance。OFL 许可允许，但风格不匹配。
2. **不照搬完整 `release_gate.py`**：1008 行、依赖康熙的 mapping/geometry/scan；我们只需借“绑定 + 分闸 + clean tree + finalize”思想，按三线裁剪。
3. **不把 D21 当绝对教条**：D21 针对刻本；A 是写本，孔洞仍可能是有意义的真损失，但**判据必须对照 source mask，不用文楷拓扑**——这与我们的两栏计划一致。
4. **不直接复制其代码到 guangeti**：其 LICENSE 是 MIT（可借鉴），但路径/依赖/数据约定不同；移植需保留版权声明并适配，先小样本验证。

## 5. 建议落进下一版质量计划的三个动作

1. **Q1 立刻借用复核包格式**：A-Q2/B-Q4/C-Q1 统一改成“成品 + OFL 参照 + 原书裁片 + ledger”，先做 100 字小样本；可直接移植 `review_sheet.py`/`make_round_pack.py` 的版式思想（MIT，需署名）。
2. **用“源墨保真/缺件/框线逃逸”替换孔洞主指标**：`71_holes` 保留作诊断，但不再当“质量门”；`71` 的 seed/cmd 已有，补 source mask 对照。
3. **给 83/验收加输入绑定**：至少给 `83` 的 baseline、`71` 的 font、`73` 的 manifest 加 sha sidecar；避免换字体/换基线后静默复用旧结果。

## 6. 参考文件

- `docs/DECISIONS.md`（D5/D15/D16/D19/D20/D21/D22）
- `docs/WORKFLOW.md`（§1/§2/§5/§6/§10bis）
- `docs/reference/RELEASE-METRICS.md`
- `scripts/review_sheet.py`、`scripts/make_round_pack.py`
- `scripts/content_loss_gate.py`、`scripts/scan_missing_parts.py`、`scripts/scan_frame_escape.py`
- `scripts/gate_binding.py`、`scripts/provenance_gate.py`、`scripts/release_gate.py`
- `scripts/font_qa.py`（D21 口径）
