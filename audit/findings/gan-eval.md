# A 线 GAN 训练 / 生成 / 评估 独立审计（task-2）

> 审计员：`gan-eval`（独立审计，只发现问题，不修改代码/文档）
> 日期：2026-11-14
> 范围：`scripts/21_train_gan.py`、`22_eval_gan.py`、`24_build_singles.py`、`25_eval_singles.py`、`26_bench.py`、`29_gate_eval.py`、`30_gate_rules.py`、`31_ckpt_manifest.py`、`32_eval_clean.py`、`33_struct_metrics.py`、`34_struct_score.py`、`35–42_*.py`、`08_make_pairs.py`、`08b_make_pairs_multi.py`、`10_generate.py`；`docs/EXPERIMENTS.md`（E16/E23–E40、训练轮次一览）、`docs/PLAN-v1.5.md`、`docs/PROJECT_STATE.md` §6/§8、`data/release-a.json`、`work/ckpt/MANIFEST.json`。
> 方法：全文静态通读 + 只读复现。复现均在 `/tmp` 内写脚本，**未改动仓库任何文件、未做 git 操作、未训练、未做全量生成**；多进程/推理遵守 AGENTS 并发约束（本次自建脚本用 4 线程 / `OMP_NUM_THREADS=1`，未超 10 线程上限）。
> 分级：P0 = 阻断复现/发布可信性；P1 = 高，影响已发布产物或发布决策的证据链；P2 = 中，口径/可复现性/防呆；P3 = 建议。

---

## 0. 结论速览

- **P0 ×1**：`data/release-a.json` 声明的生成工作点与发布数据不一致——按其 `reproduce` 命令（`--res 512 --simplify 2.0`）**无法复现** `work/generated.jsonl`（发布字体的直接来源）；实际发布数据是多组参数拼合的产物。
- **P1 ×4**：① 发布检查点 `m2wt_ep090.pt` 未登记于 `MANIFEST.json`，按现行保留规则属于**可删**的 snapshot；② 被 shipped README / 发布说明 / 项目状态反复引用的「真迹互比地板 **5.16**」在 A 线**没有脚本、没有落盘数据、现有命令无法复现**；③ 发布文档把 Dice 0.549 / chamfer 5.92 当作发布口径，但这是**补位模型 m2_ep080** 的指标（发布主模型 m2wt_ep090 是 0.548/5.85，n=617 全量是 0.539）；④ E39/E40 的选点/阈值标定依据（守卫拦截率 77%→37%、−0.45 标定表）无脚本无落盘，且换血基线 `generated_v162.jsonl` 不存在。
- **P2 ×8**：E30 崩坏率与落盘文件不符；E32「均值/中位差 0.05」混淆对齐口径；E28「带符号中位」无法由 `33_struct_metrics.py` 产出；E35/E37 引用脚本与测量内容错位、关键数无落盘；`gan_fallback.json` 固定路径被探针运行清空；检查点不携带配置/数据/版本、训练日志未入库；训练轮次一览表严重过期；`PROJECT_STATE` §6/§8 与现状矛盾。
- **复核通过（未发现问题的关键项）**：干净集零泄漏（617 ∩ 任何训练 split = 0）；E32/E36/E39/E37/E35 的头牌数字与我实测一致（见表 2）；发布三件套 SHA256 与 `release-a.json` 一致、zip 内容一致、`provenance.json` 与 `generated.jsonl` 逐字对账 0 失配；E40 的 728/799/17,790 构成可从 `generated_v163/v164` 复算。
- 上一轮审计已披露的问题（评估阈值 0 vs 生产 −0.05、训练不可复现、valDice 8 样本、PatchGAN 感受野 108 vs 70/46、`--ckpt` 对 gan 无效、39/40 旧口径等）不重复列为新发现，见 §5。

---

## 1. P0

### P0-1 `data/release-a.json` 的生成工作点与发布数据不符，reproduce 命令不能复现发布字体

**事实（Lead 独立实测，2026-11-14；本审计采信）**

- 取 `work/generated.jsonl` 前 20 个前缀字形，用 `python3 scripts/10_generate.py --method gan --simplify 2.0`（**不带 `--res`，即默认 256**）生成，得到的 20 条 JSON 与 `work/generated.jsonl` 对应行**逐字节一致**；改用 `data/release-a.json` reproduce 行里的 `--res 512` 则**不一致**。
- 且有部分 `src=gen80` / `src=base` 行只与「512」或「不带 simplify」的组合匹配——即 `work/generated.jsonl` **不是单一参数产物**，而是多组参数生成后拼合/追加的文件。

**本审计的佐证与代码定位**

