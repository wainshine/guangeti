# 发布制品 / 打包 / 许可 / 字体元数据 审计（release-audit）

> 审计员：release-audit（独立审计，只报问题不改代码）
> 日期：2026-11-14
> 任务：task-3「审计发布制品/打包/许可/字体元数据/校验和（release*、build、OFL、13/14/71/83/95/97/98）」
> 约束遵守：仓库内只写本文件；`83_verify_ab_c.py` 在 `/tmp` 镜像树（symlink 只读目录 + 独立 `work-c`）中运行，
> 未写仓库 `work-c/`；`13_qa` 的 contact sheet 输出到 `/tmp`；未运行 07/11/14 重建链，未改 `release*/`、`build/`、`data/`、`docs/`。

---

## 0. 结论摘要

| 级别 | 数量 | 说明 |
|---|---|---|
| P0 | 0 | 本范围内未发现「发布件本身不可用/许可违规」级问题 |
| P1 | 4 | ① 随三线发布包分发的 `OFL.txt` 仍写「woodblock print」，且不在 97 检查器扫描范围；② 当前发布说明的孔洞指标 `0.7%` 无法复现且与同字形的历史记录矛盾；③ RELEASE-v1.7.2「不带参数重跑即发布口径」不成立（res/simplify 默认值与发布工作点不同）；④ 校验和账本不完整：8 个 A 线 zip 无任何哈希记录、3 个账本记载的 zip 在仓库中不存在、B 段哈希全部失效 |
| P2 | 10 | 见 §2 |

**最重要的 3 条**：

1. `OFL.txt`（仓库根 + 三个发布包，SHA-256 `51aae3b7…` 三包一致）第 8 行仍称语料是
   `Ming-dynasty woodblock print`。ERRATA E1/E2 已把语料定为写本、字体 name ID 0 也已改为
   `manuscript`，但**许可文本本身没有改，也不在 `97_check_terms.py` 的扫描范围内**，所以 `TERMS OK` 是盲绿。
2. `docs/RELEASE-v1.7.2.md:21` 的 `holes lost 0.7%（200 字抽样）` 用文档命令复现不出来：
   `--n 200`（默认 seed=0）得 **1.4%**，`--n 300` 得 **1.9%**（正好等于 `work/holes_a.json` 与 AGENTS 基线），
   全量 `--n 0` 得 **3.5%**；随机种子扫描 41 个 seed 的结果在 **0.7%–6.3%** 之间。同字形（v1.6.4）发布说明
   记录的是 `1.9% / 28.5%`，与本次 `--n 300` 实测逐位相同。
3. `docs/RELEASE-v1.7.2.md:12` 说「`10_generate.py` …不带参数重跑即发布口径」，但脚本默认
   `--res 256` / `--simplify 0.0`（`scripts/10_generate.py:420-423`），而 `data/release-a.json:20` 的发布口径是
   `--res 512 --simplify 2.0 --workers 6`。照说明不带参数跑，会得到与发布字形不同的合成数据。

正面复核结论（Lead 已独立验证，本报告另以只读命令复核一致，见 §3/附录 A）：三线 `release*/SHA256SUMS`
逐文件自校验全 OK；三线 zip 解包内容与 `release*/` 目录逐文件哈希一致；A/B/C 六款 build 字体与包内字体同哈希；
`data/release-a/b/c.json` 的常规哈希与实测一致；字体 name 表/cmap/UPM/metrics 正常；83 闸打印 `A/B INTACT`
与三个 `21,034`。

---

## 1. P1 发现

### P1-1 三线发布包内的 `OFL.txt` 仍把语料写成「woodblock print」，且检查器不扫该文件

**证据**

```text
$ grep -n 'woodblock\|manuscript' OFL.txt
8:Real (scanned) glyphs in this font were vectorised from the Ming-dynasty woodblock print
9:"四書白文" (attributed to 姜立綱), digitised by 書格 (shuge.org) from the 宮内庁書陵部 collection.

$ shasum -a 256 OFL.txt
51aae3b7dd5ba387b0b693f0965ae4ea3a9de40134e3e73c6c0922d6387774cc  OFL.txt
# 三包 SHA256SUMS 均为同一哈希：
$ grep OFL.txt release/SHA256SUMS release-b/SHA256SUMS release-c/SHA256SUMS
51aae3b7…  OFL.txt   （三处相同）

$ grep -n 'OFL' scripts/97_check_terms.py        # 扫描目标里没有 OFL.txt
137-141: targets = ROOT.glob("*.md") + docs/*.md + scripts/*.py + release*/README.md
$ python3 scripts/97_check_terms.py
TERMS OK （除白名单与已知遗留外一致；…）
```

对照：`ERRATA E1/E2` 已认定写本、v1.7.0 起字体 name ID 0 已改为 `Ming manuscript`（本次实测
`build/GuanGeKai-Regular.ttf` ID0 = `…Ming manuscript 四書白文…`）；`docs/ERRATA.md` 的 E2/E3/E4
只登记 name 表 / README / specimen 图，**没有任何一条覆盖 `OFL.txt`**。

**影响**
- 三个 zip 的许可文本把扫描来源误述为「刻本」，与本项目 2026-10-28 的语料性质更正自相矛盾；
  许可文本随包分发，是收件人看到的正式来源声明，不是「历史发布说明」。
- `97_check_terms.py` 是 AGENTS 发布流程第 7 步的硬闸，但它不扫 `OFL.txt`，所以该错误永远不会被闸住。
- 不是 OFL 法律条款违规（版权行与许可全文仍在），是**事实性错误 + 闸门盲区**。

**复现**：`grep -n woodblock OFL.txt`；`for d in release release-b release-c; do grep OFL.txt $d/SHA256SUMS; done`；
`python3 scripts/97_check_terms.py | tail -2`。

**建议**
1. 修仓库根 `OFL.txt` 第 8 行为 `Ming manuscript / 明代精写本`（仓库文件可改，不需要重打包）；
2. 在 `ERRATA.md` 登记「已发布包内 OFL.txt 为发布时快照，保留错误措辞」（与 E3/E4 同类），或者在下一次正式发版时重打包；
3. `97_check_terms.py` 把 `OFL.txt`、`LICENSE` 和 `release*/OFL.txt` 加入扫描（release/ 前缀天然进 LEGACY 桶，
   不阻断，但能被列出）；同时把 `release*/OFL.txt` 纳入「已知遗留」的显式清单。

