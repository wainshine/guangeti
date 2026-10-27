# GuanGe Kai v1.6.5（A 四书）

> **字形与 v1.6.4 相同。** 本版是修复轮：把审计查出的「发布不可复现」等四类问题补掉，
> 并给发布流程加了硬闸。

## 本版变更

| # | 项 | 内容 |
|---|---|---|
| 1 | **发布口径可复现**（审计 P1） | v1.6.4 的补位模型阈值 **−0.45** 是脚本外调的，而仓库里 `10_generate.py` 硬编码 `−0.05`——**按提交代码重跑，728 个补位字会偏轻约 10%**。现在 `--threshold` / `--hardtail-threshold` 都参数化且默认值即发布值 |
| 2 | **新增 `data/release-a.json`** | 记录发布用的两个检查点、两个阈值、res、simplify、逐字来源计数与**完整复现命令**，格式对齐 B 线的 `release-b.json` |
| 3 | 打包白名单 | `14_package` 遇到未知 `src` 直接中止（原来静默当成 ribbon 回退） |
| 4 | `13_qa` 期望值动态 | 真迹字数从 `work/chosen.jsonl` 读，不再硬编码 1675 |
| 5 | **孔洞审计进发布链** | `71_holes.py` 写入 AGENTS 发布流程，核对表新增一条：`holes lost` 不得高于基线 1.9% |
| 6 | 文档数字对齐 | README / AGENTS / PROJECT_STATE 的合成字构成统一为 **GAN 18,518（ep90 17,790 + ep80 728）+ 回退 799** |

## 复现（一条命令）

```bash
python3 scripts/10_generate.py --method gan --res 512 --simplify 2.0 --workers 6 \
  --ckpt-hardtail work/ckpt/m2_ep080.pt --threshold -0.05 --hardtail-threshold -0.45
```

## 指标（与 v1.6.4 同）

| 项 | 值 |
|---|---|
| 覆盖 | 20,992 / 20,992 |
| 真迹 | 1,675 |
| 合成构成 | GAN 18,518（95.9%）+ ribbon 回退 799（4.1%） |
| 孔洞 | lost 1.9% / fewer 28.5% / equal 25.2% |
| 干净集 | Dice 0.549、chamfer 5.85 |

## 已知限制（延续 v1.6.4）

1. 孔洞缺陷无工程解法（E38）；2. 合成字比真迹重约 17%（E34/E37）；
3. 补位字与主模型字有 3.8% 墨量差；4. 未做 hinting。

## 檔案

`GuanGeKai-Regular.ttf`、`GuanGeKai-Real.ttf`、`provenance.json`（四态）、`stats.json`、
`SHA256SUMS`、`OFL.txt`、`LICENSE`、`coverage.txt`、`specimen.png`、`book-vs-font.png`

校验和见 `docs/DATA.md`。B 线（史记本）**v1.2.1** 另行发布，入口见 `README-B.md` 与 `docs/RELEASE-v1.2.1-B.md`。
