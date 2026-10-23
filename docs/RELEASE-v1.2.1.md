# GuanGe Kai v1.2.1

> **状态：历史版本说明（superseded by v1.3.3）** —— 当前发布说明见 `README.md` 与 `docs/PROJECT_STATE.md` §14。



馆阁楷 v1.2.1 — 三份独立审计后的修复发布。**字形无可见变化**，改动集中在代码正确性、许可声明与文档一致性。

## 相对 v1.2.0 的修复

- `glyphvec.contour_bounds` 改为解析求解三次曲线极点（与质检口径一致）
- `.notdef` 改为 TrueType 约定方向（外框顺时针、内框逆时针）
- `brush_lib.py` 删除死代码、修正顿笔增益方向（实验代码，不在发布路径）
- 新增 `LICENSE`（代码 MIT；字体仍为 OFL 1.1）
- `docs/index.html` 回退字体由系统专有字体改为思源宋体/Noto Serif CJK
- 文档：修正版本号错标、体积、清理命令、OCR 口径；`requirements.txt` 锁定版本

## 档案

| 档案 | 内容 | 大小 |
|---|---|---|
| `GuanGeKai-Regular.ttf` | 20,992 字 = 1,675 真迹 + 19,317 合成 | 20.0 MB |
| `GuanGeKai-Real.ttf` | 仅 1,675 真迹 | 3.1 MB |
| `OFL.txt` / `LICENSE` | 字体 OFL 1.1；代码 MIT | |
| `provenance.json` / `coverage.txt` / `SHA256SUMS` | 逐字来源、覆盖、校验和 | |

## 校验和

见包内 `SHA256SUMS`，或仓库 `docs/DATA.md §5`。

## 安装

```bash
# macOS
cp GuanGeKai-Regular.ttf ~/Library/Fonts/
# Linux
cp GuanGeKai-Regular.ttf ~/.local/share/fonts/ && fc-cache -f
```

家族名 **GuanGe Kai**，PostScript 名 `GuanGeKai-Regular` / `GuanGeKai-Real`。

## 授权

字体：SIL OFL 1.1（衍生自 LXGW WenKai，已避开 RFN）。
代码：MIT。
字形来源：《四书白文》（旧传明·姜立纲书），原书藏日本宫内厅书陵部、由其图书寮数位档案扫描（档号 1000066720000）；本项目使用的 PDF 由书格整理发布；原书公有领域。
