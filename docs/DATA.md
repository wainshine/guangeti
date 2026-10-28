# 数据、许可与校验和

> 本文件回答三个问题：**每个文件从哪来、能不能用、怎么复现**。
> 所有体积为 2026-10-23 实测。

---

## 1. 输入数据

| 文件 | 体积 | 来源 | 许可 | 是否入库 |
|---|---|---|---|---|
| `四书白文.18卷.旧传明.姜立纲.pdf` | 1.1 GB | **明代精写本（手书墨迹，非刻本）**； 原本藏日本宫内厅书陵部，数字化由其图书寮数字档案完成（档号 1000066720000）；本项目用的 PDF 由书格 shuge.org 整理发布（**扫描非书格所制**） | 原书为公有领域；**书格仅为分享渠道，非权利主体**（向其确认没有授权效力）；扫描件为公版作品的忠实再现，主流法域不认为是独创性作品 | ❌ 不入库 | <!-- term-ok -->
| `史记.二十四册.传姜立纲抄本.新加坡国立大学藏.水印.pdf` | 1.4 GB | 新加坡国立大学藏本（用户提供） | 同上，**未使用** | ❌ 不入库 |
| `data/base/LXGWWenKai-Regular.ttf` | 25 MB | [LXGW WenKai v1.530](https://github.com/lxgw/LxgwWenKai/releases) | **OFL 1.1，含 Reserved Font Name**（霞鹜/霞鶩/落霞孤鹜/落霞孤鶩/LXGW） | ❌ 不入库（可自行下载） |
| `data/base/NotoSerifSC-Light.otf` | 23 MB | [noto-cjk](https://github.com/notofonts/noto-cjk) | OFL 1.1，无 RFN | ❌ 不入库 |
| `data/base/SourceHanSansCN-Regular.otf` | 8 MB | [adobe-fonts/source-han-sans](https://github.com/adobe-fonts/source-han-sans)（SubsetOTF/CN） | OFL 1.1，无 RFN | ❌ 不入库（仅骨架选型实验用） |
| `data/base/cg/ComputerGrassRegular.ttf` | 55 MB | [computer-grass](https://github.com/LingDong-/computer-grass) release | **Arphic Public License**（随包 `ARPHICPL.TXT`） | 仅评估用；`ARPHICPL.TXT` 入库 |
| `data/ids/ids.txt` | 2.1 MB | [cjkvi-ids](https://github.com/cjkvi/cjkvi-ids)（基于 CHISE IDS） | **仓库未提供顶层 LICENSE**（CHISE 系历史许可），仅用于 E4 实验、**未进入发布字体** | ⚠️ 若发布仓库需完全干净，建议移出（见 §7） |
| `data/ids/Unihan_IRGSources.txt` | 13 MB | Unicode UCD | Unicode License v3（宽松） | ❌ 未跟踪（该版本不含 kIDS，从未使用） |
| `data/canonical/{daxue,zhongyong,mengzi,lunyu}.json` | 180 KB | [chinese-poetry](https://github.com/chinese-poetry/chinese-poetry)（论语来自 lihuibng fork） | MIT | ✅ 入库 |
| `data/vendor/zi2zi-JiT/` | 93 MB | [zi2zi-JiT](https://github.com/kaonashi-tyc/zi2zi-JiT) | 代码 MIT；**权重许可未声明** | 有本地 MPS 补丁，见 §4 |

---

## 2. 生成物（`work/`，全部不入库）

| 文件/目录 | 体积 | 内容 |
|---|---|---|
| `work/cells/` + `work/masks/` | 1.9 GB | 54,109 个单字灰度裁剪 + 对应二值掩膜 |
| `work/cells.jsonl` | 12 MB | 每格元数据（页/栏/行/bbox/slot/pitch/ink） |
| `work/ocr_pages.jsonl` | 1.2 MB | 逐页 PP-OCRv6 结果 |
| `work/labeled.jsonl` | 18 MB | 每格 → 字标签（含 OCR/标准文本/一致性） |
| `work/chosen.jsonl` | 1 MB | 每字一个最佳样本（1,675 条） |
| `work/norm.json` | 337 KB | 字面框归一化仿射参数 |
| `work/real_contours.jsonl` | 57 MB | 真字轮廓（字体单位） |
| `work/generated.jsonl` | 311 MB | 合成字轮廓（19,317 条） |
| `work/gen_masks.npy` | 640 KB（最新一次 field 运行的掩膜缓存） | 合成用 256² 掩膜缓存 |
| `work/pairs/pairs.npz` | 29 MB | 风格迁移训练配对 |
| `work/align_report.json` | 9.4 KB | 每页 OCR↔标准文本匹配率 |
| `work/qa/` | 43 MB | 覆盖检查表（21 张 contact sheet） |
| `work/preview/` | 135 MB | 调试/对照图（部分用于文档） |

---

## 3. 字体许可审计

- **字体本身**：`build/*.ttf` 的 `name` 表 ID 13 = SIL OFL 1.1 全文，ID 14 = 许可 URL，ID 0 = 版权声明（含 LXGW 与 Klee 的版权行）。
- **衍生关系**：合成字由霞鹜文楷（OFL，含 RFN）派生 → 本体必须 OFL，且**不得使用 RFN**。已更名：
  - Family：`GuanGe Kai`（不含「霞鹜/霞鶩/落霞孤鹜/落霞孤鶩/LXGW」）
  - PostScript：`GuanGeKai-Regular` / `GuanGeKai-Real`
- **扫描本**：原书（明代写本）为公有领域；扫描件是公版二维作品的**忠实再现**，
  按 *Bridgeman v. Corel*（1999）与国内对纯复制性扫描的独创性门槛，不构成新作品；
  **本项目**也未对扫描图像主张权利。README 已分别署名
  「宫内厅书陵部（藏本与数字化）」与「书格（整理发布）」。
- **字体是加工产物**：字形经切分、去噪、矢量化、参数化重绘，不是扫描件的复制，
  底层书法字形本身公有领域。
- **未混入的 copyleft 数据**：未使用 MakeMeAHanzi `graphics.txt`（Arphic PL）、未使用 computer-grass 字形、未使用 AR PL UKai。IDS 数据仅用于 E4 实验，**未进入发布字体**。
- **模型权重**：zi2zi-JiT 权重来自作者 Google Drive，其许可未在仓库声明；当前**仅用于实验**，发布字体未包含其输出。若要采用其输出，需先确认权重许可。

---

## 4. `data/vendor/zi2zi-JiT` 的本地补丁（重要）

为在 Apple Silicon 上跑通，对上游克隆做了以下修改（**均不在上游**，重新克隆后需重打）：

| 文件 | 修改 |
|---|---|
| `util/model_util.py` | 硬编码 `.cuda()` → 设备无关（MPS/CPU） |
| `model_jit.py` | `attn_bias` 使用 `query.device` |
| `engine_jit.py` | `torch.cuda.synchronize()` → `_sync()` 设备无关；数组 `.cuda()` → `.to(device)` |
| `main_jit.py` | EMA 参数 `.cuda()` → `.to(device)` |
| `util/misc.py` | `.cuda()` → `.to(device)` |
| `lora_single_gpu_finetune_jit.py` | tensorboard 缺失时用 no-op `SummaryWriter` |

另需 `--num_workers 0`（macOS spawn 无法 pickle 局部 lambda）。

---

## 4.5 发布包内容（`release/` 与 zip）

`release/` 由 `14_package.py` 生成，共 11 个文件：

| 文件 | 说明 |
|---|---|
| `GuanGeKai-Regular.ttf` / `GuanGeKai-Real.ttf` | 完整版 / 真迹子集 |
| `OFL.txt` / `LICENSE` | 字体与代码许可 |
| `README.md` | 根 README 的副本（**改 README 后必须重打包**） |
| `provenance.json` | 逐字 real/gen |
| `coverage.txt` | 覆盖码位清单 |
| `stats.json` / `SHA256SUMS` | 统计与自校验 |
| `specimen.png` | 字体样张（`12_specimen.py` 可重建） |
| `book-vs-font.png` | **静态图**：左为原书页面，右为同段文字用本字体排版。图中所排皆为真迹字，故不随版本变化；左图取自彩色扫描，无法由本仓库重建 |

> 分析用的对比面板（`docs/images/eval-panel*.png`）**不进发布包**，只留在仓库里。

## 4.9 已知 drift（2026-10-28）

- 发布包 `release/README.md` 与 `release/specimen.png` 是 **v1.6.5 发布时的快照**，图上与文内仍写「刻本」； <!-- term-ok -->
  仓库文档已更正为「写本」。**不重新发版**，详见 `docs/ERRATA.md` E3/E4。
- 已发布字体 `build/GuanGeKai-Regular.ttf` 的 name 表 ID 0 仍为 `Ming woodblock print`； <!-- term-ok -->
  源字符串已在 `scripts/11_build_full.py` 改为 `Ming manuscript`，**下一版重建时生效**（ERRATA E2）。

## 5. 校验和

> 体积单位为十进制 MB（1 MB = 10⁶ 字节），与 Finder 显示一致。


```
6dfd79d6a1f16cc850fe2095ce72a595939f4735433edec31a7bf27606c86a37  build/GuanGeKai-Regular.ttf
453d14661745ef2e24c14fdd9e625b36d29cceedae78abcd346154973d7e56f2  build/GuanGeKai-Real.ttf
c28f20404593ab302c84d93b90bdc9b6564d8bd1460ef2f0fcd5b7cb9e0b5db6  GuanGeKai-v1.5.0.zip
5c4c59fa62e089fd7225fc2c19ee008a8bf08ab30f67034e0bfbe5492d926dfe  GuanGeKai-v1.5.1.zip
c998d6df4bce9506a94744ce8147908c0336635083c03f50ebc99f03fcbfc3c6  GuanGeKai-v1.5.2.zip

B 线（史记本，v1.0.1）：

```
b76cfc016e1094c8b3299298b52802abb9f8322495b72b6ba38272f984492cec  build/GuanGeKai-B-Regular.ttf
79aadc231a3bef0b3ddfc14205448aeb705aae8b53ae00b296bcbb426a3d35be  build/GuanGeKai-B-Real.ttf
f95b5e7fb736e48ed232d16e9f05baab12920a25eb996924fc6898ba0e1f02f1  GuanGeKai-B-v1.0.1.zip
```

`release-b/SHA256SUMS` 是 B 线发布包的逐文件校验和，已验证通过；B 线的数据与实验记录见 `docs/DATA-B.md` 与 `docs/EXPERIMENTS-B.md`。

```

`release/SHA256SUMS` 是发布包的逐文件校验和（重新打包会变）。

---

## 5.5 评估工具

| 脚本 | 用途 |
|---|---|
| `scripts/18_eval.py` | 指标库（Dice / 端帽剖面 / 墨量）与留出集评估 |
| `scripts/22_eval_gan.py` | 单一模型（GAN 检查点）指标 |
| `scripts/29_gate_eval.py` | 拓扑闸门复测 → `work/gate_eval.json` |
| `scripts/30_gate_rules.py` | 9 种候选闸门判据对比 → `work/gate_rules.json` |
| `scripts/31_ckpt_manifest.py` | 从磁盘重建检查点清单 |
| `scripts/32_eval_clean.py` | **617 干净集标准评估**（泛化结论只认这个） |
| `scripts/33_struct_metrics.py` | 维度化结构指标（重心/宽高比/横画角 KS） |
| `scripts/34_struct_score.py` | 分级骨架度量（chamfer/端点/交叉点） |
| `scripts/35_threshold_sweep.py` | 推理阈值扫描 + 崩坏率 |
| `scripts/36_fill_fallback.py` | 补齐 GAN 守卫回退的字（ribbon 轮廓） |
| `scripts/23_compare_all.py --set work/eval_clean3.json --n 120` | **全方案横向对比**，同时生成面板 A/B |
| `scripts/24_build_singles.py` | 构建 617 个「只出现一次」字的测试集 |
| `scripts/25_eval_singles.py` | 在该测试集上评估 ribbon / GAN / 文楷 |
| `scripts/26_bench.py --classes A,B,C` | **三类基准**（见过 / 没见过 / 书中没有），所有方案同一规则 |
| `scripts/27_fit_width.py` | 从全部真字（45,042 条笔画）重拟合逐笔宽度分布 |

留出集有三档，按用途选用：

| 文件 | 字数 | 用途 |
|---|---|---|
| `data/eval_set.json` | 200 | 分层留出（按自由端数），评测的总体抽样框 |
| `work/eval_clean3.json` | 120 | 模型训练时未见的全部字，**主力评估集** |
| `work/eval_clean2.json` | 91 | 同时不在 LoRA 训练集内，用于与 JiT 对比 |
| `work/pairs_single.npz` | 617 | **只出现一次、从未参与训练**的字，独立外部测试集 |

## 6. 重建步骤

```bash
# 0. 准备（不入库的大文件）
#    - 把 PDF 放在仓库根目录
#    - 下载 LXGW WenKai 到 data/base/LXGWWenKai-Regular.ttf
#    - （可选，zi2zi 实验）Noto Serif SC Light 到 data/base/

python3 scripts/03_build_reference.py   # 生成标准文本
python3 scripts/01_segment.py           # 切字 + 掩膜（~4.5 min）
python3 scripts/02_ocr.py               # 逐页 OCR（~4 min）
python3 scripts/04_label.py             # 标注
python3 scripts/05_select.py            # 每字选优
python3 scripts/06_norm.py              # 归一化参数
python3 scripts/07_build_real.py        # 真字子集字体
# v1.5.0 起合成走 GAN（守卫回退 ribbon）：
python3 scripts/10_generate.py --method gan --workers 6 --res 512 --simplify 2.0 \
        --out work/generated_gan.jsonl
python3 scripts/36_fill_fallback.py            # 补齐守卫回退的字（ribbon 轮廓）
mv work/generated_gan.jsonl work/generated.jsonl
# 旧方法（v1.3.x）：
# python3 scripts/10_generate.py --method ribbon --workers 6 --res 512 --simplify 2.0
python3 scripts/11_build_full.py        # 合成完整字体
python3 scripts/12_specimen.py          # 样张
python3 scripts/13_qa.py                # 覆盖率质检
python3 scripts/14_package.py           # 发布包
```

预期总耗时（M3 Ultra）：约 15 分钟。产物与本文档 §2 一致。

**已知局限**：中间产物（`work/*.jsonl`、`work/masks/`）没有校验和链，只保证"同一份 PDF +
同一版霞鹜文楷 + 锁定版本依赖"下可复现；`release/SHA256SUMS` 只覆盖最终发布文件。
若需逐字级追溯，用 `release/provenance.json`（每字 real/gen）与 `work/chosen.jsonl`
（每字取自哪一页、哪一栏、哪一格）。

---

### 6.5.1 检查点保留规则

**训练检查点是有价值的产物，默认不删**；但已退役路线的中间轮次可以清，
只要保住「最佳 + 最后一轮」两个对比锚点。

- `work/zi2zi_gan.pt`（ep150 单实例基线）、`work/ckpt/m2_*`（v1.5.0 来源）长期保留全部；
- 每次训练在 `work/ckpt/` 下留 `*_epNNN.pt`（每 5 轮）与 `*_best.pt`（验证集最好）；
- **删除动作的最后一步永远是重跑 `31_ckpt_manifest.py`**（已三次出现"清单与磁盘不同步"）。
- **保留规则（2026-10-25 修订，所有者决定）**：
  - 训练时**每 10 轮存一个快照**（`--save-every 10`，已设为默认）；
  - 清理时保留三类：**最终一轮**、**验证最佳一轮**、**核心轮次（50/100/150/200/300/400/500…）**；
    其余中间轮次可删。核心轮次是将来换配置重训时的对照锚点；
  - **正在推进的路线**（当前 `m2_*`）在推进期间保留全部；
- `work/ckpt/MANIFEST.json` 由 `python3 scripts/31_ckpt_manifest.py` 从磁盘重建
  （训练会**覆盖同名文件**，手写清单必然失配）；删除任何一项前先看它；
- 若确实需要腾空间，先确认发布包里已有等价结果，并在本文件记录删了什么、为什么。

**当前检查点分布（2026-10-25 19:30 核对）**：

| 线路 | 状态 | 快照 | 核心轮次 | 说明 |
|---|---|---|---|---|
| `m2`（v1.5.0/1.5.1 来源） | 推进中 | 010–080 每 10 轮共 8 个 + `best` | 050 ✓ | 按规则全留 |
| `m2e150`（E36，已否证） | 已退役 | 060（valDice 峰值）、150（最终） | 150 ✓ | **050 与 100 在规则生效前已删**，如需补做对照需重训 6.5 小时 |
| `attr_*`、`m1_blur05`、`zi2zi_gan_multi` | 已退役 | best + 最后一轮 | — | 归因/早期路线，够用 |

**已删除记录**：

| 时间 | 文件 | 大小 | 原因 |
|---|---|---|---|
| 2026-10-24 22:05 | `work/ckpt/zi2zi_gan_multi_g_best.pt` | 402 MB | 训练于坏数据集（`08b` 配对把 71% 的目标图映射成空白），valDice 恒为 0，模型不可用。所有者要求删除，避免日后误用；崩溃过程记录在 E23，不依赖该文件 |
| 2026-10-25 19:20 | 5 个与快照同 epoch 的重复主文件（`m2e150.pt`、`m2e150_best.pt`、`attr_multi_gD.pt`、`attr_single_patch.pt`、`m1_blur05.pt`） | 1.98 GB | 训练结束时另存的同名文件，与对应 `_epNNN.pt` 同为该 epoch，属重复。按「best + 最后一轮」规则保留快照文件，删除重复项 |
| 2026-10-25 18:50 | `m2e150` 的 13 个中间快照 | 5.2 GB | 加训 150 轮的实验结束（E36：与 80 轮完全持平，「欠训」假设被否证）。按规则留 valDice 峰值 `ep060` 与最后一轮 `ep150`（+ 训练结束时的 `m2e150.pt`），其余删除 |
| 2026-10-25 11:25 | `work/zi2zi_gan_multi_g.pt`、`work/zi2zi_gan_multi.pt`、`work/generated_simplified.jsonl` | 989 MB | 前者是坏数据集那轮的最终权重（E23，不可用）；中者与 `ckpt/zi2zi_gan_multi_ep040.pt` 同模型、属重复；后者与 `generated.jsonl` 内容完全相同（sha256 一致）。均在 §7 登记过 |
| 2026-10-25 11:10 | 15 个已退役路线的中间轮次（见下） | 5.85 GB | 按「最佳 + 最后一轮」规则精简：`zi2zi_gan_multi` ep005–035（保留 best=ep35、ep040）、`attr_multi_gD` ep005–015（保留 best=ep15、ep20）、`attr_single_patch` ep005–015（保留 best=ep15、ep20）、`m1_blur05` ep005/010（保留 best=ep5、ep15）。`m2_*` 全部保留（v1.5.0 来源，还会继续训） |

历史教训：2026-10-23 清理时删掉了 LoRA-600 与 JiT 权重，之后想复用只能重训。

## 6.5 已清理的大体积过程文件（2026-10-23）

为控制仓库体积，以下目录**当时**已删除，**均可用仓库内脚本重建**。
（部分后来又重建了，当前实际占用见 §7；下表是历史记录，不代表现在磁盘上没有。）

| 已删除 | 原大小 | 重建方式 | 重建耗时 |
|---|---|---|---|
| `work/cells/`、`work/masks/` | 2.1 GB | `python3 scripts/01_segment.py` | 约 5 分钟（**已重建，现占 2.1 GB**，见 §7） |
| 历史 `work/generated_*.jsonl`（只留当前 `generated.jsonl`） | 数百 MB | 重新生成见 §6 的命令 | ribbon 约 5 分钟；GAN 约 25 分钟（6 worker） |
| `work/gen_masks.npy` | 1.2 GB | 生成时自动重建 | — |
| 8 个历史 U-Net 检查点（保留 `style_unet.pt`、`style_dice.pt`） | 240 MB | `09_train*.py` | 各约 1 小时 |
| `data/scratch_test/`（1 epoch 试验） | 3.6 GB | `main_jit.py` | — |
| `data/models/`（JiT 预训练权重，许可不允许发布） | 2.4 GB | 上游 Google Drive 重新下载 | — |
| `data/lora_run/`、`data/lora_long/`（LoRA 检查点） | 1.5 GB | 重新训练 | 各约 1–1.5 小时 |
| `data/zi2zi_ds/`、`zi2zi_ds2` 训练集以外的 `zi2zi_glyphs/`、`zi2zi_out3/` | 180 MB | `generate_glyph_dataset.py` | — |
| `data/base/cg/`（computer-grass 字体，仅评估用） | 55 MB | 上游发布页 | — |
| `work/preview/`、`work/qa/` | 180 MB | 评测脚本自动生成 | — |

保留：两份 PDF、`build/`、`release/`、zip、`work/` 的索引与配对数据、GAN 检查点（B 线结果）。

> 两份 PDF 都**不要删**：`四书白文` 是本项目源数据；`史记` 是另一个（暂缓的）项目的源数据，
> 用户明确要求保留。它们都不入库（见 §1）。

## 7. 工作区残留（可删除，不影响复现）

这些文件只存在于磁盘，**均未被 git 跟踪**（`.gitignore` 已覆盖），删掉不影响发布或复现。
（2026-10-25 核对：下表已与磁盘实际状态对齐，原表里的一些文件早已删除。）

| 路径 | 现状 | 体积 | 说明 |
|---|---|---|---|
| `data/fonts_target/` | **已删除** | — | 旧拼写残留（Guange 拼写），与 `build/` 重复；2026-10-25 清掉 |
| `data/ids/Unihan_IRGSources.txt` | 存在 | 13 MB | 该版本不含 kIDS，从未使用 |
| `data/zi2zi_ds/` | **已删除** | — | zi2zi 实验数据集（可由脚本重建） |
| `data/zi2zi_ds2/` | 存在 | 33 MB | E5/E14 的配对数据集（train/test/inference.npz），`EXPERIMENTS.md` 复现命令引用；可由 `generate_font_dataset.py` 重建 |
| `data/base/cg/ComputerGrassRegular.ttf` | **已删除** | — | Arphic PL，仅评估用；目录只剩 `ARPHICPL.TXT`（许可证，保留） |
| `work/zi2zi_gan_multi_g.pt` | **已删除** | — | 坏数据集那轮的最终权重（E23），不可用 |
| `work/zi2zi_gan_multi.pt` | **已删除** | — | 与 `work/ckpt/zi2zi_gan_multi_ep040.pt` 同模型，去重 |
| `work/generated_simplified.jsonl` | **已删除** | — | 与 `work/generated.jsonl` 内容完全相同（sha256 一致） |
| `data/lora_test/` | **已删除** | — | 3 个 88 字节的空 tfevents，训练未真正启动，无信息量 |

### 7.1 实验证据图（**不要删**）

C 线（zi2zi-JiT / LoRA）的推理输出。**权重已删（2026-10-23），且上游许可禁止再分发，
这些 PNG 是 E5/E14/E17 结论唯一的可视化证据，删了无法重建。**
`23_compare_all.py` 与 `26_bench.py` 直接读其中几项来出对比面板。

| 路径 | 体积 | 用途 |
|---|---|---|
| `data/zi2zi_eval_zerob`、`lora40b`、`lora600b` | 7–11 MB | **面板 A 的 JiT 三行**（`23_compare_all.py` 读取） |
| `data/jit_zeroA`、`jit_l40A`、`jit_l600A` | 11–13 MB | A 组参考输出（`26_bench.py` 读取） |
| `data/jit_zeroC`、`jit_l40C`、`jit_l600C` | 11–13 MB | C 组参考输出（`26_bench.py` 读取） |
| `data/zi2zi_eval_base`、`cfg1.5`、`cfg4.0`、`lora`、`lora40` | 11–12 MB | cfg 扫描的样品（E14） |
| `data/zi2zi_out`、`zi2zi_out2`、`zi2zi_lora_out`、`zi2zi_lora_out26` | 14 MB / 0.7 MB ×3 | 早期零样本与 LoRA 的抽样输出 |

合计约 **180 MB**。价值密度低但不可再生，保留。

**仍占空间的残留**（均可重建，未删是因为下一版还要用）：

| 路径 | 体积 | 重建方式 | 重建耗时 |
|---|---|---|---|
| `work/cells/` | 1.9 GB | `04_label.py` + `05_select.py`（依赖 OCR 结果） | 约 20 分钟 |
| `work/masks/` | 212 MB | `07_build_real.py`（去掉 `--reuse-contours`） | 约 5 分钟 |
| `work/generated_gan.jsonl` | 359 MB | `10_generate.py --method gan` | 约 25 分钟（6 worker） |
| `work/generated_ribbon_v135.jsonl` | 176 MB | `10_generate.py --method ribbon` | 约 5 分钟 |
| `work/zi2zi_gan.pt` | 383 MB | 重训 150 轮 | 数小时；**B 线对照基准，不建议删** |

清理（只清确定不再需要的）：

```bash
rm -rf data/zi2zi_ds2 data/fonts_target data/ids/Unihan_IRGSources.txt
```

> 目前 git 跟踪的文件中最大的只有 `data/ids/ids.txt`（2.1 MB）与两张对照图（各 2 MB）；
> 字体二进制与发布包均不入库，改由 GitHub Releases 分发（见 README「发布」）。
> 旧版此处曾建议 `git rm --cached` 一批文件，那些文件已在 2026-10-22 的清理中移出索引，**该命令现已无需执行**。
57686b31c32c22761eb7a47398bf0726eb207dd384f4e8309ed14fd6a5e74cfd  GuanGeKai-v1.7.0.zip
