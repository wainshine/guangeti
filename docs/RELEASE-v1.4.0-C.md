# GuanGe Kai C v1.4.0（候选说明）

> 状态：**已打包候选；C-Q10 Regular 通过；完整质量门仍未签**。
> 三线版本：A **v1.7.3** / B **v1.2.5** / C **v1.4.0**。

## 数据

```
cmap       21,034
real       5,250（25.01%）
GAN        13,843
ribbon     1,899（合成字 12.1%）
punct      42
```

相对 v1.3.0：清理 11 个已确认坏字，real 5,257→5,250；用 ep090 重新生成。

## 指标

```
unseen 300: 0.469 / 6.32 / 9.7%
page 800:   0.440 / 6.62 / 13.9%
```

与 v1.3.0（unseen 0.470/6.38/8.3%；page 0.443/6.45/14.0%）相比：
- unseen Dice 0.469（略低）、chamfer 6.32（略好）、崩坏率 9.7%（更差）；
- page800 Dice 0.440（更低）、chamfer 6.62（更差）、崩坏率 13.9%（略好）；
- ribbon 1,899（合成字的 12.1%）高于 v1.3.0 的 1,313（6.25%）。

**结论：v1.4.0 不是质量提升版；只能作为候选/技术预览，不宣称通过技术指标，不作为 v1.3.0 的默认升级。**

## C-Q10

```
Regular: changed 15,603 / damaged 0 / gate_pass true
Real:    changed 0 / removed 7 / gate_pass true
```

初测 139 个比 v1.3.0 差的字形已全部回退到 v1.3.0；allowlist 未使用。

## 制品

```
build/GuanGeKai-C-Regular.ttf  8132f15f…
build/GuanGeKai-C-Real.ttf     d534e504…
GuanGeKai-C-v1.4.0.zip        613e3433…
```

`release-c/` 已更新为 v1.4.0；zip：`GuanGeKai-C-v1.4.0.zip`。
