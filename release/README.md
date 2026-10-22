# 館閣楷 GuanGe Kai

> 一款以明代刻本《四書白文》為字形來源的**館閣體**開源字體。
> An open-source *guan-ge-ti* (館閣體, Ming court/office regular script) typeface built from the Ming woodblock print *四書白文*.

<p align="center">
  <img src="docs/images/specimen.png" width="820" alt="GuanGe Kai specimen">
</p>

> **狀態：v1.2.0（2026-10-22）** —— 20,992 字全覆蓋；其中 1,675 字為刻本真跡，19,317 字為程序化合成。
> 合成字結構正確、字重接近，但**沒有真正的刻刀筆鋒**。品質定位與已知限制見
> [docs/PROJECT_STATE.md](docs/PROJECT_STATE.md)，所有實驗與指標見
> [docs/EXPERIMENTS.md](docs/EXPERIMENTS.md)，資料與許可見 [docs/DATA.md](docs/DATA.md)。

## 這是什麼

《四書白文》（十八卷，舊傳明·姜立綱書，日本宮內廳書陵部藏，書格 shuge.org 數位化）是一部典型的
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
   ↓  缺失字：以霞鶩文楷為骨架 + 程序化筆墨濾波（豎粗橫細、加重、閉合）
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
| [docs/EXPERIMENTS.md](docs/EXPERIMENTS.md) | 想复現或質疑結論的人 | 7 組實驗的配置、指標、判定、复現命令 |
| [docs/DATA.md](docs/DATA.md) | 關心許可與來源的人 | 輸入/輸出清單、逐項許可、校驗和、重建步驟 |

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
python3 scripts/10_generate.py --method brush   # 生成缺失字（發布版走筆墨濾波）
python3 scripts/11_build_full.py       # 合成完整字體
python3 scripts/12_specimen.py         # 樣張
python3 scripts/13_qa.py               # 覆蓋率質檢
python3 scripts/14_package.py          # 發布包
```

> 訓練步驟（`08_make_pairs.py` → `09_train*.py`）**不是發布版必需**：三次自訓均未達標，
> 發布版用的是程序化筆墨濾波。複現實驗見 [docs/EXPERIMENTS.md](docs/EXPERIMENTS.md)。

原始 PDF 需放在倉庫根目錄，檔名為 `四书白文.18卷.旧传明.姜立纲.pdf`（版權原因**不入庫**）。
基線字體 `data/base/LXGWWenKai-Regular.ttf` 需自行從
[LXGW WenKai releases](https://github.com/lxgw/LxgwWenKai/releases) 下載（同樣不入庫）。

## 已知限制

* 生成字形（19,317 字）在結構上保證正確（骨骼來自基線字體），但筆鋒是**程序化筆墨濾波**
  的近似（僅縱向腐蝕 + 閉合），並非模型推斷，也非刻本刀鋒；與真實字形存在可感知差異。
  v1.2.0 起墨量（1.09）與豎橫比（1.18）已對齊刻本（1.00 / 1.17），不再偏重。
  用於正文小字時建議以真實字形子集為準。
* 掃描本只覆蓋《四書》用字（1,675 個校驗後字形），因此大部分現代常用字屬於生成字形。
* 尚未做 hinting；大字号、印刷級輸出請自行 outline。

## 授權

* 字體：SIL Open Font License 1.1，見 [OFL.txt](OFL.txt)。
  生成字形衍生自 [LXGW WenKai](https://github.com/lxgw/LxgwWenKai)（OFL 1.1，保留字體名
  「霞鹜/霞鶩/落霞孤鹜/落霞孤鶩/LXGW」），本項目已按 OFL 要求更名為 GuanGe Kai。
* 代碼：MIT。
* 掃描圖像：書格（shuge.org）整理，原書藏於日本宮內廳書陵部。字形是對公有領域 2D 作品的
  忠實再現；本項目不對掃描圖像本身主張權利。

## 致謝

* 書格 shuge.org、日本宮內廳書陵部 —— 掃描本
* [LXGW WenKai 霞鶩文楷](https://github.com/lxgw/LxgwWenKai) —— 缺失字的結構基線
* [qiji-font 齊伋體](https://github.com/LingDong-/qiji-font) —— 紅章去除、向量化與字身框置中的思路
* [RapidOCR / PP-OCR](https://github.com/RapidAI/RapidOCR) —— 逐頁轉錄
* [potrace](http://potrace.sourceforge.net/) / [fontTools](https://github.com/fonttools/fonttools)
