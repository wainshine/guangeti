# C 线（《永乐大典》v1.3.0）独立审计报告

> 审计代号：line-c-audit。日期：2026-11-14。工作目录 `/Users/wainshine/newAI/guangeti`。
> 审计对象：C 线 v1.3.0（发布日 2026-11-02）的数据链、脚本、制品与 2026-10-31 专项审计的遗留项。
> 约束：只读；唯一写入为本文件。未删除/覆盖任何项目产物，未做 git 写操作、未训练、未重建、未打包。
> 方法：静态阅读 + 只读 json/npz/字体检查 + /tmp 内轻量复现（80_qa_c、83 闸门只读复算、97 术语检查）。

---

## 0. 结论摘要

| 级别 | 数量 | 一句话 |
|---|---:|---|
| **P0** | **2** | ① 发布绕过 2026-10-31 冻结的四级验收门，且 §5.2「过门前不进文档」的数字禁令被违反；② 发布质量口径（`data/release-c.json` / `AGENTS.md`）把 v1.2.1 或更早实验的数字当成 v1.3.0，且 0.4666 无任何可复核产物。 |
| **P1** | **10** | 冻结原则与 §6 结构性修复基本未落地；训练数据的「清理前 pairs」边界披露不完整且影响未评估；生成链有未记录的一次修复运行；重建文档使用的 checkpoint/轮数无法复现 v1.3.0；出厂 README 自相矛盾；83 闸门持久化缺陷；ribbon 口径三源不一致；生成墨量工作点参数不可追溯。 |
| **P2** | **10** | 脚本/文档的陈旧口径、数字与命名：80_qa_c 输出目录耦合、77 守卫阈值三写、DATA-C/CLEANUP-C 过期数字、AGENTS 日期、剔除名单无 manifest、C zip 无自动闸门等。 |

**制品本身是干净的**：字体 SHA/大小/版本、21,034 cmap、5,257 真迹、14,422 GAN + 1,313 ribbon、42 标点、provenance、`release-c/SHA256SUMS`、zip 内文件与 `release-c/` 逐项一致（见 §5）。问题集中在**发布声明、验收留痕、可复现性**，不在字体二进制。

---

## 1. P0（发布合规 / 发布口径错误）

### P0-1 冻结的四级验收门未通过，且 §5.2 的「疗效数字不进文档」禁令被违反

**证据**

- 冻结决策本身：`docs/AUDIT-2026-10-31.md:195-215`（§5.1 原则修订、§5.2 四级门 + 执行约束）、`:278-285`（§8 待登记）。
- 门 1 **实测未过**：`docs/AUDIT-2026-10-31.md:442`「WRONG_LABEL precision 实测 **23/27 = 85.2% < 90% 门**」。
- 门 2 的数据在案即已超限：同文件 `:464-468`，oracle100 中 AGREE 层 2 例错标、合计 **5/94 错标**（要求「100 格二次盲审内容错 ≤2」）；`:1005-1011` 的双行读配置自动覆盖只有 51%。
- 门 3/4（格级覆盖 ≥97%、chosen 错标率相对下降 ≥50%）与人工桶 266 字：全仓库 `grep` 无执行/过门记录（`docs/*.md` 仅审计文内目标值）。
- 572 门前置：`docs/AUDIT-2026-10-31-572-VERIFY.md:21,42-48`「auto precision **86.9% < 99%**」「572 门**不能开**」。
- 发布时点：`docs/RELEASE-v1.3.0-C.md:1-3`、`data/release-c.json:31`（release_date 2026-11-02）——**在门 1/门 2 已实测不达标之后发布**。
- 违反 §5.2 约束 5（`AUDIT-2026-10-31.md:213`：「疗效数字在 1–4 过完前不进任何文档」）：v1.3.0 文档仍写入质量数字，例如 `docs/RELEASE-v1.3.0-C.md:27`（0.4666）、`AGENTS.md:62-63`（0.471 / 0.4666）、`README-C.md:24`。
- §5.1 的两条原则（合格真迹优先、码位跟墨迹）与 §8.1 的「统计口径三查」均未登记进 AGENTS.md：`grep -n '合格真迹|码位跟墨迹|统计口径三查' AGENTS.md` 无命中，仅 `docs/AUDIT-2026-10-31.md` 自身有。
- 降级登记表未建：`ls work-c/real_rejected.jsonl` → **MISSING**（§5.1 要求字段 file/char/reason/verdict）。

**影响**：v1.3.0 的「QA OK」只覆盖字形/孔洞/打包（`RELEASE-v1.3.0-C.md:13-25` 全部是 80_qa/84_accept 项），不含标签质量门。下游读者会把发布说明里的质量数字当作「已过验收」，而项目自己冻结的验收门实际未过且未记录豁免。这是发布合规问题，不是字体缺陷。

**复现**

```bash
sed -n '205,215p;442p;464,468p' docs/AUDIT-2026-10-31.md
grep -n '合格真迹\|码位跟墨迹\|统计口径三查' AGENTS.md   # 无输出
ls work-c/real_rejected.jsonl                          # No such file
grep -n '0.4666' docs/RELEASE-v1.3.0-C.md AGENTS.md README-C.md
```

**建议**：① 在 `RELEASE-v1.3.0-C.md` 增加「验收门状态」节，逐条写明门 1 实测 85.2% 未过、门 2/3/4 未执行或未通过、发布由所有者以视觉选点批准（引用 `work-c/ckpt/v1.3/SELECTION.md`）；② 把 §5.1 两条原则与统计口径三查登记进 `AGENTS.md`；③ 建 `work-c/real_rejected.jsonl`，至少把本版 20 个全坏格与 44 个 holdout 丢失字登记进去（本次审计已给出 20 个字的完整名单，见 P2-6）；④ 此后任何质量数字必须同时在 `data/release-c.json` 或 eval json 中留可复算产物。

### P0-2 发布质量口径把 v1.2.1/旧实验数字当成 v1.3.0；0.4666 无任何可复核产物

**证据（同版本串号）**

