# GuanGe Kai B v1.2.5

> 状态：**已发布**（2026-11-15）。`release-b/` 与 `GuanGeKai-B-v1.2.5.zip` 均按 v1.2.5 生成。
> 三线版本：A **v1.7.3** / B **v1.2.5** / C **v1.4.0**。
> 字集口径不变：CJK 基本区 **20,992** + 标点/数字/空格 **42** = `cmap` **21,034**。

## 1. 本版变更（相对 v1.2.4）

**只动真迹字形，不动模型、不动工作点**：仍是 `b_ep080` + 硬尾 `b_wt_ep090`、thr −0.10、close 7。
合成字（GAN 15,784 + 硬尾 544 + ribbon 591）逐字节不变。

| # | 项 | 字数 | 内容 |
|---|---|---|---|
| 1 | **删除 `--hole-repair`** | 348 | 建真迹时不再按文楷的孔洞数逐级加密补孔。写本/抄本本来就不封口（`四`/`目`/`自`/`门` 在本书里都是开口），把文楷的孔洞数复制到成品上属于"按参照字体改字形" |
| 2 | **中缝压缩重采样** | 74（净新增 72，6 字与上一项重叠） | 装订中缝附近的列被横向压窄 10–33%；`squeeze`（该列墨迹宽高比 ÷ 该页中位）<0.90 的字，换到同字里最接近正常的样本 |
| 3 | **修错字** | 4 | `茈`（原为"此"）、`竅`（"敷"）、`簦`（"落"）、`唏`（"服"）。来源：同标签样本互相矛盾的检查 |

合计 **420 字变化**、**0 added / 0 removed**、墨量变化中位 **−5.5%**（范围 −21.7% ~ +25.5%）。

> 口径说明：`work-b/version_diff_b_124_125.json` 的 **348** 是"只删 `--hole-repair` 后"的中间态，
> 是 420 的子集；当前口径一律用 `work-b/diff_v124_v125.json` 的 **420**。

## 2. 质量卡（四层，n=300）

| 层 | 墨量/文楷 | 相对真迹 | 落在真迹 p5–p95 外 |
|---|---|---|---|
| real | 0.742 | 1.000 | 10%（定义） |
| gan | 0.818 | **+10.2%** | 16.3% |
| gan_ht | 0.780 | +5.2% | 7.3% |
| ribbon | 0.675 | **−9.0%** | 14.0% |

删掉补孔修复后真迹略轻，合成层的相对偏差由 +9.8% 变为 +10.2%（抽样噪声内）。

## 3. 交付物

```
build/GuanGeKai-B-Regular.ttf  544ce807…  21,034 码位  Version 1.2.5
build/GuanGeKai-B-Real.ttf     45d87eb0…   4,073 码位  Version 1.2.5
GuanGeKai-B-v1.2.5.zip         fce919e2…  14 MB（release-b/ 11 个文件，SHA256SUMS 自校验通过）
```

## 4. 门禁

```
63_qa_b     coverage 20992 / punct 42/42 / QA OK
68_accept   ACCEPTANCE OK（字体级 weight bias 1.088）
73          自身 OK；唯一 FAIL 是 A 线快照（A 已升 v1.7.3，预期，用 --allow 跳过）
83          A/B INTACT（B zip fce919e2… 已入基线）
97          TERMS OK
82 版本闸   420 changed / 0 added / 0 removed，与声明集一致
```

## 5. 已知缺陷（不随本版修复）

- **5 个错字**：`哲`（格里是"字"）、`怕`（"常"）、`怡`（"譽"）、`汎`（"泥"）、`銕`（"長"）。
  这些字的样本池没有干净替代（其余样本被邻字污染或超框），需回原书重切，成本高于收益。
- **标签证据**：47.6% 的真迹只有单 OCR 见证（参考文本只在 52.4% 的页面上有效）。
  PP-OCRv5 第二见证与现有标签一致率 81.1%，高置信分歧 110 个，其中 29 个是异体/简繁。
- **合成层字重**：gan +10.2%、ribbon −9.0%（相对真迹），未做逐字墨量标定。
- **中缝压窄**：39 个字无合格替代，按原样出货（已逐个确认）。

## 6. 复现

```bash
python3 scripts/57_build_real_b.py --close 7 --drop-outside-basic   # 无 --hole-repair
python3 scripts/62_build_full_b.py --drop-outside-basic
python3 scripts/13_extend_punct.py --line B --inplace
python3 scripts/63_qa_b.py && python3 scripts/68_accept_b.py
python3 scripts/82_version_diff_b.py --old work-b/v124_backup/GuanGeKai-B-Regular.ttf \
        --new build/GuanGeKai-B-Regular.ttf        # 期望 420 changed
```
