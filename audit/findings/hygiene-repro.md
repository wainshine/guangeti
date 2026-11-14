# 工程卫生 / 安全 / 环境可复现性审计（hygiene-repro）

> 审计员：hygiene-audit（独立审计；只报问题，不改代码）
> 基线：`HEAD e308ad55a0c10ee754f8047ebb3c098c96bda582`（2026-11-13 11:40:37 +0800）；审计开始前 `git status --porcelain` 为空（工作树干净）
> 审计时点：2026-11-14（Asia/Shanghai）
> 范围：`scripts/` 全部 154 个 `.py`（141 个编号脚本 + 13 个共享库）、`requirements.txt`、`.gitignore`、git 只读检查、B 线发布制品与声明的轻量一致性（`build/GuanGeKai-B-*.ttf`、`release-b/SHA256SUMS`、`data/release-b.json`、`docs/RELEASE-v1.2.4-B.md`）。B 线流水线与 C 线流水线不在本报告深审范围。
> 边界声明：本次只写入本文件；未修改/删除任何项目文件，未执行 git 写、训练、重建、打包、全量管线；所有 Python 运行均带 `PYTHONDONTWRITEBYTECODE=1 python3 -B`；`--help` 抽样、`13_qa.py`、`97_check_terms.py` 运行前后都做了修改标记比对，仓库内 0 文件被改（§4 有证据）。未打印 `.env` 的值，只看了变量名。
> 与 `audit/findings/docs-consistency.md`（docs-audit）重叠的文档类问题只交叉引用、不重复计为发现。

---

## 0. 结论摘要

| 级别 | 数量 | 内容 |
|---|---|---|
| P0 | **0** | 未发现发布制品被污染、密钥入库、凭据泄露、当前制品字节/声明冲突等一类问题 |
| P1 | **4** | P1-1 检查点清单与磁盘失配（含发布主检查点）；P1-2 发布链并发上限未落实且无 `--workers` 上限；P1-3 生成脚本先截断输出再启动 worker（Real.ttf 事故同类）；P1-4 使用系统专有字体渲染审计图（违反 AGENTS 硬约束） |
| P2 | **7**（去重后新增 6） | P2-1 `14_package.py` 导入即写 `release/`（与并行审计 a-pipeline P2-4 重复，已标注）；P2-2 打包目录无清理、依赖人工 `rm -rf`；P2-3 14 个可运行脚本无 `__main__` 保护（import/`--help` 即写盘或重活）；P2-4 C 线网络脚本 TLS 全局关闭 + 日志打印 key 前缀 + `.env` 缺失即崩；P2-5 硬编码 `/Users/...`；P2-6 `requirements` 注释漂移、传递依赖未锁；P2-7 文档/制品漂移补充（B 段旧哈希、代码围栏错位、3 处失效脚本引用、重建步骤不完整） |

**B 线轻量核对结果：全部通过**（见 §3）：SHA-256、大小、`cmap`/计数、`name` 表版本、`release-b` 自校验、zip 内容均与 `data/release-b.json`、`release-b/SHA256SUMS`、`docs/RELEASE-v1.2.4-B.md`、`docs/DATA-B.md §6` 一致。

**当前无 P0 的理由**：三线 `release*/SHA256SUMS` 都能自校验通过；A/B/C 字体 `cmap` 口径与文档一致；`.env` 未入库、git 历史无 `.env`、跟踪文件中无密钥模式；`git status` 干净、无被跟踪的生成物/大文件；发布门禁 `13_qa` 与 `97_check_terms` 实跑通过。上述问题都是流程/工具层面的风险，尚未造成当前制品损坏。

---

## 1. P1（4 条）

### P1-1 `work/ckpt/MANIFEST.json` 与磁盘失配：4 个检查点未登记，其中 `m2wt_ep090.pt` 是 v1.7.2 发布主检查点

**证据**

`work/ckpt/MANIFEST.json` 的文件 mtime 为 2026-10-26 13:03；磁盘上有 4 个晚于该时间写入的 `.pt` 不在清单内。复核脚本（只读，重算 sha256 未写盘）：

```
$ python3 -B - <<'EOF'   # 摘要：见下
manifest generated (file mtime): 2026-10-26 13:03
manifest entries: 20 | disk .pt files: 24
[entries in MANIFEST but missing on disk] none
[files on disk but NOT in MANIFEST] ['m2wt.pt', 'm2wt_best.pt', 'm2wt_ep090.pt', 'm2wt_ep100.pt']
[per-entry size/mtime/sha check]
  all recorded entries match size+mtime
[hash new files not in manifest]
  m2wt.pt         400.0 MB  sha256_16=cf391fad948efe0f  mtime=2026-10-26 23:12
  m2wt_best.pt    400.1 MB  sha256_16=f281f6f87e652445  mtime=2026-10-26 23:12
  m2wt_ep090.pt   400.1 MB  sha256_16=5f5ac04e084e130a  mtime=2026-10-26 22:46
  m2wt_ep100.pt   400.1 MB  sha256_16=be60b323d2d02510  mtime=2026-10-26 23:12
```

发布口径直接依赖其中一项：

- `data/release-a.json:6`：`"primary_ckpt": "work/ckpt/m2wt_ep090.pt"`
- `scripts/10_generate.py:82`：`GAN_CKPT` 默认即 `work/ckpt/m2wt_ep090.pt`
- `docs/RELEASE-v1.7.2.md:12`：v1.7.2「工作点固化」即主 `m2wt_ep090.pt` + 补位 `m2_ep080.pt`

而检查点规则明确要求 MANIFEST 是删除的唯一依据：`AGENTS.md:35-36`「任何删除先看 `work/ckpt/MANIFEST.json`…**删完必须立刻重跑 `scripts/31_ckpt_manifest.py`**——这一步单独做已经漏过三次」；`docs/DATA.md:204`、`:210-211` 同。`31_ckpt_manifest.py` 自身也注明「每次训练或覆盖检查点后必须重跑本脚本」（`scripts/31_ckpt_manifest.py:1-5,55`），本次是**训练后未重跑**（不是删除后），属同一失配问题的第 4 次记录。

同时 `docs/DATA.md §6.5.1`「当前检查点分布（2026-10-25 19:30 核对）」表（`:214-221`）也没有 `m2wt` 行，文档与磁盘、MANIFEST 三者不同步。

**影响**
- MANIFEST 是所有者定的清理规则唯一索引；漏登记 4 个约 **1.6 GB** 检查点（含发布主模型与 `best`/`final`），后续按清单清理时可能把发布来源当中间轮次删掉。删后要恢复只能重训（M2 系列约 6.5 小时，见 `docs/DATA.md:219`），且会破坏 v1.7.2 的可复现性。
- 与新检查点的实际状态相反，MANIFEST 现在给人「磁盘只有 20 个 `.pt`」的错误印象。