| 字段 | 值（v1.3.0 口径文件） | 实际来源 | 证据 |
|---|---|---|---|
| `clean_dice` / `clean_chamfer` / `clean_broken` | 0.471 / 6.19 / 12.0% | **v1.2.1** 的 clean 数字 | `data/release-c.json:22-24,62`；`docs/RELEASE-v1.2.1-C.md:31` 同一组数 |
| `clean_font_dice/chamfer/broken` | 0.484 / 6.52 / 12.0% | **C/E30 的「v2 字体」**（n=3,201） | `data/release-c.json:55-56,62`；`docs/EXPERIMENTS-C.md:454-460` |
| `weight_bias` | 0.998 | v1.2.1 遗留（未重测） | `git show ef6e3f8^:data/release-c.json` 同值；当前 v1.3.0 字体实测见 `work-c/accept_c.json` = **1.009** |
| `weight_bias_px` | 0.906/0.902/0.958/0.939 | v1.2.1 遗留 | 同上；当前 `work-c/accept_c.json` 的 size_sweep bias 为 0.946/0.910/0.984/0.956 |
| `fallback_share_of_block` | 0.0712 | v1.2.1 的 1,495/20,992 | `git show ef6e3f8^:data/release-c.json`（ribbon_chars 1495）；v1.3.0 应为 1,313/20,992 = **0.0625** |
| `unseen_dice` | 0.4666 | **无可复核产物**（见下） | `data/release-c.json:58` |

- `docs/RELEASE-v1.3.0-C.md:27` 与 `work-c/ckpt/v1.3/SELECTION.md` 都写 ep090 CPU 300 字 Dice ≈0.4666，但全仓库没有任何文件记录该次评测：`work-c/preview/v13_large_eval.json` 只覆盖 v121/ep20/ep35/ep80，`work-c/preview/v13_ep_metrics.json` 无 ep90；`docs/AUDIT-2026-11-01-MPS-VAL.md:25-35` 的 CPU 表也无 ep90。`grep -rn '0.4666'` 只命中 `docs/RELEASE-v1.3.0-C.md:27`。
- `clean_metric_working_point` 描述与现行脚本默认不符：`data/release-c.json:53` 写「close 2」，而 `scripts/82_eval_c.py:107` 当前默认 `--close 4`；且该 working point 下产出的 clean 数字实际来自 v1.2.1/更早。
- `AGENTS.md:62-63` 把 0.471 归属于「v1.3.0」，与 `docs/RELEASE-v1.2.1-C.md:31`（v1.2.1 clean 0.471）冲突。
- 选点证据冲突：审计正文结论是 **ep35**（`docs/AUDIT-2026-10-31.md:1267,1277`、`docs/AUDIT-2026-11-01-MPS-VAL.md:33,44`「选点改 CPU」），发布却是 ep090，仅以所有者视觉判断记录（`work-c/ckpt/v1.3/SELECTION.md`）。视觉选点本身可以成立，但发布说明把 0.4666 写成全字段数字却无 eval 产物，使选点无法复核。

**影响**：项目明示「口径 `data/release-c.json`」（`AGENTS.md:74`），而该文件的质量字段混合了两个旧版本的测量值。任何人按口径文件做对比或复现，都会得到错误的 v1.3.0 质量结论；机读发布记录不可作为验收依据。

**复现**

```bash
python3 - <<'EOF'
import json;d=json.load(open('data/release-c.json'))
print({k:d[k] for k in ('clean_n','clean_dice','clean_chamfer','weight_bias','fallback_share_of_block','unseen_dice')})
EOF
grep -rn '0.4666' docs work-c/preview work-c/logs-v1.3 2>/dev/null | grep -v Binary   # 仅 docs/RELEASE-v1.3.0-C.md
git show ef6e3f8^:data/release-c.json | head -40
diff <(python3 -c "import json;d=json.load(open('work-c/accept_c.json'));print(d['weight_bias']);print(d['size_sweep'])") /dev/null
```

**建议**：① 用 `82_eval_c.py` 在 `work-c/pairs_holdout.npz`（300 字，字级未见）上对 `work-c/ckpt/v1.3/c_ep090.pt` 重跑一次，把完整结果落盘（如 `work-c/eval_c_v130.json`），再回填 `release-c.json`；② 把 `clean_*` 字段改名为带版本来源的字段或删除，并补一次 v1.3.0 clean 集（3,210 字）实测；③ `weight_bias`/`weight_bias_px`/`fallback_share_of_block` 用 `work-c/accept_c.json` 与 1,313/20,992 覆盖，并在文件里标注测量脚本与日期；④ 在 RELEASE 中同时写「审计推荐 ep35、所有者视觉选 ep090」两条事实。

---

## 2. P1

### P1-1 §5.1 需求未落地：无降级登记表、无真迹质量闸的落地证据

- `docs/AUDIT-2026-10-31.md:195-203` 要求：合格真迹优先；未过 87 号质量闸或标签未验证时降级并在降级登记表/发布说明披露计数。现状：`work-c/real_rejected.jsonl` 不存在（`ls`）；`87_check_choices_c.py` 最后一次修改在审计之前，v1.3.0 的 chosen 生成命令（`work-c/v13_chain.sh`）没有 87 闸；发布说明没有「真迹降级计数」项（`docs/RELEASE-v1.3.0-C.md:6-11` 只写 20 个全坏格）。
- 影响：真迹优先原则的「质量闸语义」只能靠人工约定，下一版重跑 05 时无登记表可对照。
- 复现：`ls work-c/real_rejected.jsonl; grep -n '87' work-c/v13_chain.sh docs/RELEASE-v1.3.0-C.md`
- 建议：建表并把 20 个全坏格、44 个 holdout 丢失字、`园/四` 白名单特例写入；05 流程串入 87 闸或写明豁免。

### P1-2 §8 待登记事项只落地一半

| §8 条目 | 状态 | 证据 |
|---|---|---|
| 1. AGENTS.md 登记 §5.1 两条原则 + 统计口径三查 | **未落地** | `grep` AGENTS.md 无命中；AUDIT 文内目标值在 `AUDIT-2026-10-31.md:280` |
| 2. `96_fix_labels_c.py` relabel 时 `agree_ab=False` | **未落地** | 文件 `scripts/96_fix_labels_c.py`（mtime 2026-10-28 16:15）无 `agree_ab` 逻辑 |
| 3. cellbox probe 固化为 `scripts/99z_*` | **已落地**（命名 `99za`） | `scripts/99za_cellbox_probe_c.py`（10-31 10:55），仅 diagnostic，未进生产链 |
| 4. `work-c/ocr_bench.json` 建 bench 并在 DATA-C §6 登记来源/许可 | **部分** | 文件在（700 唯一格 / 1,272 原始条，`docs/DATA-C.md:113`）；§6 只有运行命令（`:154-155`），无「数据来源与许可见核」登记段 |
| 5. MANIFEST/检查点 | n/a（本轮未训练） | — |