---

### P1-2 发布孔洞指标 `holes lost 0.7%（200 字抽样）` 不可复现，与同字形历史记录相差约 2.7 倍

**证据**（`71_holes.py`，A 字体 `build/GuanGeKai-Regular.ttf = e6d8a104…`）

```text
$ python3 scripts/71_holes.py --font build/GuanGeKai-Regular.ttf --n 300 --json /tmp/holes_a300.json
  holes lost       4 / 214  (1.9%)          # 与 work/holes_a.json 完全一致；AGENTS 基线 1.9%
$ python3 scripts/71_holes.py --font build/GuanGeKai-Regular.ttf --n 200
  holes lost       2 / 145  (1.4%)          # 文档字面命令（默认 seed=0）
$ python3 scripts/71_holes.py --font build/GuanGeKai-Regular.ttf --n 0
  holes lost     528 / 15265 (3.5%)         # 全量（20,992 字）
# 41 个 seed 的 n=200 扫描（损失比例）：
  最小 1/139=0.72%(seed16) / 1/135=0.74%(seed20)；最大 10/158=6.33%(seed19)
```

**与文档对账**
- `docs/RELEASE-v1.7.2.md:21`：`孔洞 | holes lost 0.7%（200 字抽样）`；
- `docs/RELEASE-v1.7.1.md:19` 同写 `0.7%`（同一数字从 v1.7.1 沿用）；
- `docs/releases/RELEASE-v1.6.4.md:41`：`lost 1.9% / fewer 28.5%，与 v1.6.3 持平`；
  v1.6.5 发布说明 `RELEASE-v1.6.5.md:3` 明确「**字形与 v1.6.4 相同**」，v1.7.0 起又逐版声明字形不变
  （v1.7.2 `RELEASE-v1.7.2.md:5`「字形与 v1.7.1 相同」）。字形未变而 `lost` 从 1.9% 变成 0.7%，只有
  抽样波动能解释；本次 `--n 300` 的 `1.9% / fewer 28.5%` 与 v1.6.4 记录**逐位相同**。
- `work/holes_a.json`（2026-10-27）记录 `lost 4 / 214 (1.9%)`，与本次实测一致。

**影响**：发布说明里的质量指标既不是文档命令可复现的值，也不满足 AGENTS「不高于上一版基线 1.9%」的比较口径；
不同 seed 下 0.7%–6.3% 的方差说明该抽样（n=200/300）不足以支撑「0.7%」这种精度。任何接手者按 AGENTS
发布流程第 3.4 步跑出的都是 1.4%/1.9%，会被迫回头考古。

**复现**：附录 B 第 3 节命令。

**建议**
1. `RELEASE-v1.7.2.md` 的孔洞行改为**全量口径**（`528 / 15,265 = 3.5%`）或写明 `seed` 与 n 的完整命令，
   并注明「与 v1.6.4 同字形同命令 1.9% 一致」；
2. `71_holes.py` 在输出/`--json` 中记录 `seed` 与命令行（当前 json 只有 font/tested/comparable）；
3. AGENTS 的「holes lost 不高于基线」改成**固定 seed + 同 n + 全量三口径并列**，否则该闸不可比较。

---

### P1-3 RELEASE-v1.7.2「不带参数重跑即发布口径」不成立（res / simplify 默认值与发布工作点不同）

**证据**

```text
$ sed -n '12p' docs/RELEASE-v1.7.2.md
| 4 | **工作点固化** | 10_generate.py 默认改为主 m2wt_ep090.pt + 补位 m2_ep080.pt + 阈值 −0.05/−0.45，与 data/release-a.json 一致；不带参数重跑即发布口径 |

$ grep -n 'reproduce' data/release-a.json
20: "reproduce": "python3 scripts/10_generate.py --method gan --res 512 --simplify 2.0 --workers 6 --ckpt-hardtail work/ckpt/m2_ep080.pt --threshold -0.05 --hardtail-threshold -0.45",

$ sed -n '420,423p' scripts/10_generate.py
    ap.add_argument("--simplify", type=float, default=0.0, …)
    ap.add_argument("--res", type=int, default=256, …)
```

- 模型/阈值默认值确实已在 2026-10-30 的 commit `bcb74b4` 改好（`GAN_CKPT=m2wt_ep090.pt`、`HARDTAIL=m2_ep080.pt`、
  `GEN_THR=-0.05`、`HARD_THR=-0.45`），但 **`--res`、`--simplify`、`--workers` 没有**；
- 发布字形按 `data/release-a.json` 是 512px 渲染 + simplify 2.0（`RELEASE-v1.7.2` 与 PROJECT_STATE §10
  都写 512/simplify 2.0 是 v1.5.0 起的口径），不带参数跑会得到 256px/不简化 的合成数据；
- 所以「不带参数重跑即发布口径」只对模型与阈值成立，对字形不复现。发布说明内部 #4 与 `data/release-a.json`
  的 `reproduce` 行直接冲突。
- 同一现象的旁证：`docs/DATA.md §6` 的重建命令显式写 `--res 512 --simplify 2.0`，`AGENTS.md`
  也写 `--res 512 --simplify 2.0`（`10_generate.py --method gan --workers 6 --res 512 --simplify 2.0`），
  只有发布说明的「不带参数」表述是错的。

**影响**：照当前发布说明重跑得到的是 256px/不简化的旧代风格合成数据，与发布字体不符；这会直接破坏
「工作点固化」这一整条 v1.7.2 的卖点，并让第三方复现者得出不同的字形/文件大小结论。

**复现**：`python3 scripts/10_generate.py --help | grep -A2 'res\|simplify'`；对照 `data/release-a.json:20`。
（未实际重跑生成，属禁止的「重新生成字体」；代码阅读即可判定。）

**建议**：把 `--res` 默认改为 512、`--simplify` 默认改为 2.0、`--workers` 默认 6（与发布口径一致），
或把发布说明改成「模型/阈值已固化；字形仍需显式 `--res 512 --simplify 2.0`」。

---

### P1-4 校验和账本不完整：8 个 A 线 zip 无任何哈希记录；3 个账本记载的 zip 不存在；B 段哈希全部失效

**证据**（扫描 `*.md`、`docs/*.md`、`docs/releases/*.md`、`data/*.json` 中 64-hex，与 22 个根 zip + build/archive + 包内字体逐一比对）

