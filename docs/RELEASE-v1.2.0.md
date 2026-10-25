# GuanGe Kai v1.2.0

> **状态：历史版本说明（superseded by v1.3.3）** —— 当前发布说明见 `README.md` 与 `docs/PROJECT_STATE.md` §12（最新版本变更）与 `docs/RELEASE-v1.5.0.md`。



馆阁楷 v1.2.0 — 以明代刻本《四书白文》为字形来源的馆阁体开源字体，覆盖 CJK 基本区全部 20,992 字。

## 本版变更（相对 v1.1.0）

**修正合成字整体过重、对比度过高的问题。**

合成字（19,317 个）的笔墨滤波由 `横向膨胀 5×1 + 纵向腐蚀 1×3` 改为**仅纵向腐蚀 1×3**。

| 指标（120 个留出真字） | 真字 | 霞鹜文楷 | v1.1.0 | **v1.2.0** |
|---|---|---|---|---|
| 墨量（相对真字） | 1.00 | 1.20 | 1.26 | **1.09** |
| 竖横比 | 1.17 | 1.08 | 1.50 | **1.18** |

原因：霞鹜文楷的墨量已是刻本的 1.20 倍，旧参数在此基础上继续加粗，导致「又黑又平」。

真字（1,675 个）轮廓**逐点未变**；覆盖率、结构、许可均不变。

## 档案

| 档案 | 内容 | 大小 |
|---|---|---|
| `GuanGeKai-Regular.ttf` | 20,992 字 = 1,675 真迹 + 19,317 合成 | 20.5 MB |
| `GuanGeKai-Real.ttf` | 仅 1,675 真迹（原刻字形集） | 3.1 MB |
| `OFL.txt` | SIL Open Font License 1.1 | |
| `provenance.json` | 逐字来源（real / gen） | |
| `coverage.txt` | 覆盖清单 | |
| `specimen.png` / `book-vs-font.png` | 样张与对照 | |
| `SHA256SUMS` | 校验和 | |

## 校验和

```
844440e565326670e4dbd7496cf39bd33f43eb8caeb629205f3a61e0c73846e8  GuanGeKai-Regular.ttf
7119d68665d7ffefa99ba040d693cbd042960d7a05250936ccbf706463bc7459  GuanGeKai-Real.ttf
```

## 安装

```bash
# macOS
cp GuanGeKai-Regular.ttf ~/Library/Fonts/
# Linux
cp GuanGeKai-Regular.ttf ~/.local/share/fonts/ && fc-cache -f
# Windows：右键 → 安装
```

字体家族名 **GuanGe Kai**，PostScript 名 `GuanGeKai-Regular` / `GuanGeKai-Real`。
UPM 1000，TTF（glyf），基线 0，字面 0–880。

## 已知限制

- 19,317 个合成字结构正确（骨架来自霞鹜文楷），但**没有刻刀的角状收笔**；
  墨量与竖横比已对齐刻本，笔锋仍是程序化近似。
- 仅覆盖 U+4E00–U+9FFF，不含标点、拉丁、扩展区。
- 无 hinting，小字号依赖系统 autohinter。
- 建议正文小字使用 `GuanGeKai-Real`（仅真迹字形）。

## 授权

SIL Open Font License 1.1。衍生自 LXGW WenKai（OFL，含 Reserved Font Name），
本项目已按要求更名为 `GuanGe Kai`，不含任何 RFN。

字形来源：《四书白文》十八卷（旧传明·姜立纲书），日本宫内厅书陵部藏，
原书藏日本宫内厅书陵部，数位化由其图书寮数位档案完成（档号 1000066720000）；本项目使用的 PDF 由书格整理发布。原书为公有领域；本项目未对扫描图像主张权利。

专案首页：https://github.com/wainshine/guangeti
