# GuanGe Kai v1.2.1

館閣楷 v1.2.1 — 三份独立审计后的修复发布。**字形无可见变化**，改动集中在代码正确性、许可声明与文档一致性。

## 相对 v1.2.0 的修复

- `glyphvec.contour_bounds` 改为解析求解三次曲线极点（与质检口径一致）
- `.notdef` 改为 TrueType 约定方向（外框顺时针、内框逆时针）
- `brush_lib.py` 删除死代码、修正顿笔增益方向（实验代码，不在发布路径）
- 新增 `LICENSE`（代码 MIT；字体仍为 OFL 1.1）
- `docs/index.html` 回退字体由系统专有字体改为思源宋体/Noto Serif CJK
- 文档：修正版本号错标、体积、清理命令、OCR 口径；`requirements.txt` 锁定版本

## 檔案

| 檔案 | 內容 | 大小 |
|---|---|---|
| `GuanGeKai-Regular.ttf` | 20,992 字 = 1,675 真跡 + 19,317 合成 | 20.0 MB |
| `GuanGeKai-Real.ttf` | 僅 1,675 真跡 | 3.1 MB |
| `OFL.txt` / `LICENSE` | 字體 OFL 1.1；代碼 MIT | |
| `provenance.json` / `coverage.txt` / `SHA256SUMS` | 逐字來源、覆蓋、校驗和 | |

## 校驗和

见包内 `SHA256SUMS`，或仓库 `docs/DATA.md §5`。

## 安裝

```bash
# macOS
cp GuanGeKai-Regular.ttf ~/Library/Fonts/
# Linux
cp GuanGeKai-Regular.ttf ~/.local/share/fonts/ && fc-cache -f
```

家族名 **GuanGe Kai**，PostScript 名 `GuanGeKai-Regular` / `GuanGeKai-Real`。

## 授權

字體：SIL OFL 1.1（衍生自 LXGW WenKai，已避開 RFN）。
代碼：MIT。
字形來源：《四書白文》（舊傳明·姜立綱書），原書藏日本宮內廳書陵部、由其圖書寮數位檔案掃描（檔號 1000066720000）；本項目使用的 PDF 由書格整理發布；原書公有領域。
