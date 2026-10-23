# GuanGe Kai v1.2.0

館閣楷 v1.2.0 — 以明代刻本《四書白文》為字形來源的館閣體開源字體，覆蓋 CJK 基本區全部 20,992 字。

## 本版變更（相對 v1.1.0）

**修正合成字整體過重、對比度過高的問題。**

合成字（19,317 個）的筆墨濾波由 `橫向膨脹 5×1 + 縱向腐蝕 1×3` 改為**僅縱向腐蝕 1×3**。

| 指標（120 個留出真字） | 真字 | 霞鶩文楷 | v1.1.0 | **v1.2.0** |
|---|---|---|---|---|
| 墨量（相對真字） | 1.00 | 1.20 | 1.26 | **1.09** |
| 豎橫比 | 1.17 | 1.08 | 1.50 | **1.18** |

原因：霞鶩文楷的墨量已是刻本的 1.20 倍，舊參數在此基礎上繼續加粗，導致「又黑又平」。

真字（1,675 個）輪廓**逐點未變**；覆蓋率、結構、許可均不變。

## 檔案

| 檔案 | 內容 | 大小 |
|---|---|---|
| `GuanGeKai-Regular.ttf` | 20,992 字 = 1,675 真跡 + 19,317 合成 | 20.5 MB |
| `GuanGeKai-Real.ttf` | 僅 1,675 真跡（原刻字形集） | 3.1 MB |
| `OFL.txt` | SIL Open Font License 1.1 | |
| `provenance.json` | 逐字來源（real / gen） | |
| `coverage.txt` | 覆蓋清單 | |
| `specimen.png` / `book-vs-font.png` | 樣張與對照 | |
| `SHA256SUMS` | 校驗和 | |

## 校驗和

```
844440e565326670e4dbd7496cf39bd33f43eb8caeb629205f3a61e0c73846e8  GuanGeKai-Regular.ttf
7119d68665d7ffefa99ba040d693cbd042960d7a05250936ccbf706463bc7459  GuanGeKai-Real.ttf
```

## 安裝

```bash
# macOS
cp GuanGeKai-Regular.ttf ~/Library/Fonts/
# Linux
cp GuanGeKai-Regular.ttf ~/.local/share/fonts/ && fc-cache -f
# Windows：右鍵 → 安裝
```

字體家族名 **GuanGe Kai**，PostScript 名 `GuanGeKai-Regular` / `GuanGeKai-Real`。
UPM 1000，TTF（glyf），基線 0，字面 0–880。

## 已知限制

- 19,317 個合成字結構正確（骨架來自霞鶩文楷），但**沒有刻刀的角狀收筆**；
  墨量與豎橫比已對齊刻本，筆鋒仍是程序化近似。
- 僅覆蓋 U+4E00–U+9FFF，不含標點、拉丁、擴展區。
- 無 hinting，小字號依賴系統 autohinter。
- 建議正文小字使用 `GuanGeKai-Real`（僅真跡字形）。

## 授權

SIL Open Font License 1.1。衍生自 LXGW WenKai（OFL，含 Reserved Font Name），
本項目已按要求更名為 `GuanGe Kai`，不含任何 RFN。

字形來源：《四書白文》十八卷（舊傳明·姜立綱書），日本宮內廳書陵部藏，
原書藏日本宮內廳書陵部，數位化由其圖書寮數位檔案完成（檔號 1000066720000）；本項目使用的 PDF 由書格整理發布。原書為公有領域；本項目未對掃描圖像主張權利。

專案首頁：https://github.com/wainshine/guangeti
