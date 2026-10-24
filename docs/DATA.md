# 数据、许可与校验和

> 本文件回答三个问题：**每个文件从哪来、能不能用、怎么复现**。
> 所有体积为 2026-10-23 实测。

---

## 1. 输入数据

| 文件 | 体积 | 来源 | 许可 | 是否入库 |
|---|---|---|---|---|
| `四书白文.18卷.旧传明.姜立纲.pdf` | 1.1 GB | 原本藏日本宫内厅书陵部，数字化由其图书寮数字档案完成（档号 1000066720000）；本项目用的 PDF 由书格 shuge.org 整理发布（**扫描非书格所制**） | 原书为公有领域；扫描方未主张额外权利，但**发布前应向书格确认条款** | ❌ 不入库 |
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
- **扫描本**：字形是对公有领域二维作品的忠实再现，本项目未对扫描图像主张权利；
  README 已分别署名「宫内厅书陵部（藏本与数字化）」与「书格（整理发布）」。
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

## 5. 校验和

> 体积单位为十进制 MB（1 MB = 10⁶ 字节），与 Finder 显示一致。


```
b48fe367e20904690774ebc01322046c8c2087c45aa595fbb19de54f263c3e81  build/GuanGeKai-Regular.ttf
2c690b15a431ca41ba4cc50c826be4b6c99d237ace4981d756ade8ce07e50505  build/GuanGeKai-Real.ttf
373fab7e5a8ea17220c5f6b1108b55feaf9fa73b06bc9edbc440771d3e4db291  GuanGeKai-v1.3.5.zip
```

`release/SHA256SUMS` 是发布包的逐文件校验和（重新打包会变）。

---

## 5.5 评估工具

| 脚本 | 用途 |
|---|---|
| `scripts/18_eval.py` | 指标库（Dice / 端帽剖面 / 墨量）与留出集评估 |
| `scripts/22_eval_gan.py` | 单一模型（GAN 检查点）指标 |
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
python3 scripts/10_generate.py --method ribbon --workers 12 --res 512 --simplify 2.0 \
        --out work/generated.jsonl    # 合成缺字（512 渲染+矢量化，轮廓简化 2/1000 em）
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

**训练检查点不删。** 一次 40 轮的训练要 6 小时，删掉等于把这 6 小时扔了。

- `work/zi2zi_gan.pt`（ep150，单实例基线）、`work/zi2zi_gan_multi.pt`（多实例 + PatchGAN）长期保留；
- 每次训练在 `work/ckpt/` 下留 `*_epNNN.pt`（每 5 轮）与 `*_best.pt`（验证集最好）；
- `work/ckpt/MANIFEST.json` 由 `python3 scripts/31_ckpt_manifest.py` 从磁盘重建
  （训练会**覆盖同名文件**，手写清单必然失配）；删除任何一项前先看它；
- 若确实需要腾空间，先确认发布包里已有等价结果，并在本文件记录删了什么、为什么。

历史教训：2026-10-23 清理时删掉了 LoRA-600 与 JiT 权重，之后想复用只能重训。

## 6.5 已清理的大体积过程文件（2026-10-23）

为控制仓库体积，以下目录已删除，**均可用仓库内脚本重建**：

| 已删除 | 原大小 | 重建方式 | 重建耗时 |
|---|---|---|---|
| `work/cells/`、`work/masks/` | 2.1 GB | `python3 scripts/01_segment.py` | 约 5 分钟 |
| 6 份历史 `work/generated_*.jsonl`（只留当前 `generated.jsonl`） | 2.2 GB | `10_generate.py --method ribbon --res 512 --simplify 2.0` | 各约 5 分钟 |
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

这些文件只存在于磁盘，**均未被 git 跟踪**（`.gitignore` 已覆盖），删掉不影响发布或复现：

| 路径 | 体积 | 说明 |
|---|---|---|
| `data/fonts_target/GuangeKai-Real.ttf` | 3.2 MB | 旧拼写残留，与 `build/` 重复 |
| `data/ids/Unihan_IRGSources.txt` | 13 MB | 该版本不含 kIDS，从未使用 |
| `data/zi2zi_ds/`、`data/zi2zi_ds2/` | 140 MB | zi2zi 实验数据集，可由脚本重建 |
| `data/base/cg/ComputerGrassRegular.ttf` | 55 MB | Arphic PL，仅评估用 |

清理：

```bash
rm -rf data/fonts_target data/ids/Unihan_IRGSources.txt data/zi2zi_ds data/zi2zi_ds2
rm -rf data/base/cg/ComputerGrassRegular.ttf data/base/cg/cg.zip
```

> 目前 git 跟踪的 75 个文件中最大的只有 `data/ids/ids.txt`（2.1 MB）与两张对照图（各 2 MB）；
> 字体二进制与发布包均不入库，改由 GitHub Releases 分发（见 README「发布」）。
> 旧版此处曾建议 `git rm --cached` 一批文件，那些文件已在 2026-10-22 的清理中移出索引，**该命令现已无需执行**。