```text
根目录 zip 共 22 个（全部实测 SHA-256，见附录 A）。
在仓库文档/JSON 中找不到其 zip 哈希的 A 线版本（8 个）：
  v1.6.0 / v1.6.1 / v1.6.2 / v1.6.3 / v1.6.4 / v1.6.5* / v1.7.0 / v1.7.1
  （*v1.6.5 的哈希只出现在 docs/CONVENTIONS.md:142 的一段历史代码引用里，
    是迁移计划的旧 ZIPS 常量，不是发布账本；83 里的 v1.6.5 已被替换为 v1.7.2）
而 docs/releases/RELEASE-v1.6.0.md:48、v1.6.1:56、v1.6.2:28、v1.6.3:46、v1.6.4:53、v1.6.5:44、
RELEASE-v1.7.0.md:51 都写「校验和见 docs/DATA.md」，但 DATA.md §5 只有 v1.5.0/1.5.1/1.5.2
和当前 build 字体；v1.7.2 zip 哈希以裸行挂在文件最末（docs/DATA.md:309，§7 之后，不在 §5 的代码块内）。

账本记载但仓库中不存在的制品（哈希无法核对）：
  GuanGeKai-B-v1.0.1.zip   —— docs/DATA.md:120（并见 RELEASE-v1.6.0/1.6.1 说明）；根目录没有该 zip
  GuanGeKai-C-v1.0.1.zip   —— docs/RELEASE-v1.0.1-C.md:100 的 041bfa97…；根目录没有该 zip
                             （仅 build/archive/release-c-v1.0.1/ 目录，且 CLEANUP-C.md:99 明确要求保留
                              v1.0.0~v1.3.0 的 zip，v1.0.1 是唯一缺的）
  GuanGeKai-v1.2.0.zip     —— docs/releases/RELEASE-v1.2.0.md 记录的 844440e5…/7119d686… 字体哈希
                             及 zip 不在仓库（A 线历史 zip 只剩 v1.5.0 起）

B 段失效：docs/DATA.md:115-121 的「B 线（史记本，v1.0.1）」三条哈希（b76cfc01…/79aadc23…/f95b5e7f…）
与实测 B 线 v1.2.4 字体（aa19d6d2…/7d10e460…）对不上，且被引用的 B-v1.0.1.zip 不存在；
DATA-B.md §6 才是当前 B 线的正确校验和。
```

**影响**：AGENTS 发布流程第 6 步要求「同步校验和到 DATA.md / PROJECT_STATE」；当前历史 A 线 8 个 zip
的完整性没有任何可核对记录，B 段是失效指针，3 个账本条目无法验证。外部下载者拿到 v1.6.x 文件后无法
从文档核对，这违背了 `docs/DATA.md:190` 自己写的「中间产物没有校验和链，只保证最终发布文件可核对」的承诺。

**复现**：附录 B 第 1 节（脚本：收集 64-hex 与实测哈希比对）。
（格式层面：DATA.md §5 代码围栏在 108/117/121/125 行错配，B 线标签被包进代码块、B 哈希裸露在代码块外，
v1.7.2 哈希挂在文件尾；该格式问题与 docs-consistency 审计的 P1-12 重叠，本报告只补充「缺失清单」。）

**建议**
1. 在 DATA.md §5 建立「A 线全版本 zip」表：v1.5.0–v1.7.2 每行 `哈希 + 文件名 + 大小 + 发布日期`，
   v1.7.2 行从文件尾移回表内；
2. DATA.md 的 B 段改为指向 `DATA-B.md §6`，删除 v1.0.1 三条失效哈希（或注明「历史版本，制品未保留」）；
3. `CLEANUP-C.md` 要求保留的 `GuanGeKai-C-v1.0.1.zip` 要么找回、要么在 CLEANUP-C/DATA-C 登记「已丢失」；
4. 增加一个 `scripts/xx_check_sums.py`（或扩 `83`）自动核对「文档中出现的每个 zip 哈希 ↔ 磁盘文件」，
   防止再出现裸行/失效段。

---

## 2. P2 发现

### P2-1 发布 zip 不能逐字节复现：Info-ZIP 把文件 atime 写进 UT 扩展字段

**证据**

```text
# 同内容、同顺序、同文件 mtime，用 AGENTS 第 5 步的命令重打包：
$ ( cd release && zip -q -r /tmp/z_dir.zip . )
$ shasum -a 256 /tmp/z_dir.zip GuanGeKai-v1.7.2.zip
6b4c7b6c…  /tmp/z_dir.zip
14483141…  GuanGeKai-v1.7.2.zip          # 不同
$ cmp -l /tmp/z_dir.zip GuanGeKai-v1.7.2.zip | wc -l
16                                        # 仅 16 字节不同，全部位于 UT 扩展字段的 atime 4 字节
$ unzip -q GuanGeKai-v1.7.2.zip -d /tmp/zipcheck/a && ( cd /tmp/zipcheck/a && zip -q -r /tmp/rezip_a.zip . )
3af1dc89…  /tmp/rezip_a.zip              # 解包后目录顺序变化，同样不同
$ touch 两个 ttf 后重打包
fcea41e0…  # mtime 变化即再变
```

**影响**：DATA.md:127 已承认「重新打包会变」，83 的 ZIPS 注释也承认 zip 哈希是发布快照；但
`docs/RELEASE-v1.2.4-B.md:68-72` 声称「上面的命令连跑两次产出完全相同的字节（实测 7db260a6…/7db260a6…，
4e80d782…/4e80d782…）」。在当前工具链下 zip 的字节同时依赖**文件顺序、mtime、atime**，该声明对 zip
不成立（对字体字节可以成立）；若按此声明做 CI 校验会随机失败。

**建议**：AGENTS 第 5 步改为确定性打包：`cd release && TZ=UTC find . -type f | sort | \
  zip -X -q ../GuanGeKai-vX.Y.Z.zip -@`（`-X` 去掉 UT/ux 扩展字段），或使用 `bsdtar --options
  zip:compression=deflate` + `SOURCE_DATE_EPOCH`；并修正 B 发布说明的「可复现」措辞，只对字体声明字节一致。

### P2-2 历史 zip 内 `Real.ttf` 自报版本号与本包版本不一致（未披露）