- 影响：审计要求的「可追溯性」尾部欠账；其中 96 的 stale `agree_ab` 会在后续 05 运行中继续影响 `--prefer-ab` 的选择（16 个 亙 格的已知问题）。
- 建议：按表逐项补登记；96 的修复按审计给的方案改（relabel 时同步 `agree_ab=False`）。

### P1-3 §6 的核心结构性修复（P0-A/P0-C）未落地；v1.3.0 只是数据链小补，发布文档未声明差距

- `docs/PLAN-C-v1.3.0.md:233-247` 的 P0-A「字符框对位层」：`scripts/92_ocr_c.py`（mtime 2026-10-27）无 `return_word_box`/`return_single_char_box`（`grep -c` = 0），OCR 产物仍只有行级框；匹配器只以 diagnostic 形式存在（`scripts/99za_cellbox_probe_c.py`），未接入标注/选优。
- P0-A.4「05 只读 verified 池、删除 q」：`scripts/05_select.py:171-183` 仍以 `-0.25*q`（Laplacian 锐度）参与打分，且脚本无任何 verified 池过滤；`work-c/verified/index.jsonl` 只有 572 行，是 VLM bench 锚点，不是 chosen 候选池。
- P0-C「池级守卫硬闸」：`scripts/99q_wenkai_ref_c.py:1-7` 文件头明写「never used as a hard gate」；该文件最后修改 2026-10-30，早于审计。
- 新增的只有 `05 --drop-if-all-flagged` 与 `自` 换样本（`docs/RELEASE-v1.3.0-C.md:8-9`）。`plan-v1.3.0 §5` 的验收表（500 常用字硬闸、每字 top-10 全跑、成品反查 OCR 全量回归等）无任何执行记录。
- 影响：v1.3.0 的标签仍依赖未经格级验证的双引擎一致（README 已披露 6.7% 盲审错标率），与「审计后应有结构性修复」的预期不符；发布文档未说明这一差距，只写「QA OK」。
- 建议：RELEASE 增「本版未执行项」清单；下一版按 §6 顺序落地 P0-A/P0-C，或由所有者正式冻结放弃并写进 AGENTS。

### P1-4 ep090「清理前 pairs 训练、清理后 chosen 生成」边界成立，但披露不完整、影响未评估

- 边界成立：训练日志 `work-c/logs-v1.3/train_v13.log`（11-01，ep80 于 20:19 结束）+ `train_v13_90.log`（23:54 结束）；清理链 `work-c/logs-v1.3/clean_05/06/76/08/73/75` 均在 **11-02 08:31–08:38**；`work-c/ckpt/v1.3/c_split.json` 记录 `n_train_pairs 4,857`，当前 `work-c/pairs/pairs.npz` 只有 4,961 字（差 20），与「清理后重建」一致。
- 披露位置只有 `docs/RELEASE-v1.3.0-C.md:40-41`；**出厂包内的 `README.md`（= `README-C.md` 换图片前缀）没有这条边界**，`data/release-c.json:32` 的 note 也没有。
- 未评估的具体影响：被剔除的 20 个字全部在 ep090 的训练目标集里（`c_split.json` 的 `train_chars` 含全部 20 字），而它们现在的字体字形由同一个模型重新生成（17 个 `base` + 3 个 `gen`，见 `work-c/generated.jsonl`）。这 3 个 GAN 字形是「模型曾在这些字自己的、后被判定为不可用的坏格上训练」的产物，风险高于普通合成字；发布说明未提示、无人工复核记录。
- 复现：

```bash
python3 - <<'EOF'
import json
s=json.load(open('work-c/ckpt/v1.3/c_split.json')); tr=set(s['train_chars'])
dropped=set('侂倭呀哽喋婬淝矍筴簸耋蚩貔蹂鄄鏘顱餕黠齬')
print('dropped in train_chars:', len(dropped & tr))
gen={}
for l in open('work-c/generated.jsonl'):
    r=json.loads(l); gen[r['char']]=r.get('src')
print({c:gen[c] for c in dropped})
EOF
```

- 建议：① 把这条边界补进出厂 README 的「已知限制」；② 对 20 个字（尤其 3 个 GAN 字 婬/餕/齬）做一次视觉/结构复核并记录；③ 下一版重生成/重训前把这 20 字从训练目标中彻底隔离。

### P1-5 生成链有一次未记录的重跑：主运行日志与出厂产物对不上，1,313 的构成不可复核

- 主运行日志 `work-c/logs-v1.3/gen_v13_ep90.log:1`「to generate **15715** method gan …; skip 5277 real chars」，末行「done **15715** of 15715; fallback **836**」。
- 出厂 `work-c/generated.jsonl` 是 **15,735 行**（= 20,992 − 5,257）；`work-c/gan_fallback.json` 只有 **17 项**（恰为 20 个被剔除字中 17 个走后处理回退的字），文件 mtime 11-02 08:35。
- 唯一自洽解释：清理链把 chosen 从 5,277 降到 5,257 后，又对 20 个字做了一次 `77 --only … --out-append` 修复运行（无日志文件），它把 `gan_fallback.json` 覆盖成了只含本次的 17 项，并 append 了 20 行（17 `base` + 3 `gen`）。该运行没有命令记录，主运行的 836 项回退原因列表因此丢失。
- 另外：按 `77_generate_c.py:333` 的判定条件复算，1,313 个 `base` 中 622 个满足 `s2t(ch)!=ch`（可能来自结构守卫），691 个不满足（只能来自基础守卫失败；其中 17 个即上述后处理回退）。**回退原因在产物里不可区分**，文档只给了总量。
- 影响：无法从仓库复现「1,313 = 守卫失败多少 + 结构守卫多少」；若后续按 `gan_fallback.json` 统计会严重低估（17 vs 836）。`docs/EXPERIMENTS-C.md:510` 已记录同类口径事故（旧 REPORT 只数 602），本版仍有残留。
- 复现：`head -1 work-c/logs-v1.3/gen_v13_ep90.log; tail -1 work-c/logs-v1.3/gen_v13_ep90.log; wc -l work-c/generated.jsonl; wc -c work-c/gan_fallback.json`
- 建议：① 把 20 字修复运行写成脚本并补日志/命令记录；② 生成脚本把「每个 base 行的原因」写进 generated.jsonl（如 `fallback_reason: struct_guard|guard|trace`），或在 manifest 里保存本次 run 的 fallback 列表；③ 在 RELEASE 里给出可复核的分解。

