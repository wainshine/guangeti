# GuanGe Kai B v1.2.4

> **字集口径更正**：撤出两个弯引号码位，`cmap` 21,034 = 基本区 20,992 + 标点/数字/空格 42。
> 模型、工作点、生成字全部未动；真迹仍是 4,073。

随主版本 **GuanGeKai v1.7.2** 发布。A = 四书精写本（`GuanGe Kai`）、
B = 史记明抄本（`GuanGe Kai B`，本包）、C = 永乐大典嘉靖内府录副本（`GuanGe Kai C`）。

## 1. 本版变更

| # | 项 | 内容 |
|---|---|---|
| 1 | **撤出弯引号** | 删除 U+201C/U+201D（`“ ”`）。文楷的这两个字形只有 350/1000 em 宽，与汉字并排会黏字；中文正文用的是已有的 `「」『』` |
| 1b | **剔除扩展 A** | 删掉 5 个基本区外的真迹字（`㓗㢮㯉䍧䳒`），`cmap` 不再有区外码位；真迹 4,078 → **4,073** |
| 2 | **口径统一** | 现为 **20,992 + 42 = cmap 21,034**。定义源由各线自己维护改为共享模块 `scripts/punct_set.py` |
| 3 | **不改** | 真迹 4,073、GAN 15,784、救回 544、回退 591（3.5%）逐字节不变；模型仍是 `b_ep080` + thr −0.10 + close 7 + hole-repair |

与上一个公开版 v1.2.2 相比：少了 5 个扩展 A 真迹字、多了 42 个标点/数字/空格码位；
**正文汉字一个字也没动**。中间构建 v1.3.0 / v1.3.1 未对外发布，编号作废、产物已清理（本线按 patch 递增）。

## 2. 交付物

| 文件 | 内容 | 大小 |
|---|---|---|
| `GuanGeKai-B-Regular.ttf` | `cmap` **21,034** = 20,992 + 42 | 15.43 MB |
| `GuanGeKai-B-Real.ttf` | 仅 **4,073** 真迹（不含标点） | 3.82 MB |
| `GuanGeKai-B-v1.2.4.zip` | 上述 + OFL + 覆盖表 + 逐字来源 + 校验和 | 14.3 MB |

字体名表版本串 `Version 1.2.4`；家族名、PostScript 名不变。

## 3. 实测

```
63_qa_b        coverage 20992/20992 · punct 42/42 · outside 42 · cmap 21034 · QA OK
68_accept_b    字重比 1.082 · 包围盒 1.031 · 回退 3.5% · ACCEPTANCE OK
              小字号 12/16/24/48px = 1.008 / 1.025 / 1.051 / 1.033
97_check_terms TERMS OK
83_verify_ab_c B 字集 21,034 = 20,992 + 42
```

`stats.json`：`codepoints 20992`（基本区口径）、`codepoints_total 21034`、`real 4073`、`glyphs 21035`（含 `.notdef`）；
`provenance.json` 21,034 条，其中 `punct` 42 条。

## 4. 已知限制

与 v1.2.2 相同：孔洞全丢 1.0%；标点取自文楷、与正文并排略轻；拉丁字母不补、由系统回退；
未做 hinting。新增一条：**弯引号 `“ ”` 现在由系统字体回退**，与 `「」『』` 并存时风格会不一致。

## 5. 校验和

```
aa19d6d2000d504af7123741fe9273bee157fee1f2915c570a9d05d27bab8f9d  build/GuanGeKai-B-Regular.ttf
7d10e4602313f3ca440953ed20f75e3a96f1428d96c8c4c75e17e23857f1498a  build/GuanGeKai-B-Real.ttf
543f20bae9bbe511394d2f0c8edee78e5ec4898eddaffd9a28d61dee4dc98062  GuanGeKai-B-v1.2.4.zip
```

包内 `release-b/SHA256SUMS` 逐文件自校验。

## 6. 复现

```bash
python3 scripts/57_build_real_b.py --reuse-contours --drop-outside-basic   # 4,073
python3 scripts/62_build_full_b.py --drop-outside-basic                   # 基本区 20,992
python3 scripts/13_extend_punct.py --line B --inplace                     # cmap 21,034
python3 scripts/63_qa_b.py && python3 scripts/68_accept_b.py
rm -rf release-b && python3 scripts/64_package_b.py
```

**可复现**：上面的命令连跑两次产出完全相同的字节
（实测 `7db260a6…` / `7db260a6…`，`4e80d782…` / `4e80d782…`）。
`fontbuild.build_font()` 与 `13_extend_punct.py` 都已固定时间戳。
