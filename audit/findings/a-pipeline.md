# A 线核心流水线审计报告（pipeline-a）

> 审计员：pipeline-a（独立审计，只读，不修改代码）
> 基线：`HEAD e308ad5`（2026-11-13），审计时工作树干净（`git status --porcelain` 仅 `?? audit/`）
> 审计时点：2026-11-14
> 唯一写入文件：本文件（`audit/findings/a-pipeline.md`）。所有复跑输出均重定向到 `/tmp/a_audit/`，未执行 git 写操作，未改动 `docs/ scripts/ build/ release*/ work*/ data/` 下任何文件。
> 并发：全部轻量复现单进程，`OMP/MKL/OPENBLAS_NUM_THREADS=1`，单条命令 <2 分钟（05/07/08 各约 1–2 分钟，无训练/全量重建/打包）。

审计范围：`scripts/01_segment.py`、`02_ocr.py`、`03_build_reference.py`、`04_label.py`、`05_select.py`、`06_norm.py`、`07_build_real.py`、`08_make_pairs.py`、`10_generate.py`、`11_build_full.py`、`13_qa.py`、`14_package.py`、`16_check_real.py`，以及共享库 `pageproc.py / select_lib.py / glyphvec.py / fontbuild.py / brush_lib.py / punct_set.py` 中被 A 线调用的部分；对照 `docs/PROJECT_STATE.md §3/§4`、`docs/DATA.md §6`、`AGENTS.md` 发布流程与现行 `work/` 数据。

## 0. 结论摘要

| 等级 | 数量 | 内容 |
|---|---|---|
| **P0** | **0** | 未发现会直接产出错字形或破坏发布包的问题 |
| **P1** | **2** | ①发布包的 `Real.ttf` 与 `Regular.ttf` 真字形不一致 + 文档发布路径重建出的 `Real.ttf` 哈希与发布记录不符（发布不可复现）；②`AGENTS.md` 发布流程缺「标点扩展」步，按文档执行会在 `13_qa` 中止 |
| **P2** | **8** | 06 norm 不可复现/陈旧、07 `--reuse-contours` 防呆与接口脆弱、10_generate 静默参数/副作用/行序不确定、14_package 新鲜度闸门与硬编码、13_qa 缺 Real⊆Regular 闸门、01/02 失败静默与部分重跑覆盖、PROJECT_STATE §4/§3 与代码不一致、低风险代码卫生与陈旧诊断件 |
| 已披露/未修 | 5 类 | 01 旋转坐标系错位、04_label 丢 351 格与 dpi×2 硬编码、05_select 评分项 q/sz、norm_glyph 双份实现（均旧审计已披露，本轮复核确认仍在）；另 1 类仅交叉引用 docs-consistency |
| 已核查不成立 | 11 项 | 见 §4.1；关键计数、成对文件、norm 覆盖、三层合字集合、05/08 可复现性、13_qa 实跑、发布哈希、对齐报告、生成工作点、07 防呆均复核通过 |

**最严重的问题**：发布的 `build/GuanGeKai-Real.ttf` 与 `build/GuanGeKai-Regular.ttf` 中同一字形的真字轮廓不一致（176/1,675 字不同），且按 `AGENTS.md` 第 1 步 `07_build_real.py --reuse-contours` 重建会得到另一个 Real 哈希（`5733ca42…`），与 `docs/DATA.md:110`、`data/release-a.json:46` 记录的 `bf278ab1…` 不符——A 线的 Real 发布链不可字节复现，而 B 线已在 `docs/DATA-B.md:206-218` 明确记录同一现象并规定了「以缓存路径为准」的纪律，A 线未采用。

---

## 1. P1 发现

### P1-1 发布包内 `Real.ttf` 与 `Regular.ttf` 的真字形不一致；按文档重建 Real 得到不同哈希