**复现**

```bash
cd /Users/wainshine/newAI/guangeti
ls -l work/ckpt/MANIFEST.json          # mtime 2026-10-26 13:03
ls work/ckpt/*.pt | wc -l              # 24
python3 -c "import json;d=json.load(open('work/ckpt/MANIFEST.json'));print(len(d['items']))"  # 20
ls -l work/ckpt/m2wt*.pt               # 4 个文件，mtime 2026-10-26 22:46–23:12
```

**改进建议**
1. 由所有者/Lead 执行一次 `python3 scripts/31_ckpt_manifest.py`（本审计不代做，避免写 `work/`）。
2. 在流程上把「训练结束 / 删除检查点后跑 31」写进训练脚本收尾：`21_train_gan.py` 结束分支调用 `31_ckpt_manifest.main()`（或在 `latest` 收尾处提示并阻塞退出），从机制上消除第 5 次。
3. 给 `31_ckpt_manifest.py` 增加 `--check` 只读模式：集合或 sha 不一致时 `exit 1`；可作为发布前门禁的一步。
4. 同步更新 `docs/DATA.md §6.5.1` 的检查点分布表，加入 `m2wt` 行（best / ep090 / ep100 / final）。

---

### P1-2 发布链的并发上限未在脚本内落实，且 `--workers` 无上限校验（01_segment / 02_ocr 默认即可能超预算）

**证据**

硬约束原文：`AGENTS.md:24-28` 要求跑任何多进程脚本前 `torch.set_num_threads(1)`、`cv2.setNumThreads(1)`、`OMP_NUM_THREADS=MKL_NUM_THREADS=OPENBLAS_NUM_THREADS=1`，`--workers ≤ 8`，启动后 `ps` 核对总 CPU ≤ 2000%；并记录了 2026-10-25 的 16 worker 事故。

发布流程第 1、2 步（`AGENTS.md:149-150`、`docs/DATA.md:169-170`）对应的两个脚本：

| 脚本 | 默认 workers | 进程池 | 线程限制 |
|---|---|---|---|
| `scripts/01_segment.py` | **8**（`:84`） | `ctx.Pool(args.workers)`（`:108-111`），worker 内 `cv2.cvtColor`（`:31`） | **无**：全文 `cv2.setNumThreads` 0 处；无 OMP/MKL/OPENBLAS 设置 |
| `scripts/02_ocr.py` | **6**（`:46`） | `ctx.Pool(args.workers)`（`:62-63`） | **无**：`get_engine()` 用裸 `RapidOCR()`（`:15-24`），无 onnxruntime 线程参数 |

```
$ grep -c 'setNumThreads' scripts/01_segment.py scripts/02_ocr.py
scripts/01_segment.py:0
scripts/02_ocr.py:0
$ grep -rn 'OMP_NUM_THREADS\|MKL_NUM_THREADS\|OPENBLAS_NUM_THREADS' scripts/
（无输出：没有任何脚本设置这三个环境变量）
```

`02_ocr.py:23` 的 `RapidOCR()` 走 rapidocr 默认配置；本机安装的 rapidocr 3.10.0 默认 `intra_op_num_threads: -1`，而 onnxruntime 引擎只在 `!= -1` 时才覆盖：

```
$ grep -n 'intra_op_num_threads' <site-packages>/rapidocr/config.yaml
26:        intra_op_num_threads: -1
$ grep -n 'intra_op_num_threads' <site-packages>/rapidocr/inference_engine/onnxruntime/main.py
85:        intra_op_num_threads = cfg.get("intra_op_num_threads", -1)
86:        if intra_op_num_threads != -1 and 1 <= intra_op_num_threads <= cpu_nums:
87:            sess_opt.intra_op_num_threads = intra_op_num_threads
```

即每个 worker 的 onnxruntime 会话默认按物理核数开线程；本机 32 核，6 worker 的最坏线程数可达 6×32。

**没有任何脚本校验 `--workers` 上限**（唯一含 `args.workers >` 的判断是 `scripts/05_select.py:108`，只是「是否启用多进程」；`grep -rn 'args.workers >|workers > 8|choices=.*workers' scripts/` 无上限校验）。文档的复现命令（`docs/DATA.md:168-186`）也没有前置 env。

**已披露未修复**：`docs/AUDIT-2026-10-26.md:100`（P2-3）与 `docs/AUDIT-2026-10-26-rev2.md:94`（2-3）都列过同一问题，rev2 的建议「所有 mp 脚本入口设环境变量 + worker 限线程；`--workers` 加 ≤8 校验」至今未实施。本次从「仍有复发风险」角度升级为 P1。

**影响**
- 按文档默认命令跑发布流程第 1、2 步，就存在超出所有者 CPU 预算（10 线程 / 20 核、总 ≤2000%）的风险；与 2026-10-25 被叫停的 16-worker 事故同类。多进程脚本里 `01/02` 是仅有的两个既默认 >1 worker、又完全没有线程限制的发布链脚本。

**复现**（只读）

```bash
cd /Users/wainshine/newAI/guangeti
sed -n '24,28p' AGENTS.md
sed -n '84p;108,111p' scripts/01_segment.py
sed -n '46p;15,24p;62,63p' scripts/02_ocr.py
grep -c 'setNumThreads' scripts/01_segment.py scripts/02_ocr.py   # 0 / 0
grep -rn 'OMP_NUM_THREADS' scripts/ | head                       # 无
```

**改进建议**
1. 在 `01_segment.py` / `02_ocr.py` 的**入口、import numpy/cv2 之前** `os.environ.setdefault(...)` 设置 `OMP/MKL/OPENBLAS/VECLIB/NUMEXPR=1`，worker 首行 `cv2.setNumThreads(1)`；`02` 的 `RapidOCR(params={...intra=1, inter=1})`（B/C 线的 `52_ocr_b.py:35-40`、`92_ocr_c.py:45-50` 已有正确写法，可直接抄）。
2. 所有多进程脚本 `--workers` 改 `choices=range(1, 9)` 或显式 `if not 1 <= args.workers <= 8: ap.error(...)`。
3. 把 env 前缀写进 `AGENTS.md` 发布命令块与 `docs/DATA.md §6` 的复现命令，避免依赖操作者记忆。

---

### P1-3 生成脚本先以 `"w"` 打开输出、再启动进程池：worker 失败即截断既有产物（Real.ttf 事故同类）

**证据**

四个发布/生成路径都在进入 `with` 时先截断输出文件，之后才启动进程池、加载检查点：

