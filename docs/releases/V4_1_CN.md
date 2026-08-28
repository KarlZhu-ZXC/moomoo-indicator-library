# moomoo Indicator Library v4.1

本版本同步自用户已在 moomoo 客户端验证的 v4/v4.1 指标基线。

## 已确认结果

- v4 移除旧版数百层 `ref → compare → iff` 计算图后，快速切换标的的内存峰值约为 2–3GB，并能观察到明确回收；基线不再持续抬升。
- v4.1 在该内存架构上继续修正状态和视觉，没有重新引入 500/501 层扫描循环。

## 指标版本

| 指标 | Plot | 主要更新 |
|---|---:|---|
| `SMC_STR` | 28/50 | 原生滚动 trailing extremes、EQH/EQL 当前 pivot 标签高度、更大标签间距 |
| `SMC_OB` | 46/50 | 32条候选 lane、20状态槽、原生 HHV 区间选 K、同 bar mitigation |
| `SMC_IMB` | 31/50 | 20个 FVG 状态槽、槽内排名、原生 HHV/LLV 价值区域 |
| `OTE_CP` | 45/50 | ChartPrime shift/anchor 状态、SH/SL、浅灰 Fib、浅黄色 OTE、可选历史集 |

## v4.1 保真修复

1. 同一确认 K 线同时满足 HH 与 LL 时，先处理 bullish、再处理 bearish；两个事件输出都保留，最终方向为 bearish。
2. EQH/EQL 标签纵坐标使用当前新确认 pivot，而不是两个 pivot 的平均值。
3. 默认标签间距调整为：

```text
Internal Label Gap ATR = 0.40
Swing Label Gap ATR    = 0.50
EQ Label Gap ATR       = 0.40
StrongWeak Gap ATR     = 0.40
```

4. `OTE_CP` 增加普通 swing 的 `SH`/`SL` 固定文字，与触发方向切换的 `HH ▲` / `LL ▼` 区分。
5. Fibonacci 网格改为更接近 ChartPrime 的浅灰样式；OTE 使用浅黄色半透明区域。

## 平台边界

- moomoo 无 Pine 动态 line/box/label 生命周期，历史对象和未来空白区延伸只能使用有界静态通道等价表达。
- `plot_text()` 不能使用逐 bar 动态字符串，无法直接显示 `0.618 (动态价格)`。
- 任意周期 FVG 缺少已验证的 `request.security()` 等价接口。
- 精确 trailing、OB 和 OTE 搜索范围限定为最近500根 K，避免深计算图回归。

## 建议验收

- QCOM、TTWO 日线检查 BOS/CHoCH 线段和 EQH/EQL 标签高度。
- OTE_CP 与 TradingView 使用相同 `Pivot Length = 10` 比较 SH/SL、HH/LL、anchor 和 OTE 区域。
- 快速切换多个标的后确认内存仍能回收，不出现持续单向增长。