- **严重度**：P1（发布一致性 + 发布不可复现；无肉眼级字形损坏）
- **证据**
  1. 文档给的两条 Real 重建路径互相矛盾：
     - `AGENTS.md:149`（发布流程第 1 步）：`python3 scripts/07_build_real.py --reuse-contours`（读 `work/real_contours.jsonl`）；
     - `docs/DATA.md:174`（§6 重建）：`python3 scripts/07_build_real.py`（从 `work/masks/` 重新描摹）。
  2. 实测两条路径产出的 `Real.ttf` 不是同一份字节（复跑命令见 §6）：
     ```
     --reuse-contours（缓存路径，AGENTS 第 1 步）  sha256 5733ca42f8a389d2…  3,322,124 B
     重新描摹（masks 路径，DATA §6）              sha256 bf278ab1631bdb0d…  3,291,812 B  ← 发布版
     build/GuanGeKai-Real.ttf 实测                sha256 bf278ab1631bdb0d…  3,291,812 B
     docs/DATA.md:110 / data/release-a.json:46    bf278ab1631bdb0da75a1b1b6b9c8628d7ec8b4792da7ef904c81f71f4dd1c86
     ```
     即：**发布的 Real 是「重新描摹」版，而 AGENTS 规定的第 1 步会得到「缓存」版**，与 DATA.md/release-a.json 的记录不符。
  3. 缓存内容本身没问题：把 07 复制到 `/tmp`（仅改输出路径，`ROOT` 不变）从当前 masks+cells+norm 重新描摹，得到的 `real_contours.jsonl` 与仓库缓存 **逐字节相同**（两者 sha256 `8ad6301d124874f8…`）。差异只来自「轮廓点从 JSON 读回后是 `list`、内存里是 `tuple`」。
  4. 机制（可复核）：`fontbuild.py:136` 用 `rec.moveTo(c["start"])` 直传点类型；缓存路径 start 是 `list`，seg 端点是 `tuple`。fontTools 4.61.1 的 `reversedContour()` 用 `if firstOnCurve != lastOnCurve:` / `if firstPts != secondPts:` 做**点值相等判断**（`/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/fontTools/pens/reverseContourPen.py`），`[x,y] != (x,y)` 恒真 → 反向轮廓被额外插入一个「隐式闭合 lineTo」。`build_font` 的 `drop_duplicate_last_point`（`fontbuild.py:138-144`）默认关闭，缓存路径没启用它。
  5. 后果实测（逐字 draw `RecordingPen` 比较）：
     ```
     build/GuanGeKai-Regular.ttf 真字 vs build/GuanGeKai-Real.ttf : 176/1675 轮廓不同
     build/GuanGeKai-Regular.ttf 真字 vs 缓存路径 Real           :   0/1675 不同（=Regular 用的是缓存版）
     发布版 Real                  vs 缓存路径 Real               : 176/1675 不同
     256px 渲染比较：13 字有像素差，其中 8 字 ink 掩膜不同；最差「崇」IoU 0.99653（45 px 差），
     其餘 讓/駟 14 px、祭/轉 5 px、孽 4 px、懲/次 3 px
     ```
  6. B 线已记录同一现象并规定了对策：`docs/DATA-B.md:206-218`——「重新描摹 vs 缓存……发布用的就是缓存这一份，可字节复现；发布链以缓存路径为准，这样 Real 与 Regular 的同字轮廓一致；根治办法是在 `fontbuild.build_font()` 里丢掉『末点 == 起点』的重复点」。A 线既未采用该纪律，发布链也恰好相反（Real=重描摹、Regular=缓存），且没有任何闸门能发现（`13_qa.py:61-75` 只比较 Real 的 glyph/cmap 数量，`83_verify_ab_c.py` 只比哈希与计数）。
- **影响**
  - 同一发布包内两个字体的同一字真字形状不一致（小但客观；用户混排两字体时同字轮廓不同）。
  - 「`Real` 是 `Regular` 真字子集（同轮廓）」的隐含承诺不成立；`DATA-B.md:198` 的 `Real ⊆ Regular` 纪律对 A 线不成立。
  - 按 `AGENTS.md:149` 发布，`build/GuanGeKai-Real.ttf` 哈希会变成 `5733ca42…`，`docs/DATA.md:110`、`data/release-a.json:46`、`83_verify_ab_c.py` 的 Real 基线全部失效（`83` 会打印 A `GuanGeKai-Real.ttf` DIFF），即**发布记录不可复现**。
- **复现步骤**
  1. `python3 scripts/07_build_real.py --reuse-contours --out /tmp/a_audit/Real_from_cache.ttf` → `shasum -a 256` 得 `5733ca42…`。
  2. 把 `scripts/07_build_real.py` 复制到 `/tmp/a_audit/rb/07_build_real_rb.py`，仅把 `ROOT` 固定为仓库绝对路径、把 `real_contours.jsonl`/`real_glyph_sources.json`/字体输出改到 `/tmp/a_audit/rb/`；运行 → `shasum` 得 `bf278ab1…`，与发布版一致。
  3. 用 fontTools `RecordingPen` 逐字比较 `build/GuanGeKai-Real.ttf`、`build/GuanGeKai-Regular.ttf`、`/tmp/a_audit/Real_from_cache.ttf`。
- **建议改进**
  1. 在 `fontbuild.build_font()` 入口做类型归一（如 `rec.moveTo(tuple(c["start"]))`，一行），或在 build_font 内统一「末点==起点则丢弃」，使内存/缓存两条路径字节一致；
  2. 发布只保留一条路径（建议按 B 线纪律用缓存路径），同时把 `docs/DATA.md:174` 的命令补上 `--reuse-contours`，并把 Real 的产出口径写进 `data/release-a.json`（含 `real_contours.jsonl` 的 sha256 输入指纹）；
  3. `13_qa.py` 增加 `Real ⊆ Regular` 轮廓/字形一致性断言（逐字 `RecordingPen` 或 glyf 比较，秒级），失败即 ABORT；
  4. 决定后重打 v1.7.2 的 Real 或登记为已知 drift（二选一），避免文档/校验和与制品长期不一致。

### P1-2 `AGENTS.md` 发布流程缺「标点扩展」步：按文档执行会在 `13_qa` 中止，或漏标点打包