- 代码默认值与 release-a 声明不一致：`scripts/10_generate.py:420-423`（`--simplify` 默认 `0.0`、`--res` 默认 `256`、`--workers` 默认 `8`）；`data/release-a.json:10-11` 声明 `"res": 512, "simplify": 2.0`；`data/release-a.json:20` 的 `reproduce` 行显式带 `--res 512 --simplify 2.0`。
- GAN 推理始终在 256（`10_generate.py:101` `GAN_RES = 256`），`--res` 只决定**矢量化（trace）分辨率**（`10_generate.py:114-115, 489`）与简化是否生效（`:491-492`）。因此 `--res 256 --simplify 2.0` 与 `--res 512 --simplify 2.0` 会得到不同轮廓坐标、不同节点数、不同 TTF 哈希。
- 该文件内部存在管线签名差异（旁证，非决定性）：统计 `work/generated.jsonl` 每条轮廓是否含三次曲线段，`src=gen` 行 **99.90%** 全为直线段（说明 `--simplify 2.0` 生效）；`src=gen80` 行只有 **82.69%** 全直线（17.31% 含 C 段），`src=base` 行 **99.50%**。同一 run、同一 `--simplify` 下三类行不该有 170 倍的曲线残留差（注意：`10_generate.py:298-300` 的 `_simplify` 对 <3 点的微小轮廓会保留原曲线，可解释一部分但不是全部，故此条仅作旁证，不作判据）。
- 发布说明的表述与事实相反：`docs/RELEASE-v1.7.2.md:12` 写「…与 `data/release-a.json` 一致；**不带参数重跑即发布口径**」——不带参数时 `--res 256 --simplify 0`，与发布数据不符。shipped 的 `release/README.md:143` 给出的也是 `python3 scripts/10_generate.py --method gan`（无 `--res/--simplify`），按它重建会得到不同字体（E33 记载：不简化时字体 28 MB，简化后 15 MB）。
- `docs/DATA.md:176-179` 的重建链带 `--res 512 --simplify 2.0`，同样不能复现 `work/generated.jsonl`。

**影响**

- release-a.json 是 v1.7.2 明文的「发布口径唯一来源」（`docs/RELEASE-v1.7.2.md:12`），但它给出的命令**不能重建发布字体**；任何按文档重建的人都会得到不同 TTF（哈希不同），发布可复现性主张不成立。
- 发布数据是多参数拼合 → 同一字体的 19,317 个合成字来自不同矢量化分辨率/简化参数的管线；这使「同一工作点」的质量结论（墨量、chamfer、字体级验收）只能覆盖某一子集，也解释了为什么逐字 provenance 之外没有可复现的生成参数记录。
- 该文件是 `build/GuanGeKai-Regular.ttf` 的唯一合成字来源（`14_package.py` 由 `generated.jsonl` 生成 provenance；本审计已核对 `release/provenance.json` 与 `generated.jsonl` 完全一致），因此字号/轮廓简化相关的差异会直接进入发布字体。

**复现**

```bash
# 取 20 个前缀字（Lead 实测；本审计未重复）
python3 scripts/10_generate.py --method gan --simplify 2.0 --limit 20 --out /tmp/gen20_default.jsonl
diff <(head -20 work/generated.jsonl | python3 -c 'import sys,json;[print(json.dumps(json.loads(l),sort_keys=True)) for l in sys.stdin]') \
     <(python3 -c 'import json;[print(json.dumps(json.loads(l),sort_keys=True)) for l in open("/tmp/gen20_default.jsonl")]')
# 预期一致；把 --simplify 2.0 换成 --res 512 --simplify 2.0 后不一致
```

**改进建议**

1. 先确认发布数据的真实参数组合：按 `src`（gen/gen80/base）分别用 `res ∈ {256,512}` × `simplify ∈ {0,2.0}` 重生成 30–50 字，逐字节判定每类行的来源参数，落盘 `work/gen_params_probe.json`。
2. 用**一个驱动脚本**（如 `scripts/43_build_generated_a.py`）固化混合检查点生成：主/补位/回退三类各自的 ckpt、阈值、res、simplify 全部显式写在脚本常量或 CLI；输出单一 `generated.jsonl`，并把输入 ckpt 的 sha256、参数、`work/generated.jsonl` 的 sha256 写入 `data/release-a.json`。
3. `release-a.json` 的 `reproduce` 改为调用该驱动脚本；加硬闸：重生成后与登记 sha256 不一致即失败。
4. 修 `RELEASE-v1.7.2.md:12`、`release/README.md:143`、`docs/DATA.md:176-179` 三处命令，明确 `--res/--simplify` 不能省。

---

## 2. P1

### P1-1 发布检查点未登记，且按现行保留规则属于「可删」类别

**证据**

- `work/ckpt/` 实际 24 个 `.pt`，`MANIFEST.json` 只登记 20 个；**在盘不在册的 4 个全是发布依赖**：
  `m2wt_ep090.pt`（`data/release-a.json:6` 的 `primary_ckpt`）、`m2wt_ep100.pt`、`m2wt_best.pt`、`m2wt.pt`。
- `MANIFEST.json` mtime 2026-10-26 13:03，而 `m2wt_*.pt` mtime 2026-10-26 22:46–23:12（E39 训练在 manifest 之后）；`31_ckpt_manifest.py` 头部明确要求「Run after every training run」。
- 发布主检查点**没有任何登记的 sha256**：实测 `m2wt_ep090.pt` sha256[:16] = `5f5ac04e084e130a`，`data/release-a.json` 与 `release/` 均无此值；唯一在册的发布检查点 `m2_ep080.pt`（补位）实测 `9a859d6a9b7ec9a0`，与 MANIFEST 一致。
- 保留规则会把两个发布检查点判成可删：`31_ckpt_manifest.py:17,20-28` 把 `_ep90` 归为 `snapshot`（核心轮次只有 50/100/150/…），当前 MANIFEST 也把 `m2_ep080.pt` 标为 `"kind": "snapshot"`。该脚本是**唯一**的检查点分类器，没有任何「发布依赖」白名单。
- 实测别名关系（本审计 `torch.load` 对比 + epoch 字段）：
  - `m2_ep080` 的 G 权重 == `m2.pt`（epoch 80，最终轮）——补位模型有一份受「最终一轮」规则保护的副本；
  - `m2wt_ep100` 的 G 权重 == `m2wt.pt`（epoch 100，最终轮）；
  - `m2wt_ep090` **没有任何等价副本**，`m2wt_best.pt` 是 epoch 100（valDice 最佳落在最后一轮），所以 ep90 既不是 best 也不是 final。
  → 若日后按 AGENTS/DATA §6.5.1 规则清理 snapshot，**唯一会直接删除发布主模型**。
