# 館閣楷 GuanGe Kai

> 一款以明代刻本《四書白文》為字形來源的**館閣體**開源字體。
> An open-source *guan-ge-ti* (館閣體, Ming court/office regular script) typeface built from the Ming woodblock print *四書白文*.

<p align="center">
  <img src="docs/images/specimen.png" width="820" alt="GuanGe Kai specimen">
</p>

> **狀態：v1.3.5（2026-10-23）** —— 20,992 字全覆蓋；其中 1,675 字為刻本真跡，19,317 字為程序化合成。
> 合成字的筆畫骨架取自霞鶩文楷，結構與其一致（拓撲相同率 97%），但**沒有真正的刻刀筆鋒**；
> 與刻本真跡的拓撲一致率約 47%，這部分差異繼承自基線字體。品質定位與已知限制見
> [docs/PROJECT_STATE.md](docs/PROJECT_STATE.md)，所有實驗與指標見
> [docs/EXPERIMENTS.md](docs/EXPERIMENTS.md)，資料與許可見 [docs/DATA.md](docs/DATA.md)。

## 這是什麼

《四書白文》（十八卷，舊傳明·姜立綱書，原藏日本宮內廳書陵部（圖書寮數位檔案 shoryobu.kunaicho.go.jp，檔號 1000066720000））是一部典型的
**館閣體**刻本：結體方正、筆畫豐腴、橫細豎粗、起收分明。本項目把它變成一套可安裝、可再分發的
CJK 字體：

| 項目 | 內容 |
| --- | --- |
| 家族名 | GuanGe Kai（館閣楷） |
| 覆蓋 | CJK 基本區 U+4E00–U+9FFF，共 **20,992** 字 |
| 格式 | TTF（glyf，UPM 1000） |
| 授權 | SIL Open Font License 1.1 |
| 真實字形 | **1,675** 字直接取自掃描本（向量化；僅保留書中出現 ≥2 次、可做同字聚類校驗的字） |
| 生成字形 | **19,317** 字由程序化筆墨合成補齊（缺失字） |

字體分兩級發布：

* **GuanGeKai-Real** —— 只含掃描本真實字形（1,675 字），可視為「原刻字形集」。
* **GuanGeKai** —— 完整 20,992 字，其餘由 19,317 個生成字形補齊。

原刻本（左）與本字體排印相同文字（右）：

<p align="center">
  <img src="docs/images/book-vs-font.png" width="520" alt="book vs font">
</p>

## 字形來源與方法

```
PDF 掃描 (410 頁)
   ↓  去紅圈點 / 去框線 / 糾偏 / 網格與連通域分割
54,000+ 個單字切片
   ↓  PP-OCR 逐欄轉錄 + 《四書》標準文本對齊 + 同字聚類投票
2,300 個字的標註（保留 1,675 個可交叉校驗的字）
   ↓  potrace 向量化 / 基線與字身框歸一化
GuanGeKai-Real
   ↓  缺失字：霞鶩文楷骨架 → 帶狀掃掠（斜切端頭 + 逐筆墨量波動）
19,317 個生成字形 → 向量化
   ↓  合併、構建 OpenType
GuanGeKai (20,992 字)
```

細節見 [docs/method.md](docs/method.md)。

## 文檔索引