```
$ grep -n 'ctx.Pool(args.workers) as pool, open(args.out, "w")' scripts/10_generate.py scripts/60_generate_b.py scripts/77_generate_c.py
scripts/10_generate.py:481:        with ctx.Pool(args.workers) as pool, open(args.out, "w") as fh:
scripts/10_generate.py:513:        with ctx.Pool(args.workers) as pool, open(args.out, "w") as fh:
scripts/60_generate_b.py:260:    with ctx.Pool(args.workers) as pool, open(args.out, "w") as fh:
scripts/77_generate_c.py:318:    with ctx.Pool(args.workers) as pool, open(args.out, "w") as fh:
```

`with` 的多上下文按从左到右进入：Pool 创建后立刻执行 `open(..., "w")` 截断，随后 `imap_unordered` 才真正调用 worker。`10_generate.py` 的 GAN 路径在 worker 里 `torch.load(ck)`（`:82-91`）；若检查点被清掉（见 P1-1 的清理规则）、路径写错、内存不足或任一 worker 抛异常，异常在迭代结果时冒泡，此时输出文件已经被清空/只剩部分行。

**对照**：AGENTS 记录的三步闸门确实已修好——`07_build_real.py:119-123`（`glyphs < 1000` 拒写）、`11_build_full.py:45-48`（`real<1000` 或 `missing>0` 拒写）、`13_qa.py:73-80`（real 子集/覆盖率/空字形闸）都存在；但同一失败类在 `10/60/77` 没有防护。

**影响**
- 与所有者记录在案的事故同类：`AGENTS.md` 踩坑 #2「删掉 `work/masks` 后重跑 07 产出 0 字形仍写出文件，并把 `work/real_contours.jsonl` 截断为 0 字节…最终打出只有 1 个字形的 `GuanGeKai-Real.ttf`」。
- 现在的受损对象更大：`work/generated.jsonl` 是 19,317 个合成字（A 线发布主体），一旦被截断，重建需要先有 `m2wt_ep090.pt`（400 MB，未入库）；若该检查点恰好被清，就必须先重训约 6.5 小时。B/C 线同理（`work-b`/`work-c` 的 generated.jsonl）。

**复现**（只读静态证据已足够；若真要复现，务必用 `/tmp` 作 `--out`）

```bash
grep -n 'ctx.Pool(args.workers) as pool, open(args.out' scripts/10_generate.py scripts/60_generate_b.py scripts/77_generate_c.py
grep -n 'torch.load' scripts/10_generate.py | head
# 安全复现思路（不要对仓库输出跑）：--out /tmp/x.jsonl + 不存在的 --ckpt → 观察进程退出前 /tmp/x.jsonl 已被创建为 0 字节
```

**改进建议**
1. 统一改为「写临时文件再原子替换」：`tmp = args.out + ".tmp"` → 全部成功后再 `os.replace(tmp, args.out)`；失败时旧文件原样保留。
2. 在**打开输出前**完成所有资源加载与输入校验（ckpt 存在、可读、轮廓数量预期），把「坏输入」挡在截断之前。
3. 可选：成功收尾时打印 `lines == expected` 并把该断言写入脚本（当前 `10_generate.py:490` 只打印计数、不比较）。

---

### P1-4 使用 macOS 系统专有字体渲染审计图，违反 AGENTS 明文硬约束

**证据**

`AGENTS.md:21-22`：「**禁止使用任何专有/商业字体**（含操作系统自带的中文字体）——即使只做测量或对照」。

但 C 线两个人工审计图脚本直接加载系统字体：

```
$ sed -n '25,33p' scripts/99zs_stamp_sheets_c.py
font_lab = ImageFont.truetype('/System/Library/Fonts/Songti.ttc', 30, index=1)   # :27
font_sid = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 20)          # :32
$ sed -n '170,176p' scripts/99zo_572_route_c.py
font_lab = ImageFont.truetype('/System/Library/Fonts/Songti.ttc', 30, index=1)   # :173
font_sid = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 20)          # :174
```

`99zs` 的 docstring 甚至把「Songti.ttc index=1」写成了固定选择（`:5`）。两脚本输出到 `work-c/preview/…` 的人工标注图，不进入发布字体；未发现专有字体进入 `build/` 或 `release*/` 的证据。

**影响**
- 明文硬约束被违反（「即使只做测量或对照」句已覆盖此类用法）；若这些审阅图被当作风格参照、或公开进文档，会把专有字体渲染结果带入审计链。
- `/System/Library/...` 是 macOS 专属路径，换机/容器/其他线会话直接崩溃，属可移植性缺陷。

**复现**

```bash
grep -rn --include='*.py' -E '/System/Library/Fonts|Songti|Helvetica|PingFang|SimSun' scripts/
# 命中 99zs_stamp_sheets_c.py:27,32 与 99zo_572_route_c.py:173,174
```

**改进建议**
- 标注/图签类渲染统一用项目内 OFL 字体 `data/base/LXGWWenKai-Regular.ttf`（已在库、已入库许可审查）或 Source Han/Noto（OFL）；只给拉丁图签可用 `data/base/SourceHanSansCN-Regular.otf`。
- 在 `97_check_terms.py` 或一个轻量 grep 门禁里加「`/System/Library/Fonts` 零命中」检查，防止再次引入。

---

## 2. P2（7 条）

### P2-1 `14_package.py` 导入即写 `release/`，且 `--out` 语义被绕过

**证据**

```
$ grep -n '^_fix_charset_records' scripts/14_package.py
141:_fix_charset_records(ROOT / "release")
$ sed -n '24,29p;104,106p' scripts/14_package.py
24:def main():
...
26:    ap.add_argument("--out", default=str(ROOT / "release"))
...
104:if __name__ == "__main__":
105:    main()
106:
```

`_fix_charset_records()` 定义在 `if __name__ == "__main__"` 之后（`:106`），却在模块层被**无条件调用**（`:141`），内部写 `provenance.json`、`stats.json`、`SHA256SUMS`（`:116-138`）。后果：
1. 任何 `import 14_package`（审计脚本、测试、`runpy`）都会改写 `release/`；
2. 传 `--out /tmp/x` 时 `main()` 写临时目录，但 `:141` 仍然重写默认 `release/`——`--out` 语义错误；
3. `:126-127` 硬编码 A 线口径（`st["codepoints"]=20992`、`EXPECTED_CMAP`），函数名却是通用的，复制到 B/C 会写错数字。
4. 顺序脆弱：`main()` 在 `:105` 执行完才轮到 `:141`；若 main 提前 `SystemExit`（所有 `ABORT` 分支），helper 不会执行——恰好使「打包失败」路径不修记录。

**影响**：审计/测试用「import 一下」就会污染发布目录并重算自校验文件；与「发布目录只由打包脚本在明确命令下写入」的预期不符。

