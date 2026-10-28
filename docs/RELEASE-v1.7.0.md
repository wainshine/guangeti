# GuanGe Kai v1.7.0（A 四书）

> **字形没有任何变化。** 本版是一次**身份更正**：把《四书白文》从「刻本」改正为「写本」，
> 并把这个更正写进字体元数据、全库文档和发版闸门。

## 本版变更

| # | 项 | 内容 |
|---|---|---|
| 1 | **字体 name 表更正** | ID 0 由 `Real glyphs extracted from the Ming woodblock print 四書白文` 改为 `...Ming manuscript...`。这是本版唯一改动二进制的原因 |
| 2 | **术语体系** | 全库 60 余处「刻本 → 写本」「刻刀笔锋 → 墨笔笔锋」「刀刻刻本 → 墨笔写本」；三条线定位由「载体」改为「书写者与场合」 |
| 3 | **新增规范** | `docs/GLOSSARY.md`（唯一术语规范）、`docs/ERRATA.md`（历史勘误，不逐条改历史发布说明） |
| 4 | **新增发版闸** | `scripts/97_check_terms.py`：扫文档 / 代码注释 / 字体 name 表，未过即 `exit 1` |
| 5 | **技术路线改名** | 旧的「路线 A/B/C」统一为方法名 `ribbon` / `zi2zi-GAN` / `zi2zi-JiT`（`R0–R7` 保留给闸门判据），避免与字形线 A/B/C 混淆 |

## 为什么是 minor 而不是 patch

字体二进制变了（name 表），且新增了全库级的命名规范与发版闸。使用者看到的元数据（字体信息面板里的
"版权/描述"）会从 `woodblock print` 变成 `manuscript`，这属于可感知的变化。

## 证据

《四书白文》是**明代精写本**（手书墨迹）。一手证据取本地 PDF 第 11 页 600 dpi 局部，
见 `docs/images/manuscript-evidence.jpg`：

1. **决定性**：版心空白——中缝无书名、卷次、叶码、刻工、牌记，而刻本正常都会刻这些；
2. 强旁证：笔画有墨色浓淡、末端锋芒、牵丝飞白；同一页字径不匀、基线起伏；
3. 旁证：书格将该书归入「稿钞本」，著录为「明代精写本」。

## 指标（与 v1.6.5 相同）

| 项 | 值 |
|---|---|
| 覆盖 | 20,992 / 20,992 |
| 真迹 / GAN / 回退 | 1,675 / 18,518（ep90 17,790 + ep80 728） / 799（4.1%） |
| 干净集 | Dice 0.549、chamfer 5.85 |
| 孔洞 | `holes lost` 0.5%（300 字抽样，基线 1.9%） |

## 已知限制（延续）

1. 孔洞缺陷：`四/国/目/自/年` 等字仍实心；高 dpi 只能恢复 22% 的缺孔字（E38），无工程解法。
2. 合成字比真迹重约 17%（E34/E37 已拆解成因）。
3. 补位字（ep80）与主模型字有 3.8% 墨量差（E40）。
4. 未做 hinting。

## 檔案

`GuanGeKai-Regular.ttf`、`GuanGeKai-Real.ttf`、`provenance.json`（四态）、`stats.json`、
`SHA256SUMS`、`OFL.txt`、`LICENSE`、`coverage.txt`、`specimen.png`、`book-vs-font.png`

校验和见 `docs/DATA.md`。B 线（史记 v1.2.2）与 C 线（永乐大典 v1.0.1）同日发布，
入口见 `README-B.md`、`README-C.md`。
