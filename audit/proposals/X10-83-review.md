# X10：`83_verify_ab_c.py` 改造 — 共享 owner review 单

- **授权**：所有者 2026-11-14 选「A」：主会话直接改共享脚本，**A 做共享 owner review**；
  C 跑一次回归；B 不跑。patch 见 `audit/proposals/X10-83.patch`（202 行）。
- **改动文件**：`scripts/83_verify_ab_c.py` + 文档引用（`AGENTS.md`、`README-C.md`、`docs/{DATA-C,PLAN-C,CONVENTIONS}.md`、本检查单）。
  **未改** `release-c/README.md`（包内快照，改动会使 `SHA256SUMS` 失配）。

## 改了什么

1. **真正的 `--help` + argparse**：原来任何参数（含 `--help`）都会执行并写盘；现在 `--help` 只打印。
2. **默认只读**：默认不写 `work-c/`；新增
   `--write`（C 线落盘基线）、`--out-dir DIR`（写到别处，如 `/tmp`）、`--baseline PATH`（只读比对）、
   `--no-write`（显式只读，与 `--write` 互斥）。
3. **`ZIPS` 改为读 `data/release-{a,b,c}.json`**：
   - A：`artifacts.zip` / `artifacts.zip_sha256`；
   - B：`zip_sha256`，文件名按 `GuanGeKai-B-v{version}.zip` 推导（`release-b.json` 无 `zip` 字段）；
   - C：顶层 `zip` / `zip_sha256`。
   重打包后更新 release json 即可，不再手改脚本；缺字段时打印 WARN 而不是静默。
4. **写盘移到所有检查之后**：修复 audit findings `line-c.md` P1-8——
   原脚本先写 `info["ok"]` 再做 C 字集检查，字集失败时 `verify_ab.json` 仍写 `ok:true`；
   现在 `verify_ab.json` 与退出码一致。
5. 文档字符串纠正（A/B 版本、B chosen 4,073）。

## 主会话自测（2026-11-14 12:03 CST，HEAD f2fc6ed + 工作区改动）

| 测试 | 结果 |
|---|---|
| `--help` | 打印 usage，不执行、不写盘 |
| 默认运行 | `A/B INTACT`；A/B/C 三个 zip OK；三行 `21034 = 20,992 + 42`；`work-c/ab_baseline.json`、`verify_ab.json` mtime 保持 11:28:53 |
| `--out-dir /tmp/83test` | exit 0；`/tmp/83test/verify_ab.json` `ok=true`、`issues=[]`；`work-c/` 未动 |
| `--write --no-write` | argparse 报互斥错误 |
| `--write` | 未在仓库内跑（按规则由 C 跑，避免写 C 工作区） |

## A review 检查点

- [ ] 默认只读、`--write`/`--out-dir` 才写，符合 X10 要求；
- [ ] `ZIPS` 从 release json 读取的三线字段映射正确（A 嵌套 / B 推导 / C 顶层）；
- [ ] 写盘已移到字集检查之后（P1-8 修复）；
- [ ] 没有改变 A/B 字体、zip、baseline 的语义；
- [ ] 文档引用（C 线命令加 `--write`）没有误伤包内快照。

## C 回归（A review / 提交后由 C 执行）

```bash
python3 scripts/83_verify_ab_c.py --write
# 期望：RESULT: A/B INTACT；三行 OK ...21034；WROTE work-c/verify_ab.json + ab_baseline.json
python3 scripts/97_check_terms.py
# 期望：TERMS OK
```

B 不需要跑；A/B 若需复核可跑默认（只读）。