**复现**（静态；不要实际 import，会写 `release/`）

```bash
sed -n '104,141p' scripts/14_package.py
```

**改进建议**：把 helper 改成 `def _fix_charset_records(out_dir)`，在 `main()` 末尾用 `Path(args.out)` 调用；口径从 `scripts/punct_set.py` 读取；删除模块层调用。

---

### P2-2 打包目录不做清理，`SHA256SUMS` 会收录目录内全部旧文件；清理完全依赖人工 `rm -rf`

**证据**

三个打包脚本都对输出目录做 `glob("*")` 全量哈希，且都不删除旧文件：

```
$ grep -n "sorted(out.glob(\"*\"))" scripts/14_package.py scripts/64_package_b.py scripts/81_package_c.py
scripts/14_package.py:98
scripts/64_package_b.py:139
scripts/81_package_c.py:162
```

文档把清理交给人工：`AGENTS.md:154`「`rm -rf release && python3 scripts/14_package.py`」、`docs/RELEASE-v1.2.4-B.md:66`、`docs/DATA-B.md:274`。AGENTS 的踩坑 #1 已经证明「先打包后改 README」会造成包内说明落后；同理，**忘记 `rm -rf` 时旧文件会被原样打进 zip，并被新 `SHA256SUMS` 合法化**。

当前实测无污染：`release/`、`release-b/`、`release-c/` 各 11 个文件，`shasum -a 256 -c SHA256SUMS` 三个目录全部 OK；`release-b` 的 11 个文件与 zip 内 11 个文件一一对应。

**影响**：流程性风险（发布包混合上一版残留文件、zip 内容与预期集合不符），且是人工步骤，违反「发布流程顺序固定、勿跳步」的意图。

**复现**

```bash
cd /Users/wainshine/newAI/guangeti
for d in release release-b release-c; do (cd $d && shasum -a 256 -c SHA256SUMS >/dev/null && echo "$d OK"); done
ls release release-b release-c | wc -l   # 每个目录 11 个文件（含 SHA256SUMS）
sed -n '96,100p' scripts/14_package.py
```

**改进建议**：脚本内先写 `out.tmp/` 目录，成功后替换；或在写入前断言「输出目录集合 ⊆ 期望集合」并把白名单外文件移到 `_stale/`；至少加 `--clean` 开关并在文档命令中默认使用，避免依赖 `rm -rf`。

---

### P2-3 14 个可运行脚本（外加 2 个「库」）没有 `__main__` 保护：import / 误用 `--help` 即写盘或做重活

**证据**

AST 扫描 154 个文件：127 个有 `if __name__ == "__main__"`，27 个没有；其中 13 个是共享库，其余 **14 个是可运行脚本**：

```
scripts/15_verify_labels.py, 16_check_real.py, 19_cap_geom.py, 41_regen_fallback.py,
42_hidpi_probe.py, 99v_compare_checkpoints_c.py, 99w_compare_all_c.py,
99x_compare_ab_gan_c.py, 99y_synthetic_compare_c.py, 99z_build_ocr_bench_c.py,
99zm_v13_compare_c.py, 99zs_stamp_sheets_c.py, 99zt_no_real_compare_c.py,
99zu_visual_ep20_30_80_85_90_c.py
```

其中带写盘/重活的模块级语句（import 即执行）：

| 文件 | 行 | 行为 |
|---|---|---|
| `scripts/15_verify_labels.py` | `:46` | 写 `work/label_check.json` |
| `scripts/16_check_real.py` | `:11`、`:64` | import 时加载 LXGW 字体；写 `work/real_check.json` |
| `scripts/41_regen_fallback.py` | `:13-14`、`:35` | 加载字体+npz；**覆写 `work/generated.jsonl`** |
| `scripts/42_hidpi_probe.py` | `:31`、`:50` | import 时打开 PDF；写 `work/hidpi_probe.json` |
| `scripts/99v_compare_checkpoints_c.py` | `:45` | 写 `work-c/preview/compare_*.png` |
| `scripts/99w_compare_all_c.py` | `:59` | 写 `work-c/preview/all_compare_*.png` |
| `scripts/99x_compare_ab_gan_c.py` | `:43` | 写 `work-c/preview/abgan_compare_*.png` |
| `scripts/99y_synthetic_compare_c.py` | `:14`、`:49` | 读 `chosen.jsonl`；写 `work-c/preview/synth_compare_*.png` |
| `scripts/99z_build_ocr_bench_c.py` | `:54` | 写 `work-c/ocr_bench.json` |
| `scripts/99zm_v13_compare_c.py` | `:57-58` | 写 PNG + `v13_ep_metrics.json` |
| `scripts/99zs_stamp_sheets_c.py` | `:74-76` | 写 meta/csv |
| `scripts/99zt_no_real_compare_c.py` | `:51-52` | 写 PNG + json |

此外 `eval_model.py`、`zi2zi_make_npz.py` 虽被列为「共享库」，实际是 `argparse` CLI 且无 guard（import 即跑）。另有 3 个**有** guard 的脚本在模块层做重活：`99za_cellbox_probe_c.py:19`（import 时读两份大 `cells.jsonl`，`--help` 实测 14.4 s）、`99zn_572_collect_c.py:39`（读 `cells.jsonl`）、`77_generate_c.py:29-30`（import 时初始化 OpenCC）。

**影响**：这些脚本只能「直接运行」，不能 import/测试/被别的脚本复用；一旦有人（或未来的批处理）import 它们，就会写盘、甚至覆写 `work/generated.jsonl`（41 行）。当前仓库里的 `SourceFileLoader` 链（`99zh_rescore_c.py:12` → `99zf`、`99za_cellbox_probe_c.py:12`/`99zk_v5_boxes_c.py:8` → `92_ocr_c`）加载的脚本都有 guard，未触发；但模式很脆弱。

**复现**

```bash
cd /Users/wainshine/newAI/guangeti
python3 -B -c "import ast,pathlib; print([p.name for p in pathlib.Path('scripts').glob('*.py') if '__main__' not in ast.dump(ast.parse(p.read_text()))])"
grep -n 'json.dump\|write_text\|im.save' scripts/15_verify_labels.py scripts/16_check_real.py scripts/41_regen_fallback.py
```

**改进建议**：统一 `if __name__ == "__main__": main()`；对 `eval_model.py`/`zi2zi_make_npz.py` 明确定位为 CLI；重活移到函数内，模块层只留常量与 def。

---

### P2-4 C 线网络脚本的安全卫生：进程级关闭 TLS 校验、错误日志打印 key 前缀、`.env` 缺失即崩

**证据**（均为 C 线人工/审计脚本，不在发布链上）

