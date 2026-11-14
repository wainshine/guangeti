# 文档一致性审计报告（docs-consistency）

> 审计员：docs-audit（独立审计，只读）
> 基线：`HEAD e308ad55a0c10ee754f8047ebb3c098c96bda582`（2026-11-13 11:40:37 +0800，工作树干净）
> 审计时点：2026-11-14
> 唯一写入文件：本文件（`audit/findings/docs-consistency.md`）。未修改 docs/、README、scripts/ 等任何文件，未执行 git 写操作。
> 所有 `file:line` 均以 HEAD 为准；数字证据优先取单一数据源（`data/release-*.json`、`release*/stats.json`、`work/*.json`、`build/*.ttf` 实测）。

## 0. 结论摘要

| 等级 | 数量 | 含义 |
|---|---|---|
| **P0** | **3** | 与当前发布事实直接矛盾，会让接手者/审计者按错误前提做判断或复现 |
| **P1** | **18** | 陈旧或自相矛盾的关键数字/版本/路径/引用，发版或复验前必须处理 |
| **P2** | **16** | 口径未注明、编号/格式、历史档案与检查器覆盖面问题 |
| 已披露/已接受 | 9 类 | ERRATA/CONVENTIONS 已登记，不重复当新发现（个别「已登记但正文未修」已另报） |
| 已核查不成立 | 12 项 | 疑似问题经实测/脚本复核后排除 |
| 未覆盖 | 7 项 | 见 §6 |

**最严重的三条**：

1. `docs/PROJECT_STATE.md:139` 仍写「**当前发布版用 E**（v1.3.3）」，与同文件 §17、AGENTS、`data/release-a.json` 的 GAN 发布口径（v1.7.2，GAN 18,518）直接矛盾（P0-1）。
2. 四个文件仍写「源 PDF 已被去色、无红色像素」，与 ERRATA E5/AGENTS/PROMPT-YONGLE 的实测结论（源 PDF 是彩色的，`r−g` 最大约 103）相反；其中一处还在**已发布的 `release/README.md`（zip 内）里**（P0-2）。
3. `docs/PROJECT_STATE.md:211-212` 的「如何独立审计」仍按 v1.5.0 口径写「90.5% GAN / 9.5% 回退」，并让人用 `work/ckpt/m2_ep080.pt` 复验 0.549，而当前发布口径是 95.9%/4.1%、主模型 `m2wt_ep090`、617 全量 Dice **0.539**（P0-3）。

另有一个跨线关键点：**v1.7.1 实际发布的 cmap 是 21,036（44 个标点/数字/空格 × 含 U+201C/U+201D），不是其发布说明写的 21,034**（解 zip 实测，见 P1-15）。ERRATA 未登记这段过渡口径。

---

## 1. P0（3 条）

### P0-1 PROJECT_STATE §6 仍称「当前发布版用 E（v1.3.3）」，且用「路线 A–F」旧命名

- **位置**：`docs/PROJECT_STATE.md:139`（另见 `:128` 节标题「三条路线均已实测」、`:130` 表头「路线」、`:132-137` 行标 A.–F.）
- **问题**：`:139` 写「**当前发布版用 E**（v1.3.3）。D 是 v1.1–v1.2 的旧方案；C 有幻觉与许可两个未决问题」。同一表 `:137` 的 F 行却写「GAN（5 层 PatchGAN + hinge + 增强，**v1.5.0 采用**）」——同节自相矛盾；且「三条路线」标题下挂了 6 行。
- **对照证据**：
  - `data/release-a.json:5` `"method": "gan"`、`:6` `"primary_ckpt": "work/ckpt/m2wt_ep090.pt"`、`:15-17` counts（real 1675 / gan_ep90 17790 / gan_ep80 728 / ribbon_fb 799）；
  - `AGENTS.md:43-47`「当前状态（A v1.7.2 / B v1.2.4 / C v1.3.0）… 发布版 = 真迹 1,675 + GAN 18,518 + 回退 799」；
  - `docs/PROJECT_STATE.md:358-374`（§17 v1.5.0 变更）已写「合成器从带状扫掠换成 GAN」；
  - `build/GuanGeKai-Regular.ttf` 实测 name ID5 = `Version 1.7.2`、name ID0 含 `Ming manuscript`；
  - 术语规范 `docs/GLOSSARY.md:22-33`：技术路线只写 `ribbon`/`zi2zi-GAN`/`zi2zi-JiT`，`A/B/C` 只指字形线。
- **影响**：接手者按 §6 会认为当前仍用 ribbon、把 GAN 当历史实验；A–F 字母还会与字形线 A/B/C 混淆。这是交接文档中信息量最大的「技术路线」一节。
- **建议改法**：§6 改写为「方法演进史（按方法名）」，明示当前发布 = `zi2zi-GAN` 混合检查点（m2wt_ep090 主 + m2_ep080 补位，阈值 −0.05/−0.45，回退 4.1%），并删/改 A–F 字母为方法名或 RT1–RT3 短码。

### P0-2 「源 PDF 已被去色 / 无红色像素」的结论仍在四处正文中，其中一处随发布包分发

- **位置**：
  - `docs/PROJECT_STATE.md:118`（§5.1「PDF 已被去色…`r−g` 最大 9–14，`(r−g)>32` 命中 0 像素」）
  - `docs/PROJECT_STATE.md:146`（§7.1「本 PDF 已去色」）
  - `docs/method.md:6-8`（§1「本项目使用的 PDF 已去色（实测无红色像素）」）
  - `README.md:202-204`（致谢节「本 PDF 已被去色（實測 `r−g` 最大僅 11–14，無紅色像素）」）
  - `release/README.md:202-204`（**随 `GuanGeKai-v1.7.2.zip` 分发的包内 README 同样有此段**）
- **对照证据**（均已披露或已实测）：
  - `AGENTS.md:196-202`：「**源 PDF 也是彩色的**（`get_pixmap` 出来 `r−g` 最大约 103）… 早期『PDF 已被去色（`r−g` 最大 9–14）』的结论就是这么误测出来的」；
  - `docs/ERRATA.md:61-72`（E5）：全库 410 页实测 p95 19.97%、max 97.99%；
  - `docs/PROMPT-YONGLE.md:58-62`：「A 线的源 PDF 也是彩色的（`r−g` 最大约 103）… **早期文档里『A 线源图被去色』的说法是错的**，那是在流水线输出的灰度 PNG 上误测的」；
  - `docs/DATA-B.md:24` 对 B 线同源数据的实测亦为「红色句读 存在（全页 `r−g` 最大 127）」。