```
GuanGeKai-v1.6.4.zip:  GuanGeKai-Real.ttf  name ID5 = "Version 1.6.3"  sha256 54d22b65…（= v1.6.3 的 Real，逐字节相同）
GuanGeKai-C-v1.2.1.zip: GuanGeKai-C-Real.ttf name ID5 = "Version 1.2.0" sha256 0cbb7cb1…（= v1.2.0 的 Real，逐字节相同）
```

原因应是这两版只改了合成字/Regular，Real 未重建（C v1.2.1 说明确实写「Real 仍为 5,302」），但发布说明都
没有说「包内 Real 的版本串不随包版本递增」。用户用字体信息面板判断版本会得到旧号。
**建议**：在下一版把 Real 的版本串随包递增（重建成本仅一次 `07 --reuse-contours` 等价操作），
或在 ERRATA 登记这两条历史制品差异。

### P2-3 `build/` 存在未登记制品（实验字体 + 归档目录）

```
build/GuanGeKai-C-Big-Regular.ttf   17,004,404 B  Version 0.1.0-exp  family "GuanGe Kai C Big"
    → docs/、README、DATA.md、PROJECT_STATE 均无引用（grep 'C-Big|C Big|CBig' 无命中）
build/archive/  （共 37 个文件）
    release-c-v1.0.1/、release-c-v1.1.0/、release-c-v2/ 三套完整发布快照
    GuanGeKai-C-Regular-v1.2.0.ttf / -Real-v1.2.0.ttf / GuanGeKai-C-v1.2.0.zip
    → DATA.md §2/§7、PROJECT_STATE §2 均无登记
```

**影响**：发布台账无法区分「发布件」与「实验/归档件」；`build/*.ttf` 在 `71_holes`、`97_check_terms`
的扫描通配内，误把 C-Big 当发布字体检查/分发会造成混淆；且 archive 内含 zip，容易被外部当作正式发布包。
**建议**：在 DATA.md §2 增加 `build/` 清单（含 archive 与 C-Big 的用途/保留决定），或在 `build/archive/README`
写明「仅归档，不是发布件」。

### P2-4 三线发布日期在制品/账本/文档间不一致；B 包在账本日期之后重建

```
A：GuanGeKai-v1.7.2.zip           mtime 2026-10-30 17:12
    release/README.md            内文「A v1.7.2 / B v1.2.4 / C v1.2.0（2026-10-30）」
    data/release-a.json:51       release_date = 2026-11-13
    README.md:11                 「A v1.7.2 / B v1.2.4 / C v1.3.0（2026-11-02）」
B：GuanGeKai-B-v1.2.4.zip         mtime 2026-11-13 09:21（provenance/stats/README 等条目也是 11-13）
    data/release-b.json:15       release_date = 2026-10-30
C：zip mtime 2026-11-02，data/release-c.json:31 release_date = 2026-11-02（一致）
```

A 的 `release_date=2026-11-13` 比制品晚 14 天；B 的 `release_date=2026-10-30` 比实际打包时间早 14 天。
`release_date` 的语义（版本定稿日 / 打包日 / 账本更新日）三线不一致，也没有文档定义。
**建议**：给 `release-a/b/c.json` 增加 `artifacts_built_at`（取 zip mtime 或写明）并把 `release_date`
定义为「版本发布日」；或统一由脚本从制品时间生成。

### P2-5 `docs/DATA.md §3` 对字体 name 表的描述与实测不符

```
DATA.md:47  「name 表 ID 13 = SIL OFL 1.1 全文，ID 14 = 许可 URL，ID 0 = 版权声明（含 LXGW 与 Klee 的版权行）」
实测 A/B/C 字体：
  ID13 = 单行短声明「This Font Software is licensed under the SIL Open Font License, Version 1.1.
         This license is available with a FAQ at: https://openfontlicense.org」→ 不是「全文」
  ID0  = 「… Generated glyphs derived from LXGW WenKai (OFL 1.1). Copyright 2026 The GuanGe Kai Project Authors.」
         → 不含 Klee 版权行；Klee 版权行只出现在 OFL.txt（`Copyright 2020 The Klee Project Authors`）
```

**影响**：许可审计的关键事实（「OFL 全文在 name 表里」）不成立。OFL 条件 2 允许许可以独立文件随包提供，
当前三包都带 `OFL.txt` 全文，因此**不构成违规**；但 DATA.md §3 的这句错误陈述会让后续审计误以为
name 表自带全文，从而漏检「OFL.txt 是否随包分发」。
**建议**：改为「ID13 = OFL 1.1 标准短声明；OFL 全文与 LXGW/Klee 版权行见随包 `OFL.txt`」。

### P2-6 `13_qa.py` 不是三线通用闸：对 B/C 用正确 `--real` 会 ABORT，用默认值会「绿但校验错对象」

```
$ python3 scripts/13_qa.py --font build/GuanGeKai-B-Regular.ttf --real build/GuanGeKai-B-Real.ttf --outdir /tmp/qa/b13
real-subset glyphs 4073 cmap 4073 -> BROKEN
ABORT: GuanGeKai-Real.ttf expected 1675/1675, got 4073/4073
$ python3 scripts/13_qa.py --font build/GuanGeKai-B-Regular.ttf --outdir /tmp/qa/b13d
real-subset glyphs 1675 cmap 1675 -> OK      # 默认 --real 指向 A 的 Real，校验的是 A 的子集
（C 同理：5257/5257 -> BROKEN；默认时 OK）
```

原因：`scripts/13_qa.py:72-84` 的期望值固定从 `work/chosen.jsonl` 读（A 线 1,675），且默认 `--real`
是 `build/GuanGeKai-Real.ttf`。B/C 各有自己的闸（`63_qa_b.py`、`80_qa_c.py`，本次均实测 `QA OK`）。
**影响**：任务要求的「13_qa（三线各一次）」无法照做；若有人对 B/C 直接跑 13_qa，默认参数会给绿灯但
实际没有检查 B/C 的 Real 子集。**建议**：给 13_qa 加 `--work`（chosen.jsonl 路径）参数，
或在文档中明确「13_qa 仅 A 线；B/C 用 63/80」。

### P2-7 发布闸辅助图落后于当前版本；95 的 `--check` 硬闸未进发布流程，C 字体缺 build↔release-c 硬核对