### P1-6 重建说明无法复现 v1.3.0（checkpoint、轮数、val 协议均不同，且无告警）

- `docs/DATA-C.md:180-183` 的生成命令用 `--ckpt work-c/ckpt/c_ep030.pt`（v1.0.0 时代）与 `--epochs 80`，不是发布的 `work-c/ckpt/v1.3/c_ep090.pt`/90 轮；`docs/DATA-C.md:176` 的训练命令写 `--epochs 80` 且**没有** `--val-data work-c/pairs_holdout.npz`（实际训练用了它，见 `docs/AUDIT-2026-10-31.md:1232`）。
- `scripts/77_generate_c.py:198` 的 `--ckpt` 默认值是 `work-c/ckpt/c_ep034_v120.pt`（v1.2.0），而 77 对 release 工作点的交叉校验只覆盖 threshold/close/blend/hole_repair/struct_guard（`:265-284`），**不校验 checkpoint**，也没有告警。照 DATA-C 或默认参数执行会静默得到另一个模型的字体。
- 复现：`sed -n '173,184p' docs/DATA-C.md; grep -n 'c_ep034_v120' scripts/77_generate_c.py; sed -n '265,285p' scripts/77_generate_c.py`
- 建议：DATA-C §6 更新为 v1.3.0 实际命令（含 ckpt、90 轮、`--val-data`、`--val-n 300`）；77 增加 checkpoint 哈希/路径与 `release-c.json:checkpoint` 的比对告警（只读告警即可）；把 `work-c/v13_chain.sh`、清理链、生成命令一并进仓库脚本。

### P1-7 出厂 README（= `release-c/README.md`）自相矛盾且含错误跨线数字

| 位置 | 问题 |
|---|---|
| `README-C.md:21` | 「清理 20 個全壞格（**5,302 → 5,257**）」：20 格只解释 5,277→5,257；5,302→5,277 是 44 丢失 + 19 新增的数据链变化（`docs/AUDIT-2026-11-01-V13-DATA-VERIFY.md:15-19`）。`docs/RELEASE-v1.3.0-C.md:8` 与 `data/release-c.json:32` 同一错误。`work-c/ckpt/v1.3/SELECTION.md` 写的才是正确的 5,277→5,257。 |
| `README-C.md:22` vs `:97` | 同一份文档先说「合成字由 **90 輪 ep090** 生成」，处理链一节又写「GAN（**30 輪**…；ep20–30 已進平台）」。 |
| `README-C.md:66` | 对照表写 B 線真跡 **4,078（19.4%）**；实际 B v1.2.4 为 **4,073**（`README-B.md:21,54`、`data/release-b.json:real`、`build/GuanGeKai-B-Real.ttf` numGlyphs−1 = 4,073，`work-c/verify_ab.json` 同）。 |
| `README-C.md:114` | 「合成字與真跡字重比 0.948（48px）」「真跡墨量/文楷 0.705」与 `work-c/accept_c.json` 的 48px bias 0.956、real_ink_over_wenkai 0.635 不同口径且未注明，无法复核。 |

- 影响：出厂包内文档是用户唯一能看到的说明，其中两处直接矛盾、一处跨线数字错误。
- 建议：改 README 后按 AGENTS 发布流程重跑 81/打包/哈希并同步 `release-c/SHA256SUMS`、zip 与 `data/release-c.json`（注意这会改变 zip 哈希，需一并更新）。

### P1-8 `83_verify_ab_c.py` 的持久化证据早于 C 字集检查写入，闸门结果可与落盘文件矛盾

- `scripts/83_verify_ab_c.py:141-144` 先把 `info["ok"]=bool(ok)` 写进 `work-c/verify_ab.json`；`:148-166` 才做三线 21,034 字集检查并可能在失败时 `ok=False`。因此 C 字集检查失败时：脚本退出码 1、屏幕打印 FAIL，但 `work-c/verify_ab.json` 里仍是 `"ok": true, "issues": []`。
- 同一段的 C 检查还有两个覆盖缺口：字体不存在时 `continue` 静默跳过（C 字体缺失也能打印 `A/B INTACT`）；`ZIPS` 只钉 A/B 三个 zip（`:40-43`），C 的分发 zip 不在任何闸门覆盖内（见 P2-7）。
- 附：`work-c/verify_ab.json` 目前只有 A/B 的 `checks`，没有 C 的任何字段；`83` 的 docstring 还写着「B chosen 4,078」（`:10`），代码实际断言 4,073（`:99`）。
- 复现：`sed -n '136,170p' scripts/83_verify_ab_c.py; cat work-c/verify_ab.json | head -5`
- 建议：把 punct 循环移到 `info` 写入之前；C 缺失时 `ok=False` 或显式 `WARN` 并写进 info；给 C zip 加哈希钉（或明确说明 C zip 由 81/14 打包流程单独校验）。

### P1-9 ribbon 计数三源不一致（1,228 / 1,313、6.25% / 8.3% / 0.0712）

| 位置 | 数字 |
|---|---|
| 实际（字体 provenance / `generated.jsonl`） | **1,313**（= 20,992 的 6.25%，= 15,735 合成块的 8.34%） |
| `docs/GLOSSARY.md:26`、`docs/CONVENTIONS.md:115` | C 线 **1,228 字（7.8%）**（过期） |
| `AGENTS.md:60` | 1,313（**6.25%**，分母 20,992） |
| `docs/RELEASE-v1.3.0-C.md:22`、`README-C.md:23` | 1,313 / 15,735 = **8.3%** |
| `data/release-c.json:27` vs `:46` | `fallback_share` 0.0834（正确，块分母）与 `fallback_share_of_block` 0.0712（v1.2.1 遗留）并存 |

- 影响：术语规范源（GLOSSARY）本身是过期数；同一「占比」在文档里有三种分母且只有 RELEASE 写清分母。
- 建议：统一写成「1,313 = 20,992 的 6.25% = 15,735 合成块的 8.34%」，更新 GLOSSARY/CONVENTIONS，删除或修正 `fallback_share_of_block`。