- **影响**：该错误会直接误导数据侧决策（以为无需颜色分离、或据此解释 red_mask 无用）；且错误结论随 zip 分发给最终用户，与 ERRATA 的公开勘误相反。
- **建议改法**：四处统一改为「源 PDF 为彩色（`r−g` 最大约 103），`ink_mask()` 的 `red_mask()` 一直在生效；A 线正文页红色占比 0.1–0.4%（中位 0.27%），收益接近 0」。包内 README 属发布快照（ERRATA E3），不重打包时至少加一条 ERRATA 指针；下次发版重打包自然修正。

### P0-3 PROJECT_STATE §9「如何独立审计」用的是 v1.5.0 口径：90.5% GAN / 9.5% 回退、m2_ep080、0.549/5.92

- **位置**：`docs/PROJECT_STATE.md:211`（「合成字构成（90.5% GAN / 9.5% 回退）」及其复验命令）、`:212`（「泛化指标（Dice 0.549 / chamfer 5.92）」+ `32_eval_clean.py --gan work/ckpt/m2_ep080.pt`、`34_struct_score.py`）
- **对照证据**：
  - `work/generated.jsonl` 实测（19,317 行）：`Counter({'gen': 17790, 'gen80': 728, 'base': 799})` → GAN = 17,790+728 = **18,518（95.9%）**，ribbon = **799（4.1%）**；与 `data/release-a.json:13-18` 一致；
  - `docs/EXPERIMENTS.md:1084` 的「17,484 字走 GAN（90.5%）、1,833 回退（9.5%）」是 **v1.5.0/E33** 的旧口径；
  - 当前主检查点是 `data/release-a.json:6` `m2wt_ep090`（补位才是 `m2_ep080`）；
  - 617 全量干净集实测 Dice = **0.539**（`data/release-a.json:32-33`、`work/eval_clean_a172.json`）；0.549 是 E32 的 n=150 抽样（`data/release-a.json:42` `note_vs_experiments` 明示「以本行为发布口径」）；
  - `:211` 给出的命令只输出 `gen/gen80/base` 三个原始键，不会打印 90.5%/9.5%。
- **影响**：审计者按这一节复验会得到「数字对不上」的假警报，或反过来接受错误基线；这是全库唯一一节「怎么独立审计」。
- **建议改法**：改为「GAN 18,518（95.9%，ep90 17,790 + ep80 728）/ ribbon 799（4.1%）」，命令改为对 `src` 做显式映射统计；泛化行改为 `m2wt_ep090`、n=617、Dice 0.539（0.549 注明 n=150 口径）。

---

## 2. P1（18 条）

### P1-1 PROJECT_STATE §0 快速开始仍指向 v1.5.0 发布包，且字号自相矛盾

- **位置**：`docs/PROJECT_STATE.md:27`（「发布包：`release/`、`GuanGeKai-v1.5.0.zip`」）、`:26`（「15.6 MB」）
- **对照证据**：同文件 `:55` 已写 `GuanGeKai-v1.7.2.zip`；`:27` 指向的是历史 zip（根目录 `GuanGeKai-v1.5.0.zip` 仍在，但当前发布物是 `GuanGeKai-v1.7.2.zip`，14,009,360 B）；`data/release-a.json:49` `"zip": "GuanGeKai-v1.7.2.zip"`；字体实测 15,739,524 B（十进制 15.7 MB），与 `:53`「15.7 MB」一致而与 `:26`「15.6 MB」不一致。
- **影响**：快速开始是接手第一屏，指向不存在的发布包会浪费排查时间。
- **建议**：`:27` 改 `GuanGeKai-v1.7.2.zip`；`:26` 与 `:53` 统一为 15.7 MB。

### P1-2 PROJECT_STATE §12–§20 版本记录：三处导航行编号错位、缺 v1.7.1/v1.7.2 小节

- **位置**：`docs/PROJECT_STATE.md:296`（§13 内「§12 v1.6.1 → §13 v1.6.0 → …」）、`:313`（§14 内）、`:330`（§15 内）；`:277-278`（§12 注）
- **对照证据**：实际标题为 §12 v1.7.0（`:275`）、§13 v1.6.1（`:294`）、§14 v1.6.0（`:311`）、§15 v1.5.2（`:328`）、§16 v1.5.1、§17 v1.5.0、§18 v1.3.x、§19 v1.2.1、§20 v1.2.0。因此 §13/§14/§15 的导航行整体错位一位（仍按「v1.6.1 是 §12」的旧编号）；`:278` 写「v1.6.2–v1.6.5 的说明在 `docs/RELEASE-v1.6.*.md`」，实际在 `docs/releases/`。
- **另缺**：最新两版 **v1.7.1 / v1.7.2** 没有对应小节（文件 `docs/RELEASE-v1.7.1.md`、`docs/RELEASE-v1.7.2.md` 存在；文件头 `:10`「最后更新 2026-11-13」；`:5-6` 已写 A v1.7.2）。
- **影响**：版本记录是「最新在 §12 还是 §20」的索引，错位会让读者按错号查找；缺最新两版会让「当前版本改了什么」断档。
- **建议**：重排为「§12 v1.7.2 → §13 v1.7.1 → §14 v1.7.0 → …」或保持由旧到新但修正三处导航行；补 v1.7.1/v1.7.2 摘要（字集 42、工作点固化）。

### P1-3 PROJECT_STATE §8 列表编号重复错序，且 GAN 段仍是 M2 之前的最优配置

- **位置**：`docs/PROJECT_STATE.md:174`（`0b.` 加训无效）、`:178`（`0.` B 线（GAN））、`:183`（第二个 `0b.` 结构口径）
- **问题**：同一有序列表出现两个 `0b.`、`0.` 位于 `0b.` 之后、随后又跳 `1.`，顺序为 0b → 0 → 0b → 1 → 2…；`:178` 用「B 线（GAN）」把字形线字母当技术路线名（GLOSSARY §2 禁止）；`:178-180`「最优配置是单实例 + PatchGAN + 15 轮…Dice 0.540 vs ribbon 0.413、chamfer 6.68 vs 8.76」是 E25/E26 阶段结论，已被 E32/M2（80 轮、Dice 0.549、chamfer 5.92）取代。
- **对照证据**：`docs/EXPERIMENTS.md:1035-1074`（E32 M2 成功）、`:1196-1202`（E36）；`docs/AGENTS.md:121-124`（M2 是转折点）。
- **影响**：读者会以为 GAN 只训 15 轮、当前最优仍是 0.540/6.68。
- **建议**：重排列表编号（0/0b → 1…）；`B 线（GAN）` 改 `zi2zi-GAN`；把 GAN 段更新为 M2/v1.5.0 后的最终配置，或注明「此段为 E29 阶段结论，已被 §17 取代」。