| 文檔 | 給誰看 | 內容 |
|---|---|---|
| [docs/method.md](docs/method.md) | 想懂技術路線的人 | 從掃描到字體的完整流程與參數 |
| [docs/PROJECT_STATE.md](docs/PROJECT_STATE.md) | **接手的 agent / 審計者** | 現狀、決策、已知缺陷、未決問題、審計方法 |
| [docs/EXPERIMENTS.md](docs/EXPERIMENTS.md) | 想复現或質疑結論的人 | 21 組實驗（E1–E21）的配置、指標、判定、复現命令 |
| [docs/DATA.md](docs/DATA.md) | 關心許可與來源的人 | 輸入/輸出清單、逐項許可、校驗和、重建步驟 |
| [docs/RELEASE-v1.3.5.md](docs/RELEASE-v1.3.5.md) | 想了解本版改了什麼的人 | v1.3.5 的變更、檔案、校驗和、已知限制 |
| [docs/PLAN-v1.4.md](docs/PLAN-v1.4.md) | 想知道下一步的人 | v1.4.0 起三線並行的分工、產物命名與評估口徑 |
| [docs/REPORTS/](docs/REPORTS/) | 想看實測數據的人 | 每次橫向評測的完整報告（指標表 + 兩個面板） |

## 安裝

```bash
# macOS
cp build/GuanGeKai-Regular.ttf ~/Library/Fonts/
# Linux
cp build/GuanGeKai-Regular.ttf ~/.local/share/fonts/ && fc-cache -f
```