### P1-10 生成工作点的墨量参数不可追溯；ribbon 回退拟合在清理后重建，与主运行不同源

- 发行记录声明墨量工作点：`data/release-c.json:37-41`（`ink_curve: [39.4438, 0.4318]`、`ink_gain 1.25`）。但 `scripts/77_generate_c.py:237-241` 的默认值是 `--ink-a 38.7258`、`--ink-exp 0.5701`、`--ink-gain 1.10`；仓库内唯一的生成封装 `work-c/finalize_c.sh` 与 `docs/DATA-C.md:181-183` 的命令**都没有传这三个参数**，77 的发行交叉校验（`:265-284`）也只查 threshold/close/blend/hole_repair/struct_guard，**不查 ink_a/ink_exp/ink_gain**。v1.3 的生成命令没有留下 argv（`work-c/logs-v1.3/gen_v13_ep90.log` 只有汇总行），因此无法确定出厂字形实际用的是 39.4438/0.4318/1.25 还是代码默认 38.7258/0.5701/1.10——两者在字重上约差 10–14%。
- ribbon 回退的拟合也在同一窗口里被重建：`scripts/generate_lib.py:120-134` 的 `ribbon_scale_c` 在运行时读 `work-c/ribbon_fit.json`；该文件由 `73_fit_width_c.py` 从 pairs 现拟合。主生成运行（11-02 01:36）之后，清理链在 **11-02 08:34** 重跑了 73（`work-c/logs-v1.3/clean_73.log`），`ribbon_fit.json` 现值为 a=36.492/exp=0.4233/base=1.1238；随后 17 个字的修复运行（P1-5，08:35）用的就是这份**新的** fit，而主运行的 1,296 个 ribbon 字用的是清理前 fit。两种 ribbon 笔画标定混在同一份 `generated.jsonl` 里。
- 影响：出厂字重的「声明值」与「实际生成值」两者至少有一个无法证明；1,313 个 ribbon 字形内部存在两套拟合常数。这两点都直接关系到 README 的「合成字与真迹字重比」口径（P1-7）。
- 复现：`sed -n '235,245p' scripts/77_generate_c.py; sed -n '118,135p' scripts/generate_lib.py; cat work-c/ribbon_fit.json; grep -n 'ink_curve\|ink_gain\|ink_a\|ink_exp' data/release-c.json`
- 建议：① 把 v1.3 的实际生成命令落盘（含全部参数），或直接用 `release-c.json` 的值重新显式传入并在 77 中加「与 release 工作点不一致即警告」的完整参数校验（含 ink_*）；② `finalize_c.sh` 补 `--ink-a/--ink-exp/--ink-gain`；③ 若确认 17 字修复用的 fit 与主运行不同，重跑这 17 字的 ribbon（<1 分钟）以统一标定；④ 在 RELEASE 写明墨量工作点的实际来源。

---

## 3. P2

### P2-1 `80_qa_c.py` 的工作目录从 `--outdir` 的父目录推断，自定义输出目录必失败
`scripts/80_qa_c.py:114` `wd = Path(args.outdir).parent`，脚本没有 `--work` 参数；`:120` 找不到 chosen.jsonl 就 `SystemExit`。实测：
`python3 scripts/80_qa_c.py --outdir /tmp/cqa --sheets 1` → **QA FAILED: cannot determine the expected real-subset size**；加 `--real-expect 5257` 后全部通过（见 §5 B4）。另 docstring `:12` 仍写「default 4070」（B 线遗留）。建议：加 `--work`，默认 `work-c`，real 期望与 chosen 从 `--work` 读。

### P2-2 `77_generate_c.py` 的组件数守卫阈值三处写法不一致
`:58` docstring「components off by **>3**」；`:107` 实际 `abs(comps-comps_w) <= CFG["comp_tol"]`，默认 **6**（`:212`，与 `release-c.json:comp_tol` 6 一致）；`:333` 结构守卫分支用 **>2**（与 `AGENTS.md:72` 一致）。另：`w = raw**1.4` 与 `78_fill_fallback_c.py:49` 的相同常数、以及 78 硬编码的 ribbon `turdsize=8`（GAN 用 `turdsize=3`）都没有在 C 线文档登记，建议一并写入 DATA-C §6。建议：改 docstring 为「base guard: comp_tol 6；struct guard: >2」，并把两个阈值分开命名。

### P2-3 `docs/DATA-C.md` 陈旧数字与版本混杂
`:108` chosen 5,302 行（现 5,257）；`:123` 「最终真迹 5,302 字（25.26%）」（v1.3.0 为 5,257/25.04%，同文档 §5.1 已写 v1.3.0 5,257）；`:106` ocr_v6/v5「待补」；§5 校验和仍是 v1.2.1 的（`:129-132`，§5.1 才是 v1.3.0）；`:110` pairs.npz「5,002 对」（实际 4,961）；`:163-165` 的 pairs_clean 备注「建于 2026-10-28」对 v1.3.0 已不成立（现文件 11-02 08:37）。建议：把 §4/§5 明确标「v1.2.1 历史值」或更新到 v1.3.0。

### P2-4 `docs/CLEANUP-C.md` 数字与命名
`:179` pairs_clean「3,200」实际 **3,210**（`work-c/pairs_clean.npz` 与 `data/release-c.json:clean_n` 均 3,210）；`:174-178` §I 标题「v3c 核心切图收口」列出的 `chosen.jsonl 5,299` 既不是 v1.3.0 的 5,257 也不是当时的 5,277，且 v1.3 用的是 v3d2 而非 v3c，章节名与内容矛盾。建议：更正数字与 v3c/v3d2 指称。

### P2-5 `AGENTS.md:62` 的 v1.3.0 日期错误
写「v1.3.0（**2026-11-12**）」，但发布记录、zip、字体、`data/release-c.json:31` 全部是 **2026-11-02**；11-12/13 只有文档与脚本修订（git `83d01d9` 2026-11-13）。建议改 2026-11-02，11-13 的修订另注。