```
docs/images/lines-compare.png   最后提交 bcb74b4 2026-10-30（早于 C v1.3.0 构建 2026-11-02 10:15）
docs/images/style-{A,B,C}.png   同上（2026-10-30）
docs/images/eval-panelA/B.png   最后提交 501f204 2026-10-28（早于 A v1.7.2）
AGENTS.md:155  发布流程 4.5 调 `python3 scripts/95_compare_lines.py`（没有 --check）
scripts/95_compare_lines.py:44-45  --check 会核对 build/*.ttf 与 release*/SHA256SUMS，不一致 exit 2
```

**影响**：AGENTS 把 95/98 当「发布视觉闸」，但三线对照图停在 C v1.2.1 时代，不能作为 C v1.3.0 的验收证据；
且 `83_verify_ab_c` 只核 A/B 字体与 3 个 zip，唯一能核 C 字体「build==release-c」的 95 `--check` 默认不跑。
**建议**：AGENTS 4.5 改为 `python3 scripts/95_compare_lines.py --check`，并在 C 发版清单加「重出
lines-compare/style-C 并提交」；CI 里放 `95 --check`。

### P2-8 QA 脚本 docstring/注释陈旧（不影响闸功能，但误导审计）

```
scripts/83_verify_ab_c.py:9-10   「release/SHA256SUMS (A v1.6.5) / release-b/SHA256SUMS (B v1.2.1)」
                                 实际 A v1.7.2 / B v1.2.4；:11 「B chosen 4,078」实际 4,073
scripts/71_holes.py:2            「generic for both lines (A and B)」实际 C 线也经 80_qa_c 调用
scripts/80_qa_c.py:1             「B-line: coverage / … for the 史記 font」——从 63 复制，C 线脚本
docs/DATA-C.md:4                 「数字均为 2026-10-27 实测」，正文包含 2026-11-02 的 v1.3.0 数字
```

**建议**：把版本号/线名改成从 `data/release-*.json` 读，避免下次再落后。

### P2-9 ERRATA E3/E4 对「包内快照」的版本标注与实际不符，会让后续审计重复考古

```
ERRATA E3（docs/ERRATA.md:39-51）：「release/README.md v1.6.5」
  实测 release/README.md 是 v1.7.2 时期的快照：内文「A v1.7.2 / B v1.2.4 / C v1.2.0（2026-10-30）」，
  且 C 数据为 v1.2.0（5,299 真迹/6.0% 回退），不是 v1.6.5。
ERRATA E4（:53-59）：「release*/specimen.png 与 book-vs-font* 带旧措辞（刻本），包内旧图不动」
  实测 release/specimen.png = docs/images/specimen.png = 当前 scripts/12_specimen.py 的输出，
  三者逐字节相同（77472b61…，本次重出验证），图注是「寫本」；E4 对 specimen 的描述已过期。
ERRATA E3 还写「release-c/README v1.0.1（联合发版时已重打包）」，实际 release-c/README.md 是 v1.3.0 当前版
  （与 README-C.md 除 `docs/images/` 前缀外逐字节相同）。
```

**影响**：ERRATA 的目的是「避免每个接手的人重新考古」；E3/E4 的版本/内容标注失真会让人以为 A 包 README
是 v1.6.5、specimen 仍是旧措辞，从而放过真正的 v1.7.2 包内跨线数字漂移（C v1.2.0 写在 A 包里）。
**建议**：更新 E3/E4 的具体版本与文件清单；E4 注明「specimen 在 v1.7.2 打包时已是新图，仅 book-vs-font
与（A 包旧 README）仍为快照」。

### P2-10 `release-a.json` 的发布口径干净集 Dice（0.539）与当前发布说明（0.549）并存且未注明换算关系

```
data/release-a.json:33-45  clean.n=617 / dice 0.539 / ink 0.983
                           note_vs_experiments: 「E32 报 0.549（n=150 抽样）；本行是 n=617 全量…
                           以本行为发布口径」
docs/RELEASE-v1.7.2.md:22  「干净集 | Dice 0.549、chamfer 5.92」
AGENTS.md:129              「干净集 Dice 0.549」
```

两个口径本身都真实，但当前**发布说明**给出的 0.549 是旧抽样值，与账本自称的「发布口径 0.539」冲突，
且发布说明没有说「0.549 是 n=150，全量 0.539」。与 docs-consistency 审计的 P1-18 重叠，此处只补账本侧证据。
**建议**：RELEASE-v1.7.2 的指标行改为「0.539（n=617 全量；旧 n=150 抽样口径 0.549、chamfer 5.92）」。

---

## 3. 已核查不成立 / 正面复核（不构成缺陷）