### P1-4 C 线 ribbon 数量/占比在多份规范与共享文档中陈旧或分母不一致

- **位置**：`docs/GLOSSARY.md:26`（「C 线 1,228 字（7.8%）」）、`docs/CONVENTIONS.md:115`（同 1,228/7.8%）、`AGENTS.md:60`（「1,313 带状回退（6.25%）」）、`README.md:30`（C 帶狀回退 6.3%）
- **对照证据**：`data/release-c.json:27` `"fallback_share": 0.0834`、`:35` `"ribbon_chars": 1313`、`:68` `"ribbon_fallback": 1313`；`README-C.md:23`「ribbon **1,313**（生成字的 **8.3%**）」；`docs/RELEASE-v1.3.0-C.md:10,22` 同样 1,313/8.3%。→ 1,228（7.8%）是 v1.2.0 旧值；6.25%/6.3% 用 21,034 作分母，与 A 线 4.1%（799/19,317，生成字为分母）及 C 线自己的 8.3% 口径不一致。
- **影响**：GLOSSARY 是「唯一规范源」，其数字错误会扩散；三线回退率不可横向比较。
- **建议**：GLOSSARY/CONVENTIONS 更新为 1,313 字（占生成字 8.3%），并在 GLOSSARY 或 DATA-C 明确定义分母（建议「占合成字」与 A/B 对齐）；AGENTS:60 与 README:30 用同一口径。

### P1-5 README 字库构成标题与守卫占比自相矛盾（同一页 4.1% vs 9.5%）

- **位置**：`README.md:84`（标题「字庫構成（v1.5.1）」）、`:90-92`（17,790=92.1%、728=3.8%、799=4.1%）、`:162-163`（「9.5% 觸發守衛時回退為帶狀掃掠…Dice 0.549」）
- **对照证据**：`:90-92` 的 799/4.1% 与 `data/release-a.json:15-18` 一致；`:162` 的 9.5% 是 v1.5.0 数字（E33），且与同页 4.1% 直接冲突；标题 v1.5.1 与内容（v1.6.4 起的 17,790/728/799 构成、当前 v1.7.2）不符。
- **影响**：面向使用者的首屏 README 内部矛盾，用户无法判断回退率。
- **建议**：标题改 v1.7.2（或删版本号写「当前」）；`:162` 改「4.1%（799 字）」。

### P1-6 README 文档索引仍列 C v1.2.0，与同页 C v1.3.0 矛盾

- **位置**：`README.md:113`（`docs/RELEASE-v1.2.0-C.md` /「**C v1.2.0**」）、`:116`（`README-C.md` /「GuanGe Kai C v1.2.0」）；`:114`（「已被取代的 **17 份**發布說明」）
- **对照证据**：同页 `:11`、`:28`、`:38` 均已是 C v1.3.0；`README-C.md:18` 为 v1.3.0；`docs/releases/` 实际有 **18** 份 RELEASE-*.md（`ls docs/releases/*.md | wc -l` = 19 含 README）。
- **影响**：README 的发布说明索引指向旧版本，用户可能下载/阅读错误的 C 发布说明。
- **建议**：`:113` 改为 `docs/RELEASE-v1.3.0-C.md`；`:116` 改 C v1.3.0；`:114` 改 18 份（并同步 `docs/releases/README.md` 索引，见 P2-5）。

### P1-7 README 的「拓扑相同率 97% / 与真迹 47%」与 E28 结论冲突

- **位置**：`README.md:15-16`
- **对照证据**：`docs/EXPERIMENTS.md:903-917`（E28）：「vs 真迹：ribbon 17/150、GAN 16/150、文楷 17/150… **这个指标全员 ~11%**… 决定：结构评估不再使用『与文楷拓扑全等』」；`:881-885`（E27）GAN 对文楷拓扑 23/150。`docs/CONVENTIONS.md:91` 只要求把「刻本」改「写本」、数值不变，但那是 E28 之前的决定；`docs/PROJECT_STATE.md:183-187` 已写「旧口径『与文楷拓扑全等』作废」。
- **影响**：README 是公开发布页，这两个数字会被外部引用为「本字体结构正确率」。
- **建议**：删除「拓扑相同率 97% / 47%」，改为当前可辩护的表述（骨架取自文楷、GAN 生成；结构指标以 Dice/chamfer 与真迹参照口径为准，见 method/E28）；若保留历史数字须标注「旧口径（E24），E28 已作废」。

### P1-8 README 重建步骤只给一个旧检查点，照做无法复现发布口径

- **位置**：`README.md:151-153`
- **对照证据**：`data/release-a.json:6-9`：主 `m2wt_ep090.pt` + 补位 `m2_ep080.pt`，阈值 −0.05/−0.45；`:11` reproduce 命令带 `--ckpt-hardtail/--threshold/--hardtail-threshold`；`docs/RELEASE-v1.7.2.md:12` 亦说明「不带参数重跑即发布口径（主 m2wt_ep090 + 补位 m2_ep080 + 阈值 −0.05/−0.45）」。README 只写 `work/ckpt/m2_ep080.pt`（380 MB）与「Dice 0.414 vs 0.549」。
- **影响**：按 README 重建只能得到 v1.5.0 的字形，不是发布字体。
- **建议**：补充两个检查点、两个阈值与 `--res 512 --simplify 2.0`（可直接引用 release-a.json 的 reproduce 行）。

### P1-9 method.md 的 potrace 参数与现实现不符

- **位置**：`docs/method.md:40`（「potrace（`turdsize=8, alphamax=1, opticurve`）」）
- **对照证据**：`scripts/glyphvec.py:204` 现默认 `turdsize=2`（`:207` 注释「turdsize=2 (was 8)」）；`scripts/10_generate.py:350,378,388,486` 与 `scripts/36_fill_fallback.py:44` 用 `turdsize=4, alphamax=0.4`；变更记录见 `docs/PROJECT_STATE.md:320`（v1.6.0 turdsize 8→2）、`:407`（v1.3.3 alphamax 0.4）。
- **影响**：method.md 是「从扫描到字体」的流程文档，参数错误会误导复现。
- **建议**：改为现行参数（默认 turdsize=2；合成/回退链路 turdsize=4、alphamax=0.4），或注明「默认值与发布链路不同」。

### P1-10 method.md 通篇仍是 v1.5.0 状态，且含已被 E34 推翻的小字号结论（勘误已登记但正文未修）