- **严重度**：P1（流程不可按文档完成；不是数据错误）
- **证据**
  - `AGENTS.md:144-160` 的「发布流程（顺序固定，勿跳步）」只有：07 → 11 → 13_qa → 71 → 23 → 14 → 95 → 98 → zip；**没有** `13_extend_punct.py`。
  - `scripts/11_build_full.py:36-44,49-55`：只对 `0x4E00–0x9FFF` 的 20,992 个 CJK 码位合字，`build_font` 只写 CJK 字形；全文无 punct 调用。
  - `scripts/13_qa.py:81-86` 用 `punct_set.verify(cmap)` 做硬闸：缺 42 个码位或 `len(cmap) != 21,034` 即 `ABORT punct`（`punct_set.py:14-28,31-38`）。
  - 实际发布字体 cmap 是 21,034 / glyphs 21,035（实测），只能由 `13_extend_punct.py --line A --inplace` 追加；该脚本 `scripts/13_extend_punct.py:19` 自己写着「Order: run AFTER 11_build_full.py, BEFORE 14_package.py」，`docs/PLAN-PUNCT.md:84` 也给了 A 线命令，但**规范流程（AGENTS）与 `PROJECT_STATE.md §4` 流水线表都未登记这一步**。
- **影响**
  - 接手者按 AGENTS 顺序执行：`11` 重建出 cmap 20,992 的字体 → `13_qa` 第 3 步直接 `ABORT punct`，发布流程卡死；
  - 若跳过 `13_qa` 继续打包，会发出缺 42 个标点/数字/空格的字体，与 v1.7.2「cmap 21,034」的发布口径矛盾（`docs/RELEASE-v1.7.2.md:8-11`）。
- **复现步骤**（只读）
  ```
  python3 - <<'EOF'
  import sys; sys.path.insert(0,'scripts')
  from fontTools.ttLib import TTFont; import punct_set
  print(len(TTFont('build/GuanGeKai-Regular.ttf').getBestCmap()), len(TTFont('build/GuanGeKai-Regular.ttf')['maxp'].numGlyphs))
  print(punct_set.verify(TTFont('build/GuanGeKai-Regular.ttf').getBestCmap()))
  EOF
  # 实测输出：21034 21035 / []（发布字体已扩展）
  grep -n "punct" scripts/11_build_full.py   # 无命中 → 11 不补标点
  ```
- **建议改进**
  1. 在 `AGENTS.md:150` 后插入 `python3 scripts/13_extend_punct.py --line A --inplace`（并注明「顺序：11 → 13_extend_punct → 13_qa → 14」）；
  2. `docs/PROJECT_STATE.md:99-112` 流水线表补一行（步骤、脚本、耗时、失败模式「cmap≠21034 时 13_qa 中止」）；
  3. 或在 `11_build_full.py` 内直接合并标点（避免手工步骤），`14_package.py` 打包前再断言 cmap == `punct_set.EXPECTED_CMAP`。

---

## 2. P2 发现

### P2-1 `06_norm.py` 输出不可复现：`work/norm.json` 是旧版 `glyphvec.trace` 参数下的产物（3/1675 字不同）

- **证据**
  - `work/norm.json` mtime `2026-10-22 23:05`；此后 `scripts/glyphvec.py`（10-28）、`scripts/06_norm.py`（10-27）有改动。`glyphvec.py:204` 的 `trace()` 默认 `turdsize=2`，`:207-208` 注释写着 `turdsize=2 (was 8)`，`docs/PROJECT_STATE.md:320`（v1.6.0）记录了这次 8→2 的共享库改动；而 `06_norm.py:41` 调用 `trace(ink)` **不传 turdsize**，因此重跑会走新默认。
  - 实测（/tmp 沙箱复跑 06）：
    ```
    当前默认（turdsize=2）重跑 vs 仓库 norm.json：3/1675 键值不同（人、禦、昏）
      例「人」：sy 1.478568 → 1.476895；dy -245.460956 → -244.269188（差 1.19 font unit）
    把 trace 显式改为 turdsize=8 重跑 vs 仓库 norm.json：0/1675 不同
    ```
  - 新鲜度佐证：`work/norm.json` 10-22，而它服务的 `work/real_contours.jsonl` 是 10-30 重描摹产物（`work/cells/masks` 也是 10-24 重新切出的），说明 v1.6.0 重建时没有重算 norm。
- **影响**：从零按 `docs/DATA.md §6` 重建时，06 会产出新的 norm.json（3 个字略变），07 的 Real 随之变几个单位 → **发布哈希不可字节复现**；现有 `work/` 状态可复现（本轮用现存 norm 复跑 07 得到发布版 `bf278ab1…`）。字形影响可忽略（≤1.2/1000 em），问题在可复现性与「共享库改动后下游未重跑」的流程缺口。
- **建议**：重跑 06 并记录；把 `trace()` 参数（`turdsize/alphamax/opttol`）显式传参且写进输出（或在 `norm.json` 记一行输入指纹），避免共享库默认值漂移；在 `docs/DATA.md §6` 标注「norm.json 需在 glyphvec 变更后重算」。

### P2-2 `07_build_real.py --reuse-contours` 的防呆与接口脆弱

- **证据**
  - `07_build_real.py:56-57`：缓存路径只断言 `len(glyphs) < 1000` 就 `ABORT`；**不是 1,675**。缓存被截断到 1,001–1,674 个时仍会写出 `build/GuanGeKai-Real.ttf`，只能等 `13_qa`（第 3 步）才发现数量不符（`13_qa.py:67-73` 以 `work/chosen.jsonl` 行数为期望）。
  - `07_build_real.py:58-59`：fast path 用 `sys.argv.index("--out")` 解析输出路径，只有在参数写成 `--out /path` 时生效；写成 argparse 同样支持的 `--out=/path` 时 `"--out" in sys.argv` 为 False，**会静默覆盖默认 `build/GuanGeKai-Real.ttf`**。
  - fast path 不校验缓存与 `chosen.jsonl`/`masks` 是否同代（若 chosen 或 masks 更新而缓存旧，会静默按旧集合建 Real）；`--limit` 等参数也被 fast path 忽略。
  - fast path 不写 `work/real_glyph_sources.json`（`07_build_real.py:130-131` 只有非 reuse 分支写），来源表会与 Real 不同代。