### P2-6 20 个被剔除字没有 manifest，发布说明只具名 3 个
`docs/RELEASE-v1.3.0-C.md:8`、`README-C.md:21` 只列「含哽/筴/呀」；完整名单只能通过 `diff work-c/v13_preclean_chosen.jsonl work-c/chosen.jsonl` 得到。本次审计复核出的完整名单（已核对全部 `bad=true`）：
**侂 倭 呀 哽 喋 婬 淝 矍 筴 簸 耋 蚩 貔 蹂 鄄 鏘 顱 餕 黠 齬**（`v13_preclean_chosen.jsonl` 5,277 − `chosen.jsonl` 5,257 = 20，`generated.jsonl` 中现为 17 `base` + 3 `gen`）。建议在 P1-1 的登记表里逐一登记，并在 RELEASE 给出完整名单。

### P2-7 C 分发 zip 没有自动闸门
`83` 的 `ZIPS` 不包含 `GuanGeKai-C-v1.3.0.zip`（`scripts/83_verify_ab_c.py:40-43`，只钉 A/B）；`81_package_c.py` 只对 `release-c/` 目录写 `SHA256SUMS`，zip 的 SHA 是手工写进 `data/release-c.json:71-72` 与 `docs/DATA-C.md:214`。**本次已手工核对一致**（§5 B2），但流程上 zip 完整性依赖人。建议把 C zip 哈希加入 83 或独立 checklist 脚本。

### P2-8 83/CONVENTIONS 的陈旧示例
`scripts/83_verify_ab_c.py:10` docstring「B chosen 4,078」（代码 4,073）；`docs/CONVENTIONS.md:139-142` 举例仍写「`83_verify_ab_c.py:31` 硬编码 `GuanGeKai-v1.6.5.zip`」及其哈希（现为 v1.7.2 / B v1.2.4 / B v1.2.2）。建议同步。

### P2-9 `84_accept_c.py` 字重闸实现与文档口径的微差
文档口径「字体级字重 0.90–1.15」（`AGENTS.md:83`）；实现中字体级 `weight_bias` 检查双侧 0.90–1.15（`84_accept_c.py:227`）、12px 只查上界 1.15（`:235`，下界无）、16px 用 0.88–1.15（`:239`）。建议在 RELEASE 或脚本 help 里写清「12/16px 为辅助闸、用宽松下界」，避免读者以为四档都是 0.90–1.15。

### P2-10 `data/release-c.json` 描述性字段不随代码默认
`:53` `clean_metric_working_point` 写「close 2」，`scripts/82_eval_c.py:107` 当前默认是 4。该字段描述的是旧测量工作点，但未标版本；与 P0-2 一起修。

---

## 4. AUDIT-2026-10-31 冻结决策、行动清单、待登记事项逐条落地核对

### 4.1 §5 冻结决策

| 条目 | 状态 | 证据 |
|---|---|---|
| §5.1 合格真迹优先（质量闸语义） | **未落地**（AGENTS 未登记，无降级表） | `AUDIT-2026-10-31.md:195-203,280`；`ls work-c/real_rejected.jsonl` 缺失 |
| §5.1 码位跟墨迹 | **未登记** | `grep AGENTS.md` 无命中；96 的 relabel 行为存在但无纪律记录 |
| §5.2 门 1 WRONG_LABEL precision ≥90% | **实测未过**：23/27 = 85.2% | `AUDIT-2026-10-31.md:442` |
| §5.2 门 2 AGREE precision（100 格错 ≤2） | **无过门记录**；oracle100 合计 5/94 错标 | 同文 `:464-468` |
| §5.2 门 3 覆盖终态 ≥97% | **无执行记录** | 全仓库 grep 仅审计文内目标值 |
| §5.2 门 4 chosen 错标率相对下降 ≥50% | **无执行记录** | 同上 |
| §5.2 约束：过门前疗效数字不进文档 | **违反** | `RELEASE-v1.3.0-C.md:27`、`AGENTS.md:62-63`、`README-C.md:24` |
| §5.2 约束：v1.2.1 冻结不动 | 表面成立（v121_backup 与 v1.2.1 zip 在） | `work-c/v121_backup/`、`GuanGeKai-C-v1.2.1.zip` |
| §5.2 约束：不全量重切 | 成立（v3d2 cells 未重跑） | `work-c/cells` mtime 2026-10-30 |
| §5.2 约束：人工桶下限 266 字 | **无执行记录** | 无对应产物 |
| §5.3 冻结数字表 | 未复算（本报告未做 labeled 全量扫描） | 列入 §6 未覆盖 |

### 4.2 §6 行动清单

| 条目 | 状态 | 证据 |
|---|---|---|
| P0-A.1 92 加字符框 API | **未做** | `grep -c 'return_word_box\|single_char' scripts/92_ocr_c.py` = 0，mtime 10-27 |
| P0-A.2 匹配器 | **仅 diagnostic** | `scripts/99za_cellbox_probe_c.py`，未接入 05/94 |
| P0-A.3 verified 池进标注/训练 | **未做** | `work-c/verified/index.jsonl` 572 行为 bench 锚点；05 无 verified 过滤 |
| P0-A.4 05 只读 verified、删 q | **未做** | `scripts/05_select.py:171-183` q 仍在、无 verified 池 |
| P0-A.5 266 字人工口径 | **无记录** | — |
| P0-B OCR bench | **已落地** | `work-c/ocr_bench.json`（700 唯一 / 1,272 原始，`DATA-C.md:113`）、`scripts/99z_build_ocr_bench_c.py` |
| P0-C 池级守卫硬闸 | **未做** | `scripts/99q_wenkai_ref_c.py:1-7`「never used as a hard gate」 |
| P1-A 训练测量修复 | **部分** | val 用 pairs_holdout ✓（`c_split.json`、`AUDIT:1232`）；但训练内 val 只 8 对（`AUDIT:1240`）、`_best` 按 MPS val（`SELECTION.md`/`MPS-VAL:32`）、clean 未换 verified 格 |
| P1-B 训练抗噪（多目标/自清洗） | **未做** | 无产物；且与 PLAN-C-v1.3.0 D2「不做多目标」冲突未裁决 |
| P2 VLM 第三见证 | **实验完成、生产未接入** | `scripts/99zb/99zd/99ze`；无 pin 与生产记录 |
| P3 96 relabel 同步 agree_ab=False | **未做** | `scripts/96_fix_labels_c.py` 无 agree_ab |
| 「明确不做」清单遵守情况 | 未重切 ✓ / 无轮廓补偿 ✓ / 不把聚类当标签 ✓ | — |