- **位置**：`docs/method.md:48-57`（「发布版（**v1.5.0**）…全量触发 9.5%…Dice 0.549」）、`:97`（「小字号偏重：v1.5.0 的合成字在 12–14px 比真迹重 12–20%」）
- **对照证据**：当前发布 v1.7.2，回退 4.1%（`data/release-a.json`）、617 全量 Dice 0.539（`data/release-a.json:33`）；E34 已把「小字号偏重 12–20%」更正为「全字号恒定偏重约 17%」（`docs/EXPERIMENTS.md:1125-1133`、`docs/PROJECT_STATE.md:353` 第 3 条已记录该更正）。
- **影响**：method.md 是从 README 链出的技术主文档；`:97` 属「勘误已登记但正文未修」的残留。
- **建议**：更新发布版描述为 v1.7.2（GAN 混合检查点 + 4.1% 回退 + 0.539）；`:97` 改为 E34 的正确结论。

### P1-11 DATA.md §4.9 对发布包 drift 与字体 name 表的描述已过时（name 表早已不是 woodblock）

- **位置**：`docs/DATA.md:98`（「`release/README.md` 与 `release/specimen.png` 是 **v1.6.5 发布时的快照**，图上与文内仍写『刻本』」）、`:100-101`（「已发布字体 `build/GuanGeKai-Regular.ttf` 的 name 表 ID 0 仍为 `Ming woodblock print`…**下一版重建时生效**」）
- **对照证据**：
  - 当前 `release/README.md` 是 **v1.7.2 包内快照**（13,477 B，与 `GuanGeKai-v1.7.2.zip` 内 `README.md` 同一文件；`release/SHA256SUMS` 记录其 sha256 = `fbe44906…`），且全文 grep 无「刻本/woodblock」；
  - `build/GuanGeKai-Regular.ttf` 实测 name ID 0 = `GuanGe Kai (館閣楷). Real glyphs extracted from the Ming manuscript …`；`docs/ERRATA.md:30-37`（E2）明确写「**v1.7.0 重建后已生效**」；
  - `release/specimen.png` 与 `docs/images/specimen.png` 同哈希（Oct 29 生成，属 v1.7.x 轮次），并非 v1.6.5 快照。
- **影响**：审计者会被引导去「修复」一个已修好的元数据；drift 描述也不再匹配真实包内容。
- **建议**：§4.9 改为「包内 README/specimen 为 v1.7.2 发布快照，与仓库 README 有已接受 drift（CONVENTIONS §4）」；name 表行改为「v1.7.0 起已是 manuscript（ERRATA E2）」。

### P1-12 DATA.md §5 校验和缺当前版本，v1.7.2 哈希以裸行挂在文件末尾；发布说明的指针失效

- **位置**：`docs/DATA.md:109-121`（仅 v1.5.0/v1.5.1/v1.5.2 三个 zip + B 线 v1.0.1 三行）、`:309`（文件最后一行 `14483141…  GuanGeKai-v1.7.2.zip`，在代码块外）；`docs/RELEASE-v1.7.2.md:36`（「校验和见 `docs/DATA.md`」）
- **对照证据**：`data/release-a.json:44-50`（artifacts：regular_sha256 `e6d8a104…`、real `bf278ab1…`、zip `14483141…`）；`data/release-b.json`（B v1.2.4：font `aa19d6d2…`、zip `2537de50…`）；DATA.md 的 B 线三行仍是 v1.0.1 的 `b76cfc01…/79aadc23…/f95b5e7f…`（旧版本）。
- **影响**：发布流程第 6 步要求「同步校验和到 DATA.md/PROJECT_STATE.md」，当前 DATA.md 找不到 v1.7.2/B v1.2.4 的可读条目（仅一行无说明的裸行），且 RELEASE-v1.7.2 的指针指空。
- **建议**：§5 补齐当前 A/B/C 三线制品校验和（直接引用 release-*.json），删掉末尾裸行；C 线已有 DATA-C §5.1，可只保留指针。

### P1-13 DATA.md 检查点/重建两处与发布口径或自身矛盾

- **位置**：`docs/DATA.md:175-188`（§6 重建：`10_generate.py --method gan` 未带发布阈值/补位参数；`:188`「预期总耗时…约 15 分钟」）、`:203`（「每次训练…`*_epNNN.pt`（每 5 轮）」）vs `:206`（「每 10 轮存一个快照」）
- **对照证据**：`data/release-a.json:11` reproduce 命令含 `--ckpt-hardtail work/ckpt/m2_ep080.pt --threshold -0.05 --hardtail-threshold -0.45`；同文 `:242`/`:296` 写「GAN 约 25 分钟（6 worker）」；所有者规则「每 10 轮」见 `AGENTS.md:30`、`DATA.md:206`。
- **影响**：按 §6 重建得不到发布字体；15 分钟与 25 分钟自相矛盾；「每 5 轮」与现行规则冲突（会让看 DATA 的人按旧规则清理检查点）。
- **建议**：§6 直接给「发布口径 = release-a.json 的 reproduce 命令行 + 36_fill_fallback」；`:203` 改每 10 轮；`:188` 改约 25 分钟或注明分步骤。

### P1-14 孔洞「lost」指标四个数字并存，最新发布说明的 0.7% 无落盘可复核

- **位置**：`docs/RELEASE-v1.7.2.md:21`（0.7%，200 字抽样）、`docs/RELEASE-v1.7.1.md:19`（0.7%，200 字抽样）、`docs/PROJECT_STATE.md:286`（0.5%，300 字抽样）、`AGENTS.md:169`（当前基线 **1.9%**，见 `work/holes_a.json`）
- **对照证据**：`work/holes_a.json:3-7`：`tested 300 / comparable 214 / lost 4` → lost/comparable = **1.87%**（`scripts/71_holes.py:92` 的口径即 lost/rows）；`docs/EXPERIMENTS.md:1262` 另给「完全丢孔 2.8%」。同一字体自 v1.7.0 起字形未变（v1.7.1/1.7.2 只加标点与元数据），0.5%/0.7%/1.9% 不可能由同一口径得出。
- **影响**：发布流程的孔洞闸门期望值（1.9%）与最新发布说明（0.7%）冲突，审计无法复核 0.7%。
- **建议**：统一为「`71_holes --n 300` → lost 4/214 = 1.9%」并注明口径与落盘文件；若要保留抽样差异，必须同时记录 n、random seed 与可比数。

### P1-15 v1.7.1 发布说明的标点数字自相矛盾；实际发布过 21,036，ERRATA 未登记

