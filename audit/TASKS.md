# 三线任务板 v1.4（主会话维护，2026-11-14 10:52 核验 `0e22ade` 收口提交）

> 规则：见 `audit/OPERATING.md` v1.2.1。主会话不代写；三线执行并回报；所有者裁定优先级。
> 本版依据 `beaa524`（三线合并交付，2026-11-14 10:34）的实测核验，逐项更新状态。
> 状态：`待办` / `进行中` / `待复核` / `完成` / `阻塞` / `已关闭` / `部分完成`。

## 0. 所有者决策

| ID | 事项 | 状态 |
|---|---|---|
| O1 | A 两处修复是否提交 | 完成（`27eab26`） |
| O2 | 共享资产归属 | 记录现状：共享 docs/scripts 由 A 维护（缺原文，不阻塞、非排他授权） |
| O3 | 各线自签发布、主会话复核不代签 | **已确认（所有者 2026-11-14）** |
| O4 | zip 是否承诺字节可复现 | 建议不承诺（记录为发布快照） |
| O5 | 三线是否必须同步发版 | 建议不强制 |
| O6 | `release_date` / `artifacts_built_at` 语义 | **已确认（所有者 2026-11-14）**：签核日 / 打包日，ISO 日期字符串，三线同义 |
| O7 | OFL.txt 已发布 drift | 已关闭：不改、不单独 patch；ERRATA E8 登记为已接受 |

## 1. A 线（A 会话）

| ID | 任务 | 验收标准 | 状态 |
|---|---|---|---|
| A1 | DATA.md `--res 512`→256 | 已改 L176（历史 ribbon 注释 L182 保留）；重建链仍含过时 `36_fill_fallback`/`generated_gan`（见 A6b） | 完成 |
| A2a | 31 重建 MANIFEST + `m2wt*` 入册 + `m2wt_ep090` SHA 写 release-a + DATA §6.5.1 | 磁盘 24 / MANIFEST 24 / ckpt SHA 一致 / `m2wt_ep090`+`m2_ep080` 均 `kind=release`（31 已加 `release_ckpts.json` 机制）。**P3**：release 列表在 `work/`（gitignore）、31 的 `CK` 硬编码 A 的 `work/ckpt`、DATA §6.5.1 未登记该文件 | 完成（P3 备注） |
| A2b | 可选：31 加只读 `--check` | 共享脚本变更协议；未做 | 待办（可选） |
| A3 | floor 5.16 产物 + 文档口径 | `scripts/43_chamfer_floor.py` + `work/chamfer_floor.json`（floor 5.42，CI 5.28–5.60；clean617 GAN 6.13）；AGENTS/README/PROJECT_STATE/EXPERIMENTS/ERRATA E9 已改 | 完成 |
| A4 | golden repro 钉路径 + 文档 + **A 自跑金样** | 完成：`work/logs/golden_repro_a_2026-11-14.log`（07 retrace→`bf278ab1`、11→13 extend→`e6d8a104`、13_qa real-subset OK）；build 10:40–10:41 重建后字节一致 | 完成 |
| A5a | 97 扫描面只加 `docs/index.html` | 97 已加 index.html；index.html 已改「寫本」；97 TERMS OK | 完成 |
| A5b | E8 登记已发布 OFL drift | E8 已提交（`6bbcf3c`）；末句"可选" | 完成 |
| A5b-follow | E8 末句改"重打包则必须修正"（所有者建议） | 一句文档；随 A 的下一个非 audit 提交 | 待办（P3） |
| A6a | 指标 n 口径收口 | 部分完成：README 0.549→0.539（n=617）、AGENTS holes 注 n=300 基线 1.9% ✓。**残留**：AGENTS C 段仍写 `unseen 0.4666`（C1 已改 0.470）；AGENTS 称 n=200 0.7% 但 `work/holes_a.json` 只有 n=300（0.7 无 artifact）；EXPERIMENTS E36/E39 历史表仍用 0.549/5.92 未标"口径已更正" | 部分完成 |
| A6b | PROJECT_STATE/README/DATA §4.9/§5 旧口径清理 | 仍在：PROJECT_STATE:118 去色、:139「当前发布版用 E」、:211 90.5%/9.5%；README:15 拓扑 97%/47%、:55 程序化筆墨、:113/:116 C v1.2.0、:162 9.5%、:202 去色；DATA §4.9/§5 旧账；DATA 重建链 36 步 | 待办 |
| A7 | README B/C 单行例外 | 已写入 AGENTS「文档约定」 | 完成 |

## 2. B 线（B 会话）

| ID | 任务 | 验收标准 | 状态 |
|---|---|---|---|
| B1 | E15 中间态哈希说明 | 已随 `5940a6d` 提交（VERSION 1.2.4，62 确定性） | 完成 |
| B2 | `release_date`/`artifacts_built_at` 语义 | `release-b.json` 增加 `artifacts_built_at=2026-11-13` 与 date_semantics；DATA-B 同步 | 完成 |
| B3/B5/B7 | 澄清/历史例外/嵌套单一源 | 已关闭 | 已关闭 |
| B4 | golden repro 两步金样 | `work-b/golden_repro_2026-11-14.log`：Real `7d10e460`、Regular `62→extend→aa19d6d2`，前后制品一致 | 完成（证据在 work-b） |
| B6 | 63/68/97/73 输出 | 同日志：QA OK、ACCEPTANCE OK、TERMS OK、SELF-AUDIT OK；83 未跑（合规） | 完成 |
| B8 | DATA-B 仍写「C v1.2.0」 | 已改 `C v1.3.0`（`0e22ade`） | 完成 |