### 4.3 §8 待登记事项

见 P1-2 表。

### 4.4 跨线一致性（05/06/08/10/punct_set/13_qa/83）核对

| 共用面 | 状态 | 证据 |
|---|---|---|
| `05_select.py` / `06_norm.py` / `08_make_pairs.py` | A/B 产物未被 C 改动破坏 | A/B 字体 SHA 与各自 release 校验和一致、A chosen 1,675 / B chosen 4,073 / 覆盖 20,992（§5）；AUDIT 要求的「C 兼容改动用 A 数据复跑」结论在 `AGENTS.md:85-86`，本次无法重跑但产物级等价复核通过 |
| `punct_set.py` | 唯一真源且校验是精确集合校验 | `punct_set.py:19-20` CHARS 2+10+10+20=42，`EXPECTED_CMAP=21034`；`verify()` 缺任一码位即报错、残留弯引号也报错。三线 cmap 均 21,034（§5） |
| `13_qa.py` | **C 线并不使用**（C 用 `80_qa_c.py`）；AGENTS 把它列在共用脚本里是口径不清 | `scripts/13_qa.py` 无 `--line`/C 分支，默认 A 字体；AGENTS.md 最短验证命令只用于 A |
| `83_verify_ab_c.py` | 覆盖 A/B 全字集 + C 的标点集合口径，但 C 的字数/真迹数不在 `checks` 里 | `83:88-101` 的 `checks` 只有 A/B；C 只走 `:148-166` 的 `punct_set.verify`；C 缺失静默跳过（P1-8） |
| 共享脚本回归风险 | 本次未发现已发生的回归；**未来**改 05/06/08 后没有自动 A/B 重建对比，83 只能发现「字体文件被改」，不能发现「脚本行为变了但 A/B 未重建」 | 建议把 AUDIT 的 A 数据复跑（或 `07+11` 的 A 重建 diff）固化成脚本 |
| w 口径（逐笔相对宽度） | C 用自己的 `work-c/stroke_rel_width.npy`（73 从 C pairs 拟合，`ribbon_fit.json:rel_widths 89389`），符合「C 自己的曲线，不复用 A/B」（`docs/PLAN-C.md:58`）；但 `w = raw**1.4` 的 1.4 是从 A 线写法直接复用（`docs/EXPERIMENTS.md:537` 记的是 A 线 `dip^1.4`），C 线文档没有登记这两个常数 | `scripts/77_generate_c.py:129`、`78_fill_fallback_c.py:49`；`docs/PLAN-C.md:58` |

---

## 5. 已核查不成立 / 已披露（复核通过，写在这里避免重复报告）

| 检查 | 结果 | 证据/命令 |
|---|---|---|
| 字体 SHA、大小、版本 | 全部一致 | `shasum -a 256 build/GuanGeKai-C-*.ttf` = `data/release-c.json:69-70` = `docs/RELEASE-v1.3.0-C.md:34-35` = `docs/DATA-C.md:212-213` = `release-c/SHA256SUMS` |
| cmap 21,034 / 基本区 20,992 / 42 标点 | 一致 | fontTools：Regular 21,034（block 20,992 + 42）、Real 5,257（non-block 0）、版本 `Version 1.3.0`、family `GuanGe Kai C` |
| 真迹 5,257、GAN 14,422、ribbon 1,313 | 一致 | `generated.jsonl` src = gen 14,422 / base 1,313；`chosen.jsonl` 5,257 唯一；`real_contours.jsonl` 5,257；`provenance.json` 21,034 条 = real 5,257 + gan 14,422 + ribbon_fb 1,313 + punct 42，且集合与 chosen/generated 完全相等 |
| release-c 目录完整性 | 10/10 OK | `cd release-c && shasum -a 256 -c SHA256SUMS` 全 OK |
| zip 完整性 | SHA 与包内文件均一致 | zip SHA = `4b473775…f5498`（`data/release-c.json:72`）；`unzip -l` 11 文件；包内字体/provenance/stats/coverage/README 的 SHA 与 `release-c/` 对应文件逐一相同 |
| 80_qa_c 验收块（RELEASE:13-25） | 可复现，全部通过 | /tmp 复跑：coverage 20,992；empty/tiny/huge 0；real-subset 5,257 OK；holes lost **3/214 = 1.4%**（汜/秠/誙）；fewer 53/214=24.8%；common holes 0；punct OK；QA OK。与 `work-c/qa/stats.json`、`work-c/qa/holes.json` 一致 |
| 83「三个 21,034 + A/B INTACT」 | 只读复算通过 | A/B 四款字体 SHA 与 `release/SHA256SUMS`、`release-b/SHA256SUMS` 全部 OK；A/B/C coverage 20,992；punct_set.verify 三线 21,034 全 OK；三个钉住的 zip 哈希 OK；A chosen 1,675 / B chosen 4,073 / A prov real 1,675 / B prov real 4,073 全对 |
| 97 术语检查 | 通过 | `python3 scripts/97_check_terms.py` → `TERMS OK`（白名单 23 文件、15 行豁免） |
| 「训练 val 改字级未见 pairs_holdout」 | **成立**（针对出厂 checkpoint） | `c_split.json` val_chars 300 = `char_holdout.json` = `pairs_holdout.npz` chars；train_chars 4,981 与 val 无交集；`AUDIT-2026-10-31.md:1232` 确认训练命令带 `--val-data work-c/pairs_holdout.npz` |
| 「ep090 清理前 pairs 训练」边界 | **成立**，已在 RELEASE 披露（但 README 未披露，见 P1-4） | 训练日志 11-01；清理链日志 11-02 08:31-08:38；`n_train_pairs 4,857` vs 当前 pairs 4,961 |
| 20 个全坏格剔除 | 可复现 | `v13_preclean_chosen.jsonl` 5,277 → `chosen.jsonl` 5,257，20 字全部 `bad=True`；名单见 P2-6；`SELECTION.md` 记 5,277→5,257 正确 |
| `自` 换回完整样本 | 成立 | `chosen.jsonl` 中 `自` 的 file = `p31_0054_c00_l02_s019.png`，n_samples 3,121 |
| 结构守卫口径 | 与 AGENTS 一致（只有 docstring 过期） | `77_generate_c.py:333` 结构守卫 >2；基础守卫 comp_tol 6 与 `release-c.json:comp_tol`、DATA-C 命令一致 |
| work-c-big 与文档 | 一致 | chosen 651、pairs 651、pairs_clean 109、generated gen 19,090 + base 1,251；`work-c-big/REPORT.md:4,20,48-62` 已含 109→47 unseen 更正；`104_eval_big_c.py` 已改 CPU、旧 MPS 面板已作废（`REPORT.md:59`） |
| 2026-11-13 audit commit 的 C 相关改动 | 一致，未引入不一致 | `100_review.py` 给 C 的 B2 板改用 `pairs_holdout.npz` 并缺失即报错；新增 C 专用 strata seed；`104_eval_big_c.py` 改 `dev="cpu"`；与 `docs/EXPERIMENTS-C.md:472-510` 的更正一致 |
| release-c 包内 README 与仓库 README-C | 仅图片前缀不同 | `diff README-C.md release-c/README.md` 只有 2 行 `docs/images/` 前缀差异（81_package_c 设计如此） |
| 孔洞白名单 | 正确 | `80_qa_c.py:common_holes` 不含 四/园；实测跳过 `门`（文楷本身无孔） |
| A/B 未受 C 影响 | 成立 | §5 83 复算；A/B 字体 SHA 与各自发布校验和一致 |
| release-c/stats.json `glyphs 21035` | 正常 | = cmap 21,034 + `.notdef`；`codepoints 20992` 指基本区，`cmap_codepoints 21034` 指总码位 |

