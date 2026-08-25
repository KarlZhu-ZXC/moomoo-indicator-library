# moomoo Smart Money Suite

<p align="center">
  <strong>面向 moomoo Python 自定义指标的 Smart Money Concepts 三模块套件</strong><br>
  Structure · Order Blocks · Fair Value Gaps · Premium / Discount
</p>

<p align="center">
  <img alt="Version 3.2" src="https://img.shields.io/badge/version-3.2-089981?style=for-the-badge">
  <img alt="moomoo" src="https://img.shields.io/badge/platform-moomoo-00C805?style=for-the-badge">
  <img alt="Python" src="https://img.shields.io/badge/language-Python-3178C6?style=for-the-badge">
  <img alt="CC BY-NC-SA 4.0" src="https://img.shields.io/badge/license-CC_BY--NC--SA_4.0-F23645?style=for-the-badge">
</p>

<p align="center">
  <img src="docs/assets/fig1_structure.png" alt="Market structure, BOS and CHoCH diagram" width="900">
</p>

> [!IMPORTANT]
> 本项目是非官方、非商业的跨平台适配。算法参考 LuxAlgo 的开源 Pine Script，并针对 moomoo 的序列 API 和每指标 50 个 plot 调用上限进行了重构。它不是 LuxAlgo 官方产品，也不承诺与 TradingView 像素级一致。

## 为什么拆成三个指标

moomoo 自定义指标目前对单个脚本设置了静态绘图调用上限。将完整 SMC 拆为三个可叠加模块，既保留主要功能，也让每个模块的职责、参数和绘图预算清晰可控。

| 指标 | 功能 | 静态绘图预算 |
|---|---|---:|
| `SMC_STR` | Internal/Swing Structure、BOS、CHoCH、HH/HL/LH/LL、EQH/EQL、Strong/Weak、趋势染色 | 28 / 50 |
| `SMC_OB` | Internal/Swing Order Blocks、波动过滤、mitigation、`iOB`/`sOB` 标签 | 50 / 50 |
| `SMC_IMB` | 当前图表周期 FVG、Auto Threshold、Premium/Equilibrium/Discount、FVG 标签 | 46 / 50 |

## 快速安装

1. 打开 moomoo 桌面端的自定义指标管理器。
2. 新建 **Python 主图指标**，分别复制以下文件的完整内容：
   - [`indicators/SMC_STR.py`](indicators/SMC_STR.py)
   - [`indicators/SMC_OB.py`](indicators/SMC_OB.py)
   - [`indicators/SMC_IMB.py`](indicators/SMC_IMB.py)
3. 指标名称分别使用 `SMC_STR`、`SMC_OB`、`SMC_IMB`。
4. 将三者叠加到同一张 K 线主图；建议先逐个加载和验证，再组合使用。

> [!TIP]
> 首次测试可用 QCOM 或 TTWO 日线。先验证 Structure 的线段起止位置，再加载 OB，最后打开 FVG 与 Premium/Discount Zones。

## v3.2 亮点

- BOS、CHoCH、EQH/EQL、Strong/Weak 标签使用 ATR(200) 自适应间距，减少压线。
- Order Block 增加 `iOB` / `sOB` 标签，并保留 active block 与 mitigation 语义。
- FVG 增加方向着色标签；在 50 plot 限制内支持最多 20 个区域与 20 个标签。
- Structure 线段使用独立 stickline 图元，避免不同事件被 `plot()` 自动连接成斜线。
- 附带完整中文 SMC 手册、可编辑 Word 版、PDF 版与原创示意图。

## 视觉导览

| Liquidity · EQH/EQL | Order Blocks · FVG |
|---|---|
| ![Liquidity](docs/assets/fig2_liquidity.png) | ![Order Blocks and FVG](docs/assets/fig3_ob_fvg.png) |

| Premium · Equilibrium · Discount |
|---|
| ![Premium, equilibrium and discount zones](docs/assets/fig4_zones.png) |

## 推荐参数与排查

Structure 标签仍拥挤时，可逐步提高以下 ATR 倍数；这些设置只移动文字，不改变事件或价位：

```text
Internal Label Gap ATR = 0.45
Swing Label Gap ATR    = 0.55
EQ Label Gap ATR       = 0.45
```

完整参数说明、术语解释、交易工作流与风险管理见：

- [Smart Money Concepts 中文实战手册（Markdown）](docs/Smart_Money_Concepts_实战手册_CN.md)
- [PDF 版](docs/Smart_Money_Concepts_实战手册_CN.pdf)
- [Word 可编辑版](docs/Smart_Money_Concepts_实战手册_CN.docx)
- [v3.2 详细变更说明](docs/README_V3_2_CN.md)

## 与 TradingView 原版的边界

本项目尽量对齐结构状态、pivot、BOS/CHoCH、OB、FVG、EQH/EQL 与价值区域的核心算法，但以下差异来自平台能力：

- moomoo 使用静态序列绘图，无法等价复现 Pine 的动态 `line`、`label`、`box` 对象管理。
- FVG 仅支持当前图表周期；客户端已验证的 Python runtime 不提供任意 `request.security()` 周期。
- Previous Day/Week/Month High-Low 未纳入当前三模块。
- 历史扫描显式限制为 500 bars，以匹配可用运行时与绘图预算。
- 真实 moomoo 客户端仍是最终编译和渲染标准。

详见 [兼容性说明](docs/COMPATIBILITY.md)。

## LuxAlgo 参考与署名

本项目是对以下开源作品的适配与修改：

- 原作品：**Smart Money Concepts (SMC) [LuxAlgo]**，© LuxAlgo
- 官方页面：[TradingView 开源脚本](https://www.tradingview.com/script/CnB3fSph-Smart-Money-Concepts-SMC-LuxAlgo/)
- 固定参考源码：[Pine v5 mirror @ `31756c8615aff4cefe9cf97350e78bd427f663cd`](https://github.com/deepentropy/lightweight-charts-indicators/blob/31756c8615aff4cefe9cf97350e78bd427f663cd/docs/official/indicators_community/Smart%20Money%20Concepts%20%28SMC%29%20%5BLuxAlgo%5D.pine)
- 原作品及本适配采用：[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/)

主要修改包括：Pine v5 到 moomoo Python/`ftool` 的语言迁移、按平台绘图上限拆分模块、静态序列状态重建、线段绘制替代、标签间距与 OB/FVG 标签增强。完整说明见 [NOTICE.md](NOTICE.md)。

LuxAlgo、TradingView、moomoo 与 Futu 相关名称和商标归各自权利人所有。本仓库与这些主体均无附属、认可或合作关系。

## 风险提示

SMC 指标不能直接识别银行、基金或机构账户的真实订单。它只是使用公开 OHLC 数据组织市场结构、流动性与价格失衡的观察框架。所有内容仅供学习、研究与技术验证，不构成投资建议；历史表现不代表未来结果。

## License

在原作品许可证要求下，本项目以 **Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International** 发布。你必须保留署名、仅作非商业使用，并以相同许可证分享改编版本。参见 [LICENSE](LICENSE) 与 [NOTICE.md](NOTICE.md)。