| # | 假设 | 复核结果 | 证据 |
|---|---|---|---|
| 1 | 包内字体与 `build/` 不同 | **不成立**。A/B/C 六款字体 build 与 release* 同哈希：`e6d8a104…`/`bf278ab1…`、`aa19d6d2…`/`7d10e460…`、`765d0848…`/`6caf9d82…` | `shasum -a 256 build/*.ttf release*/*.ttf` |
| 2 | zip 内字体与 release 目录不同 | **不成立**。三包解包后与 release*/ 逐文件哈希完全一致；11 文件/包；无 `.DS_Store`/`__MACOSX` | `/tmp` 解包 `diff`；附录 A |
| 3 | zip 内 `SHA256SUMS` 是假的 | **不成立**。三包 `shasum -a 256 -c SHA256SUMS` 全 OK；22 个历史 zip 全部 11 文件、全部自校验 OK | 附录 A |
| 4 | 字体元数据仍是 woodblock | **不成立**（E2 已修复）：A/B/C 六款 ID0 = `Ming manuscript`；仅 `OFL.txt` 与 A 包 README 快照仍有旧说法（前者的发现见 P1-1，后者属已接受 drift） | `fontTools` name 表 dump |
| 5 | `Real.ttf` 含标点/合成字 | **不成立**。A/B/C Real cmap 分别 1,675/4,073/5,257，全部在 U+4E00–U+9FFF；与 `release*/provenance.json` 的 `real` 集合**完全相同** | 集合比较；A: `real_prov==real_cmap True` |
| 6 | Regular 与 Real 的真字轮廓不一致 | **不成立（视觉层）**。栅格 128px IoU：A 仅 3/1,675 字 <0.999（全部 ≥0.95）；C 68/5,257 <0.999（全部 ≥0.95）；B 零差异。差异来自冗余末点/起点编码（fontTools 重建时丢重复末点） | 逐字 RecordingPen + PIL 栅格 IoU |
| 7 | `13_extend_punct` 输出不可复现（RELEASE-v1.7.2 #3） | **成立（正面）**。对 shipped 字体连续跑两次均得 `e6d8a104…`（= 发布字体）；把 42 码位剥掉后用当前脚本重补，仍得 `e6d8a104…` | `13_extend_punct --line A --out /tmp/a_ext{1,2}.ttf`；strip+extend 实验 |
| 8 | `punct_set.py` 不是唯一源/脚本硬编码 | **基本成立**。`13_extend_punct/13_qa/63_qa_b/64_package_b/80_qa_c/83/14_package` 均 import `punct_set`；脚本里没有硬编码 `21,034`（`83:164` 的打印串 `20,992 + 42` 是文案且数字正确；`14_package.py:126` 硬编码的是基本区 20992 而非 cmap 总数，属 P2 级代码卫生，见 a-pipeline 报告） | `grep -ln punct_set scripts/*.py`；`grep -rn '21,?034' scripts` |
| 9 | `83_verify_ab_c` 只打印不中止 / 不打印三线 21034 | **不成立**。实测打印 `RESULT: A/B INTACT` 与三行 `OK A/B/C 字集 21034 = 20,992 + 42`；任一 diff `raise SystemExit`（exit 1） | 附录 A 第 2 节 |
| 10 | `71_holes` 应按硬闸中止 | **不成立（设计如此）**。脚本始终 `return 0`；AGENTS 明示「记录，不阻断」。B/C 的硬闸在 63/80 里（`max-lost-frac`），本次 B/C QA 均 OK | 读代码 + 实跑 |
| 11 | `13_qa` 硬闸不生效 | **不成立**。覆盖率/empty/tiny/huge/punct/fontRevision/real-subset 均 `raise SystemExit`；A 实跑通过 | 读代码 + `13_qa` A 实跑 |
| 12 | UPM/metrics 与文档不符 | **不成立**。六款字体 UPM 1000、hhea asc 880 / desc −120 / lineGap 0、OS/2 typo/win 880/120；A glyphs 21,035（含 .notdef）、cmap 21,034；basic 20,992 + 42 punct 精确 | fontTools dump |
| 13 | `LICENSE` 与 README 授权陈述矛盾 | **不成立**。`LICENSE` = MIT（含「字体二进制走 OFL」的 scope note）；三包均含 OFL.txt + LICENSE；README「代码 MIT / 字体 OFL」一致 | `cat LICENSE`、包内容 |
| 14 | 家族名用了 OFL 保留字体名 | **不成立**。ID1/4/6 分别 `GuanGe Kai`/`GuanGe Kai Regular`/`GuanGeKai-Regular`（B/C 同理），无 霞鹜/霞鶩/LXGW；RFN 仅出现在 OFL.txt 的衍生声明里（允许） | name 表 dump |
| 15 | `release-a.json` 的 provenance 计数是编的 | **不成立**。用 `work/chosen.jsonl` + `work/generated.jsonl` 逐字重算 provenance：real 1,675 / gan_ep90 17,790 / gan_ep80 728 / ribbon_fb 799 / punct 42，与发布 `release/provenance.json` **零不一致**；`stats.json` 各字段亦一致 | 附录 B 第 4 节 |
| 16 | 22 个历史 zip 有损坏/缺文件 | **不成立**。22/22 全部 11 文件、`SHA256SUMS` 自校验 OK、无多余文件；仅两处版本串不一致（P2-2） | 附录 A |
| 17 | `specimen.png` 是旧措辞 | **不成立**（E4 过期）：当前 `12_specimen.py` 重出 = `docs/images/specimen.png` = `release/specimen.png` = `77472b61…`，图注「寫本」 | 实跑 12_specimen 到 /tmp 比对 |

---

## 4. 已披露 / 已接受（按任务要求不算新发现）

| 项 | 依据 | 本审计备注 |
|---|---|---|
| A 包 `release/README.md` 是发布时快照，内容落后于仓库（含 C v1.2.0、5,299 真迹、6.0% 回退），三包「只改仓库，包内不动」 | `docs/ERRATA.md` E3；`docs/CONVENTIONS.md` §4（:136-154） | 接受。但 E3 的**版本标注**本身失真（见 P2-9）。仓库 README 已更新到 C v1.3.0，包内未动属既定决策 |
| `release*/specimen.png` / `book-vs-font*` 为发布时快照 | `ERRATA.md` E4 | 接受。补充：v1.7.2 打包时 specimen 已是新图（P2-9），book-vs-font 仍是人工静态图 |
| 已发布字体 name 表曾写 woodblock | `ERRATA.md` E2 | v1.7.0 起已修好，实测确认 |
| `97_check_terms` 的 `build/*.ttf` 与 `release*/README` 若命中只算「已知遗留」 | `ERRATA.md` E2/E3/E4；`97_check_terms.py` 的 LEGACY_PREFIX | 接受；P1-1 是 OFL.txt 完全在扫描范围外，与这条不同 |
| 中间产物无校验和链 | `docs/DATA.md:190-191` | 接受；P1-4 只针对「最终发布文件」的账本缺口 |
| B 线 v1.2.4「字形未动」导致 zip 内 Real 沿用旧字节 | `docs/RELEASE-v1.2.4-B.md`、`docs/DATA-B.md` | 部分披露：说明写了「不改」，但没写「Real 版本串停在旧号」（P2-2） |

---

## 5. 与其它审计报告的去重

本目录已有 `a-pipeline.md`、`docs-consistency.md`、`hygiene-repro.md`、`line-c.md`。本报告只保留
**发布制品/许可/校验和/发布闸**视角，以下条目与它们重叠、以对方为主：

- `DATA.md §5` 格式损坏与当前版本缺失 → docs-consistency P1-12；本报告 P1-4 只补「缺失 zip 清单 / 失效 B 段 / 缺失制品」。
- 孔洞 lost 多数字并存 → docs-consistency P1-14；本报告 P1-2 补种子扫描量化与同字形历史对账。
- C 线 ribbon 1,228/1,313、6.25%/8.3%/0.0712 → line-c P1-9；本报告不重复，认可其结论。
- `14_package.py` 导入即写盘 → hygiene-repro P2-1；`a-pipeline` P2-4；本报告不重复。
- README/PROJECT_STATE 陈旧条目 → docs-consistency 的 P1-x/P2-x；本报告只保留与「发布包快照」直接相关的 P2-9。
- 83 持久化证据早于 C 字集检查 → line-c P1-8；本报告不复核其内部写入顺序，仅复核闸输出正确。
- B 线发布制品轻量核对 → hygiene-repro §3；本报告附录 A 独立复核并一致。

