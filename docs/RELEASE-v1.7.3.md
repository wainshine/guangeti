# GuanGe Kai v1.7.3（构建说明）

> 状态：**构建版，尚未打包**。`release/` 仍是 v1.7.2。
> 三线版本：A **v1.7.3** / B **v1.2.5** / C **v1.4.0**（候选）。

## 本版变化

- 617 个“只出现一次”的字复核：586 ok / 28 wrong / 3 reject_quality；
- 586 个 `real_single` 纳入真迹：Real 1,675 → **2,261**；
- Regular 相对 v1.7.2：**586 changed / 0 added / 0 removed**；
- 586 个变化中，内容闸有 40 个 damaged；这是 GAN 字形替换为真实字形的预期变化，
  但**不能写成 `46` PASS**，需 allowlist 或逐条解释。

## 制品

```
build/GuanGeKai-Regular.ttf  89120d52…  21,034  Version 1.7.3
build/GuanGeKai-Real.ttf     59b1154d…   2,261  Version 1.7.3
```

## 质量口径

```
Regular 合成 = 18,731（GAN 17,932 + ribbon 799）
Real          = 2,261
```

v1.7.2 的 `release/`、`GuanGeKai-v1.7.2.zip` 未变；v1.7.3 尚未打包。