## 3. C 线（C 会话）

| ID | 任务 | 验收标准 | 状态 |
|---|---|---|---|
| C1 | 0.4666/0.469 对齐 | `work-c/eval_v130_unseen_c2.json`：0.470/6.38/8.3%；`release-c.json` 与 RELEASE-C 已更新 | 完成 |
| C2 | clean 0.471 来源 | 标为 v1.2.1 继承（n=200，`work-c/eval_v121_ep090.json`）；`clean_eval_n/source` 已加 | 完成 |
| C3 | 删/重算 `fallback_share_of_block` | 0.0712 已删；`fallback_share_of_basic=0.0625`、双口径说明 | 完成 |
| C4 | 日期归一 | AGENTS C 行已改「发布日 2026-11-02；共享文档登记日 2026-11-12」（`0e22ade`）；release-c/RELEASE-C 已同口径 | 完成 |
| C5 | 未记录生成运行 | DATA-C 确认 08:38 最终运行（15,715/836 → 15,735/17），并登记以后必须留日志 | 完成 |
| C6 | golden repro 金样 | `work-c/logs-v1.3/golden_c_v13.log`：Real `6caf9d82`、Regular `765d0848`，与制品一致 | 完成（证据在 work-c） |
| C7 | 两套验收标准表 | RELEASE-C 新增表（门 1 85.2%、门 2 5/94、门 3/4 无签字），并注明"发布 QA ≠ 四级门" | 完成 |
| C8 | C-big 体量 | DATA-C 改为 5.5 GB（apparent 5.93） | 完成 |
| C9 | weight_bias | release-c 改 1.009 + source | 完成 |
| C10/C11 | C-big 训练/面板状态 | EXPERIMENTS-C 登记（未重训、MPS 面板作废待 CPU 重生成） | 完成 |
| C12 | README-C 旧值 0.469/0.4666 | 已改 0.470/6.38/8.3%，并保留 v1.2.1 历史行（`0e22ade`） | 完成 |

## 4. 跨线（主会话）

| ID | 任务 | 验收标准 | 状态 |
|---|---|---|---|
| X1 | 外部冻结台账 v6（`head=0e22ade`） | `audit/facts/frozen-hashes-2026-11-14T1050.json` | 完成 |
| X2 | 跨线发布检查项清单 | `audit/facts/release-gate-checklist.md` v0 已写；待三线 review | 待复核 |
| X3/X4/X11 | 快照/共享变更/主会话只读规则 | 已写入 OPERATING v1.2.1 | 完成 |
| X5/X6 | 事实台账 v5 / 报告同步 | 已完成 | 完成 |
| X7 | 追溯登记共享改动 | 97（A5a）、31（A2a release 标记）、早前 21_train_gan/100_review（C）：登记影响面 + 83/97 + A review | 待办 |
| X8 | 快照重建与 `committed_in` 回填 | v5 `committed_in=6858c08` 已回填；v6 已建（`previous_snapshot.committed_in=6858c08`），v6 自身待回填 | 完成（v6） |
| X9 | 文档数字 vs release-*.json 持久对账闸 | 小脚本/检查单（可在 checklist 的 G 节先手查） | 待办 |
| X10 | 83 `--no-write`/`--help` + `ZIPS` 读 release json | 共享脚本变更；未做 | 待办（P1） |

## 5. 本批合并交付核验结论

| 线 | 结论 | 说明 |
|---|---|---|
| A | **基本通过** | A1/A2a/A3/A4/A5a/A5b/A7 完成（A4 金样日志、A2a release 标记已补）；余 A6a 残留、A6b 文档旧口径 |
| B | **通过（无需重发）** | B2/B4/B6 完成、证据齐、制品未变；仅 DATA-B 一句 P3 |
| C | **通过** | C1–C12 完成、金样日志齐；C4 日期与 README-C 已改 |
| 制品 | **无回归** | 六 TTF/三 zip 哈希未变；B/C build 重建后字节一致；A build 未重建 |
| 门禁 | **通过** | 三线 `SHA256SUMS` 自检 OK；A/B/C MANIFEST 24/14/43；97 TERMS OK |

## 6. 已关闭/已裁决（仅列本轮新增）

| 项 | 结论 |
|---|---|
| E9 撤回「5.16/5.92/差 15%」 | 新口径 floor 5.42（n=800）/ clean617 6.13；AGENTS/README/PROJECT_STATE/EXPERIMENTS 已改 |
| A 步骤 1 reuse/retrace | AGENTS 已改为 retrace 并注明 reuse 非发布路径 |
| 97 加 `docs/index.html` | 已加且通过；index.html 已改「寫本」 |
| A MANIFEST 24/24 | 已入册；ckpt SHA 与磁盘一致 |
| B/C golden 金样 | B/C 日志哈希与发布一致 |
| 快照 v5 | `beaa524`；v4 `committed_in=56edd05` 已回填 |
| A4 金样自跑 | `work/logs/golden_repro_a_2026-11-14.log`：`bf278ab1` / `e6d8a104`，13_qa OK |
| A2a release 标记 | 31 加 `release_ckpts.json` 机制；`m2wt_ep090`/`m2_ep080` `kind=release`（P3：文件在 work/） |
| C4 日期归一 | AGENTS C 行「发布日 11-02；共享文档登记日 11-12」 |
| C12 / B8 | README-C 0.470/6.38/8.3%；DATA-B C v1.3.0 |
| 快照 v6 | `0e22ade`；v5 `committed_in=6858c08` 已回填 |