- `docs/DATA.md:214-221` 的「当前检查点分布（**2026-10-25 19:30 核对**）」早于 E39/E40，全文无 `m2wt` 字样；AGENTS 要求删除登记在 DATA §6.5.1，但发布检查点本身从未被登记。

**影响**：发布主模型的完整性与来源无登记；一次例行清理即可让 v1.7.2 的发布字体不可再生成，且没有哈希可证明「现在的 m2wt_ep090.pt 就是当初发布的那个」。

**复现**

```bash
ls work/ckpt/*.pt | wc -l                      # 24
python3 -c "import json;m=json.load(open('work/ckpt/MANIFEST.json'));print(len(m['items']))"   # 20
python3 -c "import json;m=json.load(open('work/ckpt/MANIFEST.json'));print([x for x in m['items'] if x['file']=='m2_ep080.pt'])"
sha256sum work/ckpt/m2wt_ep090.pt | cut -c1-16 # 5f5ac04e084e130a（release-a 未登记）
```

**改进建议**：立刻重跑 `31_ckpt_manifest.py`；给 `kind` 增加 `release`（来源：`data/release-a.json` 的 `primary_ckpt`/`hardtail_ckpt`）并禁止删除；把两个发布检查点的 sha256 写进 `data/release-a.json`；`31` 加 `--check-release` 硬闸（release-a 引用的路径必须存在且哈希一致）；`docs/DATA.md §6.5.1` 补 m2wt 行与「发布检查点例外」。

### P1-2 「真迹互比地板 5.16」在 A 线无实现、无落盘、无法按现有命令复现，却已随发布包公开

**证据**

- 引用面（均为公开/半公开文档）：`release/README.md:164`（**在 `GuanGeKai-v1.7.2.zip` 内**）、`docs/releases/RELEASE-v1.5.0.md:9,48`、`RELEASE-v1.5.1.md:36`、`RELEASE-v1.5.2.md:30`、`RELEASE-v1.6.0.md:40`、`RELEASE-v1.6.1.md:22`、`docs/EXPERIMENTS.md:113,1068`、`docs/PROJECT_STATE.md:363`、`docs/method.md:57`、`docs/EXPERIMENTS-B/C.md`、`docs/PLAN-C-v1.1.0.md`、`docs/PROMPT-SHIJI.md`。
- 被引用的数不止中位：`EXPERIMENTS.md:1068-1069` 还有「GAN 5.92 [5.14, 7.27] vs 真迹 **5.16** [4.27, 6.65]，**KS p<0.001、Mann-Whitney 单侧 p=0.0001**」——仓库中**没有任何脚本**产生这些区间/检验，也没有输出文件。
- A 线评估脚本不具备算地板的能力：`scripts/34_struct_score.py:96` 硬编码 `work/pairs_single.npz`（617 个「书中只出现一次」的字，**每个字只有一份真迹**，原理上无法做同字两样本互比），且无 `--eval-data`/floor 分支（参数仅见 `:90-93`）。全仓库 A 线（01–42）无 `floor_same_char`/同字地板代码（`grep -rn "floor" scripts/0*.py 1*.py 2*.py 3*.py 4*.py` 只命中 `06/24` 的 `--pitch-floor`，与地板无关）。
- 能力代码存在但**没有产物、没有命令**：`08_make_pairs.py:93-95` 的 `--chosen` 注释说用于「same-character pairs needed for the chamfer floor」，`24_build_singles.py:27-29` 有 `--from-chosen`；但 `work/pairs/pairs_second.npz` **不存在**（`work/pairs/` 只有 pairs/pairs_blur05/pairs_blur10），`work/` 下也没有任何 floor json。对照组：B 线有专门实现 `scripts/65_eval_b.py:218-243`（用 `pairs_second.npz`，seed 1、抽 800 对），C 线有 `scripts/82_eval_c.py:232`；**唯独 A 线没有**。
- 口径还会漂移：上轮审计（`docs/AUDIT-2026-10-26.md` 2-10）之后 `24_build_singles.py:22` 的 `--sigma` 默认已从 1.0 改为 0.0；当年地板若按旧默认重建参照，今天照旧命令重跑会得到不同的目标图。

**影响**：这是「GAN 已逼近真迹（差 15%）」这一核心质量主张的唯一标尺，也是决定是否继续 M4/512 重训、以及 B/C 线跨书比较（B 3.57 / C 6.98 都用同族口径）的依据。数字不可复核 = 发布决策证据链缺口；且它已随 zip 分发。

**复现（证明缺口）**

```bash
grep -rn "真迹互比\|floor_same\|_floor" scripts/0[0-9]*.py scripts/1*.py scripts/2*.py scripts/3*.py scripts/4*.py   # 无 A 线实现
ls work/pairs/pairs_second.npz   # No such file
sed -n '88,98p' scripts/34_struct_score.py   # 无 --eval-data，硬编码 pairs_single
```