---

## 6. 未覆盖 / 审计限制

1. **未运行 `83_verify_ab_c.py` 原脚本**：它会写 `work-c/verify_ab.json` 与 `work-c/ab_baseline.json`（项目文件），按审计约束改为只读等价复算（§5）。
2. **未重跑标注质量门**：四级门的 WRONG_LABEL/AGREE 复测需要人工盲审或第三方 VLM，超出本次只读范围；本报告只核对「已有记录是否过门」。
3. **未复算 §5.3 冻结数字表**（需要全量扫 `work-c/labeled.jsonl` 731 MB 并按审计 §9 命令重算 266/175/791/1051）；如需可补跑，预计 1–2 分钟。
4. **未验证 struct-guard 是否对繁体/异体码位过度回退**：需要以 `--no-struct-guard` 重跑生成（禁止）；本次只能给出「1,313 个 base 中 622 个满足 s2t 条件、691 个只能来自基础守卫」的静态分解。
5. **未检查 C 线最终字形的视觉质量/小字号表现**（需渲染面板，属人工判断）；未重生成 `98_style_sheet` 类面板。
6. **未逐条复核** `docs/PLAN-C.md`、`PLAN-C-v1.1.0.md`、`PLAN-C-CLUSTER.md`、`PLAN-C-v3d2-split.md` 的历史断言（这些文档描述 v1.2.0 及更早流程；与当前状态无直接冲突，但未做全文比对）。
7. **未核对 C/E32 的 47 字 unseen 复跑原始数据**（只按 `work-c-big/REPORT.md` 的更正结论判为一致）。
8. **未运行 100_review.py 出板、未跑任何训练/生成/重打包**（约束禁止）。
9. 未验证 `data/base/LXGWWenKai-Regular.ttf` 是否为 v1.530 指定版本（只读其存在与许可记录）。

---

## 7. 建议的修复顺序（供所有者/Lead 决策）

1. **先修口径**（P0-2）：重跑 ep090 的 300 字 CPU eval 落盘；用真实测量覆盖 `data/release-c.json` 的 clean/weight 字段；RELEASE 写清 ep35 vs ep090 的选点事实。
2. **补发布披露**（P0-1、P1-4、P1-5、P1-7）：验收门状态、20 字影响、生成链修复运行、README 矛盾与 B 线数字。
3. **补留痕**（P1-1、P1-2、P2-6）：`real_rejected.jsonl`、20 字名单、AGENTS §5.1 登记、96 修复。
4. **修闸门**（P1-8、P2-7）：83 写入顺序 + C 缺失处理 + C zip 钉哈希。
5. **修文档/脚本口径**（P1-6、P1-9、P2-1~P2-10）：DATA-C 重建命令、77 默认 ckpt 告警、GLOSSARY/CONVENTIONS/AGENTS 更新。
6. 下一版再按 AUDIT §6 做 P0-A/P0-C 结构性修复（P1-3），或在 AGENTS 正式登记放弃。

---

## 附录 A：本次审计使用的关键只读命令

```bash
# 制品/校验和
shasum -a 256 build/GuanGeKai-C-Regular.ttf build/GuanGeKai-C-Real.ttf GuanGeKai-C-v1.3.0.zip
cd release-c && shasum -a 256 -c SHA256SUMS
unzip -l GuanGeKai-C-v1.3.0.zip

# 数据链计数（一次 python 扫描）
python3 - <<'EOF'
import json, collections
src=collections.Counter(); gen={}
for l in open('work-c/generated.jsonl'):
    r=json.loads(l); gen[r['char']]=r.get('src'); src[r.get('src')]+=1
chosen=[json.loads(l)['label'] for l in open('work-c/chosen.jsonl')]
prov=json.load(open('release-c/provenance.json'))
print(len(gen), dict(src), len(chosen), collections.Counter(prov.values()))
EOF

# QA 闸门（输出到 /tmp，不覆盖 work-c）
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  python3 scripts/80_qa_c.py --outdir /tmp/cqa2 --real-expect 5257 --sheets 1

# 术语
python3 scripts/97_check_terms.py
```

## 附录 B：本报告引用的数据文件

`work-c/chosen.jsonl`、`work-c/v13_preclean_chosen.jsonl`、`work-c/generated.jsonl`、`work-c/gan_fallback.json`、`work-c/pairs/pairs.npz`、`work-c/pairs_clean.npz`、`work-c/pairs_holdout.npz`、`work-c/ckpt/v1.3/c_split.json`、`work-c/ckpt/v1.3/SELECTION.md`、`work-c/logs-v1.3/*`、`work-c/qa/{stats,holes}.json`、`work-c/accept_c.json`、`work-c/build_manifest.json`、`work-c/verify_ab.json`、`release-c/{provenance,stats}.json`、`release-c/SHA256SUMS`、`data/release-c.json`、`work-c-big/REPORT.md`。
