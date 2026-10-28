# GuanGe Kai v1.6.0（含 GuanGe Kai B v1.0.0）

> 本版把项目从「一本书」变成「两本书、两套字体」。
> **A = 四书白文（GuanGe Kai v1.6.0）· B = 史记抄本（GuanGe Kai B v1.0.0）**

## 两条线

| | A · 四书白文 | B · 史记抄本 |
|---|---|---|
| 字体 | `GuanGeKai-Regular.ttf` / `-Real.ttf` | `GuanGeKai-B-Regular.ttf` / `-B-Real.ttf` |
| 家族名 | GuanGe Kai | GuanGe Kai B |
| 版本 | **1.6.0** | **1.0.0** |
| 真迹 | 1,675 | 见 `README-B.md` |
| 合成 | GAN 17,484 + ribbon 回退 1,833 | 见 `README-B.md` |

两套字体独立训练、独立评估，**互不复用字形**；四条评估纪律（真迹参照、干净集、五项同报、
否证记录）对两条线同样适用。

## A 线这一版改了什么

**字形重新由源码构建**（v1.5.2 之后 `real_contours.jsonl` 曾被实验污染，本版已用发布设置重生成）：

| 项 | 变化 |
|---|---|
| `fontbuild._orient` | 嵌套判定由「控制点」改为「曲线采样 + 多点投票」。控制多边形会自交，导致孔环被判为外轮廓 |
| `glyphvec.trace` | `turdsize` 默认 8 → **2**，小孔不再被当斑点丢弃 |
| `10_generate` / `36_fill_fallback` | ribbon 回退的墨量口径补上分辨率归一 `comp256 = wm.sum()*(256/S)²`，修掉回退字偏轻 ~15% |
| `21_train_gan` | valDice 的 `[:8]` 硬编码改为自适应 |
| `31_ckpt_manifest` | 每条检查点加 `kind`（final/best/core/snapshot），落实保留规则 |
| `07_build_real` | 新增可选 `--carve-holes`（实验，默认关闭） |

## 已知限制（必须读）

1. **孔洞缺陷（P0，未修）**：`四/国/目/自/年/見/具` 等常用字在发布字体里以实心形态出现。
   分层抽样 A 403 字仅 54% 孔数与基线字体一致（15.6% 偏少，10 字全无孔）。
   三层根因已定位：① 掩膜里孔与外部连通（真迹源图即如此）；② 绕向判定（本版已修）；
   ③ 小孔在 1000 upm 下不足 2 单位，`Cu2Qu` 后塌成一点。
   **本版无法修复**，修法需要 450–600 dpi 重渲染全链路重跑。
2. 合成字比真迹重约 17%（5–7% 是字集构成，约 5% 来自模型输出字面偏小，E34/E37）。
3. 骨架 chamfer 5.92 px vs 真迹互比地板 5.16 px。
4. 未做 hinting。

## 檔案

A：`GuanGeKai-Regular.ttf`、`GuanGeKai-Real.ttf`、`provenance.json`（三态）、`stats.json`、
`SHA256SUMS`、`OFL.txt`、`LICENSE`、`coverage.txt`、`specimen.png`、`book-vs-font.png`

B：见 `GuanGeKai-B-v1.0.0.zip` 与 `README-B.md`