- **影响**：旧事故（masks 缺失 → 0 字形 → 覆盖 Real + 截断缓存，`AGENTS.md:176-180`）已被 `<1000` 防住，但「部分缺失」与「参数形式导致的误覆盖」仍无保护；审阅者容易误以为 AGENTS 第 1 步就是发布口径（见 P1-1）。
- **建议**：fast path 也用 argparse；断言集合作 `== 集合(chosen 标签)` 或至少 `>= 1675`；与 chosen/masks 做集合差并打印；fast path 同步写 `real_glyph_sources.json`（或删除该中间文件）。

### P2-3 `10_generate.py` 的静默参数、固定路径副作用与非确定行序

- **证据**
  - **`--ckpt` 对 `--method gan` 无效**：`10_generate.py:411` 定义 `--ckpt`，但 `gan` 分支从环境变量/硬编码读主模型（`:82` `GAN_CKPT`，默认 `work/ckpt/m2wt_ep090.pt`）；`args.ckpt` 只在 `--method model` 分支使用（`:464-469`）。命令行传 `--ckpt` 会被静默忽略。
  - **`work/gan_fallback.json` 是固定路径副作用**：`:498` 始终写 `ROOT/work/gan_fallback.json`，与 `--out` 无关。当前该文件只有 2 字节 `[]`（mtime 2026-10-30 08:06），而 `work/generated.jsonl` 是 10-27 的发布数据（799 个 `src=="base"`）——两者不同代；`docs/DATA.md:178` 的 `36_fill_fallback.py` 读它后 `todo` 为空、变成无操作步骤（`36_fill_fallback.py:23-31` 已确认）。实际上当前 `gan` 分支已直接输出 ribbon 轮廓（`:134-143` 落盘 `src="base"`），36 号脚本在 v1.5.0 之后已是冗余。
  - **行序不确定**：`gan` 分支用 `pool.imap_unordered`（`:482`）**按完成顺序**写 `--out`（`:483-494`），未按 chars 排序；对照 `gen_chunk` 分支（`:512-521`）有排序。实测 `work/generated.jsonl` 全局非序（最长连续升序 1,200/19,317），因此该中间文件的 sha256 不能作为数据指纹。
  - **provenance 标签硬编码**：`14_package.py:64` 把生成侧 `src` 映射写死 `{"gen":"gan_ep90","gen80":"gan_ep80","base":"ribbon_fb"}`；换检查点/阈值重建时 provenance 会错标（`data/release-a.json` 才是工作点唯一来源）。
- **影响**：可复现性弱（行序、清单路径、provenance 命名都与「实际用了什么模型」解耦）；误以为是换模型实际没换；docs/DATA.md §6 的 36 号步骤是死步骤。
- **建议**：`gan` 分支用 `args.ckpt`（或删掉该参数）；`gan_fallback.json` 写到 `--out` 同目录；写盘前按 codepoint 排序（与 `gen_chunk` 分支一致）；provenance 的 ckpt 名从生成侧写入或从 `release-a.json` 读；从 DATA.md 删除 36 号步骤或注明「v1.5.0+ 已并入 10」。

### P2-4 `14_package.py` 的新鲜度闸门不完整、模块级副作用、统计硬编码

- **证据**
  - 新鲜度只查 `work/chosen.jsonl` 与 `work/generated.jsonl`（`14_package.py:32-40`），**不查** `work/real_contours.jsonl` 与 `work/norm.json`（两者都是 `11` 的输入）。这两份更新后打包不会中止（当前它们都比字体旧，故现状能通过）。
  - `14_package.py:141` 在模块级无条件调用 `_fix_charset_records(ROOT / "release")`，且该函数（`:106-138`）的目标目录写死为仓库 `release/`，与 `--out`（`:26-27`）无关。于是 `python3 scripts/14_package.py --out /tmp/trial` 会：把包写到 `/tmp/trial`，同时**改写真实 `release/` 的 provenance/stats/SHA256SUMS**；任何 `import 14_package` 也会触发。
  - `_fix_charset_records` 里 `st["codepoints"] = 20992`、`st["codepoints_total"] = 21034` 为硬编码（`:126-127`），不读字体 cmap、也不读 `punct_set.EXPECTED_CMAP`。这与 `docs/RELEASE-v1.7.2.md:10`「唯一定义源……禁止硬编码数量」自相矛盾，且若字体实际缺标点，stats 仍会写 21034。
- **影响**：打包记录可能与真实字体不同代；试运行会污染发布目录（虽多数情况下幂等）；统计数字无法作为闸门。
- **建议**：deps 增加 `real_contours.jsonl`、`norm.json`（必要时加 `build/GuanGeKai-Real.ttf`）；把 `_fix_charset_records` 并入 `main()` 并对 `args.out` 生效；`codepoints` 用 `len(font.getBestCmap()) - len(punct_set.CHARS)` 实测计算，`codepoints_total` 用 `punct_set.EXPECTED_CMAP` 并在打包前断言实测 cmap 相等。