- **位置**：`docs/RELEASE-v1.7.1.md:10`（「`20,992 → 21,034`：新增 **44 码位**——空格…半角数字…全角数字…中文标点 20 个」）
- **对照证据**：
  - 20,992 + 44 = **21,036 ≠ 21,034**；`docs/PLAN-PUNCT.md:68` 写的是「新增 44 码位：空格×2 + 半角数字×10 + 全角数字×10 + 中文标点×**22**」，加起来才是 44；
  - 实测解 zip：`unzip -p GuanGeKai-v1.7.1.zip GuanGeKai-Regular.ttf` → cmap **21,036**、`Version 1.7.1`；`GuanGeKai-v1.7.2.zip` → cmap **21,034**；`v1.7.0` → 20,992；
  - 即 v1.7.1 含 U+201C/U+201D（v1.7.2 才删除，见 `docs/RELEASE-v1.7.2.md:9`）；
  - `docs/GLOSSARY.md:80` 只写「已废弃写法 `44 个码位`、`cmap 21,036`」，未记录它曾是 v1.7.1 的真实发布口径；`docs/ERRATA.md` 无相关条目；
  - 该文件在 `scripts/97_check_terms.py:51` 的 `docs/RELEASE-` 白名单内，44 不会被闸门发现（另见 P1-17）。
- **影响**：唯一记录 v1.7.1 字集扩张的文档写错了实际数字；`44` 这一「禁止写法」在正文里仍存在且语义成立（曾是真实值），会让后来者误以为它从不存在。
- **建议**：因历史发布说明不改写（CONVENTIONS §5.1），建议在 ERRATA 新增条目：「v1.7.1 发布 21,036（44 个标点/数字/空格，含 U+201C/U+201D）；v1.7.2 撤 2 个 → 21,034（42），`44`/`21,036` 自 v1.7.2 起作废」；同时修正 `RELEASE-v1.7.1.md` 的 21,034→21,036 或加勘误注（二者择一，需所有者定）。

### P1-16 AGENTS 中 C v1.3.0 的日期 2026-11-12 与三份 C 线权威文件不符

- **位置**：`AGENTS.md:62`（「**v1.3.0（2026-11-12）**：训练 val 改用字级未见 `pairs_holdout`…」）
- **对照证据**：`data/release-c.json:31` `"release_date": "2026-11-02"`；`docs/RELEASE-v1.3.0-C.md:3`「2026-11-02」；`docs/DATA-C.md:206`「v1.3.0 校验和（2026-11-02）」；`build/GuanGeKai-C-Regular.ttf` mtime 2026-11-02 10:15 且与 release-c.json sha256 一致（未在 11-12 重建）。11-12/11-13 的更正属于 `work-c-big` 探索实验（`docs/EXPERIMENTS-C.md:493`），不是 v1.3.0 发布变更。
- **影响**：跨线交接时 C 版本日期错误；该行同时把「val 改用 pairs_holdout」记为 v1.3.0 发布内容，需 C 线专项确认。
- **建议**：日期改回 2026-11-02；「val 改用 pairs_holdout」若无 v1.3.0 训练记录支撑，移到 C-Big/审计注记或删除。

### P1-17 97_check_terms 的扫描范围/正则/白名单存在盲区：live 页面 `docs/index.html` 中的「刻本」不会被发现

