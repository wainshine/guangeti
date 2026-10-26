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

抄本是墨笔手抄，通行本是刻本系统，二者必然有差异。处理原则：

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

## 5.9 `head.fontRevision`

TrueType 的 `fontRevision` 是 **16.16 定点数**。本版（v1.1.0）由共用库按
`major + minor/10 + patch/100 = 1 + 1/10 + 0 = 1.1` 写入；定点量化后实测
`1.1000061035`，与 name 表 `Version 1.1.0` 对应。

注意：v1.0.1 时它是截断的 `1.0`（共用库旧行为，审计 3-3）；v1.1.0 起与 name 表一致。
A 线的 v1.6.2 同一公式给出 `1.62`（实测 `1.6199951`）。

## 6. 校验和（v1.1.0）

```
886ecf25f449c6f160fe6856aad55cf9a6db70a5d329b8cd7d96fdefd988febf  build/GuanGeKai-B-Regular.ttf
3009c3a0b5d7937b3aa89034ac7e14a04a73f9aa308b0f16fff639aaa84f6e07  build/GuanGeKai-B-Real.ttf
bd78f57adee6c91cce0b305c84c8c1b959c278d354da8aff4ec23d3424043e62  GuanGeKai-B-v1.1.0.zip
```

发布包内 `release-b/SHA256SUMS` 逐文件自校验。字体构建把时间戳钉死
（`SOURCE_DATE_EPOCH`），同一份输入可复现字节一致的 TTF。

> 复验 A 线未被波及：`python3 scripts/67_verify_a.py` 必须打印 `A LINE INTACT`
> 判据已改为**跟随 `release/SHA256SUMS`**（A 每次发版自动更新）；`v1.5.2` 的哈希只作历史兜底。
> 脚本还会单独列出 `build/` 与 `release/` 的对照，用来判断"A 是否已重建但尚未重新打包"。

### 6.5 B 线检查点（`work-b/ckpt/`）

| 文件 | 说明 |
|---|---|
| `b_ep010.pt` … `b_ep080.pt` | 每 10 轮快照，各 ≈400 MB；**ep080 是发版检查点**（干净集 Dice 0.532 / chamfer 5.57 / capKS 0.016），ep050/060 是对照 |
| `b_best.pt` | 按训练内 valDice 选出的“最佳”。**已核对：内容与 `b_ep010.pt` 逐张量相同**（最后一次写入在 ep10，valDice 0.603）。它**不是发版检查点**——发版用 ep50，由干净集 Dice/chamfer 决定；打包脚本走路径参数，不会误读它 |
| `b.pt` | 每轮覆盖写的最新权重（停在 ep51 的训练中断点） |
| `b_split.json` | 按**字**划分的训练/验证清单 |

`MANIFEST.json` 由 `python3 scripts/31_ckpt_manifest.py --ckpt-dir work-b/ckpt` 从磁盘重建，
记录每个文件的体积、mtime 与 sha256 前 16 位。**每次续训/覆盖/删除检查点后必须重跑**——
四书线在这件事上漏过三次（AGENTS.md 有记录），B 线从第一天就制度化。

合计约 2.8 GB。按 A 线的保留规则（最终一轮 + 验证最佳 + 核心轮次 50/100/…），
`b_ep080` 必须保留（发版检查点），`b_ep050`/`b_ep060` 是决策证据；`ep010–040` 是平台证据。
磁盘充足，**均暂未清理**。若将来续训到 100+ 轮，按同一规则保留 100/150/… 即可。

## 7. 复现步骤

```bash
# 0. 下载霞鹜文楷到 data/base/LXGWWenKai-Regular.ttf；把史记 PDF 放在仓库根目录
python3 scripts/53_build_reference_b.py          # 参考文本
python3 scripts/51_segment_b.py --workers 8      # 纠偏 + 切字（1672 页，约 20 分钟）
python3 scripts/52_ocr_b.py --workers 8          # OCR（纠偏后的图，约 15 分钟）
python3 scripts/54_label_b.py                    # 标注 + 对齐率
python3 scripts/05_select.py --work work-b       # 每字选优
python3 scripts/06_norm.py   --work work-b --pitch-floor 100
python3 scripts/57_build_real_b.py               # build/GuanGeKai-B-Real.ttf
python3 scripts/24_build_singles.py --work work-b --pitch-floor 100   # 干净集
python3 scripts/08_make_pairs.py --work work-b   # 训练配对
python3 scripts/27_fit_width.py --work work-b    # 逐笔宽度分布（B 线自拟合）
python3 scripts/21_train_gan.py --data work-b/pairs/pairs.npz \
        --out work-b/ckpt/b.pt --ckpt-dir work-b/ckpt \
        --patchgan --hinge --aug --epochs 80
python3 scripts/60_generate_b.py --method gan --workers 6 --res 512 --simplify 2.0 \
        --ckpt work-b/ckpt/b_ep080.pt --out work-b/generated_gan.jsonl
python3 scripts/61_fill_fallback_b.py && mv work-b/generated_gan.jsonl work-b/generated.jsonl
python3 scripts/62_build_full_b.py               # build/GuanGeKai-B-Regular.ttf
python3 scripts/63_qa_b.py && python3 scripts/64_package_b.py
```
