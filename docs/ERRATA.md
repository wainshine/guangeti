# 勘误（三线共用）

> 记录**已发布制品与历史文档中不再更正的错误**，避免每个接手的人都重新考古一次。
> 规范见 `docs/GLOSSARY.md`；迁移计划见 `docs/CONVENTIONS.md`。

## E1.《四书白文》是写本，不是刻本（2026-10-28）

**结论**：《四书白文》十八卷是**明代精写本**（手书墨迹），不是刻本。旧文档里 60 余处「刻本」均为错误。

**一手证据**（本地 PDF 第 11 页，600 dpi，见 `docs/images/manuscript-evidence.jpg`）：

1. **版心空白**：中缝无书名、卷次、叶码、刻工、牌记——刻本正常都会刻这些；
2. 笔画有墨色浓淡、末端锋芒、牵丝飞白；同一页字径不匀、基线起伏；
3. 朱色句读与墨字分属不同颜色层、位置不贴合字形（后加圈点）。

旁证：书格将该书归入「稿钞本」，著录为「明代精写本」，原站文件名含「明钞本」。

**影响范围**：

| 位置 | 状态 |
|---|---|
| 仓库文档 | 由 `docs/GLOSSARY.md` §4 规范，`scripts/97_check_terms.py` 检查 |
| 历史发布说明（`docs/RELEASE-*`） | **保留原文**，不逐一更正 |
| 历史审计（`docs/AUDIT-*`） | **保留原文** |
| 研究记录（`docs/EXPERIMENTS.md`、`method.md`） | 只改结论句里承重的表述，其余保留 |
| 已发布字体元数据 | 见 E2 |

**指标不受影响**：Dice、墨量、chamfer、孔洞、端帽都是对图像测的，与「刻/写」无关，**无需重算**。

## E2. 已发布字体的 name 表曾写 woodblock（**v1.7.0 已修复**）

`build/GuanGeKai-Regular.ttf` 的 name ID 0 为
`Real glyphs extracted from the Ming woodblock print 四書白文...`。

- 源字符串已在 `scripts/11_build_full.py:51` 改为 manuscript，**v1.7.0 重建后已生效**（`6dfd79d6…`）；
- v1.6.5 二进制**不重建**（重建会改 TTF 哈希、连带 `release/SHA256SUMS` 与 `83_verify_ab_c.py` 的基线）；
- `97_check_terms.py` 对 `build/*.ttf` 加白名单，输出里单列「已知遗留」。

## E3. 包内 README 停留在发布时措辞

三个发布包的 `README.md` 仍是「刻本」措辞（它们是发布时的快照）：

```
release/README.md     v1.6.5
release-b/README.md   v1.2.1
release-c/README.md   v1.0.1（2026-10-28 联合发版时已重打包，本条不再适用）
```

**决定**：A/B 不重新发版，包内为历史快照；**C 线例外**——v1.0.1 在 2026-10-28 三线联合发版时重打包
（字体未变，README 已按当前 `README-C.md` 更新），C 的 drift 解除。`docs/DATA.md`、`DATA-B.md`
记 drift；`83_verify_ab_c.py` 的 A/B zip 哈希视为发布快照，不随文档变动。

## E4. `release*/specimen.png` 与 `book-vs-font*.png` 带旧措辞

这些图里印着「明代《四書白文》刻本」，且都在 `release*/SHA256SUMS` 内。

- 仓库里的 `docs/images/specimen.png` 可重出（生成器 `scripts/12_specimen.py` 已改）；
- 包内旧图**不动**，与 E3 同性质（C 线的 `specimen-c.png` / `book-vs-font-c.jpg` 图注本就写「重寫本」，不在本条）；
- 若要整包更新，需一次正式发版（改哈希、改 `83`、改 DATA），不在本轮范围。

## E5. A 线红像素比例（旧数字更正过一次，这次改成分布）

旧 `AGENTS.md` 写「每页红像素 0.08–0.16%」。全库 410 页实测（100 dpi，`pageproc.red_mask`）：

```
p5 0.086% | 中位 0.265% | p95 19.97% | 最大 97.99%
<0.18% 的页 123 张；>0.27% 的页 201 张；>5% 的页 22 张（红封面/红印/暖色纸）
正文页抽样 8 页：0.098–0.271%
```

**不要当常数用**：多数正文页在 0.1–0.4%，但有整页发红的例外。
结论不变——`red_mask()` 一直在跑，四书这份红色标记少、收益接近 0。

## E6. 《永乐大典》C 线真迹集含碎片格（已记录，未修）

`work-c/chosen.jsonl` 中约 0.1% 的样本 `ink<0.05`（碎片），例：`覽` 的 chosen 样本
`p14_0061_c00_l10_s012.png` 是页边碎片（`ink 0.025`，`agree_ab=True` 但内容是碎片）。
成因：页边切格产生碎片 → 标签按行序列分配 → 双见证只验行文本。修复方案见
`docs/CONVENTIONS.md` 之外的 C 线专项（结构闸 + 格级对账），由 C 线会话执行。