---

## 6. 未覆盖 / 限制

1. **未从零重跑整链**：未运行 `07/11/14/10_generate`（任务硬约束：禁止重建/重新生成字体）。因此
   「按 AGENTS 全链重建能否逐字节得到 e6d8a104…」只做了两个局部验证：`13_extend_punct` 的字节可复现、
   strip+extend 复现发布哈希；`10_generate` 的默认值问题只做代码判定。
2. **未复核 B/C clean-set 指标**（需模型推理）；只核对了 `work/eval_clean_a172.json`、
   `work-b/eval_v124_release.json`、`work-c/accept_c.json` 与账本数字一致。
3. **未做视觉判断**（specimen/style 图、对比面板的「风格连续/粗细」需人眼）；只核对了图的存在/新鲜度/可重建性。
4. **未运行 23_compare_all/95/98**（会写 `docs/images/`，且非任务许可命令）；95 的 `--check` 只读代码审查。
5. **历史 zip 内容没有逐个对照各自发布说明**（22 个 × 11 文件）；只做了完整性/自校验/字体版本/哈希记录核查。
6. **未验证 `data/release-b.json` 的 clean 复现命令**（65_eval_b 需模型）；已核对其输出文件 `work-b/eval_v124_release.json` 存在且数字一致。
7. **未审计 `docs/index.html`**（live 页面；docs-consistency P1-17 已覆盖 97 不扫 html 的盲区）。
8. **未覆盖 `release*` 二进制层面的 hinting/license 兼容性深检**（如 OFL RFN 的 AGL 名称、fsType 已核为 0）。

---

## 附录 A：实测数据（2026-11-14，全部只读）

### A.1 当前三线制品校验和

```
e6d8a104c9bcc284165de2d2c2abc8f0729f23031b33ec062b6de27ce097edac  build/GuanGeKai-Regular.ttf
bf278ab1631bdb0da75a1b1b6b9c8628d7ec8b4792da7ef904c81f71f4dd1c86  build/GuanGeKai-Real.ttf
14483141b854056aa887f6e4be37c78053692419dd304a4e3de432be7256835b  GuanGeKai-v1.7.2.zip
aa19d6d2000d504af7123741fe9273bee157fee1f2915c570a9d05d27bab8f9d  build/GuanGeKai-B-Regular.ttf
7d10e4602313f3ca440953ed20f75e3a96f1428d96c8c4c75e17e23857f1498a  build/GuanGeKai-B-Real.ttf
2537de50f67517696fea70102c97ecb4da0f8bd29d3746baebad629ee4e83c46  GuanGeKai-B-v1.2.4.zip
765d08486b75da52e196cbe81570efd29226cea26d4f4198d6acd62dbf440f48  build/GuanGeKai-C-Regular.ttf
6caf9d82d71ad716eb5cbcf7a8c2947245756141a24b53f061130783752f359d  build/GuanGeKai-C-Real.ttf
4b4737758a342e8ddc59ac60615e846c760564faadfb87760f08bf70639f5498  GuanGeKai-C-v1.3.0.zip
```

与 `data/release-a/b/c.json` 的 `regular_sha256 / real_sha256 / zip_sha256`（A）与 `font_sha256 / real_sha256 / zip_sha256`（B/C）**全部一致**；
三处 `release*/SHA256SUMS` 的 `shasum -a 256 -c` 全部 `OK`；三包解包后与 `release*/` 目录逐文件哈希一致。

### A.2 `83_verify_ab_c.py` 实跑（/tmp 镜像树，未写仓库）

```
OK GuanGeKai-Regular.ttf e6d8a104c9bcc284 15,739,524 B
OK GuanGeKai-Real.ttf    bf278ab1631bdb0d  3,291,812 B
OK GuanGeKai-B-Regular.ttf aa19d6d2000d504a 15,432,348 B
OK GuanGeKai-B-Real.ttf    7d10e4602313f3ca  3,818,680 B
OK A coverage 20992 / A real glyphs 1675 / A chosen 1675 / A provenance real 1675
OK B coverage 20992 / B real glyphs 4073 / B chosen 4073 / B provenance real 4073
OK A family 'GuanGe Kai' / OK B family 'GuanGe Kai B'
OK GuanGeKai-v1.7.2.zip 14483141b854056a
OK GuanGeKai-B-v1.2.4.zip 2537de50f6751769
OK GuanGeKai-B-v1.2.2.zip d9da537640fbac12
OK A 字集 21034 = 20,992 + 42
OK B 字集 21034 = 20,992 + 42
OK C 字集 21034 = 20,992 + 42
RESULT: A/B INTACT
```

### A.3 三线 QA 实跑

```
python3 scripts/13_qa.py --font build/GuanGeKai-Regular.ttf --outdir /tmp/qa/a
  coverage 20992/20992 = 100.0000% / empty 0 tiny 0 huge 0 / real-subset 1675/1675 -> OK
python3 scripts/63_qa_b.py --outdir /tmp/qa/b63 --real-expect 4073 --sheets 1
  punct 42/42 outside 42 cmap 21034 / real-subset 4073/4073 OK / counters lost 1/214 (0.5%) / QA OK
python3 scripts/80_qa_c.py --outdir /tmp/qa/c80 --real-expect 5257 --sheets 1
  punct OK / real-subset 5257/5257 OK / counters lost 3/214 (1.4%) / QA OK
python3 scripts/97_check_terms.py    → TERMS OK（23 文件白名单、15 行显式豁免）
```

### A.4 孔洞复核（A，`71_holes.py`，本报告 P1-2）

```
--n 300 : lost 4/214 = 1.9%，fewer 61/214 = 28.5%   （= work/holes_a.json，= v1.6.4 文档记录）
--n 200 : lost 2/145 = 1.4%                        （文档字面命令，seed 0）
--n 0   : lost 528/15265 = 3.5%                    （全量 20,992 字）
n=200 seed 0..40：lost 比例 0.72%–6.33%（41 个结果，见正文）
```