**改进建议**：① 用 `08_make_pairs.py --chosen work/second.jsonl --sigma 1.0 --out work/pairs/pairs_second.npz` 重建（`work/second.jsonl` 现有 1,675 行、每字一例）；② 新写 `scripts/43_chamfer_floor_a.py`：固定 seed 7、抽 800 对、用 `34_struct_score.score` 同口径算 chamfer，同时输出中位/分位/bootstrap CI 与 KS/Mann-Whitney 检验；落盘 `work/chamfer_floor.json` 并把命令写进 EXPERIMENTS E32；③ 重算后如与 5.16 不同，统一更新所有引用处（release README 在 zip 内，需要一次正式发版才能改）。

### P1-3 发布文档把「补位模型 m2_ep080」的指标当作发布口径；n=150 与 n=617 两个口径混用

**证据（本审计实测，见表 2）**

| 来源 | 写法 | 实际对应 |
|---|---|---|
| `docs/RELEASE-v1.7.2.md:22` | 「干净集 Dice **0.549**、chamfer **5.92**」 | **m2_ep080**（E32 的 80 轮模型）n=150 |
| `release/README.md:163-164`（shipped） | 同上 + 地板 5.16 | 同上 |
| `data/release-a.json:33-34` | `"dice": 0.539, "ink": 0.983`，注明「n=617 全量，发布口径」 | 发布主模型 m2wt_ep090 |
| `AGENTS.md` | 「干净集 Dice 0.549（E32，n=150）」 | m2_ep080 |

- 实测（4 线程复现，`32_eval_clean` 同口径）：`m2_ep080` n=150 → Dice **0.5485**／ink 0.9913；`m2wt_ep090` n=150 → **0.5483**／0.9864；617 全量 → ep090 **0.5386**／0.9826、ep080 **0.5393**／0.9897。
- 即：发布字体主用 ep090（17,790 字），而 v1.7.2 发布说明与包内 README 引的 **0.549/5.92 是 ep080 的数**；ep090 是 0.548/5.85（E39）；n=617 口径是 0.539。三套数字在文档中并列且互相不加注，读者无法判断哪个是发布口径。
- E39 的 ep090「墨量比 0.981」也无法用 `32_eval_clean` 复现（阈值 0 → 0.986）：该行指标未落盘、无命令，疑似用了中位或另一阈值（阈值 +0.05 时 M2 的 ink 正好 0.981，见 `work/threshold_sweep_m2.json`）。

**影响**：对外披露的「干净集」数字与发布模型不对应，属于可复核性问题；虽然差 0.001–0.010 不影响定性结论，但「发布口径唯一」的治理目标没有达成。

**改进建议**：`release-a.json` 增 `clean.by_model`；发布文档统一引用 release-a 的 n=617 行并在括号注明 `n=150 seed7` 的对照值；E39/E40 每条指标补「命令 + 输出 json」。

### P1-4 E39/E40 的发布决策依据无脚本、无落盘；换血基线文件已不存在

**证据**

- E39 的守卫改善数字「150 个现有回退字仍被拦 **115（77%）→56（37%）**」「全量回退率 9.5%→7.9%（1,833→1,527）」（`EXPERIMENTS.md:1288-1297`）：仓库内无对应脚本、无输出 json；1,527/17,790/9.5% 可由 `work/generated_v163.jsonl` 复算（本审计已复算：gen 17,790 / base 1,527），但 **77%→37% 的拦截率无任何数据可核**。
- E40 的阈值标定表「−0.05 → 0.932 / −0.15 → 0.943 / −0.30 → 0.972 / **−0.45 → 1.001**（差 3.8%）」（`EXPERIMENTS.md:1337-1342`）是「补位模型各自标定阈值」这条通用教训的唯一实证，也是 `data/release-a.json:21` 补位阈值 −0.45 的依据；无脚本、无 json、无命令。
- E39「1,034 个字从 ribbon 改为 GAN，728 个从 GAN 掉回 ribbon」（`EXPERIMENTS.md:1296-1297`）需要 v1.6.2 的 `generated` 基线，但 `work/` 只有 `generated_v163.jsonl`（v1.6.3）与 `generated_v164.jsonl`（v1.6.4），**没有 v1.6.2 产物**。本审计能复算的只有 v163→v164：`gen 17,790→17,790`、`base 1,527→799`、`base→gen80 728`（与 E40 最终构成一致；E40 的「728 与预测完全一致」因此部分成立），但 E39 的换血数字不可重建。
- 此外 `10_generate.py:124-133` 的硬编码补位逻辑（主模型失败→副模型→ribbon）没有把每字的**失败原因/守卫值**落盘，`work/gan_fallback.json` 只记最终失败字（而且已被清空，见 P2-5），无法事后审计「为什么这 728 字被捞回」。

**影响**：发布字体 4.1% 回退率 / 728 补位 / −0.45 阈值是发布说明的核心卖点，但支撑它们的实验没有可复跑命令与数据；换血叙事（1,034/728）无法验证。

**改进建议**：把 E40 混合生成固化成一个脚本（输入两个 ckpt → 输出 generated + per-char `guard_log.jsonl`：每字的 ink/comps/阈值/是否通过/最终 src），并在 `release-a.json` 记录命令；E39/E40 的表格数值落盘 `work/e39_e40_metrics.json`；保留每次生成的 `generated_v*.jsonl`（至少保留发布前两版）。

---

## 3. P2

