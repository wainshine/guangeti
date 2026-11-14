# 三线任务板 v2.0（第 5 代审计分诊版，2026-11-14 15:45，HEAD a134850）

> 本版接第 5 代审计（对抗性复核后）。**旧 v1.10 的 A/B/C/X 闭环仅指第 2 代审计范围；第 5 代审计重新打开了若干项，见下。**
> 规则见 `audit/OPERATING.md` v1.2.2。主会话负责协调/复核；A 为共享脚本 owner；B/C 各线脚本/文档自管。
> 不重打包、不改制品。脚本改动：A review + C 回归 + 主会话只读复核；文档文字类：主会话直改（2026-11-14 授权）。

## 0. 第 5 代审计裁决（先读）

1. **P1-1 线程**成立，但描述更正为「每 worker 首个 chunk 峰值」：`gan_chunk` 入口先设 1，`exec_module` 后回到 6；A 的 `10_generate` step=40 字、8 worker（峰值 48），B/C 的 `60/77` step=10 字、6 worker（峰值 36）。仍需修。
2. **P1-2/P1-3 降为 P2**：`docs/RELEASE-v1.7.2.md` **不在 zip 内**（zip 仅 11 文件，无 `docs/`；包内 README 无该句/表），属仓库文档，不是已分发制品；修文档即可，不重打包。
3. **P2-3 的“codepoints 冲突”驳回**：`release/stats.json` 的 `codepoints=20992` 与 `codepoints_total=21034` 语义不同；成立的是 `14_package` 模块级副作用/硬编码。
4. **X9 诊断更正**：`check_doc_numbers.py` 不是“只对哈希”，真实盲区是漏 `docs/DATA.md`、短哈希只查前缀、正则无词边界。
5. **C 的 C-5 驳回**：第 5 代报告没有把 C1/C2/C5/C6 当未修；不重开。
6. **A-漏2 不动作**：包内 README 是发布快照，与根 README 不同属预期。
7. “41 seed 扫描”无落盘产物，只作为未复核线索；0.7% 已被 n=200 的 1.4% 取代。

## 1. A 线（共享脚本 owner + A 线）

| ID | 优先级 | 任务 | 验收 |
|---|---|---|---|
| A-P1 | **P1** | `21_train_gan.py:21` 改惰性（import 不设线程）；`10_generate.py` 在 `exec_module` 后重置 1；`01/02` 补线程限制；`10` 的 `--workers` 上限 ≤8 | import 测试 `1→1`；`ps ≤2000%`；83/97 通过；制品不变 |
| A-P2 | **P1** | `31_ckpt_manifest.py`：`--release-file` 对任意 `--ckpt-dir` 生效、补 `epoch`、读失败告警、原子写 | A 24/24；B/C 用同一脚本重建后 release 项正确 |
| A-P3 | P2 | `83`：C 字体缺失 fail；SHA256SUMS 缺失 NO-BASELINE 置 fail；`--write --out-dir` 时 baseline 语义一致 | 缺文件/缺基线用例有 FAIL；C 跑 `--write` 回归 |
| A-P4 | P2 | `71_holes.py` 输出补 `seed/cmd/args`；重出 A 两个 holes 基线 | json 含字段；数字可复跑 |
| A-P5 | P2 | `43_chamfer_floor.py` 重跑保留人工键；clean617 固化到脚本参数/独立键 | 重跑后 population_note/gan_clean617 不丢 |
| A-P6 | P2 | `14_package.py` 去模块级 `_fix_charset_records` 副作用、尊重 `--out`、从 cmap 算 codepoints | import 不写 release；`--out` 只写目标 |
| A-P7 | P2 | `10_generate.py` fallback 去重；`--ckpt` 在 gan 分支的语义明确（或删/或文档） | 同字只记一次；文档与 CLI 一致 |
| A-P8 | P2 | `97_check_terms.py` docstring/scan_fonts 路径更新 | TERMS OK |
| A-P9 | P3 | `release-a.json` 补 `artifacts_built_at`（O6） | 与 B/C 同义 ISO 日期 |
| A-P10 | 签字 | 主会话 M-P3 改完 A 线文档后，A 确认 A 线口径 | 不重复写，只 review |

## 2. B 线

| ID | 优先级 | 任务 | 验收 |
|---|---|---|---|
| B-P1 | **P1** | 建 `data/release_ckpts_b.json`（`b_ep080.pt`、`b_wt_ep090.pt`）；用 `31 --ckpt-dir work-b/ckpt --release-file ...` 重跑 | `work-b/ckpt/MANIFEST.json` 两条 `kind=release`；不删 ckpt |
| B-P2 | **P1** | `data/release-b.json` 补 `checkpoint_sha256` / `checkpoint_hardtail_sha256`（全量） | 与磁盘一致 |
| B-P3 | P2 | `73_selfaudit_b.py` 严格 fresh：逐条 `sha256_16` 对磁盘 + 发布检查点 `kind=release` | 改一字节能被抓；不改变现有断言 |
| B-P4 | **P1** | `60_generate_b.py` `_load_gan` 后重置 1；`--workers` 上限 | 首 chunk 后 `torch.get_num_threads()==1` |
| B-P5 | P2 | `README-B.md:108` RFN → 霞鹜／霞鶩／落霞孤鹜／落霞孤鶩／LXGW | 与 OFL.txt 一致 |
| B-P6 | P2 | `DATA-B.md:279` zip 名 `v1.1.0` → `v1.2.4` | 链可跑通 |
| B-P7 | 回归 | 31 重建/83 默认只读/97 | 全部 OK；B 不跑 83 --write |

