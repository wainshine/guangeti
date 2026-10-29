# 非汉字补全方案（标点 / 数字 / 空格）

> 起因：三套字体只覆盖 CJK 基本区（20,992），**空格、数字、拉丁、标点全部落到 `.notdef`（空心方框）**。
> 直接当正文用会满篇 □。本方案把「必补」的最小集合补齐，B/C 线跟随执行。
>
> **状态（2026-10-28）**：`scripts/13_extend_punct.py` **已实现并实测通过**（A 线试跑 +44 码位，
> 基本区 20,992 未变，样张无方框）。**尚未并入正式字体**——等下次发版时执行 §6。

## 1. 现状（实测）

| 项 | A | B | C | 文楷 |
|---|---|---|---|---|
| cmap | 20,992 | 20,997 | 20,992 | 46,926 |
| 基本区 | 20,992 | 20,992 | 20,992 | 20,992 |
| 区外 | 0 | **5（扩展 A）** | 0 | — |
| 空格 U+0020 / U+3000 | ✗ | ✗ | ✗ | ✓ |
| 数字 0–9 / 全角 | ✗ | ✗ | ✗ | ✓ |
| 中文标点 | ✗ | ✗ | ✗ | ✓（24/24） |
| 拉丁 A–Z a–z | ✗ | ✗ | ✗ | ✓ |

`.notdef` 是两个轮廓的空心方框（bbox 40,-120 → 960,880，upm 1000），所以缺字必然显眼。

## 2. 补什么（两档，本方案只做第一档）

### 第一档：必补（约 40 字）

```
空格      U+0020, U+3000
半角数字  0-9                       （10）
全角数字  ０-９                      （10）
中文标点  、。，；：？！「」『』（）《》〈〉— … · "" ''
```

### 第二档：可选（本轮不做）

半角标点、拉丁 A–Z / a–z。理由见 §4。

## 3. 视觉测试结论（2026-10-28）

同一段中文 + 文楷标点，1.00 与 1.08 两种缩放：

- **标点**：1.00 即可用，`，。《》` 与馆阁体重心基本齐平；
- **数字**：明显偏现代（文楷数字是印刷体），全角比半角协调；
- **1.08 缩放**：整体更“实”，但标点会略胖，**建议 1.00，不做缩放**。

结论：**标点取 1.00 直接搬，数字只补全角**。

## 4. 为什么拉丁留给系统回退

文楷的 A–Z 是思源系的现代字形，与楷书笔意完全不搭。补进去等于在楷书里嵌一段印刷体，
比“回退到系统字体”更破坏一致性。README 需写明这一点。

## 5. 技术实现（已落地）

```
scripts/13_extend_punct.py        已实现，三线共用

用法
  python3 scripts/13_extend_punct.py --line A                     # 出 build/...-Ext.ttf
  python3 scripts/13_extend_punct.py --line A --inplace           # 覆盖 build 字体
  python3 scripts/13_extend_punct.py --line B --drop-outside-basic --inplace
  python3 scripts/13_extend_punct.py --line C --inplace
  python3 scripts/13_extend_punct.py --line A --dry-run           # 先看会加/删哪些码位

实测（A 线，2026-10-28）
  原字体   cmap 20,992   基本区 20,992   区外 0
  补后     cmap 21,036   基本区 20,992   区外 44
  新增 44 码位：空格 ×2 + 半角数字 ×10 + 全角数字 ×10 + 中文标点 ×22

处理
  1. 按 §2 第一档码位从 `data/base/LXGWWenKai-Regular.ttf` 取 glyf 轮廓
  2. upm 同为 1000，**scale = 1.00**（不缩放，见 §3 视觉结论）
  3. 字宽 hmtx 取自文楷；取不到时用 em 宽度兜底
  4. 字形命名 `uniXXXX`，追加到 glyph order，写入所有 format 4/12 cmap 子表
输出  `--inplace` 覆盖 `build/GuanGeKai[-B|-C]-Regular.ttf`；否则写 `*-Ext.ttf`
顺序  必须在 `11_build_full.py` **之后**、`14_package.py` **之前**
校验  基本区覆盖仍为 20,992；区外新增 == 44（B 开 --drop-outside-basic 时为 39）
```

## 6. 三线动作（下次发版时执行）

| 线 | 命令 | 结果 |
|---|---|---|
| **A** | `python3 scripts/13_extend_punct.py --line A --inplace` | cmap 20,992 → 21,036 |
| **B** | `python3 scripts/13_extend_punct.py --line B --inplace` | 20,992（先删 5 个扩展 A）→ **21,036**，见 §7 |
| **C** | `python3 scripts/13_extend_punct.py --line C --inplace` | 20,992 → 21,036 |