## 從源碼重建

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python3 scripts/01_segment.py          # PDF -> 單字切片 (約 4 分鐘, 12 進程)
python3 scripts/02_ocr.py              # 逐頁 PP-OCR
python3 scripts/03_build_reference.py  # 生成《四書》標準文本
python3 scripts/04_label.py            # 切片 -> 字
python3 scripts/05_select.py           # 每字挑最優樣本（默認剔除僅出現 1 次的字）
python3 scripts/06_norm.py             # 字身框歸一化參數
python3 scripts/07_build_real.py       # 真實字形子集字體
python3 scripts/10_generate.py --method ribbon  # 生成缺失字（發布版：帶狀掃掠）
python3 scripts/11_build_full.py       # 合成完整字體
python3 scripts/12_specimen.py         # 樣張
python3 scripts/13_qa.py               # 覆蓋率質檢
python3 scripts/14_package.py          # 發布包
```

> 訓練步驟（`08_make_pairs.py` → `09_train*.py`）**不是發布版必需**：自訓 U-Net、
> zi2zi 系列均未達標，發布版用的是**帶狀掃掠渲染**（`render_ribbon`）。
> 複現實驗見 [docs/EXPERIMENTS.md](docs/EXPERIMENTS.md)。

原始 PDF 需放在倉庫根目錄，檔名為 `四书白文.18卷.旧传明.姜立纲.pdf`（版權原因**不入庫**）。
基線字體 `data/base/LXGWWenKai-Regular.ttf` 需自行從
[LXGW WenKai releases](https://github.com/lxgw/LxgwWenKai/releases) 下載（同樣不入庫）。

## 已知限制

* 生成字形（19,317 字）的骨架與拓撲來自基線字體（與其 97% 一致），筆形由**帶狀掃掠**
  （斜切端頭 + 逐筆墨量擾動 + 沿程 taper）程序化生成，並非模型推斷，也非刻本刀鋒；
  墨量與真跡基本持平（字體級 1.009，同口徑），端帽形狀 KS 0.063（掩膜級），是目前最接近刻本的方案。
  用於正文小字時建議以真實字形子集為準。
* 掃描本只覆蓋《四書》用字（1,675 個校驗後字形），因此大部分現代常用字屬於生成字形。
* 尚未做 hinting；大字号、印刷級輸出請自行 outline。

## 授權

* 字體：SIL Open Font License 1.1，見 [OFL.txt](OFL.txt)。
  生成字形衍生自 [LXGW WenKai](https://github.com/lxgw/LxgwWenKai)（OFL 1.1，保留字體名
  「霞鹜/霞鶩/落霞孤鹜/落霞孤鶩/LXGW」），本項目已按 OFL 要求更名為 GuanGe Kai。
* 代碼（`scripts/`）：MIT（見 `LICENSE`）。
* 掃描圖像：原書藏於日本宮內廳書陵部，數位化由其圖書寮數位檔案完成
  （檔號 1000066720000）；本項目使用的 PDF 為書格（shuge.org）整理發布的版本。
  字形是對公有領域 2D 作品的忠實再現，本項目不對掃描圖像本身主張權利。

## 致謝

本項目的字形品質來自「別人的字」遠多於我們的代碼。以下按用途分類，
**每一項都說明我們用了它的什麼或受了它什麼啟發**。

### 緣起：最早的三個參考

本項目最早的技術路線，是照著這三個項目定下來的（都只看流程，沒有複製代碼/數據）：

* **[qiji-font 齊伋體](https://github.com/LingDong-/qiji-font)** —— 「刻本掃描 → 切字 → OCR → 字體」的完整流程樣板，
  我們的分頁、切格、OCR 校驗、字形歸一化都受它啟發
* **[Image-to-font-extractor](https://github.com/wyattmattoe/Image-to-font-extractor)**（MIT）——
  「字形圖 → SVG → 可安裝 TTF」的最小可行路徑，確立了我們「先出字體、再談風格」的順序
* **[FontForge](https://github.com/fontforge/fontforge) / [fontTools](https://github.com/fonttools/fonttools)** ——
  字體組裝工具；最終實現全部走 fontTools（FontForge 僅作流程參考）

### 數據與掃描

* **日本宮內廳書陵部（圖書寮數位檔案）** —— 原書藏本與**數位化掃描**（檔號 1000066720000）
* **書格 shuge.org** —— 將該掃描整理成可下載的 PDF（**掃描並非書格製作**）
* 說明：本 PDF 已被去色（實測 `r−g` 最大僅 11–14，無紅色像素），原書的**紅色圈點**在我們這份檔案裡
  已變成深灰，故顏色分離無效，實際用「厚度 + 連通域」判據剔除（`scripts/pageproc.py`）。
  若使用未去色的掃描，`red_mask()` 仍可直接生效。

### 字體（OFL）

* **[LXGW WenKai 霞鶩文楷](https://github.com/lxgw/LxgwWenKai)** —— 19,317 個缺失字的**結構骨架**；
  本字體是它的衍生作品，已按 OFL 要求避開保留字體名
* **Noto Serif SC / 思源宋體** —— 作為「內容字形」輸入（zi2zi 系列實驗）與對照基準

### 工具

* [FontTools](https://github.com/fonttools/fonttools) —— 字體組裝（UPM、name 表、cmap、輪廓寫入）
* [potrace](http://potrace.sourceforge.net/) / [potracer](https://pypi.org/project/potracer/) —— 點陣轉向量
* [OpenCV](https://opencv.org/)、[NumPy](https://numpy.org/)、[SciPy](https://scipy.org/)、
  [scikit-image](https://scikit-image.org/)、[Pillow](https://python-pillow.org/) —— 影像處理
* [RapidOCR / PP-OCR](https://github.com/RapidAI/RapidOCR) —— 逐頁轉錄（OCR）
* [PyMuPDF](https://pymupdf.readthedocs.io/) —— PDF 渲染與頁面處理

### 參考項目與思想

* **[kaonashi-tyc/zi2zi](https://github.com/kaonashi-tyc/zi2zi)**（Apache-2.0）——
  路線 B 的配方來源：U-Net + 全局判別器 + `L1×100 + 對抗 + 常量損失`，由我們獨立重寫為
  `scripts/21_train_gan.py`，未使用其任何權重
* **[kaonashi-tyc/zi2zi-JiT](https://github.com/kaonashi-tyc/zi2zi-JiT)**（代碼 MIT）——
  路線 C 的架構；**其預訓練權重沒有許可聲明**（LICENSE 僅寫 "MIT License (Software)"），
  故本項目只將其輸出作為**評價參考**，從未進入發布字體
* **[computer-grass](https://github.com/LingDong-/computer-grass)** —— 逐筆墨量擾動 `dip`
  與「針狀收筆」的思路；其字形數據的授權與 OFL 不兼容，**未使用**
