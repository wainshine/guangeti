# 数据、许可与校验和

> 本文件回答三个问题：**每个文件从哪来、能不能用、怎么复现**。
> 所有体积为 2026-10-22 实测。

---

## 1. 输入数据

| 文件 | 体积 | 来源 | 许可 | 是否入库 |
|---|---|---|---|---|
| `四书白文.18卷.旧传明.姜立纲.pdf` | 1.1 GB | 书格 shuge.org 数字化；原本藏日本宫内厅书陵部 | 原书为公有领域；扫描方未主张额外权利，但**发布前应向书格确认条款** | ❌ 不入库 |
| `史记.二十四册.传姜立纲抄本.新加坡国立大学藏.水印.pdf` | 1.4 GB | 新加坡国立大学藏本（用户提供） | 同上，**未使用** | ❌ 不入库 |
| `data/base/LXGWWenKai-Regular.ttf` | 25 MB | [LXGW WenKai v1.530](https://github.com/lxgw/LxgwWenKai/releases) | **OFL 1.1，含 Reserved Font Name**（霞鹜/霞鶩/落霞孤鹜/落霞孤鶩/LXGW） | ❌ 不入库（可自行下载） |
| `data/base/NotoSerifSC-Light.otf` | 23 MB | [noto-cjk](https://github.com/notofonts/noto-cjk) | OFL 1.1，无 RFN | ❌ 不入库 |
| `data/base/cg/ComputerGrassRegular.ttf` | 55 MB | [computer-grass](https://github.com/LingDong-/computer-grass) release | **Arphic Public License**（随包 `ARPHICPL.TXT`） | 仅评估用；`ARPHICPL.TXT` 入库 |
| `data/ids/ids.txt` | 2.1 MB | [cjkvi-ids](https://github.com/cjkvi/cjkvi-ids)（基于 CHISE IDS） | **仓库未提供顶层 LICENSE**（CHISE 系历史许可），仅用于 E4 实验、**未进入发布字体** | ⚠️ 若发布仓库需完全干净，建议移出（见 §7） |
| `data/ids/Unihan_IRGSources.txt` | 13 MB | Unicode UCD | Unicode License v3（宽松） | ⚠️ 当前入库（该版本**不含 kIDS**，实际没用上，可删） |
| `data/canonical/{daxue,zhongyong,mengzi,lunyu}.json` | 180 KB | [chinese-poetry](https://github.com/chinese-poetry/chinese-poetry)（论语来自 lihuibng fork） | MIT | ✅ 入库 |
| `data/vendor/zi2zi-JiT/` | 93 MB | [zi2zi-JiT](https://github.com/kaonashi-tyc/zi2zi-JiT) | 代码 MIT；**权重许可未声明** | 有本地 MPS 补丁，见 §4 |

---

## 2. 生成物（`work/`，全部不入库）

| 文件/目录 | 体积 | 内容 |
|---|---|---|
| `work/cells/` + `work/masks/` | 1.9 GB | 54,109 个单字灰度裁剪 + 对应二值掩膜 |
| `work/cells.jsonl` | 23 MB | 每格元数据（页/栏/行/bbox/slot/pitch/ink） |
| `work/ocr_pages.jsonl` | 6 MB | 逐页 PP-OCRv6 结果 |
| `work/labeled.jsonl` | 25 MB | 每格 → 字标签（含 OCR/标准文本/一致性） |
| `work/chosen.jsonl` | 1 MB | 每字一个最佳样本（1,675 条） |
| `work/norm.json` | 472 KB | 字面框归一化仿射参数 |
| `work/real_contours.jsonl` | 57 MB | 真字轮廓（字体单位） |
| `work/generated.jsonl` | 240 MB | 合成字轮廓（19,317 条） |
| `work/gen_masks.npy` | 1.2 GB | 合成用 256² 掩膜缓存 |
| `work/pairs/pairs.npz` | 3 MB | 风格迁移训练配对 |
| `work/align_report.json` | 20 KB | 每页 OCR↔标准文本匹配率 |
| `work/qa/` | 39 MB | 覆盖检查表（21 张 contact sheet） |
| `work/preview/` | 132 MB | 调试/对照图（部分用于文档） |

---

## 3. 字体许可审计

- **字体本身**：`build/*.ttf` 的 `name` 表 ID 13 = SIL OFL 1.1 全文，ID 14 = 许可 URL，ID 0 = 版权声明（含 LXGW 与 Klee 的版权行）。
- **衍生关系**：合成字由霞鹜文楷（OFL，含 RFN）派生 → 本体必须 OFL，且**不得使用 RFN**。已更名：
  - Family：`GuanGe Kai`（不含「霞鹜/霞鶩/落霞孤鹜/落霞孤鶩/LXGW」）
  - PostScript：`GuanGeKai-Regular` / `GuanGeKai-Real`
- **扫描本**：字形是对公有领域二维作品的忠实再现，本项目未对扫描图像主张权利；README 已署名书格与宫内厅。
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

## 5. 校验和

```
55e16c025e1468e0de5b72fae9394367a95809859ae499f6d26bb2060f6c6778  build/GuanGeKai-Regular.ttf
32c9d657fd6b2833b156be235e379439f9c35cd660ab620b8ed159769d5cf16a  build/GuanGeKai-Real.ttf
ac12d2ad43ed8346cf08b0c5117951ad7d40b68762ee12bd559038f8eac57547  GuanGeKai-v1.1.0.zip
```

`release/SHA256SUMS` 是发布包的逐文件校验和（重新打包会变）。

---

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
python3 scripts/10_generate.py --method brush   # 合成缺字
python3 scripts/11_build_full.py        # 合成完整字体
python3 scripts/12_specimen.py          # 样张
python3 scripts/13_qa.py                # 覆盖率质检
python3 scripts/14_package.py           # 发布包
```

预期总耗时（M3 Ultra）：约 15 分钟。产物与本文档 §2 一致。

---

## 7. 建议的清理（交给仓库维护者决定）

当前 git 里跟踪了几个体积较大、且可由脚本重建的文件：

| 文件 | 体积 | 建议 |
|---|---|---|
| `data/ids/Unihan_IRGSources.txt` | 13 MB | 删除（该版本无 kIDS，未使用） |
| `data/ids/ids.txt` | 2.1 MB | 保留或改由脚本下载（许可待确认） |
| `data/zi2zi_ds/test.npz` | 12 MB | 删除（实验中间产物） |
| `data/zi2zi_ds2/inference.npz` | 4.5 MB | 删除（可由 `scripts/zi2zi_make_npz.py` 重建） |
| `data/fonts_target/GuangeKai-Real.ttf` | 3.1 MB | 旧名残留（与 `build/` 重复），**建议 `git rm`** |
| `data/base/cg/ARPHICPL.TXT` | 6.7 KB | 可保留（评估记录） |
| `GuanGeKai-v1.1.0.zip` | 17 MB | 已在版本库中；发布包属构建产物，建议 `git rm --cached`，改由 GitHub Releases 发布 |

一键清理（由仓库维护者执行，agent 不代跑）：

```bash
git rm --cached data/ids/Unihan_IRGSources.txt \
                  GuanGeKai-v1.1.0.zip \
                  data/zi2zi_ds/test.npz \
                  data/zi2zi_ds2/inference.npz \
                  data/zi2zi_ds2/test.npz \
                  data/fonts_target/GuangeKai-Real.ttf
git commit -m "chore: drop large intermediate files (see docs/DATA.md §7)"
```

> `.gitignore` 里已加 `/*.zip`，但对**已被跟踪**的文件无效——需要先 `git rm --cached`。
> `data/fonts_target/GuangeKai-Real.ttf` 是旧拼写的残留（与 `build/GuanGeKai-Real.ttf` 重复），
> 文件名只差大小写，在 macOS 上删除时勿用 `GuangeKai-*` 通配符（会误删新文件）。