### P2-1 E30 的崩坏率数字与它自己指定的落盘文件不符
`docs/EXPERIMENTS.md:998-999` 写「崩坏率（Dice<0.30，n=150）已落盘 `work/failure_rates.json`：ribbon 4.67%，GAN 0.67%」。实测该 json：`ribbon.frac_below_0.30 = 0.0467`（=4.67% ✓），但 `gan_t0.frac_below_0.30 = **0.0**`（不是 0.0067）。0.67% 与 E29 的 n=300「0.7%」同源，疑似转录时把两个抽样混写。**建议**：改文或重跑该脚本落盘；`failure_rates.json` 记录 ckpt/seed/n。

### P2-2 E32「均值 0.549 / 中位 0.599，两个口径差 0.05」把「对齐」与「均值/中位」混为一谈
`EXPERIMENTS.md:1053-1054` 的注让读者以为同口径下中位是 0.599。实测：0.5485 是 `32_eval_clean` 的**未对齐均值**；0.599 是 `34_struct_score` 的**质心对齐后**中位（`34_struct_score.py:128` 对每个指标取 median，`:67-69` 先 `shift_to_centroid`）。未对齐中位≈均值（60 字实测 0.562/0.5645）。`PLAN-v1.5.md:160` 的「未对齐 0.543 → 质心对齐 0.591」才是正确解释。**建议**：表注改为「0.549 未对齐均值；0.599 为质心对齐后的中位，不可与 0.549 直接比」。

### P2-3 E28「横画角带符号中位 −2.3°/−9.0°」无法由被引脚本产出
`EXPERIMENTS.md:919-929` 声称由 `scripts/33_struct_metrics.py` 测得「带符号中位」−2.3°（文楷）/−9.0°（真迹）。但 `33_struct_metrics.py:36-43` 对每个 Hough 角取 `abs(a)` 后入分布，脚本**不可能输出负数**；实测落盘 `work/struct_metrics.json` 为 `霞鹜文楷 h_angle_median 3.4 / 真迹 10.54 / KS 0.513 / counter 39/120`（KS 与 39/120 和文档一致，唯独符号/数值不符）。即「文楷比写本横画更平（−2.3 vs −9.0）」这一方向性陈述没有证据（只能证明写本倾角**幅度**更大）。**建议**：改用带符号角度保存到 json 并重跑，或删掉「带符号」与方向解释。

### P2-4 E35/E37 的引用脚本与测量内容错位，关键数字无落盘（结论本身本审计已复算成立）
- `EXPERIMENTS.md:1143` 说四层测量「见 `scripts/38_ink_calib.py`」，但该脚本做的是**亚像素腐蚀对墨量/Dice/chamfer/端子** 的影响（`38_ink_calib.py:1-5,44-60`），**不产出** E35 表里的 ① 文楷同组 1.05 ② 模型输出 0.995 ③ 成品 1.086 ④ 分辨率 0.994，也没有输出 json。
- E37 的 bbox 0.971/0.978/面积 0.949 与「轮廓/掩膜 = 0.9997」同样没有脚本/落盘（`work/` 无 e35/e37 json；`39/40_contour_*.py` 只算面积比，不算 bbox）。
- 本审计用一次性脚本复算并**支持这些结论**：E37 bbox 宽 **0.971**、高 **0.978**（面积积 0.9497≈0.949 ✓，n=120 干净字，ep080，阈值 −0.05）；E35 ①「文楷同两组之差」实测 gen/real = **1.049**（≈5% ✓）；E37 的轮廓/掩膜比在 trace@256 = 0.9988、trace@512 = 0.9996（≈1.0 ✓，且证明该结论对 256/512 都成立）。
- **建议**：把这三段测量固化成 `scripts/43_ink_layers.py`（E35 四层 + E37 bbox + 轮廓/掩膜）并落盘 `work/e35_e37_metrics.json`；修正 E35 的脚本引用。

### P2-5 `work/gan_fallback.json` 是固定路径且会被任何探针运行清空；36/41 会用旧口径破坏四态 provenance
- `10_generate.py:498` 无条件写 `work/gan_fallback.json`，与 `--out` 无关。现状：`work/gan_fallback.json` = `[]`（mtime 10-30 08:06），而 `work/generated.jsonl` 里 `base` 有 799 条（mtime 10-27 10:22）→ **发布的回退清单已被一次探针运行覆盖丢失**（只能从 generated.jsonl 的 tag 反推）。
- `36_fill_fallback.py:26-33` 只认 `src=="gen"`、其余一律按「缺失」重画；`41_regen_fallback.py:19-33` 只保留 `src=="gen"`、其余改写成 `"base"`。若在 v1.6.4+ 的数据上重跑二者，会把 728 个 `gen80` **降级成 base**，破坏 `data/release-a.json:13-19` 的四态统计与 `14_package.py:63-67` 的映射。
- **建议**：`--fallback-out` 参数（默认不写项目路径/`--dry-run` 只打印）；36/41 加 `gen80` 白名单并注明「E40 后不再适用」，或直接归档这两个脚本。