**每条线还要做三件事**：

1. `13_qa` / `80_qa_c` 的覆盖断言改为「**基本区 == 20,992**」（不是 cmap 总数 == 20,992），
   否则补完标点会误报；
2. `README*.md` 写明：字体含 CJK 基本区 20,992 + 标点数字 44，**拉丁字母仍由系统回退**；
3. 重跑打包与校验和（字体二进制变了，zip 哈希也会变）。

## 7. B 线细则（B 会话补，2026-10-28）

B 的 cmap = 20,997 = 基本区 20,992 + **5 个扩展 A**（`㓗 㢮 㯉 䍧 䳒`，全部是 real）。
`13_extend_punct.py --line B` 只处理 `GuanGeKai-B-Regular.ttf`，**不碰 `-Real`**。

### 7.1 命令与顺序

```bash
# 1) 先删 5 个扩展 A（builder 层，见 §7.2.1）
python3 scripts/57_build_real_b.py --reuse-contours --drop-outside-basic   # Real 4,078 → 4,073
python3 scripts/62_build_full_b.py --drop-outside-basic                   # Regular 20,997 → 20,992
# 2) 再补 44 个标点
python3 scripts/13_extend_punct.py --line B --dry-run    # 应报：新增 44、删除 0
python3 scripts/13_extend_punct.py --line B --inplace    # cmap → 21,036
# 3) 质检与打包
python3 scripts/63_qa_b.py                               # 断言按基本区，不受影响
rm -rf release-b && python3 scripts/64_package_b.py
```

### 7.2 决定：**删**（所有者 2026-10-28 定；重训押后）

cmap = 20,997 − 5 + 44 = **21,036**；glyph 数 20,998 + 44 − 5 = **21,037**。
**本轮不重训**：模型仍是 v1.2.2 那份（训练时 4,078 对，含 5 个已删码位）。这 5 个字在字体里走真迹、
从不经过 GAN，删掉不影响任何已发布字形；`pairs.npz` 保留为 v1.2.2 的训练快照并注明，
下一次重训（v1.3.x）再从 4,073 重建。

### 7.2.1 在哪一层删：**builder 层，不是 extend 层**

`13_extend_punct.py` 的 `FONTS` 只指向 `GuanGeKai-B-Regular.ttf`，**不会处理 `-Real`**。
如果只在 extend 层 `--drop-outside-basic`，结果会是「Regular 没有这 5 个字、Real 还有」，
`Real ⊆ Regular` 破掉。所以：

1. `57_build_real_b.py` 与 `62_build_full_b.py` 各加 `--drop-outside-basic`
   （加载 `real_contours.jsonl` 时跳过 `0x4E00–0x9FFF` 之外，5 个字自然不进两个字体）；
2. `13_extend_punct.py --line B --inplace` 只负责补 44 个标点，不再需要 drop 开关（留着兜底）。

### 7.3 执行清单（按依赖顺序）

| # | 动作 | 文件/命令 | 验证 |
|---|---|---|---|
| 1 | 加 drop 开关 | `57_build_real_b.py`、`62_build_full_b.py` | 两个脚本都能 `--drop-outside-basic` |
| 2 | 重建 Real | `57 --reuse-contours --drop-outside-basic` | maxp 4,074（含 .notdef）= 4,073 字 |
| 3 | 重建 Regular | `62 --drop-outside-basic` | 块内 20,992、无区外 |
| 4 | 补标点 | `13_extend_punct --line B --inplace` | cmap **21,036**、glyph **21,037** |
| 5 | 过滤 chosen | 备份后去掉 5 行 → 4,073 | `wc -l work-b/chosen.jsonl` = 4,073 |
| 6 | **改闸门断言** | `83_verify_ab_c.py` 三处 `4078 → 4073` | 需 C 线知晓：B 变化会让它先变红 |
| 7 | 重打包 | `rm -rf release-b && 64_package_b.py` | `stats.real 4073 / real_ext_a 0 / codepoints 20992` |
| 8 | 文档 | `README-B.md`（4,078×4、20,997×1）、`docs/DATA-B.md` | 全改；写明 21,036 的构成 |
| 9 | 发版 | 建议 **v1.3.0**（cmap 与真迹数都变了）+ 新 release note | 与 A 1.7.0 / C 同批或单独 |
| 10 | 收尾 | `63_qa_b` → `97_check_terms` → `83_verify_ab_c` | 三者全绿 |

**第 6 步是跨线的**：`83_verify_ab_c.py` 是 C 线的发版闸门，里面三处 4,078 断言写在
`B real glyphs / B chosen / B provenance real`。B 一删，它必然先报 `B CHANGED`，
必须同批改成 4,073；否则 C 那边会以为 B 被外力改坏了。