- **位置**：`scripts/97_check_terms.py:137-142`（targets 只含 `*.md`、`docs/*.md`、`scripts/*.py`、`release*/README.md`）、`:51`（`docs/RELEASE-`、`docs/releases/`、`docs/AUDIT-` 前缀白名单，本次跳过 23 个文件）、`:62`（过期数字正则 `44\s*个码位|cmap\s*21,?036`）、`:27-29`（docstring 仍称 build 字体是 woodblock）
- **对照证据**：
  - `docs/index.html:19` 仍写「明代《四書白文》**刻本**」，当前用户页面、不在扫描范围（97 输出「TERMS OK … 白名单 23 个文件未扫；15 行显式豁免」，未报 index.html）；
  - `docs/REPORTS/2026-10-24-handoff.md:7` 亦有「明刻本」，同样不在 `docs/*.md` glob（子目录被漏）；
  - 正则 `44\s*个码位` 匹配不到真实写法「44 码位」（RELEASE-v1.7.1:10「新增 **44 码位**」、PLAN-PUNCT「+44 码位」），`cmap 21,?036` 只在 GLOSSARY 元引用里出现；
  - docstring 的「Known legacy: build/*.ttf name tables still say woodblock」已不成立（见 P1-11 实测）。
- **影响**：术语闸门对当前用户可见页面失效；数字闸门实际不可用；白名单使 v1.7.1 的 44/21,036 口径问题（P1-15）无法被检查。
- **建议**：targets 增加 `docs/index.html`、`docs/REPORTS/*.md`；数字正则改为 `(?:^|[^0-9])44\s*码位|21,?036`（并区分真实计数 44 字 vs 44 码位）；更新 docstring；白名单 23 个文件建议输出文件名清单，便于审计确认。

### P1-18 发布/重建口径数字各处混用 0.549（n=150 抽样）与 0.539（n=617 全量）

- **位置**：`AGENTS.md:50`、`docs/PROJECT_STATE.md:137`、`:212`、`docs/method.md:57`、`docs/RELEASE-v1.7.2.md:22`、`README.md:163`
- **对照证据**：`data/release-a.json:32-42`（`clean.set = work/pairs_single.npz`，`n: 617`，`dice: 0.539`，`measured 2026-11-13`，并注「E32 报 0.549（n=150 抽样）；本行是 n=617 全量…**以本行为发布口径**」）；`work/eval_clean_a172.json` 实测 m2wt_ep090 n=617 dice 0.539。0.549 只属于 E32 的 n=150 抽样（`docs/EXPERIMENTS.md:1053-1063`）。
- **影响**：同一指标两个值散落在六处，发布说明与「发布口径」声明冲突；外部引用会取错值。
- **建议**：统一写「617 全量 Dice **0.539**（chamfer 保留 E32 n=150 的 5.92 时须注明 n）」，或统一写 0.549 但明确 n=150 并指向 release-a.json 的发布口径说明。

---

## 3. P2（16 条）

### P2-1 逐字来源「三态/四态」与实际的 5 类取值不符

`docs/PROJECT_STATE.md:29`（三态 `real`/`gan`/`ribbon_fb`）、`:55`（四态）、`docs/DATA.md:88`（「逐字 real/gen」）vs `release/provenance.json` 实测 21,034 条：`gan_ep90 17,790 / gan_ep80 728 / real 1,675 / ribbon_fb 799 / punct 42`。建议统一写「real/gan_ep90/gan_ep80/ribbon_fb/punct 五类」。（§16:351 的「三态」是 v1.5.1 历史，保留。）

### P2-2 当前文档仍用「木刻」这一禁用词族

`docs/PROJECT_STATE.md:154`「极少数真字仍有**木刻**飞白/纸褶」。GLOSSARY §4 的词表禁「刻本/刻刀/刀刻」等，97 的正则（`scripts/97_check_terms.py:57-64`）未含「木刻」，因此漏检（97 输出 TERMS OK）。建议改「写本残墨/纸褶」。

### P2-3 PROJECT_STATE §7.3 工作区体积/目录与实际磁盘不符

`docs/PROJECT_STATE.md:160-161` 写 `work/` 4.1 GB、`data/models/` 2.4 GB、`data/lora_run/` 760 MB。实测 `du -sh work` = **14 GB**；`ls -d data/models data/lora_run` 均不存在（`docs/DATA.md:246-247` 已记这两个目录被清理）。建议改为「work/ 约 14 GB；data/models、data/lora_run 已清理（见 DATA §6.5）」。

### P2-4 「崩坏率 4.7%→0.7%」应注抽样口径

`docs/PROJECT_STATE.md:363` vs `AGENTS.md:120`/`docs/EXPERIMENTS.md:110,967-968` 的「5.7%→0.7%（n=300）」，以及 `EXPERIMENTS.md:999-1000`（E30）的「ribbon 4.67%、GAN 0.67%（n=150）」。同一个落差在 n=300 是 5.7、n=150 是 4.67，文档未注 n。建议统一注明 n。

### P2-5 ERRATA E3 的包内 README 快照表已过时

`docs/ERRATA.md:39-51`：表格写 `release/README.md v1.6.5`、`release-b/README.md v1.2.1`、C v1.0.1；正文又说「三个发布包的 README 仍是『刻本』措辞」「A/B 不重新发版」。实测当前三包 README 已无「刻本/woodblock」字样，A 包 README 为 v1.7.2 快照、B 包为 v1.2.4（Nov 13 重出）、C 包为 v1.3.0；「A/B 不重新发版」也被后续 v1.7.x / B v1.2.4 发版事实取代（P1-11 已报 DATA 侧的同类描述）。建议更新 E3 表格并加一句「本条在后续发版后仅保留结论：包内 README 视为发布快照，不追改」。

### P2-6 docs/releases 索引与档案内「当前版本」指针陈旧

`docs/releases/README.md:3` 写「当前版本…A `RELEASE-v1.7.0.md`、B `RELEASE-v1.2.2-B.md`、C `RELEASE-v1.0.1-C.md`」，实际当前是 A v1.7.2 / B v1.2.4 / C v1.3.0；索引表 17 行但目录有 18 份，缺 `RELEASE-v1.7.0.md`（`ls docs/releases/RELEASE-*.md` = 18）。另 `docs/releases/RELEASE-v1.3.3.md:3` 仍称「当前发布版」；`RELEASE-v1.2.0.md:3`、`RELEASE-v1.2.1.md:3` 指向 `v1.3.3`/`RELEASE-v1.5.0.md`。建议只改索引与指针（历史正文按 CONVENTIONS 不改）。

### P2-7 发布日期的字段语义不统一

`data/release-a.json:51` `release_date: 2026-11-13`（但 A v1.7.2 的 zip 内 README、`release/` 字体与包内 specimen 均为 2026-10-29/30；`docs/RELEASE-v1.7.2.md` 无日期；该字段是 HEAD 提交 e308ad5 新增，同日只加了 n=617 评测）；`data/release-b.json` `release_date: 2026-10-30` 而 B v1.2.4 包与 `release-b/SHA256SUMS` 于 2026-11-13 重出（zip 哈希在 83d01d9 变更）；`README.md:11` 又写「2026-11-02」。建议区分「制品发布日」与「记录更新日」，并在三线统一。

### P2-8 EXPERIMENTS：训练轮次一览/章节索引/总表顺序不完整

`docs/EXPERIMENTS.md:12-24`「训练轮次一览」只列 6 轮（自训 U-Net 3 + LoRA 2 + GAN 150ep），但同文还有 E23（40 轮 / 6.1h）、E26（归因四格 20 轮）、E32（80 轮）、E36（150 轮）、E39（续训 20 轮）等训练，与「回答这是第几轮」的定位不符；`:8` 写「评估集统一为 work/eval_clean2.json（91 字）」，而 E25 起改用 617 干净集、E32/E36 用 n=150；`:41-76` 章节索引止于 E33，缺 E34–E40 共 7 条（正文标题存在）；`:117-121` 总表 E37–E40 顺序倒置为 E36→E40→E39→E38→E37。建议补齐/重排。

### P2-9 EXPERIMENTS 内部「文楷 vs 真迹拓扑一致率」两值打架

`docs/EXPERIMENTS.md:777`（E24）「文楷与真迹的拓扑一致率只有 47%」vs `:913`（E28）「vs 真迹：文楷自己 17/150（~11%）」。同一指标两名数、未注明 n/口径；README:16 引用了 47%（P1-7）。建议在 E24 处加「旧口径，E28 已改」注。

### P2-10 PLAN-v1.5 标题与状态注已被 E36 推翻

`docs/PLAN-v1.5.md:1`「把 **B 线（GAN）** 推到可验收」（B 线是字形线，术语冲突）；`:5-6`「M2 曲线到 ep80 仍在涨……若继续提升应优先『加训』而非『加分辨率』」——E36 已否证加训（`docs/EXPERIMENTS.md:1196-1202`、`AGENTS.md:123-124`）；`:184`「GAN 作 v1.4.0 主体」与其后「发 v1.5.0」不一致。建议标题改 `zi2zi-GAN`，状态注加「E36 已更正：加训无效」。

### P2-11 发布包内 README 的相对链接全部失效（未在 ERRATA 登记）

`release/README.md` 有 25 处、`release-b/README.md` 5 处、`release-c/README.md` 4 处相对链接指向包内不存在的路径（例：`release/README.md:17` → `docs/PROJECT_STATE.md`、`:38` → `docs/RELEASE-v1.7.2.md`、`:34` → `README-B.md`；zip 内只有 11 个文件）。这是用户打开 zip 时的实际断链，与 ERRATA E3/E4 的「快照」性质不同。建议下次发版时在 `14_package.py` 里改写/剥离链接，或在 README 顶部注明「本包只含字体与许可，文档链接指向仓库」。

### P2-12 CONVENTIONS 的验收声明与 83_verify 硬编码描述过时

`docs/CONVENTIONS.md:139-143` 引用「`scripts/83_verify_ab_c.py:31` **硬编码**了 `GuanGeKai-v1.6.5.zip` 的哈希」，现脚本 `:31` 附近的 `ZIPS` 已更新为 v1.7.2 / B v1.2.4 / B v1.2.2；`:207`「当前剩 17 处」与 `:4`「97 全绿后本文件降级为历史」——实测 `scripts/97_check_terms.py` 已输出 `TERMS OK`，按 §10 第 7 条应加「已完成」横幅。建议更新引用并执行降级（或注明「全绿但覆盖面有盲区，见 P1-17」）。

### P2-13 文档约定（加粗/emoji）执行不严

`README.md:26` 表格对非数字/非判定加粗（「**多人分抄**」）；`docs/DATA.md:12-21` 的 §1 表格用 ❌/⚠️（约定只允许总表判定列用 emoji）；`docs/PLAN-OCR-IMPLEMENT.md:533,543,547`、`docs/PLAN-PUNCT.md:169`、`docs/PROMPT-SHIJI.md:98`、`docs/PROMPT-YONGLE.md:330` 等正文含 ✓/⚠️/❌。建议按 AGENTS「文档约定」统一（历史 AUDIT 不受此限）。

### P2-14 PROJECT_STATE §2 的「结构正确」表述与 E24/E27/E28 实测不符

`docs/PROJECT_STATE.md:62`「19,317 个合成字是**近似**：结构正确（来自霞鹜文楷骨架）、笔画重量接近」。E27 实测 GAN 原样对文楷拓扑仅 23/150（`:884`），E28 实测字碗只有 39/120 对得上（`:927`）。建议改为「结构主要继承自文楷骨架；与真迹的笔画级结构仍有差距（E28）」。（`:61` 对 Real.ttf 的判断不受影响。）

### P2-15 DATA.md 的「2026-10-23 实测」与仓库最大文件描述已过时

`docs/DATA.md:4`「所有体积为 2026-10-23 实测」；`:306`「git 跟踪的文件中最大的只有 `data/ids/ids.txt`（2.1 MB）与两张对照图（各 2 MB）」。实测（`git ls-files -z | xargs -0 stat`）：`data/ids/ids.txt` 2,161,631 B ✓，但还有 `data/reference-b/shiji_raw.txt` 1.84 MB、`data/reference-b/reference.txt` 1.50 MB、`data/ids/Unihan_Variants.txt` 0.73 MB；文档对照图实际 0.69–0.83 MB，不是各 2 MB。建议更新体积表与「最大文件」句。

### P2-16 AGENTS/DATA 仍把 `m2_*` 写成「当前推进的路线」

`AGENTS.md:34`、`docs/DATA.md:209`「正在推进的路线（当前 `m2_*`）在推进期间保留全部」；`docs/DATA.md:218` 表中 `m2` 状态仍为「推进中」。实际当前发布主模型是 `m2wt_ep090`（`data/release-a.json:6`），`m2_*` 已退役。建议改为「当前 `m2wt_*`；`m2_*` 为 v1.5.0 历史基线」。

---

## 4. 已披露 / 已接受（不重复当新发现）

1. **ERRATA E1**：《四书白文》是写本非刻本；历史 `docs/RELEASE-*`、`docs/AUDIT-*` 保留原文。→ 这些文件中的「刻本」不计新缺陷。
2. **ERRATA E2**：v1.6.5 字体 name 表 `woodblock` 不重建；v1.7.0 起已修。→ 已核实当前字体为 manuscript（见 P1-11 的证据），E2 本身结论成立。
3. **ERRATA E3/E4 + CONVENTIONS §4**：包内 `README.md`/`specimen.png` 视为发布快照，与仓库 README 不要求逐字节一致。→ `release/README.md` 仍写 C v1.2.0、旧数字，属该决定范围，不单列为新缺陷（但 E3 表格过时已报 P2-5；包内断链另报 P2-11）。
4. **ERRATA E5**：A 线红像素分布（中位 0.27%、p95 19.97%、max 97.99%）。→ 与 P0-2 的「已去色」矛盾，P0-2 报的是正文未采纳该结论，不是重复 E5。
5. **ERRATA E6/E7**：C 线碎片格、`work/generated_simplified.jsonl` 清理记录不成立。→ 已核对，不重复。
6. **CONVENTIONS §5.1**：`docs/PLAN-v1.2/PLAN-v1.4`、历史 RELEASE/AUDIT 的术语问题按计划不改（P2 优先级）。→ `RELEASE-v1.1.0-B.md:3`、`RELEASE-v1.2.1-B.md:3` 的「四书刻本」不单列。
7. **v1.5.0 时代的 9.5% 回退披露**（`docs/releases/RELEASE-v1.5.0.md`、`PROJECT_STATE §17`、`EXPERIMENTS E33`）：历史版本记录，保留。→ 但未标注历史语境的 P0-3/P1-5 已单独报。
8. **`44` / `21,036` 在历史文档中的出现**（`PLAN-PUNCT.md`、`AUDIT-*` 的 44 字计数、GLOSSARY 元引用）：按「历史文档不改」接受；其中 v1.7.1 发布说明的自相矛盾另报 P1-15。
9. **97 白名单里的 23 个文件**（`docs/RELEASE-*`、`docs/AUDIT-*` 等）：设计如此，不报；报的是扫描范围缺口（P1-17）。

---

## 5. 已核查不成立（疑似问题，实测后排除）

| # | 疑似问题 | 核查方法与结果 |
|---|---|---|
| 1 | `release/`、`build/`、zip 的哈希与 `data/release-a.json` 不一致 | `shasum -a 256` 实测：build/release 字体 `e6d8a104…`/`bf278ab1…`，zip `14483141…`，与 release-a.json:44-50 完全一致；`release/SHA256SUMS` 亦一致 |
| 2 | 字体版本/字集/字形数错误 | fontTools 实测：name ID5 `Version 1.7.2`、head.fontRevision 1.72、cmap 21,034、glyphs 21,035、UPM 1000、hhea 880/−120；`13_qa` 输出 `coverage 20992/20992`、`real-subset glyphs 1675 cmap 1675 -> OK` |
| 3 | `release/provenance.json` 真字计数或行数不对 | 实测 21,034 条，`real`=1,675（与 `wc -l work/chosen.jsonl`=1,675 一致） |
| 4 | 合成字构成不对 | `work/generated.jsonl` 19,317 行 = gen 17,790 + gen80 728 + base 799 = 17,790+728+799，与 release-a.json 一致 |
| 5 | PROJECT_STATE §3 数据事实（410 页/54,109 格/2,292 标签/358-384/0.899） | 实测一致：`work/page_stats.csv` 410 行、`work/cells.jsonl` 54,109 行、`work/labeled.jsonl` 唯一标签 2,292、`work/align_report.json` 384 条中 358 条 rate>0.5、均值 0.8986 |
| 6 | B/C 制品哈希与 `data/release-b.json`/`release-c.json` 不一致 | `shasum` 实测一致（B `aa19d6d2…`/`7d10e460…`；C `765d0848…`/`6caf9d82…`）；三线 zip 均 11 个文件 |
| 7 | docs 内相对链接/图片失效 | 脚本检查根 README + docs/*.md + docs/releases/*.md + index.html：全部存在；仅有 3 处 `nolines` 是代码片段 `label_src="nolines"` 的误报。`docs/images/{lines-compare,style-A,cmp-v162-v163,seam-v164,manuscript-evidence}.png` 均存在 |
| 8 | 97_check_terms 没过 | 实跑输出 `TERMS OK （除白名单与已知遗留外一致；白名单 23 个文件未扫；15 行显式豁免）`，退出码 0（覆盖率问题另报 P1-17） |
| 9 | `release/` 目录未重新打包导致制品失配 | release/ 字体哈希 = build/ = release-a.json；zip 哈希 = release-a.json；只是 README 为发布快照（已接受 drift） |
| 10 | `docs/RELEASE-v1.7.2.md` 的「provenance 增 42 punct（20,992→21,034）」 | provenance 实测 21,034 条、punct 42 条，成立 |
| 11 | AGENTS 的 A 线当前数字（18,518/799/95.9%/4.1%）与 release-a.json 冲突 | 完全一致（17,790+728=18,518；799/19,317=4.14%） |
| 12 | DATA §4.5「release/ 共 11 个文件」 | `ls release/ \| wc -l` = 11，成立 |

---

## 6. 未覆盖与限制

1. **B/C 线文档未深审**（另有专项）：仅做了跨线口径抽查（C v1.3.0 日期 P1-16、C ribbon 数/分母 P1-4、B 发布日期 P2-7）。B/C 的 README、DATA-B/C、EXPERIMENTS-B/C、PLAN-B/C 细节不在本报告判定范围。
2. **未重跑 PDF→切字→OCR→训推全链路**：只复核 `work/` 索引与计数，未验证底层图像/OCR 数据本身；`work/` 真实体积 14 GB 与磁盘占用一致，但未逐目录核对。
3. **图片内容未 OCR/目视**：`release/specimen.png`、`book-vs-font*.png` 上是否仍印「刻本」字样无法用 grep 判定，按 ERRATA E4 视为已知；如需确认建议人工看图。
4. **外部网络链接未逐一访问**：只检查仓库内相对链接；README 的 GitHub/OFL 外链未抓取。
5. **字体质量指标未重测**：Dice/chamfer/holes 只引用已有落盘文件（`work/eval_clean_a172.json`、`work/holes_a.json`、`data/release-a.json`），未重新推理生成；因此 P1-14 的 0.7% 只能用「无落盘文件」判定不可复核，而非重测反驳。
6. **provenance 与字体构建输入的新鲜度绑定**（`docs/AUDIT-2026-10-26*` 的 P1-4）未重验。
7. **历史遗留工作区文件**（ERRATA E7、`work/generated_simplified.jsonl` 等）未再核。

---

## 附录 A：审计命令与数据源

```bash
# 基线
git log -1 --format='%H %ad %s' --date=iso          # e308ad55 … 2026-11-13
git status --porcelain                              # 干净

# 字集/字体
python3 -c "from fontTools.ttLib import TTFont; f=TTFont('build/GuanGeKai-Regular.ttf'); print(len(f.getBestCmap()), len(f.getGlyphOrder()), f['head'].fontRevision)"
python3 scripts/13_qa.py --font build/GuanGeKai-Regular.ttf
shasum -a 256 build/*.ttf release/*.ttf GuanGeKai-v1.7.2.zip

# 逐字来源/合成构成
python3 -c "import json,collections;d=json.load(open('release/provenance.json'));print(len(d),collections.Counter(d.values()))"
python3 -c "import json,collections;print(collections.Counter(json.loads(l)['src'] for l in open('work/generated.jsonl')))"
wc -l work/chosen.jsonl

# 数据事实/实验落盘
cat work/holes_a.json work/eval_clean_a172.json data/release-a.json data/release-b.json data/release-c.json
python3 - <<'EOF'  # align_report / labeled
import json
ar=json.load(open('work/align_report.json')); print(len(ar), sum(1 for r in ar if r[2]>0.5))
print(len({json.loads(l).get('label') for l in open('work/labeled.jsonl') if json.loads(l).get('label')}))
EOF

# v1.7.0/1.7.1/1.7.2 实际 cmap（不落盘，流式读 zip）
for z in GuanGeKai-v1.7.0.zip GuanGeKai-v1.7.1.zip GuanGeKai-v1.7.2.zip; do
  unzip -p "$z" GuanGeKai-Regular.ttf | python3 -c "import sys,io;from fontTools.ttLib import TTFont;f=TTFont(io.BytesIO(sys.stdin.buffer.read()));print('$z',len(f.getBestCmap()))"
done

# 术语闸门
python3 scripts/97_check_terms.py

# 链接/图片存在性：python 正则扫 [..](..) 与 src=，解析相对路径后 os.path.exists
# 检查点清单 vs 磁盘：work/ckpt/MANIFEST.json 与 ls work/ckpt/*.pt 取差集
# 包内 README 断链：以 release*/ 为基准解析 README 相对链接
```

## 附录 B：建议的最小修复顺序（供 Lead 参考，不代改）

1. 先修 3 条 P0：§6 发布方法、去色结论（4 文件 + 包内 README）、§9 审计口径。
2. 再修发布链相关 P1：P1-1/2/3（PROJECT_STATE 版本记录与 §0/§8）、P1-12/13（DATA 校验和/重建）、P1-14（孔洞）、P1-15（v1.7.1 ERRATA）、P1-18（0.549/0.539 统一）。
3. 跨线：P1-4（C ribbon 数）、P1-16（C 日期）交 C 线专项确认后改；P1-17（97 覆盖面）建议由 A 线会话改脚本。
4. 其余 P2 可在下次发版随文档一并清；历史档案（releases/、AUDIT）按 CONVENTIONS 只改指针与索引。