## 3. C 线

| ID | 优先级 | 任务 | 验收 |
|---|---|---|---|
| C-P1 | **P1** | 建 `data/release_ckpts_c.json`（`c_ep090.pt`）；`31 --ckpt-dir work-c/ckpt --release-file ...` 重跑 | `v1.3/c_ep090.pt` `kind=release`；不删 ckpt |
| C-P2 | **P1** | `77_generate_c.py` `_load_gan` 后重置 1；`--workers` 上限 | 首 chunk 后线程=1 |
| C-P3 | P2 | `99zo/99zs` 的 Songti/Helvetica 换仓库自由字体（先核对许可）或移除 | 无 `/System/Library`、无专有字体 |
| C-P4 | P2 | `README-C`/`DATA-C` 重建链 `c_ep030/--epochs 30` → `c_ep090/90`（参数按实际训练命令） | 与 v1.3.0 自述一致 |
| C-P5 | P2 | `README-C:127` RFN 完整列表 | 与 OFL.txt 一致 |
| C-P6 | P2 | `DATA-C:135` v1.2.1 → v1.3.0 | 无时代错乱 |
| C-P7 | 不动作 | C1/C2/C5/C6 旧结论 | 报告未把其当未修；保留 0.470/6.38/8.3%、clean n=200、0.0712 已删 |
| C-P8 | 回归 | A 改完 83/71 后：`83 --write` + `97`；重出 `holes_c` | `A/B INTACT`、TERMS OK、json 含 seed |

## 4. 主会话

| ID | 状态 | 事项 |
|---|---|---|
| M-P1 | 完成（本轮） | 更正第 5 代报告事实错误（zip/线程峰值/codepoints/X9 诊断），见 `docs/AUDIT-2026-11-14.md` §9.19 |
| M-P2 | 完成（本轮） | 重开本任务板；fact/CHANGELOG 记录 |
| M-P3 | 待办（Phase 2） | 共享文档批量直改：RELEASE-v1.7.2、method、README、DATA、PROJECT_STATE、EXPERIMENTS、GLOSSARY/CONVENTIONS、ERRATA、AGENTS 线程预检；A/B/C 线文档不碰 |
| M-P4 | 待办（Phase 2） | X9 检查器升级：纳入 `docs/DATA.md`、数值真对账、词边界、重建链必须含 `13_extend_punct` |
| M-P5 | 待办（Phase 3） | 只读验收（线程/manifest/83/97/X9/制品哈希）；提交后建 v11、回填 v10 |
| M-P6 | 持续 | 不重打包；任何脚本改动若变制品哈希 → 停，交所有者 |

## 5. 依赖与排期

```
Phase 1（P1，先行）:
  A-P1 → A-P2（31）；B-P4 / C-P2 可先本地 reset；B-P1/B-P2、C-P1 依赖 A-P2 的 31 能力
Phase 2（P2）:
  M-P3 + M-P4 与 A-P3..A-P8、B-P3/B-P5/B-P6、C-P3..C-P6 并行
Phase 3（收尾）:
  A-P9、A-P10 签字、B-P7/C-P8 回归、M-P5 v11
```

## 6. 不动作 / 驳回

- 不重打包/不改 zip；P1-2/P1-3 仅仓库文档。
- “P1-2/P1-3 已随 zip 分发”、“codepoints 冲突”、“C1/C2/C5/C6 未修”均不成立。
- C-5、A-漏2 不动作；41-seed 无产物不作证据。
- `release*/README.md` 包内快照不改（会破坏 SHA256SUMS）。

## 7. Phase 1 验收（2026-11-14 15:55，HEAD a134850 + 工作区）

**通过**
- A-P2（31 核心）：`epoch` 字段、`--release-file` 显式告警、原子写（`.tmp` + replace）落地；`31 --help` 无副作用。
- B-P1/B-P2：`data/release_ckpts_b.json`；`work-b/ckpt/MANIFEST.json` 的 `b_ep080`/`b_wt_ep090` 均 `kind=release, epoch`；
  `release-b.json` 两个全量 SHA 与磁盘一致。