**pairs 不重建**：`08_make_pairs` 是从 chosen 生成的，chosen 变 4,073 后 pairs 仍是 4,078 的快照。
按 C 线已有的写法在 DATA-B 注明「训练时 4,078 / 当前 4,073」，避免下次审计误判。

### 7.4 Real 字体

- Real **不补标点**（遵 §9，只放真迹），但**要跟着删这 5 个字**（走 §7.2.1 的 builder 层开关）。
- 删完 Real = 4,073，与 Regular 的真迹集完全一致，`Real ⊆ Regular` 继续成立。

### 7.5 视觉复核：B 上 1.00 **偏轻**，不能直接沿用 A 的结论

§3 的「1.00 可用」只在 A 上测过。B 是明抄本（一人一笔），正文更细，文楷标点/数字偏印刷体。
本线已实跑一次（2026-10-28）：

```bash
python3 scripts/13_extend_punct.py --line B            # 出 build/GuanGeKai-B-Regular-Ext.ttf（不覆盖）
```

同句并排（`天地玄黃，館閣體。《四書》「勸學」— 0123 ４５６`）：

- 方框全部消失 ✓；
- **标点与数字比 B 的汉字明显偏细、偏窄**——逗号、破折号、半角数字尤其明显（文楷数字是半宽现代字形）。

建议 B 单独跑 1.00 / 1.05 / 1.10 三档目视后再定，不要直接抄 A 的 1.00：

```bash
python3 scripts/95_compare_lines.py                    # 三线并排看「非漢字」行
python3 scripts/98_style_sheet.py --line B             # 真迹/GAN/回退三行与标点并置
```

改 scale 时要同步改 `hmtx` 宽度（脚本现在按文楷 `hmtx` 取宽，只缩轮廓会导致字距错位）。

### 7.6 B 的验收补充

| 项 | 期望 |
|---|---|
| `63_qa_b.py` coverage | **20,992**（按块统计，补标点不动） |
| `63_qa_b.py` real-subset | **4,073**（`chosen.jsonl` 已过滤；`--real-expect` 走 chosen，自动跟上） |
| `83_verify_ab_c.py` | B coverage 20,992；**三处 4,078 断言必须先改成 4,073**，否则先报 `B CHANGED` |
| `64_package_b.py` `stats` | `codepoints 20992`、`real 4073`、`real_ext_a 0`；README 另写 cmap **21,036** |
| 渲染抽查 | `，。《》「」—…0123456789０１２３` 无方框 |
| 回归抽查 | 原本 5 个扩展 A 码位（`㓗㢮㯉䍧䳒`）在 Regular 与 Real 里都应回退到系统字体 |
| `release-b/SHA256SUMS` | 字体与 zip 哈希都会变，重打包后自校验 |

### 7.7 两处数字勘误（A 版原文）

- §6 表 B 行「20,997 → **21,031**」应为 **21,036**（20,997 − 5 + 44）。已改。
- §5「区外新增 == 44（B 开 `--drop-outside-basic` 时为 39）」：44 是新增数，39 是净增；
  B 按 §7.2 删 5 个后，**新增 44、净增 39**，最终 cmap 21,036。

## 8. 验收

```
13_qa                coverage 20992/20992（基本区不变）
13_extend_punct      A/C 新增 44；B 先删 5 个扩展 A，再新增 44（净增 39）；无 bbox 越界
渲染抽查             「天地玄黃，館閣體。《四書》—…0123456789」无方框  ← 已实测通过
95_compare_lines     非漢字行由方框变为实际字形（补完后才成立）
98_style_sheet       不受影响（只画基本区字）
```

**B 线另加四项**（详见 §7.6）：

```
63_qa_b              coverage 20992/20992（按块统计），真迹 4,073
64_package_b         stats.codepoints 20,992、real 4,073、real_ext_a 0；README 写 cmap 21,036
83_verify_ab_c       B coverage 20,992；三处 4,078 断言先改成 4,073 才会 PASS
回归抽查             㓗㢮㯉䍧䳒 在 Regular 与 Real 里都应回退到系统字体
```


## 9. 风险

| 风险 | 处理 |
|---|---|
| 字重不匹配 | 已测 1.00 可用；如个别标点偏轻，后续逐字微调 scale |
| 许可 | 文楷 OFL 1.1，含 Reserved Font Name；本项目未使用其保留名，衍生合法，保留 OFL 条款 |
| 与 Real 字体不一致 | Real 不补标点（只放真迹），文档写明 |
