# GuanGe Kai B v1.3.0

> 随主版本 **GuanGeKai v1.7.1** 发布。同一项目、三个字形来源：
> A = 四书精写本《四書白文》（`GuanGe Kai`，v1.7.1）、
> B = 史记明抄本（`GuanGe Kai B`，本包 v1.3.0）、
> C = 永乐大典嘉靖内府录副本（`GuanGe Kai C`）。

---

## 1. 一句话

**补上标点/数字/空格，并把字集口径收紧到 20,992。**
模型、工作点、生成字全部未动；真迹只少了 5 个基本区外的字。

## 2. 本版变更

| # | 项 | 内容 |
|---|---|---|
| 1 | **字集口径** | 删掉 5 个**扩展 A** 真迹字（`㓗㢮㯉䍧䳒`），`cmap` 不再有区外码位。真迹 **4,078 → 4,073** |
| 2 | **补标点** | 新增 **44 码位**：空格（U+0020 / U+3000）、半角数字 0–9、全角数字 ０–９、中文标点 22 个（`、。，；：？！「」『』（）《》〈〉—…·""''`）。`cmap` **20,992 → 21,036** |
| 3 | **来源** | 标点字形取自霞鹜文楷（OFL 1.1，未用保留名），upm 同为 1000，**1:1 复制不缩放**（与 A 线同口径） |
| 4 | **不改** | 合成字 16,919（GAN 15,784 + 救回 544 + 回退 591）**逐字节不变**；模型仍是 `b_ep080` + thr −0.10 + close 7 + hole-repair |
| 5 | **删在哪一层** | `57/62` 新增 `--drop-outside-basic`，在**构建阶段**过滤，所以 `Real ⊆ Regular` 成立（不是事后删 cmap） |

**为什么不重训**：删的 5 个字在字体里走真迹、从不经过 GAN；`pairs.npz` 仍是 4,078 对的
v1.2.2 训练快照，下次重训时再从 4,073 重建。

## 3. 交付物

| 文件 | 内容 | 大小 |
|---|---|---|
| `GuanGeKai-B-Regular.ttf` | `cmap` **21,036** = 基本区 20,992 + 标点 44 | **15.43 MB** |
| `GuanGeKai-B-Real.ttf` | 仅 **4,073** 真迹（不含标点） | **3.82 MB** |
| `GuanGeKai-B-v1.3.0.zip` | 上述 + OFL + 覆盖表 + 逐字来源 + 校验和 | **14.3 MB** |

字体名表版本串 `Version 1.3.0`；家族名、PostScript 名不变。

## 4. 实测

```
63_qa_b        coverage 20992/20992 · real-subset 4073 OK · QA OK
68_accept_b    字重比 1.082 · 包围盒 1.031 · 回退 3.5% · ACCEPTANCE OK
             小字号 12/16/24/48px = 1.008 / 1.025 / 1.051 / 1.033
71_holes       lost 0.5%（300 抽样）· 白名单 0 失孔
83_verify_ab_c A/B INTACT（B 三处断言已从 4,078 改为 4,073）
97_check_terms TERMS OK
标注检查       空格 / 全角空格 / 半角数字 / 、 / 。 / ， / 《  7/7 命中
```

`stats.json`：`codepoints 20992`、`real 4073`、`real_ext_a 0`、`glyphs 21037`。

## 5. 已知限制

与 v1.2.2 相同，另加一条：

1. **孔洞**：全字集完全丢孔 1.0%（300 抽样 0.5%），少孔 12.2%。
2. **困难字的 GAN 输出仍不如主体**：544 个救回字是模型最吃力的一档，但仍优于 ribbon。
3. **标点与数字取自文楷，不是馆阁体笔意**：1:1 不缩放；与正文并排时字重略轻。
   B 线的正文比 A 线细，所以这点在 B 上比在 A 上更明显（见 `docs/PLAN-PUNCT.md` §7.5）。
   拉丁字母不补，由系统回退。
4. chamfer 5.60 相对真迹地板 3.57 差 57%（150 dpi 扫描的结构性天花板）。
5. 未做 hinting。

## 6. 校验和

```
5e229d2f10144afda6a822df1fafcb108706d98f480f46814bf072987d5e6ec1  build/GuanGeKai-B-Regular.ttf
1d25dfa5fe43fd45b51cc9d50208e3305df1dc8c187699524051b05d4bf12db0  build/GuanGeKai-B-Real.ttf
ec5d492bc5ac1b378f3fa3f9024eb452504178b7056d4c149f61ba7758f1641b  GuanGeKai-B-v1.3.0.zip
```

包内 `release-b/SHA256SUMS` 逐文件自校验。

## 7. 复现

```bash
python3 scripts/57_build_real_b.py --reuse-contours --drop-outside-basic   # 4,073
python3 scripts/62_build_full_b.py --drop-outside-basic                   # 基本区 20,992
python3 scripts/13_extend_punct.py --line B --inplace                     # cmap 21,036
python3 scripts/63_qa_b.py && python3 scripts/68_accept_b.py
rm -rf release-b && python3 scripts/64_package_b.py
```

工作点未变，见 `data/release-b.json`。
