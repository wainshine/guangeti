# B 线数据、来源与许可

> 本文件回答：B 线每个文件从哪来、能不能用、怎么复现。A 线的数据档案在 `docs/DATA.md`，
> 两份互不覆盖。体积为 2026-10-25 实测。

## 1. 输入数据

| 文件 | 体积 | 来源 | 许可 | 入库 |
|---|---|---|---|---|
| `史记.二十四册.传姜立纲抄本.新加坡国立大学藏.水印.pdf` | 1.4 GB | 新加坡国立大学图书馆藏明抄本《史记》（二十四册）之数字化影像，页面水印 `Original from and digitized by National University of Singapore Libraries` 即来源标识 | 原书公有领域；扫描件为公版作品的忠实再现（§3） | ❌ 不入库 |
| `data/reference-b/shiji_raw.txt` | 1.8 MB | 史記全文（繁体、带标点），下载自 [183-lgtm/guji1](https://github.com/183-lgtm/guji1) `j.史書/史記.txt`；文件头注明上游为 bgc2017/chtxt（2021-02-15 版） | **文本本身公有领域**（史記成书于西汉）；本仓库只用其**汉字序列**做 OCR 对齐，不用其标点、校记（§4） | ✅ 入库 |
| `data/reference-b/reference.txt` | 1.7 MB | 由 `53_build_reference_b.py` 从上一行生成：120 篇、499,740 字、4,940 个唯一字 | 同上 | ✅ 入库 |
| `data/base/LXGWWenKai-Regular.ttf` | 25 MB | [LXGW WenKai v1.530](https://github.com/lxgw/LxgwWenKai/releases)，与 A 线同一份 | **OFL 1.1，含 Reserved Font Name**（霞鹜/霞鶩/落霞孤鹜/落霞孤鶩/LXGW） | ❌ 不入库 |

### 1.1 扫描件的物理事实（实测）

| 项 | 值 | 来源 |
|---|---|---|
| 页数 | 1672 | `pymupdf` |
| 页面尺寸 | 1080×1008 pt；另有 1300×2100 的单页（册首/册末） | 同上 |
| 内嵌 JPEG | **2250×2100 px = 原生 150 dpi** | `page.get_images()` |
| 版式 | 双页对开、竖排、右起；每半叶 8 栏上下，每栏约 20 字 | 目视 + 切字统计 |
| 字距 | 300 dpi 渲染下 174 px（＝原生 87 px） | `work-b/page_stats.jsonl` |
| 红色句读 | **存在**（全页 `r−g` 最大 127，`>32` 约 1,900 px/页） | 实测 |
| 数字水印 | 页底「Original from and digitized by National University of Singapore Libraries」，浅灰、单行、位置固定 | 目视；见 §5 |

> 150 dpi 是本项目与 A 线最大的一处资源差距：四书原生 300 dpi、字面 250×250 px，
> 史记字面只有 80×86 px。因此 B 线一律**渲染到 300 dpi** 再切字与矢量化
> （1 个源像素 = 5 个字体单位，A 线是 2.8），并且**不能**照抄 A 线的分辨率相关标定。

## 2. 生成物（`work-b/`，全部不入库）

| 文件/目录 | 内容 |
|---|---|
| `cells/` + `masks/` | 单字灰度裁剪 + 二值掩膜（约 46 万格，预计 6–7 GB） |
| `cells.jsonl` | 每格元数据（页/栏/行/bbox/slot/pitch/ink） |
| `page_stats.jsonl` | 每页纠偏与切字统计（折缝位置、叶数、字距、格数、耗时） |
| `ocr_pages.jsonl` | 逐页 PP-OCRv6 结果（**在纠偏后的图上**，坐标与字格同一坐标系） |
| `labeled.jsonl` | 每格 → 字标签（含 OCR/参考文本/一致性/对齐率） |
| `chosen.jsonl` / `second.jsonl` | 每字一个最佳样本（+ 次优） |
| `norm.json` | 字面框归一化仿射参数 |
| `real_contours.jsonl` | 真迹轮廓（字体单位） |
| `pairs/pairs.npz`、`pairs_single.npz` | 训练配对 / 干净集（只出现一次的字） |
| `stroke_rel_width.npy` | 逐笔相对宽度分布（**B 线自己拟合**） |
| `ckpt/` | GAN 检查点（每 10 轮快照 + 验证最佳） |
> **过程文件清理（2026-10-30）**：删掉了 `dewarp_survey/`、`dewarp_qa/`、`sample20/`、`sample20b/`、
> `dryrun/`、`t2/`、`t3/`、`preview/`、`qa/sheet_*.png` 以及 5 个旧变体 jsonl/npz，约 **2.1 GB**。
> 这些都能由对应脚本重生成（`50_shiji_dewarp.py`、`51_segment_b.py --dump`、`63_qa_b.py`）。
> **检查点 14 个全部保留、`cells/` 与 `masks/` 各 473,847 张一张未删**——后续换方法可能还要重选、重描。
> 清理后 `work-b` ≈ **13.1 GB**（cells 6.27 + ckpt 5.60 + masks 0.50 + 其余 0.74）。

| `dewarp_qa/`、`dewarp_survey/` | 纠偏前后对比图与指标（`dewarp_metrics.json`） |

## 3. 许可审查

### 3.1 原书：公有领域

明抄本《史记》，作者司马迁（西汉），成书约公元前 90 年；抄本本身亦为数百年之物。
著作权保护期早已届满，**原书内容属公有领域**。

### 3.2 扫描件：公版二维作品的忠实再现，不构成新作品

数字化方为新加坡国立大学图书馆（页面水印即其来源声明）。判断其为**复制品而非新作品**，
理由如下（结论必须给理由，参见 `docs/PROMPT-SHIJI.md` §0.5）：

1. **客体是二维平面作品**。被摄对象是书页这一平面，拍摄/扫描的目的是尽量**消除**拍摄者
   的取舍（使影像与原件在几何与色调上一一对应），而不是创作新的表达。
2. **独创性门槛**。美国 *Bridgeman Art Library v. Corel Corp.*（S.D.N.Y. 1999）确立：
   对公版二维作品的**忠实复制**，即使技术精湛、投入巨大，也不产生新的著作权。德国、
   英国等对这一问题的处理虽有分歧（英国曾以「照片」保护），但都限于**摄影**语境，
   且近年司法与学说普遍向「不保护纯复制」收拢。
3. **中国大陆口径**。著作权法要求作品具备**独创性**；对古籍的纯扫描既不改变表达、
   也不体现个性化选择，实务中不被认定为摄影作品或汇编作品。属于古籍整理成果的
   **点校本、校勘记**才可能受保护——本项目**没有**使用任何现代点校本
   （见 §4，参考文本只取汉字序列）。
4. **数字化方也未主张额外权利**：该 PDF 上只有来源水印，没有许可声明或使用限制。

### 3.3 本项目的立场

- 不对扫描图像主张任何权利；
- 字体是**加工产物**：字形经纠偏、切分、去噪、矢量化、参数化重绘，不是扫描件的复制；
- 发布物按 A 线格式署名：藏本与数字化 —— **NUS Libraries**；
- 字形来源、字形处理链、逐字 provenance 全部公开（`release-b/provenance.json`）。

### 3.4 不构成授权替代的说明

书格（shuge.org）一类平台只是**分享渠道，不是权利主体**，向其"确认授权"没有法律效力。
A 线 `docs/DATA.md` 里那条待办已于 2026-10-25 删除；B 线不复制这个错误模板。

## 4. 参考文本的使用边界

参考文本**只用于给 OCR 结果定位**（`54_label_b.py` 的 difflib 对齐），具体边界：

1. 只保留汉字字符（`[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]`），**丢弃标点、校记、注释**；
2. **不进入字体**：发布字体里没有任何一个字形来自参考文本，字形一律来自扫描件；
3. **不随发布包分发**：`release-b/` 里没有参考文本；
4. 版本记录：上游 `bgc2017/chtxt` 2021-02-15 版，镜像 `183-lgtm/guji1`；
5. 10 篇「表」（卷十三–卷二十二）在该版本中是表格结构、无正文串，已跳过
   （`53_build_reference_b.py` 打印 `sections 120`）。**抄本里这十篇是有的**——
   表前序文是散文（见 p250《漢興以來諸侯王年表》），表体是真表格；
   由于参考里没有对应正文，这部分（约 12 页、2,881 格）不进入真迹字表。

### 4.1 OCR 与参考文本冲突的处理

抄本是墨笔手抄，通行本是刻本系统，二者必然有差异。处理原则：<!-- term-ok -->

- 冲突字对**逐条统计**后人工归类（`work-b/ref_conflicts.json`）：
  - **异体**（爲/為、閒/間、說/説、來/来…）→ 标签取 **OCR**（保留抄本字形）；
  - **OCR 误读**（嫪→繆、毐→毒…）→ 标签取 **参考文本**（参考文本在此是校对基准）；
- 未被归类的冲突格**不进入真迹字体**（只在 `labeled.jsonl` 留档），避免错标污染字表。

具体规则与实测比例记在 `docs/EXPERIMENTS-B.md`（B/E1）。

### 4.5 人工資產（不由腳本生成，勿覆蓋）

| 檔案 | 說明 |
|---|---|
| `docs/images/book-vs-font-b.jpg` | 手工合成：左為 p1000 原書頁（《平原君虞卿列傳》），右為同一段文字用 `GuanGeKai-B-Real` 豎排。**不是**任何腳本的輸出，重跑流程不會也不需要重建它 |

> 教訓來自 A 線：`docs/images/book-vs-font.png` 曾被自動腳本覆蓋成「可生成」的樣張。
> 能自動生成的圖與手工拼圖必須分開命名。

## 5. 数字水印的处理

页底水印是**浅灰**叠加层（灰度约 150–200，字高约 35 px@300dpi），位置固定在页面下缘。
A 线的做法（全局 Otsu + 厚度判据）在这里**失效**：Otsu 把纸/墨/水印三分，阈值落在
水印之上，水印被切成 22 个"字格"（20 页抽样）。

B 线的处理（`shiji_page.ink_mask`）：

1. 纸面相对阈值（`2% 分位 + 0.45×(中位−2%分位)`），实测阈值 ≈ 143–154，水印整体在阈值之上；
2. 折缝阴影先被 `flatten()` 压平，避免阴影把水印拉进阈值；
3. **不做**任何形态学腐蚀/膨胀（E17 的教训：会吃掉端帽）。

结果：20 页抽样里水印假字格 **22 → 0**，页底 7% 区域不再产生任何字格。

## 5.8 扫描件分辨率：已到顶（2026-10-26 所有者确认）

本 PDF 的嵌入图是 **150 dpi 原生**（2250×2100 px / 1080×1008 pt）。所有者确认
**没有更高清的扫描件可获取，这就是当前最好的**。

因此与本数据相关的两条路线正式关闭：

- **高 dpi 重渲染**：A 线 E38 用 200 字批量探针证明 600 dpi 只恢复 22% 的缺孔，B 线 E9 独立
  复现同一现象（残差孔内是纸面灰度、接缝是墨）；投入 1 天全链路重做换来的是边际改善。
- **换数据源**：本线无替代扫描件可用，chamfer 5.60（地板 3.57）与「孔数偏少 19.6%」是这份
  数据的**结构性天花板**，不是工程遗漏。

后续若要再提质量，可动的只剩：回退字的形态（B/E10 已证明不能靠放宽守卫）、模型结构/容量。

## 5.9 `head.fontRevision`

TrueType 的 `fontRevision` 是 **16.16 定点数**。本版（v1.1.0）由共用库按
`major + minor/10 + patch/100 = 1 + 1/10 + 0 = 1.1` 写入；定点量化后实测
`1.1000061035`，与 name 表 `Version 1.1.0` 对应。

注意：v1.0.1 时它是截断的 `1.0`（共用库旧行为，审计 3-3）；v1.1.0 起与 name 表一致。
A 线的 v1.6.2 同一公式给出 `1.62`（实测 `1.6199951`）。

## 5.95 发布包保留规则（所有者 2026-10-27）

**不要删除任何 `GuanGeKai-B-v*.zip`**——历史版本的 zip 由所有者手动清理。
发新版时只新增 zip，旧版原地保留；`release-b/` 可以重建，zip 不行。

（本会话早前曾自动删掉 v1.0.0 / v1.0.1 的 zip，已按要求停止。）

## 6. 校验和（v1.2.4）

```
aa19d6d2000d504af7123741fe9273bee157fee1f2915c570a9d05d27bab8f9d  build/GuanGeKai-B-Regular.ttf
7d10e4602313f3ca440953ed20f75e3a96f1428d96c8c4c75e17e23857f1498a  build/GuanGeKai-B-Real.ttf
543f20bae9bbe511394d2f0c8edee78e5ec4898eddaffd9a28d61dee4dc98062  GuanGeKai-B-v1.2.4.zip
```

历史版本（zip 由所有者手动清理，不主动删）：

```
df74d6b6ef741f04f3cb60669865f3eb5090915247b136fb893d1a9d23ad1f78  GuanGeKai-B-v1.2.4.zip（首次构建，README 改动前的内部产物）
d9da537640fbac12003ea2d1a13323cdda9187ff9f5bce49fb5e10095ff4b491  GuanGeKai-B-v1.2.2.zip
c7c27df64c7f1d4afa103bfea339a2cd1fac50234fe1498bd7effedc1f2e46b8  GuanGeKai-B-v1.2.0.zip
```

发布包内 `release-b/SHA256SUMS` 逐文件自校验。

**版本号口径（2026-10-30 所有者定）**：B 线按 **patch 递增**，公开序列 v1.2.2 → **v1.2.4**
（v1.2.3 未发布，直接跳过）；中间构建 **v1.3.0 / v1.3.1 编号作废、产物已清理**，
不对应任何发布说明，文档里不再引用。
三条线独立编号：A v1.7.2 / B v1.2.4 / C v1.2.0。

**字集口径（v1.2.4 起，见 GLOSSARY）**：

- `cmap` = CJK 基本区 **20,992** + 标点/数字/空格 **42** = **21,034**；唯一定义源 `scripts/punct_set.py`；
- 过滤在 **builder 层**（`57/62 --drop-outside-basic` 删掉 5 个扩展 A 字），所以 `Real ⊆ Regular` 成立；
- `-Real` 不含标点（只放真迹）；
- **`pairs.npz` 仍是 4,078 对的训练快照**（v1.2.2 生成），本轮不重训；下次重训时从 4,073 重建。

**v1.2.4 改了什么**：撤出 U+201C/U+201D（弯引号）——文楷的这两个字形只有 350/1000 em 宽，
与汉字并排会黏字；中文正文用已有的 `「」『』`。现为 20,992 + **42** = `cmap` **21,034**。

**重新描摹 vs 缓存（2026-10-30 实测，已知不一致）**：`57 --close 7 --hole-repair`（从 masks 重新描摹）
与 `57 --reuse-contours`（读 `real_contours.jsonl`）产出的 Real 字体**不是同一份字节**——

```
重新描摹： f82ea61a…  （178 个字各少一个冗余点）
读缓存：   7d10e460…  ← 发布用的就是这一份，可字节复现
渲染比对： 178 个差异字全部 Dice = 1.000（形状完全相同）
```

原因在轮廓序列化：缓存往返后，闭合处的重复点被保留成一个额外的 `lineTo`。
**发布链以缓存路径为准**（`--reuse-contours`），这样 `Real` 与 `Regular` 的同字轮廓一致；
重新描摹只用于确认缓存没有过期。根治办法是在 `fontbuild.build_font()` 里丢掉
"末点 == 起点" 的重复点（一行判断），下次发版可以做。

**可复现性（2026-10-30 实测）**：B 的构建链**是字节可复现的**。
`fontbuild.build_font()` 把 `head.created/modified` 钉到 `SOURCE_DATE_EPOCH`，
`13_extend_punct.py:113` 保存前 `base.recalcTimestamp = False`。
实测 62→extend 连跑两次产出同一哈希；`57` 连跑两次同样一致。

## 7. 复现步骤（与 v1.1.0 发布链逐条对应）

发布口径的唯一来源是 **`data/release-b.json`**（ckpt / 阈值 / 闭运算 / 修复开关 / 版本）。
下面每条命令的参数都取自它；改工作点必须同时改那个文件和本节。

```bash
# 0. 依赖：霞鹜文楷放 data/base/LXGWWenKai-Regular.ttf；史记 PDF 放仓库根目录
python3 scripts/53_build_reference_b.py            # 公版参考文本
python3 scripts/51_segment_b.py --workers 8        # 纠偏 + 切字（1672 页，约 19 分钟）
                                                   # 顺带写入 dewarp_fail/dewarp_res100
python3 scripts/52_ocr_b.py --workers 8            # OCR（纠偏后的图，约 10 分钟）
python3 scripts/54_label_b.py                      # 标注 + 对齐；无 OCR 行的格保留为 nolines

# 选优：优先避开纠偏超标页的样本（--prefer-clean），再做单次字准入
python3 scripts/05_select.py --work work-b --prefer-clean dewarp_fail
cp work-b/chosen.jsonl work-b/chosen_min2.jsonl     # 留存"仅 ≥2 样本"的版本
python3 scripts/58_add_singletons_b.py --work work-b --out work-b/chosen.jsonl
                                                   # 双见证准入：3,807 -> 4,078（v1.2.4 起再剔 5 个扩展 A → 4,073）

python3 scripts/06_norm.py --work work-b --pitch-floor 100
python3 scripts/57_build_real_b.py --close 7 --hole-repair
                                                   # 7px 闭运算 + 逐字升级修孔（首次构建）
# 之后只想改版本号/元数据时，用缓存轮廓重建，不重新描摹：
#   python3 scripts/57_build_real_b.py --reuse-contours
python3 scripts/24_build_singles.py --work work-b --pitch-floor 100
                                                   # 干净集（单次字，与训练集互斥）
python3 scripts/08_make_pairs.py --work work-b --out work-b/pairs/pairs.npz
python3 scripts/27_fit_width.py --work work-b      # 逐笔宽度分布（B 线自拟合）

python3 scripts/21_train_gan.py --data work-b/pairs/pairs.npz \
        --out work-b/ckpt/b.pt --ckpt-dir work-b/ckpt \
        --patchgan --hinge --aug --epochs 80 --batch 16 --save-every 10
                                                   # 每轮约 380 s，全程约 8.5 小时

python3 scripts/60_generate_b.py --method gan --ckpt work-b/ckpt/b_ep080.pt \
        --ckpt-hardtail work-b/ckpt/b_wt_ep090.pt \
        --threshold -0.10 --close 7 --workers 6 --res 512 --simplify 2.0 \
        --out work-b/generated.jsonl
                                                   # 16,919 字，约 25 分钟
python3 scripts/61_fill_fallback_b.py              # 兜底：60 漏掉的字用带状扫掠补齐

python3 scripts/62_build_full_b.py --drop-outside-basic   # 基本區 20,992（不帶 5 個扩展 A）
python3 scripts/13_extend_punct.py --line B --inplace      # 補 42 個標點 → cmap 21,034
python3 scripts/63_qa_b.py                         # 硬闸：覆盖率/空字形/真跡数/孔洞
python3 scripts/68_accept_b.py                     # 硬闸：字重比/回退占比/包围盒

# 图与包
python3 scripts/66_specimen_b.py
python3 scripts/69_panel_b.py --gan work-b/ckpt/b_ep080.pt --n 16
python3 scripts/72_book_vs_font_b.py
rm -rf release-b && python3 scripts/64_package_b.py
cd release-b && zip -q -r ../GuanGeKai-B-v1.1.0.zip . && cd ..

# 复核
python3 scripts/71_holes.py --font build/GuanGeKai-B-Regular.ttf --n 300
python3 scripts/73_selfaudit_b.py                  # 制品↔文档一致性
python3 scripts/67_verify_a.py                     # A 线未被波及
```

**改动过哪些默认值**（避免"按默认重跑 ≠ 发布产物"）：

| 脚本 | 默认 | 为什么 |
|---|---|---|
| `60_generate_b --threshold` | **−0.10** | 孔洞修复后的墨量 1.00 工作点；v1.0.x 是 −0.30 |
| `60_generate_b --close` / `--hole-repair` | **7 / 开** | 孔洞修复；v1.0.0 之前没有 |
| `69_panel_b --thr` | **−0.10** | 面板必须展示成品形态 |
| `05_select --prefer-clean` | 空（不启用） | B 线发布时传 `dewarp_fail`；默认关闭以保持 A 线行为 |
| `57_build_real_b --close` / `--hole-repair` | 0 / 关 | 传 `7 --hole-repair` 才是发布形态 |