### P2-5 `13_qa.py` 缺 `Real ⊆ Regular` 一致性闸门（P1-1 因此无人发现）

- **证据**：`13_qa.py:61-75` 的 real-subset 检查只比较 `Real.ttf` 的 `maxp.numGlyphs-1` 与 `cmap` 数量是否等于 `work/chosen.jsonl` 行数；`13_qa.py:25-45` 只检查 `Regular.ttf` 的覆盖率/空字形/尺寸。没有任何步骤比较两个字体的同字轮廓。
- **影响**：P1-1 的 176 字轮廓差异、13 字渲染差异在现有发布闸门（07/11/13/71/23/14/83）下全部不可见。
- **建议**：对 `chosen.jsonl` 的每个 label，在 `Regular` 与 `Real` 上各 draw 一次 `RecordingPen`/`BoundsPen` 并比较（1,675 字，秒级）；或比较 glyf 序列化字节。失败即 ABORT 或明确打印 `Real/Regular outline mismatches: N` 并阻断发布。

### P2-6 `01_segment.py`/`02_ocr.py`：失败静默与 `--pages` 部分重跑覆盖全量输出

- **证据**
  - `01_segment.py:75-77` 逐页 `except Exception` 只打印错误最后一行并继续；`01_segment.py:118-121` 无论成功多少页都写 `cells.jsonl`，脚本 exit 0。没有「页数/格数异常」总闸（对照 07/11/13 都有 ABORT）。
  - `02_ocr.py:27-39` 的 `process_page` 无异常捕获；任一页抛错会击穿整个 Pool。OCR 返回 `None` 时静默写空行（`:35-39` 与 `:63-72`），下游 04 会把无 OCR 行的 cell 丢掉（见 §4 的 351 格）。
  - 两脚本都用 `--pages` 支持局部重跑，但输出文件名固定：`01_segment.py:118` 写 `out/cells.jsonl`（`--out` 默认 `work/`）、`02_ocr.py:70` 写 `ROOT/work/ocr_pages.jsonl`。跑 `--pages 0-5` 会把全量索引覆盖成 6 页子集（`work/cells/`、`work/masks/` 里旧文件仍存在，形成新旧混代），后续 04/05 会静默丢标签。
- **影响**：调试性重跑会污染唯一索引且无提示；单页失败会静默降低数据量，之后只能从计数差发现（本轮即通过 54,109 vs 53,758 才发现 04 阶段丢格）。
- **建议**：01 记录失败页列表并断言「成功页数 == 请求页数」/「cells 行数 >= 阈值」，否则非 0 退出；02 加逐页 try/except 并把失败页写入输出；`--pages` 模式默认输出到 `*.partial.jsonl` 或加 `--in-place` 显式开关，禁止隐式覆盖全量索引。

### P2-7 `PROJECT_STATE.md §4` 流水线表与代码/实测不一致；§3 的「有效文字页」口径未落地

- **证据**（`docs/PROJECT_STATE.md`）
  - `:101` ① 切字「~4.5 min（12 进程）」：代码默认 `01_segment.py:84 --workers 8`，且 `AGENTS.md` 并发硬约束要求 `--workers ≤ 8`；
  - `:102` ② OCR「~4 min（4 进程）」：代码默认 `02_ocr.py:46 --workers 6`；
  - `:109`/`:93` ⑨ 训练「`09_train*.py`、`style_*.pt`（三次尝试）」：v1.5.0 起主线是 `21_train_gan.py` + GAN 检查点（`docs/PROJECT_STATE.md:358-374`、`data/release-a.json:3-18`），该行与流水线图 `:93` 已过期；
  - `:110` ⑩ 合成「~5 min（19,317 字）」：`docs/DATA.md:296` 实测 GAN 约 25 分钟（6 worker），`docs/DATA.md:188` 又写总耗时约 15 分钟，自相矛盾（DATA.md §6 的重建命令问题另见 `audit/findings/docs-consistency.md`，此处只指出 §4 表与代码/实测不一致）；
  - `:99-112` 全表缺「标点扩展（13_extend_punct）」步（与 P1-2 同源）；
  - `:71` §3「有效文字页 380（另有封面/衬页/跋）」在 `work/page_stats.csv` 中无对应字段/规则：该 CSV 只有 `p,w,h,ink` 四列；实测 410 页中 `ink>0.05` 恰好 380 页，阈值未写入任何脚本或文档（口径不可复核）。
- **影响**：接手者按 §4 估计耗时/进程数/步骤会得到错误预期；「380 页」无法从数据源直接复核。
- **建议**：§4 表按当前代码默认值与 `docs/DATA.md §6` 统一（标注 worker 数），补 punct 步骤；⑨ 改为 `21_train_gan.py`；`page_stats.csv` 增 `is_text` 列或把 `ink>0.05` 规则写进 `01_segment.py`/文档；⑩ 耗时与 DATA.md 统一口径。

### P2-8 低风险代码卫生与陈旧诊断件

