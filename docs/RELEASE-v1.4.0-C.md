# GuanGe Kai C v1.4.0（候选说明）

> 状态：**候选，尚未打包，C-Q10 Regular 未通过**。
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

与 v1.3.0（unseen 0.470/6.38/8.3%；page 0.443/6.45/14.0%）基本同档，**不是全面质量提升**。

## C-Q10

```
Regular: changed 15,603 / damaged 0 / gate_pass true
Real:    changed 0 / removed 7 / gate_pass true
```

初测 139 个比 v1.3.0 差的字形已全部回退到 v1.3.0；allowlist 未使用。

## 制品

候选字体在：

```
work-c/qa/c14/GuanGeKai-C-Regular-v1.4.ttf  fd046a7e…
work-c/qa/c14/GuanGeKai-C-Real-v1.4.ttf     d534e504…
```

`release-c/` 仍是 v1.3.0；v1.4.0 尚未打包。