### P2-6 检查点不携带训练配置/数据/版本，训练命令与日志未入库
- 实测 `torch.load` 的 keys：`m2_ep080.pt`、`m2wt_ep090.pt`、`m2wt_best.pt` 均只有 `G/D/epoch`（连当前代码 `21_train_gan.py:326-339` 会写的 `best_dice` 都没有 → 说明这些文件由更早版本的脚本产生）。无法从检查点判断 recipe（`--patchgan/--hinge/--aug/--weight-complexity`）、数据集版本、`--val-data`、代码版本。
- 训练命令未记录：全仓库没有任何 A 线 GAN 训练命令行（B/C 线在 `docs/DATA-B.md:253`、`docs/DATA-C.md:175`、`docs/PLAN-C.md:60` 都有）；`work/*.log` 只有旧 U-Net 训练日志，**没有 M2/E36/E39 的日志**，而 `EXPERIMENTS.md:1050` 明确引用 `/tmp/m2.log`（临时目录，已不存在）来更正 valDice。
- `--val-n` 默认 8（`21_train_gan.py:187-188`），而 E32/E36 的表格标注「训练内 valDice（41 个按字留出的字）」（`EXPERIMENTS.md:1043,1176`）；41 是 **split 的字数**（`m2_split.json` val 41 字），实际 valDice 取了几个字没有记录。上轮审计 3-1/10-31 已披露「valDice 只算 8 个」，但文档口径仍未改。
- 附带：`--resume` 不保存 Adam 状态（`21_train_gan.py:196-198` 已注明）；E39 从 ep80 续训 20 轮用了新优化器状态，属于已知限制，但没有把「瞬时差异」量化。
- **建议**：ckpt 里存 `{"args": vars(args), "data_sha256": ..., "split": ..., "code_sha": ...}`；训练日志写 `work/logs/`；文档中的 valDice 口径改成实际值。

### P2-7 「训练轮次一览」严重过期，与 ckpt 目录对不上
`EXPERIMENTS.md:12-25` 只有 6 轮，末行「第 6 轮 zi2zi-GAN 150 ep 见 E16」，并总结「共 6 轮训练」。实际 `work/ckpt/` 有 24 个 `.pt`，对应至少 8 次 GAN 训练：`zi2zi_gan`（E16，旧 150ep）、`zi2zi_gan_multi`（E23）、`attr_multi_gD`、`attr_single_patch`、`m1_blur05`（E31）、`m2`（E32）、`m2e150`（E36）、`m2wt`（E39/E40）——**发布主模型 m2wt_ep090 不在任何「第几轮」表中**。该表正是「回答这是第几轮」的入口文档，现在会误导接手者。
**建议**：用 `31_ckpt_manifest.py` 的输出重建该表（run 名 / 起止 epoch / 配置 / 用途 / 是否发布），并在表头写「本表由 manifest 生成」。

### P2-8 `PROJECT_STATE` §6/§8 与现状矛盾
- §6 表格（`:137`）写 F = GAN「**v1.5.0 采用**」，紧接正文 `:139` 却写「**当前发布版用 E（v1.3.3）**」——同一节自相矛盾，与 v1.7.2 实际（GAN 18,518 字）不符。
- §8（`:167-172`）写「合成字整体偏重约 17%…既然是恒定偏差…**下一版可做一次全局标定**」——该结论已被 E35/E37 推翻（`EXPERIMENTS.md:1152-1154`：「不存在一个可以一键乘上去的常数」；AGENTS.md 也写「不要再做轮廓层面积补偿」）。§8 是「未决问题/下一步」清单，这条会直接误导下一版。
- 顺带：§8 `:178-182` 仍写「B 线重新打开…下一步全量生成+字体级验收」，对应的是 v1.5.0 前的状态，早已完成。
**建议**：§6 删掉「当前发布版用 E」；§8 把 17% 那条改成 E35/E37 的结论并删除「全局标定」建议；标注 §8 中已完成项。

---

## 4. 复核通过（正面结论与实测数字）

表 2：本审计只读复现（`OMP_NUM_THREADS=4`，脚本在 `/tmp`，方法逐行照抄 `32_eval_clean.py` / `34_struct_score.py` 的 GAN 分支；`pairs_single.npz`，`RandomState(7)`）：

| 文档口径 | 文档值 | 本审计实测 | 文件 |
|---|---|---|---|
| E32 / m2_ep080 / n=150 / seed7 / 未对齐均值 Dice | 0.549 | **0.5485** | 32 同口径 |
| E32 / m2_ep080 / n=150 / 质心对齐中位 chamfer | 5.92 | **5.922** | 34 同口径 |
| E32 / m2_ep080 / len_ratio | 0.886 | **0.886** | 34 同口径 |
| E32 注「中位 0.599」 | 0.599 | **0.599**（=34 对齐中位） | 34 同口径 |
| E36 / m2e150_ep150 / chamfer / len_ratio | 5.93 / 0.868 | **5.93 / 0.868** | 34 同口径 |
| E39 / m2wt_ep090 / n=150 Dice | 0.548 | **0.5483** | 32 同口径 |
| E39 / m2wt_ep090 / chamfer | 5.85 | **5.851** | 34 同口径 |
| release-a clean / n=617 / Dice / ink | 0.539 / 0.983 | **0.5386 / 0.9826** | 32 同口径 |
| release-a baseline wenkai / ribbon（n=617） | 0.434 / 0.411 | 与 `work/eval_clean_a172.json` 一致 | 32 |
| release-a 注「n=150 比 n=617 高 0.010，属抽样」 | — | **成立**：ep090 Δ0.0097、ep080 Δ0.0092 | 32 |
| E37 bbox w / h / 面积积 | 0.971 / 0.978 / 0.949 | **0.971 / 0.978 / 0.9497** | /tmp 一次性脚本 |
| E37 轮廓/掩膜（signed） | 0.9997 | **0.9996**（trace@512）、**0.9988**（trace@256） | `/tmp/gx_trace_res.py` |
| E35 ①「文楷同两组差 5%」 | ~1.05 | **1.049** | /tmp 一次性脚本 |

其它复核结论：