- **证据**
  - `04_label.py:37-72` 的 `nw()` 是约 70 行全局对齐实现，**全文件无调用**（`grep -n "nw(" scripts/04_label.py` 仅命中定义），易让维护者误以为标注主路径是全局对齐；
  - `05_select.py:18` 与 `select_lib.py:6` 仍是两份 `norm_glyph`（旧审计已提；16_check_real 用 select_lib 版，05 用内联增强版），逻辑漂移风险仍在；
  - `06_norm.py:13`、`07_build_real.py:13` 有未使用导入（`normalize_to_base`、`binarize`）；
  - `16_check_real.py:11` 在模块 import 时硬编码加载 `data/base/LXGWWenKai-Regular.ttf`；其输出 `work/real_check.json` 是 **2,300 行、576 条 flag、mtime 2026-10-22 18:05**，早于当前 `work/chosen.jsonl`（10-22 21:40，1,675 行）——不同代且未复核、未进任何闸门。
- **影响**：低；但 `work/real_check.json` 若被当作「真字标签核对结果」引用会得出错误结论（2,300 行 vs 当前 1,675 行）。
- **建议**：删除死代码/未用导入；05 统一从 select_lib 导入；16 重跑并标注生成时点，或把输出移到 `work/` 之外并在文档中标注「历史诊断、非当前数据」。

---

## 3. 闸门/防呆验证（任务必查项：是否真实生效）

结论：**07/11/13 的数量防呆确实生效，但 07 的阈值是宽松的 1,000 而非精确 1,675，13 缺 Real/Regular 一致性检查。**

| 闸门 | 代码 | 验证结论 |
|---|---|---|
| 07 非 reuse：真字过少中止 | `07_build_real.py:120-123`：`len(glyphs) < 1000` 时 `SystemExit`，且在写 `real_contours.jsonl`/字体之前 | 生效（防住 2026-10-21 的 0 字形事故）；但 1,000 ≠ 1,675，部分丢失（1,001–1,674）会通过（P2-2） |
| 07 reuse：缓存过少中止 | `07_build_real.py:56-57` | 生效；同样是 `<1000` 阈值（P2-2） |
| 11 三层合字中止 | `11_build_full.py:45-48`：`len(real) < 1000 or missing > 0` | 在当前数据下**等价于精确断言**：`generated` 集合恰为 `基本区 − chosen`（实测 19,317 字、与 real 零交集），real 少任何一个字都会使 `missing > 0` → 中止。通过静态集合核对（见 §4） |
| 13 覆盖率/空字形/尺寸 | `13_qa.py:25-45,76-80` | 生效：实测跑发布字体 exit 0，`coverage 20992/20992`、`empty 0 tiny 0 huge 0` |
| 13 Real 子集数量 | `13_qa.py:61-75` + `work/chosen.jsonl` 行数 | 生效：实测打印 `real-subset glyphs 1675 cmap 1675 -> OK`；但缺轮廓一致性（P2-5） |
| 13 标点闸 | `13_qa.py:81-86` + `punct_set.verify` | 生效（发布字体实测返回 `[]`）；也因此 P1-2 的缺失步骤会直接卡住发布 |
| 13 fontRevision 一致性 | `13_qa.py:88-95` | 生效：发布字体 `fontRevision 1.720001` 与 name ID5 `Version 1.7.2` 相符 |
| 14 打包新鲜度 | `14_package.py:32-40` | 生效但覆盖不全（只查 chosen/generated，不查 real_contours/norm；P2-4）；当前字体 mtime（11-13）晚于两项依赖，现状可通过 |

---

## 4. 已核查不成立 / 已披露（不作为新发现）

### 4.1 复核通过、不成立的疑点

1. **关键计数全部可复核**：`work/cells.jsonl` 54,109 行；`work/labeled.jsonl` 53,758 行（非空标签 53,710，唯一标签 **2,292**）；`work/chosen.jsonl` **1,675** 行（标签唯一）；`work/generated.jsonl` **19,317** 行（src：`gen` 17,790 + `gen80` 728 + `base` 799）。与 `PROJECT_STATE §3`、`AGENTS.md` 发布口径一致。
2. **chosen 引用的 cells/masks 全部成对存在**：1,675 个 `file` 在 `work/cells/` 与 `work/masks/` 均存在（0 缺失）；`work/cells`、`work/masks` 各 54,109 个文件。
3. **norm.json 覆盖完整**：1,675 键，与 chosen 标签集合完全一致（无缺、无多），每条都含 `sx/sy/dx/dy/scale/origin/slot_*`；`work/real_contours.jsonl` 1,675 行、与 chosen 标签集合完全相同、`src` 全为 `real`。
4. **三层合字来源一致（集合层面）**：`generated` ∪ `real` = 基本区全部 20,992 字；`generated ∩ real = ∅`；`基本区 − chosen = 19,317 = generated` 全部覆盖。因此 11 的「real 优先、gen 兜底」不会错层；`release/provenance.json` 实测 21,034 条 = `real 1,675 / gan_ep90 17,790 / gan_ep80 728 / ribbon_fb 799 / punct 42`，`release/stats.json` 的 `glyphs 21,035`、`file_bytes 15,739,524` 与 `data/release-a.json:45-47` 一致。
5. **05_select 重跑能精确复现 1,675**：在 `/tmp` 沙箱（`--work` 指向含 cells/labeled/cells.jsonl 符号链接的目录，不写仓库）用当前代码重跑：
   ```
   labels 2292 glyphs 53710
   chosen 1675 (dropped 617 labels with <2 samples; dropped 0 whose every sample was flagged)
   逐行比较：file/n_samples/medoid_dist/sharp 全部相同；second.jsonl 也 0 差异
   fingerprint(proj) = fingerprint(rerun) = 55e9865774c6fab5
   ```
   结论：选优确定性成立；问题在评分设计（见 4.2），不在随机性。
