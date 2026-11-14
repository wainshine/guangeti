# 三线任务板 v1.10（主会话维护，2026-11-14 12:25；全部闭环）

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
| A2a | 31 重建 MANIFEST + `m2wt*` 入册 + `m2wt_ep090` SHA 写 release-a + DATA §6.5.1 | 磁盘 24 / MANIFEST 24 / ckpt SHA 一致 / `kind=release`；声明文件已入库 `data/release_ckpts_a.json`，31 支持 `--release-file`，DATA §6.5.1 已登记（P3 已修复） | 完成 |
| A2b | 可选：31 加只读 `--check` | 共享脚本变更协议；未做 | 待办（可选） |
| X10-follow | P3（A 建议，非阻断）：`--write` + 自定义 `--out-dir` 时 baseline 默认仍读 `work-c/ab_baseline.json`；跨目录写盘需同时传 `--baseline`（或未来让 `--write` 自动读 `out_dir/ab_baseline.json`） | 以后有需要再改，不阻塞 | 待办（P3） |
| A3 | floor 5.16 产物 + 文档口径 | `scripts/43_chamfer_floor.py` + `work/chamfer_floor.json`（floor 5.42，CI 5.28–5.60；clean617 GAN 6.13）；AGENTS/README/PROJECT_STATE/EXPERIMENTS/ERRATA E9 已改 | 完成 |
| A4 | golden repro 钉路径 + 文档 + **A 自跑金样** | 完成：`work/logs/golden_repro_a_2026-11-14.log`（07 retrace→`bf278ab1`、11→13 extend→`e6d8a104`、13_qa real-subset OK）；build 10:40–10:41 重建后字节一致 | 完成 |
| A5a | 97 扫描面只加 `docs/index.html` | 97 已加 index.html；index.html 已改「寫本」；97 TERMS OK | 完成 |
| A5b | E8 登记已发布 OFL drift | E8 已提交（`6bbcf3c`）；末句"可选" | 完成 |
| A5b-follow | E8 末句改"重打包则必须修正"（所有者建议） | 已改：ERRATA E8「若因其他原因重新打包，**必须**顺带改为 `Ming manuscript`」 | 完成 |
| A6a | 指标 n 口径收口 | AGENTS C 段 `unseen 0.470`（n=300）；holes n=300 1.9%（4/214）+ n=200 1.4%（2/145，`work/holes_a_n200.json`）；EXPERIMENTS 总表加口径脚注（E32/E36/E39） | 完成 |
| A6b | PROJECT_STATE/README/DATA §4.9/§5 旧口径清理 | 完成：README 拓扑/程序化/C 指针/去色、已知限制 4.1%；PROJECT_STATE 118/139/211；method.md 4.1%/0.539/6.13/5.42；DATA §4.9 ID0 已修复说明；DATA §5 A/B/C 当前校验和 | 完成 |
| A6b-follow | DATA §5 排版回归 | 已修：删残留 3 行旧 B v1.0.1 哈希 + 错位 fence，改为统一「release*/SHA256SUMS + DATA-B/C」说明；97 OK | 完成 |
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
| X1 | 外部冻结台账 v10（`head=06fb50d`，`committed_in=b2346b8`） | `audit/facts/frozen-hashes-2026-11-14T1216.json` | 完成 |
| X2 | 跨线发布检查项清单 | **已定稿（advisory）**：`release-gate-checklist.md` v0 作为默认清单；三线可提异议，不阻塞发布 | 完成 |
| X3/X4/X11 | 快照/共享变更/主会话只读规则 | 已写入 OPERATING v1.2.1 | 完成 |
| X5/X6 | 事实台账 v5 / 报告同步 | 已完成 | 完成 |
| X7 | 追溯登记共享改动 | **已完成**：CHANGELOG 记 97（beaa524/83d01d9）、31（0e22ade/2f523d1）、21_train_gan 与 100_review（83d01d9/ef6e3f8）的影响面与验证；历史改动不回滚 | 完成（主会话） |
| X8 | 快照重建与 `committed_in` 回填 | v9 `committed_in=f2fc6ed`、v10 `committed_in=b2346b8` 均已回填；纯文档/audit 提交不新建快照 | 完成（v10） |
| X9 | 文档数字 vs release-*.json 持久对账闸 | **完成（初版）**：只读检查器 `audit/tools/check_doc_numbers.py`（11 份当前文档/2094 行）；直改 README-C「B 真迹 4,078→4,073」，RELEASE-v1.7.2 加口径更正注；复跑 `DOC NUMBERS OK` | 完成 |
| X10 | 83 `--no-write`/`--help` + `ZIPS` 读 release json | **代码完成并提交**（`06fb50d`）：默认只读；`--write` 落盘；真 `--help`；zip 读 `data/release-{a,b,c}.json`；写盘移到字集检查后（P1-8）；patch/review 单在 `audit/proposals/`。主会话自测：默认 `A/B INTACT`、`work-c` 未动；`--out-dir /tmp` 正常。**A review 通过（12:2x）；C 回归通过（12:19:25：`A/B INTACT`、`work-c` baseline 已更新、`97 TERMS OK`）** | 完成 |

## 5. 本批合并交付核验结论

| 线 | 结论 | 说明 |
|---|---|---|
| A | **通过（全闭环）** | A1/A2a/A3/A4/A5a/A5b/A5b-follow/A6a/A6b/A6b-follow/A7 全部完成；A2b 可选未做 |
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
| A6a / C 口径 | AGENTS unseen 0.470；holes n200 1.4% artifact；EXPERIMENTS 口径脚注 |
| release 标记入库 | `data/release_ckpts_a.json` + 31 `--release-file` + DATA §6.5.1；work 清理不再丢 |
| A6b 大部分 | README/PROJECT_STATE/DATA 旧口径已改（余 4 处见 A6b） |
| 快照 v7 | `2f523d1`；v6 `committed_in=2f523d1` 已回填 |
| A6b 四项残余 | README 4.1%、method.md、DATA §4.9 ID0、DATA §5 当前校验和 |
| 快照 v8 | `bcdeb10`；v7 `committed_in=bcdeb10` 已回填；新发现 DATA §5 排版回归（A6b-follow） |
| A6b-follow / A5b-follow | DATA §5 排版修复；E8 末句改「必须」 |
| 快照 v9 | `8b810f3`；v8 `committed_in=8b810f3` 已回填 |
| X10 83 改造 | 默认只读/`--write`/真 `--help`/zip 读 release json；P1-8 修复；patch+review 单入库 |
| X9 初版 / X2 / X7 | 检查器 + 两处文档直改；发布检查单 advisory；共享改动登记 |
| 快照 v10 | `06fb50d`；v9 `committed_in=f2fc6ed` 已回填 |