```
$ sed -n '20,32p' scripts/99zf_dp_align_gate_c.py
# local MITM proxy serves a self-signed chain; API transport only, measurement unaffected
ssl._create_default_https_context = ssl._create_unverified_context      # :26
...
$ sed -n '65,80p' scripts/99zf_dp_align_gate_c.py
for l in open(ROOT / '.env'):                                          # :73（无 try/except）
    k, _, v = l.strip().partition('=')
...
$ sed -n '112,122p' scripts/99zf_dp_align_gate_c.py
print(f'  HTTP {e.code} {sid}: {body_txt} | key={key[:8]} proxyny=...')  # :118
```

`.env` 本身状态良好：`-rw-------`（600）、未入库、git 历史无记录（`git log --all -- .env` 空）；仓库内只有 `99zf` 引用 `.env`。但：
1. `ssl._create_default_https_context` 是**进程级全局**关闭证书校验（注释说明是本地 MITM 代理需要），一旦 `VISION_BASE_URL` 指向真实 API，Bearer key 可被中间人截获；
2. 错误分支把 `key[:8]` 与内部代理地址打进 stdout/日志；
3. `:73` 直接 `open(.env)`：新环境缺文件时抛 `FileNotFoundError`，而 `:77-79` 本来有「无凭据则跳过 stage2」的降级分支，会永远走不到。

**影响**：密钥前缀与内网代理信息入日志；TLS 保护在进程内失效；可复现性上，C 线审计脚本隐式依赖本机 `.env`。

**复现**

```bash
grep -rn --include='*.py' -E 'ssl\.|key\[|\.env' scripts/ | head
sed -n '24,28p;70,80p;114,120p' scripts/99zf_dp_align_gate_c.py
ls -l .env && git log --all --oneline -- .env   # 600；历史为空
```

**改进建议**：仅在本地代理主机的请求上使用独立 `ssl.create_default_context(cafile=...)`/显式放行，不改全局默认；日志脱敏为 `key[:2] + '***'` 或不打印；`.env` 读取包 try/except 并复用 skip 分支；把所需 3 个变量名（不含值）写入 C 线文档。

---

### P2-5 硬编码本机绝对路径

**证据**

```
$ grep -rn --include='*.py' -E "Path\('/Users/" scripts/
scripts/99zm_v13_compare_c.py:4:ROOT=Path('/Users/wainshine/newAI/guangeti'); W=ROOT/'work-c'
scripts/99zs_stamp_sheets_c.py:15:W = Path('/Users/wainshine/newAI/guangeti/work-c')
```

其余 152 个脚本都用 `Path(__file__).resolve().parents[1]` 推导 ROOT。

**影响**：换用户名/换机器/CI 即 `FileNotFoundError`；两个脚本都在 C 线辅助脚本里，但属可复现性缺陷。

**复现**

```bash
grep -rn --include='*.py' -E "Path\('/Users/|/Users/wainshine" scripts/
```

**改进建议**：改为 `ROOT = Path(__file__).resolve().parents[1]`。

---

### P2-6 `requirements.txt` 注释漂移、传递依赖未锁

**证据**

```
$ sed -n '17p' requirements.txt
torch==2.12.1        # only for the experimental scripts/09_train*.py
$ python3 -B -c "扫描 AST 后统计 import torch 的脚本数" 
33 个（含发布链 scripts/10_generate.py 的 --method gan、以及 22/23/25/26/29/32/34/… 评估脚本）
```

- 按注释「只在 09_train* 用」裁剪依赖，会导致发布字体无法复现（`10_generate.py` 的 gan 路径 `import torch` 在 `gan_chunk` 内，`:66`）。
- requirements 只钉 14 个直接依赖；rapidocr 3.10.0 拉入的 `onnxruntime==1.26.0` 等传递依赖未锁定，也没有 venv/lock 文件。

**正面实测**：当前环境与 requirements **完全一致**、可 import（见 §4）。所以问题是「重建环境的可复现性与注释正确性」，不是当前环境坏了。

**影响**：注释误导依赖裁剪；全新机器 `pip install -r requirements.txt` 的传递依赖版本可能漂移。

**改进建议**：改注释为「发布链 10_generate.py 的 gan 方法需要」；补 `requirements-lock.txt`（`pip freeze` 全量）或写明 venv 创建步骤；在 CI/发布前核对版本。

---

### P2-7 文档/制品漂移补充（与 docs-audit 去重后仍属本范围的 4 处）

> `audit/findings/docs-consistency.md` 已覆盖 DATA.md §4.9 name 表（其 P1-11）、§5 当前版本哈希缺失（P1-12）、检查点/重建矛盾（P1-13）、release date 字段语义（P2-7）等，本报告不重复定性，只补充**对方未覆盖**的 4 点：