6. **08_make_pairs 可复现**：`--work` 指向 /tmp 沙箱重跑，`pairs.npz` 的 `X/Y/chars` 与仓库 `work/pairs/pairs.npz` **逐元素完全相同**（1,675 对、chars 与 chosen 集合一致、无重复）。
7. **13_qa 在发布字体上实跑通过**（`--outdir /tmp`）：`coverage 20992/20992 = 100%`、`empty 0 tiny 0 huge 0`、`real-subset glyphs 1675 cmap 1675 -> OK`、punct `[]`、fontRevision 相符，exit 0。
8. **发布包内字体与记录一致**：`build/`、`release/`、`GuanGeKai-v1.7.2.zip` 内 `GuanGeKai-Regular.ttf` 均为 `e6d8a104…`，`GuanGeKai-Real.ttf` 均为 `bf278ab1…`；与 `docs/DATA.md:109-110`、`data/release-a.json:45-46` 一致（但见 P1-1 的可复现问题）。
9. **`work/align_report.json` 复核**：384 页，`rate>0.5` 358 页、均值 0.8986，与 `PROJECT_STATE §3` 的「358/384，平均 0.899」一致；`work/page_stats.csv` 410 行。
10. **`10_generate.py` 的发布工作点与 `data/release-a.json` 一致**（静态核对）：主模型默认 `m2wt_ep090`（`:82`）、补位默认 `m2_ep080`（`:52`）、阈值默认 `-0.05 / -0.45`（`:53-54`），与 `release-a.json:4-11` 的 generator 配置相符。
11. **`07 --reuse-contours` 的 `<1000` 防呆能防住旧 0 字形事故**（代码路径在写盘之前，`07:56-57`），缓存现有 1,675 个字。

### 4.2 旧审计已披露、A 线仍未修（按要求只确认、不当新发现）

1. **01_segment 旋转坐标系错位（AUDIT-2026-10-26 P1-1；rev3 记「未修」）**：`01_segment.py:36-37` 用旋转后的坐标（来自 `analyze_page` 内部 `rotate`，`pageproc.py:331-332`）去裁剪**未旋转**的 `gray`；掩膜与灰度来自不同坐标系。本轮复核：`cells.jsonl` 中 8,109/54,109 格 `|angle|>0.03°`（最大 1.886°）；被选真字 **240/1,675 在 |angle|≥0.03° 页、108 在 ≥0.2°**，与旧审计的 240/108 完全一致 → 仍未修。影响：真字掩膜侧（potrace 走旋转系）自洽，发布字形不受影响；但 05 选优的锐度/尺寸项读灰度图 → 240 个选字被污染（建议同旧审计：`analyze_page` 返回旋转后图，或 01 从 `rgb_r` 裁剪）。
2. **04_label 静默丢 351 格 + `*2` dpi 硬编码（AUDIT-2026-10-26 P2-1/P2-2；rev3 记「未改」）**：实测 `cells.jsonl` 54,109 行 vs `labeled.jsonl` 53,758 行，差 **351**（分布 77 页，最多 p133 丢 19 格）；`04_label.py:105` 仍把 OCR 框坐标 `*2`（300/150 dpi 比值硬编码）。影响：这 351 格永远不能成为真字候选；换 dpi 重跑会静默错位。
3. **05_select 评分项奖励坏格（AUDIT-2026-10-31 §2.4）**：`05_select.py:170-183` 与审计时公式一致（`score = d − 0.25·q − 0.15·m + 0.35·clip(sz) + 0.15·red`）：`q`（Laplacian 锐度）奖励碎边；`sz` 以同标签组内中位为基准，组整体错标时零保护。A 线 `labeled.jsonl` 没有 `agree_ab`/`prefer-clean` 等字段，无法像 B/C 那样降权。新旁证（A 线数据）：chosen 1,675 行中 `sharp` 与 `medoid_dist` 正相关（r=0.297），提示 -0.25q 项正在给「离群/噪声」样本提供补偿。旧审计 `:239` 记录的修法（删 q、加绝对几何闸、size 用文楷绝对参照）仍未实施（A/C 共用该文件）。
4. **`norm_glyph` 双份实现（AUDIT-2026-10-26 4-14）**：`05_select.py:18` 与 `select_lib.py:6` 仍并存（见 P2-8）。
5. **DATA.md §6 重建命令与 v1.7.2 口径不符**（GAN 生成/36_fill_fallback/总耗时 15 vs 25 分钟）：已由并行审计 `audit/findings/docs-consistency.md` 记录，本报告不复述，只把「36_fill_fallback 在现行代码下已是死步骤」作为 P2-3 的补充证据。

> 注：`docs/ERRATA.md E7`（`generated_simplified.jsonl` 保留待查）与本审计范围无关，未重复核查。

---