- B-P3：`73` 已逐条 `sha256_16` 对比磁盘 + 发布检查点 kind 检查。
- B-P4：`_load_gan` 后重置 1；`--workers` 1..8；C-P2 同。
- B-P6、C-P3、C-P5、C-P6：DATA-B zip 名、99 脚本去系统字体（改用仓库 Noto）、README-C RFN、DATA-C:135 已改。
- **运行时证据**：`exec_module(21_train_gan)` 后 `torch.get_num_threads()==1`（改前为 6）。
- **制品/门禁**：六 TTF/三 zip 未变；`release*/SHA256SUMS` OK；`97 TERMS OK`；`83` 默认只读 `A/B INTACT`；`work-c` mtime 未变。

**部分完成 / 需补**
- **A-P1-follow**：`01/02` 只加了 OMP/MKL/OPENBLAS env，**没有 `cv2.setNumThreads(1)`、也没有 `--workers` 上限校验**；补后再验。
- **A-P2-follow**：①显式 `--release-file` 不存在时，当前代码会回退到默认 `CK/release_ckpts.json`（A 的 work/ckpt），应只告警并置空；②C 的 release 文件用 basename，导致 `v1.2.1/c_ep090.pt` 与 `v1.3/c_ep090.pt` 同时被标 release；需支持相对路径条目（C 用 `v1.3/c_ep090.pt`）。
- **B-P5**：根 `README-B.md:108` 仍是「霞鶩／霞鶩／…」；B 只在 DATA-B 记了包内缺陷，**根文档未改**。
- **C-P1**：受上面 basename 问题，`v1.2.1/c_ep090.pt` 被误标 release；A-P2 支持路径后 C 重跑修正。
- **C-P4**：README-C 已改 90 轮/两阶段；`DATA-C:175-176` 训练命令仍写 `--epochs 80`，只加了注释；需补续训命令或改 90。
- **B-P7 / C-P8**：回归仍待（B 不跑 `--write`；C 在 A-P3/P4 后跑 `83 --write` + `97` + `holes_c`）。

**未开始（Phase 2）**：A-P3…A-P8、B-P5 的根文档、M-P3 共享文档、M-P4 X9 升级、A-P9/A-P10。

### Phase 1 复验（2026-11-14 16:05，全部补齐）

- **A**：`01/02` 已补 `cv2.setNumThreads(1)` + `--workers choices(1..8)`；31 已修「显式 release-file 缺失不回退默认」并支持相对路径；A/B/C MANIFEST 均正确（A 2 release、B 2、C 仅 `v1.3/c_ep090.pt`）。运行时 `exec_module(21)` 后线程=1。
- **B**：根 `README-B.md:108` 已改为完整 RFN；B-P2 ckpt SHA、B-P3 73、B-P4 60 均通过。
- **C**：`data/release_ckpts_c.json` 用 `v1.3/c_ep090.pt`，C MANIFEST 不再误标 v1.2.1；DATA-C 训练命令已补 80→90 两阶段。
- **门禁**：六 TTF/三 zip 未变；`release*/SHA256SUMS` OK；`97 TERMS OK`；`83` 默认只读 `A/B INTACT`；`work-c` mtime 未变。
- **结论**：A-P1/A-P2、B-P1–B-P6、C-P1–C-P6 **完成**。B-P7/C-P8 在 A-P3/P4 后再跑；A-P3…A-P8、A-P9/A-P10、M-P3/M-P4 进入 Phase 2。Phase 1 改动仍待所有者提交；提交后建 v11。

### Phase 2 线侧复验（2026-11-14 16:10，全部通过）

- **A-P3–A-P8 完成**：83 的 C 字体缺失 fail / NO-BASELINE fail / `--out-dir` baseline 独立；71 输出含 `font_sha256/n/seed/cmd/args`；43 重跑保留 `population_note/ratio_caveat/gan_clean617/gan_in_sample`（并新增 `preserved_keys`）；14 的 `_fix_charset_records` 已并入 `main`、尊重 `--out`、codepoints 从 cmap 计算（import 测试 release 文件 mtime 未变）；10 fallback 去重 + `--ckpt` 语义；97 docstring 更新。
- **B-P5/B-P6/B-P7 完成**：根 README-B RFN 已修；DATA-B zip 名 v1.2.4；73 已改并在 16:03 产出 `work-b/verify_a_snapshot.json`。
- **C-P8 完成**：16:07:11 `83 --write` 更新 `work-c/ab_baseline.json` + `verify_ab.json`；16:07:12 `holes_c` 已含 seed/cmd；83 复跑 `A/B INTACT`；97 OK。
- **门禁**：六 TTF/三 zip 未变；`release*/SHA256SUMS` OK；`97 TERMS OK`；`DOC NUMBERS OK`；`diff --check`/py_compile 通过；work-c 基线未再被写（默认只读）。
- **剩余**：M-P3 共享文档、M-P4 X9 升级、A-P9（P3，release-a artifacts_built_at）、A-P10（A 线文档签字）。线侧 Phase 2 已全部完成，待所有者提交；提交后建 v11。