1. **干净集零泄漏成立**：`work/pairs_single.npz` 617 字 = `labeled.jsonl` 中 count==1 的全部 617 个标签（无缺/无多）；与 `chosen.jsonl` 交集 0；与全部 8 个 `*_split.json` 的 `train_chars`/`val_chars` 交集均为 **0**（含 `m2wt_split.json`、`m2e150_split.json`、`attr_*`、多实例）；`pairs.npz` 1,675 字（每字 1 例）也与其交集 0。release-a 的「从未参与训练」这一条**可信**。
2. **发布数据构成对账**：`work/generated.jsonl` 19,317 行、无重复、全在基本区，`src` 计数 `gen 17,790 / gen80 728 / base 799`，与 `release-a.json:13-19` 的 `gan_ep90/gan_ep80/ribbon_fb` 完全一致；`release/provenance.json`（21,034 条）与 `generated.jsonl` 逐字映射 **0 失配**（`14_package.py:63-67` 的映射 `gen→gan_ep90, gen80→gan_ep80, base→ribbon_fb` 生效）。
3. **发布三件套完整**：`build/GuanGeKai-Regular.ttf`、`GuanGeKai-Real.ttf`、`GuanGeKai-v1.7.2.zip` 的 sha256 与 `data/release-a.json:45-47` 完全一致；zip 内两个 ttf 哈希与 `release/` 一致；`release/SHA256SUMS` 逐项一致；`release/stats.json` 的 21034 / 1675 / 19317 / 17790 / 728 / 799 与实测一致。
4. **E40 最终构成可复算**：`generated_v163`（gen 17,790 / base 1,527）→ `generated_v164`（gen 17,790 / gen80 728 / base 799）的变化是 `base→gen80 728`、`base→base 799`、`gen→gen 17,790`；与 E40 表格的 17,790/728/799 一致（E39 的换血 1,034/728 仍不可重建，见 P1-4）。
5. **在册检查点哈希可信**：`m2_ep080.pt` 实测 sha256[:16] `9a859d6a9b7ec9a0` = MANIFEST 登记值。别名关系实测：`m2_ep080.G == m2.pt.G`（epoch 80）、`m2wt_ep100.G == m2wt.pt.G`（epoch 100）、`m2wt_best.pt` epoch=100。
6. **`--resume` 的 best_dice**：上轮审计（AUDIT-2026-10-30 P3-12）称 `--resume` 时 `best_dice` 会重置 −1；现行 `21_train_gan.py:244-257` 是从 ckpt 读取并保留（仅非 resume 才置 −1），该条**在当前代码上不成立**。
7. **质心对齐不会膨胀掩膜**（本审计曾怀疑）：`shift_to_centroid`（`34_struct_score.py:37-48`）用 bool→uint8(0/1) + `INTER_LINEAR` + `>0`，实测对齐后墨量比 **1.000**（n=60），且与整数平移的 Dice 一致（0.6023 vs 0.6026）→ 对齐口径是「真平移收益」，不是内插膨胀。E29/E32 用对齐口径**可以**解释，只是文档写法要改（P2-2）。
8. 上轮审计已修项确认：`24_build_singles.py:22` 的 `--sigma` 默认已是 **0.0**（发布干净集未模糊）；`32_eval_clean.py:42-44`、`34_struct_score.py:90-92` 已有 `--n/--seed`（默认 150/7），E32/E33 的 n/seed 口径现在可由脚本复现。

---

## 5. 已核查不成立 / 已披露（不要重复排查）

**本审计提出并已否决的假设**

- 「617 干净集仍在某次训练中被见过」→ 否。8 个 split 全部交集 0；该干净集与 `chosen.jsonl`/`pairs.npz`/`pairs_multi.npz` 均无交集。
- 「34 的质心对齐用线性插值膨胀了预测掩膜，0.599 是假高」→ 否，实测墨量比 1.000、与整数平移一致（见 §4.7）。
- 「release-a 的 0.539 与 E32 的 0.549 是模型不同导致的」→ 两个模型的 n=150 都≈0.548–0.549、n=617 都≈0.539，差异是抽样（seed 7 的 150 字偏易），release-a 的注释成立。
- 「`--resume` 会重置 best_dice」（上轮审计 P3-12）→ 当前代码已保留。
- 「potrace 在 256 分辨率下面积膨胀、E37 的 0.9997 只对 512 成立」→ 否，trace@256 的 signed 面积比 0.9988、trace@512 0.9996，均≈1（本审计实测）。
- 「`generated.jsonl` 的标签与 provenance 不一致」→ 否，逐字对账 0 失配；`stats.json` 的 `"gan": 0` 是残留字段（上轮审计已披露）。

**已由既有审计披露、本次不重复报（状态核对）**