## 5. 未覆盖项与限制

1. **未执行全量重建**：`11_build_full.py` 的字体输出、`13_extend_punct.py --line A --inplace`、`14_package.py` 均未实跑（会覆盖 `build/`、`release/`，为硬约束禁止）。P1-2 与 P2-4 的结论为代码静态推理 + 现有制品反查（`13_qa` 实跑、cmap 实测）支撑。
2. **`10_generate.py` 全量生成未跑**（约 25 分钟且会写 `work/`，禁止）；P2-3 基于代码静态分析 + 现存 `generated.jsonl`/`gan_fallback.json` 的状态核对。
3. **未验证 `11` 的输出能否逐字节复现 `e6d8a104…`**（需要全量重建）；本报告只验证了输入集合一致（§4.1 第 4 条）与 07 的 Real 复现（P1-1）。
4. **训练/评估脚本**（`09_train*.py`、`21_train_gan.py`、`32/34` 指标）不在本报告范围，由并行审计 `gan-eval` 负责；B/C 线数据链只作交叉引用，未深审。
5. **未做字形视觉质量评估**（观感、孔洞、端帽），也未重跑 `71_holes`/`23_compare_all`/`16_check_real`（后者会写 `work/real_check.json`）。
6. 未检查 `data/vendor/zi2zi-JiT/`（AGENTS 禁止修改，且非 A 线发布路径）。
7. `14_package.py` 的「import 即改写 release/」副作用与 `--out` 不一致，未做现场演示（会改发布目录），仅静态确认（`14_package.py:141`）。

---

## 6. 复现命令（全部只读或写 /tmp）

```bash
cd /Users/wainshine/newAI/guangeti
# A. 计数与来源
wc -l work/cells.jsonl work/labeled.jsonl work/chosen.jsonl work/generated.jsonl work/real_contours.jsonl
python3 - <<'EOF'
import json, collections, os
ch=[json.loads(l) for l in open('work/chosen.jsonl')]
print('chosen',len(ch),'unique',len({r['label'] for r in ch}))
print('cells/masks 缺失', sum(1 for r in ch if not os.path.exists('work/cells/'+r['file'])),
      sum(1 for r in ch if not os.path.exists('work/masks/'+r['file'])))
norm=json.load(open('work/norm.json')); print('norm keys',len(norm),'missing',len({r['label'] for r in ch}-set(norm)))
gen=[json.loads(l) for l in open('work/generated.jsonl')]
print('gen',len(gen),collections.Counter(r['src'] for r in gen))
EOF
# B. 05 重跑（写 /tmp）：chosen 1,675 逐行一致
mkdir -p /tmp/a_audit/work05 && cd /tmp/a_audit/work05 && ln -sf $OLDPWD/work/cells . && \
  ln -sf $OLDPWD/work/labeled.jsonl . && ln -sf $OLDPWD/work/cells.jsonl .
cd /Users/wainshine/newAI/guangeti && OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  python3 scripts/05_select.py --work /tmp/a_audit/work05
# C. 06 重跑与 turdsize 对照（写 /tmp）：当前默认 3/1675 不同，turdsize=8 为 0
mkdir -p /tmp/a_audit/work06 && cd /tmp/a_audit/work06 && ln -sf $OLDPWD/work/cells.jsonl . && \
  ln -sf $OLDPWD/work/chosen.jsonl . && ln -sf $OLDPWD/work/masks .
cd /Users/wainshine/newAI/guangeti && python3 scripts/06_norm.py --work /tmp/a_audit/work06
# turdsize=8 版本：复制 06/glyphvec 到 /tmp，把 `trace(ink)` 改成 `trace(ink, turdsize=8)` 后重跑
# D. 07 两条 Real 路径（写 /tmp）
python3 scripts/07_build_real.py --reuse-contours --out /tmp/a_audit/Real_from_cache.ttf
# 重新描摹：复制 07 到 /tmp，仅把 ROOT 固定为仓库绝对路径、real_contours/输出改到 /tmp 后运行
# E. 08 重跑（写 /tmp）：pairs X/Y/chars 与仓库逐元素相同
mkdir -p /tmp/a_audit/work08 && cd /tmp/a_audit/work08 && \
  ln -sf $OLDPWD/work/cells . && ln -sf $OLDPWD/work/cells.jsonl . && \
  ln -sf $OLDPWD/work/chosen.jsonl . && ln -sf $OLDPWD/work/norm.json . && \
  ln -sf $OLDPWD/work/masks .
cd /Users/wainshine/newAI/guangeti && python3 scripts/08_make_pairs.py --work /tmp/a_audit/work08 \
  --out /tmp/a_audit/work08/pairs.npz
# F. 13_qa 实跑（不写 work/qa 的方法：--outdir /tmp）
mkdir -p /tmp/a_audit/qa && python3 scripts/13_qa.py --font build/GuanGeKai-Regular.ttf --outdir /tmp/a_audit/qa
# G. 发布制品与 provenance
shasum -a 256 build/GuanGeKai-Regular.ttf build/GuanGeKai-Real.ttf release/GuanGeKai-Real.ttf
python3 - <<'EOF'
import json, collections
p=json.load(open('release/provenance.json')); print(len(p), collections.Counter(p.values()))
print(json.load(open('release/stats.json')))
EOF
```
