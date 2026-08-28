# moomoo Smart Money Concepts v3.2：标签与中文手册版

> **历史版本说明：** 本文记录 v3.2。当前正式代码为 v4.1；绘图预算、性能架构和默认标签间距以 [`../releases/V4_1_CN.md`](../releases/V4_1_CN.md) 为准。

本包在 v3.1 源码对齐版基础上，集中处理三个使用体验问题：

1. BOS、CHoCH、EQH/EQL、Strong/Weak 标签与结构线或 K 线重叠；
2. Order Block 没有文字标识；
3. FVG 没有文字标识；
4. 缺少一份完整、独立于代码的中文 SMC 使用说明。

## 文件

- `SMC_STR.py`：Internal/Swing Structure、BOS、CHoCH、HH/HL/LH/LL、EQH/EQL、Strong/Weak、趋势染色。
- `SMC_OB.py`：Internal/Swing Order Blocks、ATR/Cumulative Range 过滤、High/Low 或 Close mitigation、OB 标签。
- `SMC_IMB.py`：当前图表周期 FVG、Auto Threshold、Premium/Equilibrium/Discount、FVG 标签。
- `Smart_Money_Concepts_实战手册_CN.pdf`：适合直接阅读、打印。
- `Smart_Money_Concepts_实战手册_CN.docx`：可编辑版本。
- `Smart_Money_Concepts_实战手册_CN.md`：纯文本 Markdown 版本。
- `assets/`：手册中的原创示意图。

## 1. SMC_STR 标签间距

新增四个参数，单位都是 ATR(200) 的倍数：

- `Internal Label Gap ATR`，默认 `0.30`
- `Swing Label Gap ATR`，默认 `0.40`
- `EQ Label Gap ATR`，默认 `0.30`
- `StrongWeak Gap ATR`，默认 `0.35`

Bullish BOS/CHoCH 与 EQH 标签放在线上方；Bearish BOS/CHoCH 与 EQL 标签放在线下方。HH/LH 放在 K 线上方，LL/HL 放在 K 线下方。

若某个标的或周期仍显得拥挤，建议逐步提高对应参数，例如：

```text
Internal Label Gap ATR = 0.45
Swing Label Gap ATR    = 0.55
EQ Label Gap ATR       = 0.45
```

间距只改变文字位置，不改变结构线价位、事件日期或 BOS/CHoCH 判定。

## 2. SMC_OB 标签

新增：

- `Show OB Labels`，默认开启
- `OB Label Count 0-5`，默认 `5`
- `OB Label Size 1-3`，默认 `1`

标签文字：

- `iOB`：Internal Order Block
- `sOB`：Swing Order Block

文字颜色表示方向：蓝/青色为 Bullish，红色为 Bearish。Bullish 标签置于区块下方，Bearish 标签置于区块上方。

### 为什么最多只给 5 个 Internal + 5 个 Swing 标签

moomoo 每个自定义指标最多允许 50 个静态 plot 调用。`SMC_OB` 已使用：

- 20 个 Internal OB 填充通道
- 20 个 Swing OB 填充通道
- 5 个 Internal OB 标签通道
- 5 个 Swing OB 标签通道

总计 `50/50`。区块本身仍可显示 1–20 个，但带文字标签的最近区块每个 family 最多 5 个。

## 3. SMC_IMB FVG 标签

新增：

- `Show FVG Labels`，默认开启
- `FVG Label Count 0-20`，默认 `20`
- `FVG Label Size 1-3`，默认 `1`

每个当前仍 active 的 FVG 会在区块中部显示 `FVG`；绿色文字表示 Bullish FVG，红色文字表示 Bearish FVG。

为在 50 个 plot 限制下同时保留最多 20 个 FVG 和 20 个标签，v3.2 将 Pine 中上下两个同色 box 合并为一个完整半透明填充通道。价格上下边界、形成条件与失效条件不变；视觉结果等价，但内部图元结构不再是 Pine 的两个 box。

## 4. 推荐测试顺序

1. 只替换 `SMC_STR.py`，在 QCOM、TTWO 日线确认：
   - BOS/CHoCH/EQH/EQL 标签不再压线；
   - 结构 segment 的起点和终点不变；
   - 调高 Gap ATR 后仅文字移动。
2. 替换 `SMC_OB.py`：
   - 确认右侧当前 active OB 出现 `iOB`/`sOB`；
   - 确认文字颜色和区块方向一致；
   - 确认被 mitigation 的 OB 仍会删除。
3. 替换 `SMC_IMB.py`：
   - 打开 `Fair Value Gaps`；
   - 确认 FVG 区块中部显示 `FVG`；
   - 打开 Premium/Discount Zones，检查三个价值区域。

真实 moomoo 客户端仍是最终编译与渲染标准。若出现错误，请先提供第一条完整错误、行号与对应模块。

## 5. 绘图预算与静态检查

```text
SMC_STR   28 / 50
SMC_OB    50 / 50
SMC_IMB   46 / 50
```

三个文件均已通过：

- Python 语法编译；
- plot 全局作用域检查；
- plot 名称不超过 25 字符；
- `plot_stickline` 真实 9 参数签名检查；
- 已知不兼容全局函数检查。

## 6. 重要解释

SMC 指标不是交易所订单流、机构账户或银行持仓的直接探测器。它根据公开 OHLC 价格序列，把结构突破、流动性聚集、快速失衡和回撤区域组织成一套可重复观察的语言。详细解释、使用流程、失效标准和风险管理见随包手册。