| 既有编号 | 内容 | 现状 |
|---|---|---|
| AUDIT-2026-10-26 rev2 2-7 / rev1 4-24 | 评估 GAN 阈值硬编码 0，生产 −0.05 | **仍在**：`32_eval_clean.py:88-89`、`34_struct_score.py:116-119`、`25_eval_singles.py:40` 仍 `>0`；量级小（阈值扫描 ±0.05 内 Dice 差 0.001） |
| rev2 3-1 / 10-31 | valDice 只用 8 个样本 | **仍在**（默认 `--val-n 8`，见 P2-6） |
| rev2 3-2 / 10-30 P3-12 | 训练不可复现（增强用全局 `np.random`、shuffle 未播种） | **仍在**：`21_train_gan.py:129-141,165,228` |
| rev2 3-3 / rev1 4-3 | PatchGAN 感受野三方不一致（docstring 46 / 文档 70 / 实际 108） | **仍在**：`21_train_gan.py:106-108`（46）、`:193-194`（70×70）；实际 RF=108（k=4,5,5,5,4 / s=2,2,2,2,1） |
| rev2 3-6 | `--ckpt` 对 gan 路径不生效；阈值曾为死参数 | 阈值已参数化（`10_generate.py:428-431` ✅）；`--ckpt` 仍只用于 `--method model` |
| rev2 3-17 | `39_contour_comp.py` 死代码 + `40_contour_offset.py` docstring 与 E37 相反 | **仍在**（`39:73` return 后死代码；`39:37` 无符号面积；`40:1-5` 仍写「potrace 13% 膨胀」） |
| rev1 3-25 | 各 eval 脚本未 `torch.set_num_threads(1)` | **仍在**（32/34/35/38/39/40 均无） |
| AUDIT-2026-10-30 §3.4 | release-a reproduce 未 pin 主检查点（`GAN_CKPT`） | 默认值已改到 `m2wt_ep090.pt`（`10_generate.py:82`）✅，但仍未显式 pin、可被环境变量覆盖——并入 P0-1 一并整治 |
| AUDIT-2026-10-30 P3-5 | RELEASE「holes lost 0.7%（200 字）」不可复现 | 未复核（不在本任务范围） |
| rev2 2-11 | 26_bench leak_note 按 ckpt 名拼 split、bench_unseen 类名陈旧 | **仍在**（`26_bench.py:37-48,140-147,197-198`；默认 GAN 还是旧 `work/zi2zi_gan.pt`） |

---

## 6. 未覆盖 / 本次无法验证

1. **未运行全量 `10_generate.py`**（任务禁止），因此每行实际的 `--res/--simplify` 归属只能依据 Lead 的 20 字逐字节实测与本审计的间接签名，未做完整分类。
2. **未复现「真迹互比地板 5.16」及 KS/Mann-Whitney/CI**：A 线无实现、无数据，见 P1-2（无法用现有产物构造同字两样本）。
3. **未复现 E39 守卫拦截率（115/56）与 E40 阈值标定表**：无脚本、无落盘，需上百字推理与逐阈值重算，且做法未记录。
4. 未审计 B/C 线与 `scripts/99x_*` 等新脚本；未审 `11_build_full.py`/`14_package.py`/`13_qa.py` 的发布链细节（只交叉核对了最终哈希与 provenance）。
5. 未在 MPS 上重跑训练/推理；未复核 E38（600 dpi）与孔洞相关数字。
6. 未运行 `39_contour_comp.py`/`40_contour_offset.py` 的完整 120 字 × 多分辨率扫描（时间），只做了等价的 trace 分辨率面积测量（§4）。
7. 未验证 `release/README.md` 与仓库根 `README.md` 的措辞漂移（上轮审计 10-30 已披露包内 README 旧措辞，本次未重复）。

---

## 7. 建议的修复顺序

1. **P0-1**：先做参数归属探测（30–50 字 × 4 组合），确定发布 `generated.jsonl` 的真实生成参数；写一个混合生成驱动脚本 + `work/generated.jsonl`/两个 ckpt 的 sha256 进 `data/release-a.json`；修三处文档命令。若决定重新统一生成（单组参数），需重跑完整发布链并重新计算全部质量数字。
2. **P1-1**：重跑 `31_ckpt_manifest.py`；加 `release` kind 与「禁止删除」；把 release ckpt 哈希写入 release-a；`docs/DATA.md §6.5.1` 补登记。
3. **P1-2**：重建 `pairs_second.npz` + 写 A 线地板脚本 + 落盘；把 5.16/CI/检验一并复算；更新所有引用（zip 内 README 需下次发版）。
4. **P1-3/P1-4**：统一发布文档的「干净集」口径到 release-a 的 n=617 行；把 E39/E40 的守卫/阈值数据固化成脚本并落盘。
5. **P2**：按 §3 逐条修（E30 数、E32 注、E28 符号、E35 引用、gan_fallback 参数化、ckpt 配置记录、训练轮次表、PROJECT_STATE §6/§8）。

---

## 附：审计复现脚本说明

本审计所有实测均为 `/tmp` 内一次性脚本（未入库）：`gx_gan_eval2.py`（32 同口径、两 ckpt × {617, n150 seed7}）、`gx_struct_eval.py`（34 同口径：质心对齐 Dice/chamfer/len_ratio，150 字 seed7）、`gx_align_test.py`（对齐膨胀检验）、`gx_trace_res.py`（trace@256/512 面积比）、`gx_e37_e35.py`（bbox/charset 归因）、`gx_check1.py`（npz/split/生成标签/对账）。核心逻辑均为：

```python
# 32_eval_clean 的 GAN 行（逐字）
a = (X[i].astype(np.float32)/127.5 - 1.0)[None].repeat(3, 0)[None]
m = G(torch.from_numpy(a).float()).numpy()[0, 0] > 0        # 脚本硬编码阈值 0
t = Y[i] > 127
dice = 2*(m&t).sum()/max(1,(m.sum()+t.sum())); ink = m.sum()/max(1,t.sum())
# 34_struct_score 的行：sel = RandomState(7).choice(617,150,False); ss.score(m, Y[i]) 后取中位
```

所有数字均可用现行脚本以相同默认参数复跑；唯一需要新写代码的是同字地板（P1-2）。