### A.5 22 个根 zip 清点（全部 `shasum -c` 通过；字体版本以 name ID5 为准）

| zip | 文件数 | 自校验 | Regular 版本 / Real 版本 |
|---|---|---|---|
| GuanGeKai-v1.5.0 | 11 | OK | 1.5.0 / 1.5.0 |
| GuanGeKai-v1.5.1 | 11 | OK | 1.5.1 / 1.5.1 |
| GuanGeKai-v1.5.2 | 11 | OK | 1.5.2 / 1.5.2 |
| GuanGeKai-v1.6.0 | 11 | OK | 1.6.0 / 1.6.0 |
| GuanGeKai-v1.6.1 | 11 | OK | 1.6.1 / 1.6.1 |
| GuanGeKai-v1.6.2 | 11 | OK | 1.6.2 / 1.6.2 |
| GuanGeKai-v1.6.3 | 11 | OK | 1.6.3 / 1.6.3 |
| GuanGeKai-v1.6.4 | 11 | OK | 1.6.4 / **1.6.3（同 v1.6.3 哈希）** |
| GuanGeKai-v1.6.5 | 11 | OK | 1.6.5 / 1.6.5 |
| GuanGeKai-v1.7.0 | 11 | OK | 1.7.0 / 1.7.0 |
| GuanGeKai-v1.7.1 | 11 | OK | 1.7.1 / 1.7.1 |
| GuanGeKai-v1.7.2 | 11 | OK | 1.7.2 / 1.7.2 |
| GuanGeKai-B-v1.1.0 | 11 | OK | 1.1.0 / 1.1.0 |
| GuanGeKai-B-v1.2.0 | 11 | OK | 1.2.0 / 1.2.0 |
| GuanGeKai-B-v1.2.1 | 11 | OK | 1.2.1 / 1.2.1 |
| GuanGeKai-B-v1.2.2 | 11 | OK | 1.2.2 / 1.2.2 |
| GuanGeKai-B-v1.2.4 | 11 | OK | 1.2.4 / 1.2.4 |
| GuanGeKai-C-v1.0.0 | 11 | OK | 1.0.0 / 1.0.0 |
| GuanGeKai-C-v1.1.0 | 11 | OK | 1.1.0 / 1.1.0 |
| GuanGeKai-C-v1.2.0 | 11 | OK | 1.2.0 / 1.2.0 |
| GuanGeKai-C-v1.2.1 | 11 | OK | 1.2.1 / **1.2.0（同 v1.2.0 哈希）** |
| GuanGeKai-C-v1.3.0 | 11 | OK | 1.3.0 / 1.3.0 |

### A.6 字体元数据实测（六款）

- UPM 1000；hhea ascent 880 / descent −120 / lineGap 0；OS/2 typo 880/−120、win 880/120；fsType 0（可嵌入）；
- cmap：A/B/C Regular 各 21,034 = 20,992 basic + 42 punct；三款 Real 各 1,675/4,073/5,257，全部 basic，无 punct；
- glyph 数 = cmap + 1（`.notdef`），无不可达 glyph、无重复 glyph 名；
- name ID0：A/B/C 均 `…Ming manuscript…`；ID3/ID5 版本串 = 1.7.2 / 1.2.4 / 1.3.0；ID13 = OFL 短声明；ID14 = openfontlicense.org；
- `OFL.txt` 三包同哈希 `51aae3b7…`，其中第 8 行 `woodblock print`（P1-1）。

---

## 附录 B：复现本报告的命令（全部只读或写 `/tmp`）

```bash
cd /Users/wainshine/newAI/guangeti
# 1) 校验和与账本交叉核对
shasum -a 256 build/*.ttf release*/*.ttf *.zip
for d in release release-b release-c; do ( cd $d && shasum -a 256 -c SHA256SUMS ); done
python3 - <<'PY'   # 文档 64-hex ↔ 实测制品（含 zip 内字体）比对脚本，见 §1 P1-4
PY
# 2) 83 闸（不写仓库）：/tmp/audit83 放 build/release/release-b/work/work-b/scripts 的 symlink + 独立 work-c
#    然后 python3 /tmp/audit83/scripts/83_verify_ab_c.py
# 3) 孔洞三口径
python3 scripts/71_holes.py --font build/GuanGeKai-Regular.ttf --n 300 --json /tmp/h3.json
python3 scripts/71_holes.py --font build/GuanGeKai-Regular.ttf --n 200 --json /tmp/h2.json
python3 scripts/71_holes.py --font build/GuanGeKai-Regular.ttf --n 0   --json /tmp/h0.json
# 4) provenance 逐字重算（real ← work/chosen.jsonl，gen/gen80/base ← work/generated.jsonl）
python3 - <<'PY'
import json
MAP={'gen':'gan_ep90','gen80':'gan_ep80','base':'ribbon_fb'}
chosen={json.loads(l)['label'] for l in open('work/chosen.jsonl')}
exp={c:'real' for c in chosen}
for l in open('work/generated.jsonl'):
    r=json.loads(l); exp[r['char']]=MAP[r['src']]
import sys; sys.path.insert(0,'scripts'); import punct_set
for cp in punct_set.CHARS: exp.setdefault(chr(cp),'punct')
prov=json.load(open('release/provenance.json'))
print('mismatches', sum(1 for k in set(prov)|set(exp) if prov.get(k)!=exp.get(k)))
PY
# 5) zip 复现实验（写 /tmp）
( cd release && zip -q -r /tmp/z_dir.zip . ); shasum -a 256 /tmp/z_dir.zip GuanGeKai-v1.7.2.zip
# 6) 13_extend_punct 字节复现
python3 scripts/13_extend_punct.py --line A --out /tmp/a_ext1.ttf
python3 scripts/13_extend_punct.py --line A --out /tmp/a_ext2.ttf
shasum -a 256 /tmp/a_ext1.ttf /tmp/a_ext2.ttf build/GuanGeKai-Regular.ttf
# 7) 13_qa B/C 的两种跑法（P2-6）
python3 scripts/13_qa.py --font build/GuanGeKai-B-Regular.ttf --real build/GuanGeKai-B-Real.ttf --outdir /tmp/qa/b13
python3 scripts/13_qa.py --font build/GuanGeKai-B-Regular.ttf --outdir /tmp/qa/b13d
```