**(a) `docs/DATA.md §5` 的 B 段仍挂 v1.0.1 旧哈希，且代码围栏错位**
- `docs/DATA.md:108,117,121,125` 共有 4 个 ``` 围栏，成对解析后 block A 覆盖 109–116、block B 覆盖 122–124；结果是「B 线（史记本，v1.0.1）：」被卷进代码块，而 `b76cfc01…/79aadc23…/f95b5e7f…`（`docs/DATA.md:118-120`）落在代码块外作为普通段落渲染。
- 这 3 个哈希是 **v1.0.1 时代**的值；现行 v1.2.4 制品实测为 `aa19d6d2…/7d10e460…/2537de50…`（见 §3），`docs/DATA-B.md:170-172` 与 `release-b/SHA256SUMS` 均为新值。DATA.md 的「B 线（史记本，v1.0.1）」标题本身也落后 4 个 patch。

**(b) 文档引用不存在的脚本**
```
docs/PLAN-OCR-IMPLEMENT.md:99zh_lineend_repair_c.py     # scripts/ 下无此文件
docs/AUDIT-2026-10-31.md:99z_cellbox_probe_c.py         # 实际是 99za_cellbox_probe_c.py（少一个 a）
docs/EXPERIMENTS.md:generate_font_dataset.py            # 外部脚本，仓库没有
```
其余 311 处 `python3 scripts/…` 文档命令的脚本都存在、flags 全部被对应 `add_argument` 接受（0 处无效 flag；唯一已知例外是上面 3 个脚本引用）。历史审计文档（AUDIT-*）可保留，但 `PLAN-OCR-IMPLEMENT.md` 是规划文档，缺脚本会误导执行。

**(c) `docs/DATA.md §6`「重建步骤」不完整，「约 15 分钟」有前提**
- 列表从 `01_segment` 直接跳到 `10_generate --method gan`（`docs/DATA.md:168-186`），缺 `08_make_pairs`、`21_train_gan`（/09）、`27_fit_width` 等；而 `10_generate.py` 的默认主检查点 `work/ckpt/m2wt_ep090.pt`（`:82`，400 MB）与 `work/stroke_rel_width.npy` 都不入库、也不在步骤里生成。
- 「预期总耗时（M3 Ultra）：约 15 分钟」（`:188`）只在**保留了全部 `work/` 中间产物与检查点**的机器上成立；全新 clone 按文档走到第 10 步会直接失败（P1-3 同一路径）。
- 文档 §6 末的「已知局限」只说了中间产物没有校验和链（`:190-193`），没有说明检查点与训练步骤缺失。

**(d) `docs/DATA-B.md:187` 的跨线版本行过期**：「三条线独立编号：A v1.7.2 / B v1.2.4 / **C v1.2.0**」——C 线当前已是 v1.3.0（`AGENTS.md:60`、`build/GuanGeKai-C-Regular.ttf` nameID5 `Version 1.3.0`）。该行写于 v1.2.4 发布时，属历史快照，但与同仓文档现状不一致。

**建议**：修 DATA.md §5 围栏并改为引用 `DATA-B.md §6`；PLAN 里的脚本名改为 `99za_*` 或注明未实现；§6 补「需保留 work/ 与 ckpt」前置说明或补训练步骤；DATA-B 的跨线版本行加「本文写于 2026-10-30」时间戳。

---

## 3. B 线发布制品轻量一致性核对（全部通过）

核对命令（只读；未改动任何文件）：

<details>

```bash
cd /Users/wainshine/newAI/guangeti
shasum -a 256 build/GuanGeKai-B-Regular.ttf build/GuanGeKai-B-Real.ttf GuanGeKai-B-v1.2.4.zip
(cd release-b && shasum -a 256 -c SHA256SUMS)
python3 -B <<'PY'   # fontTools 读 name/cmap
...
PY
```

</details>

| # | 核对项 | 期望（来源） | 实测 | 结论 |
|---|---|---|---|---|
| 1 | Regular SHA-256 | `aa19d6d2…`（DATA-B §6:170、release-b.json:19、RELEASE-B:52） | `aa19d6d2000d504af7123741fe9273bee157fee1f2915c570a9d05d27bab8f9d` | 通过 |
| 2 | Real SHA-256 | `7d10e460…`（DATA-B:171、release-b.json:20、RELEASE-B:53） | `7d10e4602313f3ca440953ed20f75e3a96f1428d96c8c4c75e17e23857f1498a` | 通过 |
| 3 | zip SHA-256 | `2537de50…`（DATA-B:172、release-b.json:21、RELEASE-B:54） | `2537de50f67517696fea70102c97ecb4da0f8bd29d3746baebad629ee4e83c46` | 通过 |
| 4 | `release-b/SHA256SUMS` 自校验 | 逐文件 OK | 10/10 OK（LICENSE/OFL/README/两张图/coverage/provenance/stats/两个 ttf） | 通过 |
| 5 | zip 内容 | 包内文件 = release-b 集合 | zip 内 11 文件，与 `release-b/` 11 文件一一对应；包内 `SHA256SUMS` 与 `release-b/SHA256SUMS` 同哈希 `f4ceed88…` | 通过 |
| 6 | `stats.json` 计数 | `codepoints 20992 / codepoints_total 21034 / real 4073 / gan 15784 / gan_ht 544 / ribbon_fallback 591 / punct 42 / glyphs 21035` | 逐项相同（`release-b/stats.json`） | 通过 |
| 7 | `provenance.json` | 21,034 条，五类来源 | 21,034 条 = real 4073 / gan 15784 / gan_ht 544 / ribbon_fb 591 / punct 42 | 通过 |
| 8 | Regular `cmap` | 20,992 + 42 = 21,034（GLOSSARY 口径） | `cmap 21034`、basic-CJK 20992、非基本区 42；无 U+201C/U+201D；无扩展 A 码位 | 通过 |
| 9 | Real 子集 | 仅 4,073 真迹、无标点 | `cmap 4073`、glyphs 4074（含 .notdef）、无基本区外码位 | 通过 |
| 10 | name 表 | `Version 1.2.4`、家族 `GuanGe Kai B`、manuscript 描述、OFL 1.1 | nameID5 `Version 1.2.4`；nameID1 `GuanGe Kai B`；nameID4 `GuanGe Kai B Regular`；nameID13 OFL 1.1；nameID0「traced from the Ming manuscript 史記」 | 通过 |
| 11 | 文档大小 | RELEASE-B §2：Regular 15.43 MB / Real 3.82 MB / zip 14.3 MB（十进制） | 15,432,348 B = 15.43 MB；3,818,680 B = 3.82 MB；14,334,271 B = 14.33 MB | 通过 |
| 12 | 包内 README | 只有 `docs/images/` 前缀差异（`64_package_b.py:56-66` 打包规则） | `diff README-B.md release-b/README.md` 仅 2 处前缀差异（8 行 diff） | 通过 |
| 13 | 口径来源 | `data/release-b.json` 是 B 线单一口径源（DATA-B §6:190-196） | 逐字段（real/gan/gan_ht/ribbon/punct/codepoints_total/clean 629/dice 0.525/chamfer 5.6/broken 0.029）与 DATA-B 文本一致 | 通过 |
| 14 | 声明的时间戳固定 | RELEASE-B:69-71「fontbuild 与 13_extend_punct 已固定时间戳」 | `fontbuild.py:195` `SOURCE_DATE_EPOCH`；`13_extend_punct.py:113` `base.recalcTimestamp = False` | 静态通过（字节级见 §5 未覆盖） |

**不重复项（已由 docs-audit 披露）**：包内 README 相对链接断链（其 P2-11）；`release-b/README.md` 快照性质（ERRATA E3）。本次未核对 B 线训练/评估指标与 `work-b/` 内容（B 线另立会话）。

---

## 4. 已核查不成立 / 已披露（避免重复怀疑）

**发布的数字与门禁当前成立**
- `python3 -B scripts/13_qa.py --font build/GuanGeKai-Regular.ttf --outdir /tmp/qa13`（输出路径在 `/tmp`，仓库 0 写入）：
  ```
  coverage 20992/20992 = 100.0000%
  empty 0 tiny 0 huge 0
  real-subset glyphs 1675 cmap 1675 -> OK
  ```
  即 AGENTS「发布前必须核对」的三项数字当前都成立。
- `python3 -B scripts/97_check_terms.py` → `TERMS OK （除白名单与已知遗留外一致；白名单 23 个文件未扫；15 行显式豁免）`。
- `wc -l work/chosen.jsonl` = 1675；`release/provenance.json` 中 `real` 计数 = 1675。
- A/C 字体 `cmap` 与文档一致：A `21034`（basic 20992 + 42）、Real `1675`；C `21034`（basic 20992 + 42）、Real `5257`；nameID5 分别为 `Version 1.7.2` / `Version 1.3.0`。A `nameID0` 已是 `Ming manuscript`（与 ERRATA E2 一致）。

**失败类闸门（AGENTS 所说的三个）确实存在**
- `scripts/07_build_real.py:119-123`：`glyphs < 1000` → `SystemExit`「refusing to overwrite build/GuanGeKai-Real.ttf and work/real_contours.jsonl」；
- `scripts/11_build_full.py:45-48`：`real < 1000` 或 `missing > 0` → 拒写；
- `scripts/13_qa.py:73,78,80`：real 子集数量不符 / 覆盖率不足 / 空字形 → `SystemExit`。
  → `AGENTS.md:178`「现在 07/11/13 都会在数量异常时中止」成立。

**语法 / 危险模式（全量静态）**
- 154/154 个 `.py` AST 解析 0 syntax error（等价于全量 `py_compile`，但用内存编译，未写 `__pycache__`）。
- 无 `eval()`/`exec()` 内建调用（grep 到的 `.eval()` 全是 `torch.nn.Module.eval()`）；无 `os.system`/`os.popen`/`subprocess(shell=True)`；无 `pickle.load(s)`。
- `subprocess` 仅 5 处（`63_qa_b:159`、`73_selfaudit_b:112,191`、`79_build_full_c:88`、`80_qa_c:138`），**全部 list 参数形式**，无 shell 注入面；其中 `73_selfaudit_b:191` 用硬编码 `"python3"` 而非 `sys.executable`（P2 级小问题，可顺手改）。
- 无硬编码凭据：`grep -E '(api[_-]?key|secret|token|password)\s*=\s*["'\''][^"'\'']{6,}'` 无命中；`.env` 未入库（600 权限），git 全历史 `git log --all -- .env` 为空。

**git / 仓库卫生**
- `git status --porcelain` 审计开始时空（审计后仅多出本报告与 docs-audit 的报告，均 untracked）。
- 跟踪文件 303 个：无 `.pdf`/`.zip`/`.ttf`/`.pt`/`work*`/`build`/`.env`/`.DS_Store`/`__pycache__` 入库；`git ls-files -i -c --exclude-standard` = 0（无「被忽略却仍跟踪」的文件）。
- `.gitignore` 无漏洞迹象：22 个根目录 zip 全部被 `/*.zip` 忽略（逐个数过 22/22）；`/work/`、`/work-*/`、`/build/`、`release*/*.ttf`、`data/vendor/`、`data/models/`、`.env*`、`.DS_Store`、`__pycache__/` 均命中预期。
- 跟踪文件最大 2,161,631 B（`data/ids/ids.txt`），无 >5 MB 生成物入库；`build/`（约 60 MB ttf）与 22 个根 zip 全部本地保留、不入库。

**`--help` 抽样（104/104 通过）**
- 对「有 `__main__` guard + 有 `argparse` + 有 `parse_args`」的 104 个脚本逐一执行 `python3 -B <script> --help`（cwd=/tmp，`PYTHONDONTWRITEBYTECODE=1`，OMP/MKL/OPENBLAS/VECLIB/NUMEXPR=1）：**104/104 exit 0 且输出 `usage:`**。
- 运行前后用 `/tmp` 标记 + `find -newer` 比对 `build/ release/ release-b/ release-c/ docs/ data/ scripts/`、根目录文件、`work*/` 浅层：**0 个文件被修改**（这也是对本审计「不写仓库」约束的自证）。
- 37 个无 `argparse` 的脚本不适用 `--help`；14 个无 guard 的脚本若跑 `--help` 会执行任务，按 P2-3 处理、未运行。

**环境可复现（当前机器）**
- `python3 --version` = 3.14.2；requirements 的 14 个包实测版本**全部与 pin 一致**（pymupdf 2.0 / numpy 2.4.1 / scipy 1.17.0 / opencv-python-headless 5.0.0.93→cv2 5.0.0 / Pillow 12.1.0 / rapidocr 3.10.0 / opencc 0.1.7 / potracer 0.0.4→potrace / fonttools 4.61.1 / scikit-image 0.26.0 / scikit-learn 1.9.0 / shapely 2.1.2 / tqdm 4.67.3 / torch 2.12.1），全部 import 成功。
- `rapidocr` 模型随 pip 包分发（site-packages 内 5 个 `.onnx`），首次使用**无需联网下载**，对复现有利。
- `pip check` 无项目依赖冲突（仅全局无关包 uncompyle6/decompyle3 的 xdis 版本问题）。
- 所有 19 个 `--workers` 默认值都 ≤8（8/6/4/2/1），默认配置不越线；线程限制在 B/C 线推理脚本中已正确实现（`52_ocr_b.py:35-44`、`92_ocr_c.py:45-50,77`、`51_segment_b.py:39`、`60_generate_b.py:58-61`、`77_generate_c.py:66-69`、`93_segment_c.py:164` 等）。

**检查点清单内容本身**
- MANIFEST 已登记的 20 项与磁盘 `size+mtime` 全部一致（sha256_16 仅在 size/mtime 不符时才重算；实测无不符）——问题只是「缺 4 项」，不是「记录值错了」。

**疑似问题经核查不成立**
1. `36_fill_fallback.py:34`、`61_fill_fallback_b.py:42`、`78_fill_fallback_c.py:42` 用 `open(out, "a")` 追加写法看似会重复写——实际前面都用 `have = {…}` 去重（`36:25-28`、`78:35-38`），重跑幂等，**不是缺陷**。
2. `argparse` 默认值里的路径在主机器上全部存在：154 个脚本中带路径型默认值的参数 0 个缺失（静态解析 + `Path.exists()`）；文档 311 处命令 flags 除 §2 P2-7(b) 的 3 个失效脚本引用外**全部有效**。
3. Markdown 相对链接/图片：`AGENTS.md`、`README*.md`、`docs/*.md` 共 0 个断链（脚本外链不查）。
4. `.env` 值未泄露到仓库：未跟踪、无历史、无文档引用值（只有变量名可推测）。
5. 14_package 的 `_fix_charset_records` **不会**破坏当前 `release/`：当前 `release/SHA256SUMS` 自校验仍通过（它写入的口径与 A 线一致）；问题是副作用设计（P2-1）。

**已披露、不重复计为新发现**
- `01_segment`/`02_ocr` 线程问题：`docs/AUDIT-2026-10-26.md:100`（P2-3）、`docs/AUDIT-2026-10-26-rev2.md:94`（2-3 已列）；本报告 P1-2 只更新「仍未修复」。
- 文档类漂移（DATA.md §4.9 name 表、§5 当前版本哈希、检查点/重建矛盾、release date 语义）：`audit/findings/docs-consistency.md` 的 P1-11/12/13、P2-7 已覆盖。
- `ERRATA E6/E7`、A 线红像素等：docs-audit 已核，本报告不重复。

**与并行审计报告的重叠与去重（审计完成后发现同目录报告）**
- `audit/findings/a-pipeline.md` P2-4 与本报告 **P2-1 重复**（同一证据：`14_package.py:141` 模块级调用、`:126-127` 硬编码；建议以 a-pipeline P2-4 为准，其还补充了新鲜度闸门只查 2 个依赖的问题）。本报告保留该条只为自洽，不另计新发现。
- a-pipeline P2-8 提到 `16_check_real.py:11` 模块级加载字体，与本报告 P2-3 的同一例子重叠；P2-3 的新增部分是「14 个无 guard 脚本 + 12 处 import 即写盘」的全量清单。
- a-pipeline §4.2 第 5 条 / `docs-consistency.md` P1-13 已覆盖 DATA.md §6 重建命令与现行口径不符；本报告 P2-7(c) 只补充「缺训练步骤与 checkpoint 依赖」这一可复现性视角。
- **未被并行报告覆盖、本报告独有**：P1-1（MANIFEST 与磁盘失配）、P1-2（并发线程约束与 `--workers` 上限）、P1-3（`open("w")` 先截断后开池，10/60/77 三脚本）、P1-4（系统专有字体）、P2-2（打包目录无清理）、P2-3 的清单主体、P2-4（TLS/key 日志）、P2-5（硬编码 `/Users`）、P2-6（requirements 注释/传递依赖）、P2-7(a)(b)(d)。

---

## 5. 未覆盖 / 无法验证（明确边界）

1. **字节级可复现声明未验证**：`docs/RELEASE-v1.2.4-B.md:69-71`「上面的命令连跑两次产出完全相同的字节」、`data/release-a.json` 的 reproduce、`AGENTS.md` 第 5–6 步的 sha 同步——按硬约束未执行构建/打包，无法实测。静态佐证只有 `fontbuild.py:195`（SOURCE_DATE_EPOCH）与 `13_extend_punct.py:113`（`recalcTimestamp=False`），不足以证明字节一致（还依赖输入字体、排序、glyph order 等）。
2. **实际 CPU 占用未实测**：未运行 01/02 全量管线（禁止重建），P1-2 的线程数上限是「默认参数 + 代码 + 既往审计」推断，未用 `ps` 复核 2000%。
3. **B 线深审不在本报告**：B 线训练/评估指标（dice 0.525、chamfer 5.6、回退率）、`work-b/` 内容一致性、B 线 zip 的可复现性未核；B 线发布制品只做了 §3 的轻量一致性。
4. **C 线流水线**：`work-c/`、网络 VLM 结果的正确性、`99zf` 的 API 行为未验证（不调用外网）；C 线发布制品只顺带核了 `release-c/SHA256SUMS` 自校验。
5. **未运行的写型脚本**：`83_verify_ab_c.py`（会写 `work/verify_ab.json` 与 baseline）、`31_ckpt_manifest.py`（写 MANIFEST）、`63_qa_b.py`/`80_qa_c.py`/`71_holes.py`/`95_compare_lines.py`/`98_style_sheet.py`/`12_specimen.py`/`14_package.py`/`64_package_b.py`/`81_package_c.py` 等（写制品或 work*），均未执行；因此「发布流程可整链跑通」只按静态证据判断。
6. **git 历史深审**：只查了 `.env` 是否入库与跟踪文件中的密钥模式；未做全历史 secret 扫描、未查历史大文件。
7. **干净环境安装**：未在全新 venv 里按 requirements 重装（避免网络/环境副作用）；当前机器实测一致不等于新装可复现（见 P2-6）。
8. **`.env` 内容、`.zcode/`、PDF/数据文件内容、字体渲染质量**：不在本角色范围，未审。
9. **网络请求的合规性**：9 个 C 线脚本调用 VLM/ollama API（`99s/99zb/99zd/99ze/99zf/99zi/99zn` 等），只审了密钥/TLS 处理，未审数据外发范围与花费。

---

## 附录：本次审计实际使用的只读命令（可复核）

```bash
cd /Users/wainshine/newAI/guangeti
# 1) 检查点清单 vs 磁盘（重算 sha，未写盘）
PYTHONDONTWRITEBYTECODE=1 python3 -B - <<'EOF'  # 见 P1-1 输出
EOF
# 2) 并发
grep -rn --include='*.py' -E 'set_num_threads|setNumThreads|OMP_NUM_THREADS' scripts/
grep -rn --include='*.py' -E 'Pool\(|PoolExecutor\(' scripts/
grep -rn --include='*.py' -E 'args\.workers\s*>' scripts/
# 3) 危险模式
grep -rn --include='*.py' -E 'shell\s*=\s*True|os\.system\(|eval\(|exec\(|pickle\.(load|loads)\(' scripts/
# 4) 仓库卫生
git status --porcelain; git ls-files | wc -l; git ls-files -i -c --exclude-standard
git check-ignore -v .env .DS_Store build/GuanGeKai-Regular.ttf GuanGeKai-B-v1.2.4.zip
ls *.zip | wc -l
# 5) 语法：AST 全量解析（等价 py_compile、不写 __pycache__）
PYTHONDONTWRITEBYTECODE=1 python3 -B - <<'EOF'
import ast, pathlib
bad=[p for p in pathlib.Path('scripts').glob('*.py') if (lambda s: (ast.parse(s), False)[1])(p.read_text())]
EOF
# 6) --help 抽样：104 个有 argparse+guard 的脚本，cwd=/tmp，exit 0 且输出 usage；前后 find -newer 0 修改
# 7) 发布门禁实跑（输出到 /tmp，不写仓库）
python3 -B scripts/13_qa.py --font build/GuanGeKai-Regular.ttf --outdir /tmp/qa13
python3 -B scripts/97_check_terms.py
# 8) B 线轻量核对
shasum -a 256 build/GuanGeKai-B-*.ttf GuanGeKai-B-v1.2.4.zip
(cd release-b && shasum -a 256 -c SHA256SUMS)
unzip -l GuanGeKai-B-v1.2.4.zip
# 9) 环境
python3 --version
python3 -c "import importlib.metadata as m; [print(p, m.version(p)) for p in [...]]"
```

> 本文件是本次审计唯一的项目内写入（`git status` 中体现为 `?? audit/`，与 docs-audit 的报告同目录）。未删除、未覆盖任何既有文件。
