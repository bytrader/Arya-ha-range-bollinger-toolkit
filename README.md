# Arya-ha-range-bollinger-toolkit
Open-source toolkit for Heikin-Ashi normalization, Range bar construction, and Bollinger volatility metrics with dual-chart synchronization.


An open-source Python toolkit providing clean building blocks for dual-chart market data normalization:
- **Heikin-Ashi Bias Chart**: Smooths raw OHLCV candles to inspect directional context.
- **Range Trigger Chart**: Builds fixed-step price-range bars independent of elapsed time.
- **Bollinger Volatility Metrics**: Computes moving average, upper/lower bands, Bandwidth, and %B without embedding proprietary trading signals.
- **Look-Ahead-Safe Synchronization**: Pairs each Range trigger bar with the latest Heikin-Ashi candle available at or before its timestamp.

## Quick Example

```python
from toolkit import Candle, to_heikin_ashi, build_range_bars, synchronize_dual_chart, bollinger_metrics

raw = [
    Candle(1, 100.0, 102.0, 99.0, 101.5),
    Candle(2, 101.5, 104.0, 101.0, 103.5),
]
ha = to_heikin_ashi(raw)
rng = build_range_bars(raw, range_size=1.5)
events = synchronize_dual_chart(ha, rng)
bb = bollinger_metrics([c.close for c in ha], period=2)
