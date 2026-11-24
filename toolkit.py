from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence
import math


@dataclass(frozen=True)
class Candle:
    """Standard OHLCV candle representation."""
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


@dataclass(frozen=True)
class SyncedTriggerEvent:
    """Range bar paired with the latest closed Heikin-Ashi context without look-ahead bias."""
    range_bar: Candle
    ha_bias_candle: Optional[Candle]
    ha_direction: int  # 1 for bullish HA, -1 for bearish HA, 0 for neutral/unavailable


def to_heikin_ashi(candles: Sequence[Candle]) -> List[Candle]:
    """Convert standard OHLCV candles into Heikin-Ashi candles."""
    if not candles:
        return []

    ha_candles: List[Candle] = []
    prev_ha_open: Optional[float] = None
    prev_ha_close: Optional[float] = None

    for c in candles:
        ha_close = (c.open + c.high + c.low + c.close) / 4.0

        if prev_ha_open is None or prev_ha_close is None:
            ha_open = (c.open + c.close) / 2.0
        else:
            ha_open = (prev_ha_open + prev_ha_close) / 2.0

        ha_high = max(c.high, ha_open, ha_close)
        ha_low = min(c.low, ha_open, ha_close)

        ha_candle = Candle(
            timestamp=c.timestamp,
            open=ha_open,
            high=ha_high,
            low=ha_low,
            close=ha_close,
            volume=c.volume,
        )
        ha_candles.append(ha_candle)
        prev_ha_open = ha_open
        prev_ha_close = ha_close

    return ha_candles


def build_range_bars(ticks_or_candles: Sequence[Candle], range_size: float) -> List[Candle]:
    """Build fixed-step Range bars from sequential price points/candles."""
    if range_size <= 0:
        raise ValueError("range_size must be positive.")
    if not ticks_or_candles:
        return []

    range_bars: List[Candle] = []
    bar_open: Optional[float] = None
    bar_high: Optional[float] = None
    bar_low: Optional[float] = None
    bar_start_ts: Optional[int] = None
    acc_volume: float = 0.0

    for item in ticks_or_candles:
        prices = (item.open, item.high, item.low, item.close)
        for p in prices:
            if bar_open is None:
                bar_open = p
                bar_high = p
                bar_low = p
                bar_start_ts = item.timestamp
                acc_volume = item.volume
                continue

            assert bar_high is not None and bar_low is not None and bar_start_ts is not None
            candidate_high = max(bar_high, p)
            candidate_low = min(bar_low, p)

            if (candidate_high - candidate_low) >= range_size:
                if p >= bar_open:
                    closed_high = bar_low + range_size
                    closed_low = bar_low
                    closed_close = closed_high
                else:
                    closed_low = bar_high - range_size
                    closed_high = bar_high
                    closed_close = closed_low

                range_bars.append(
                    Candle(
                        timestamp=item.timestamp,
                        open=bar_open,
                        high=closed_high,
                        low=closed_low,
                        close=closed_close,
                        volume=acc_volume,
                    )
                )

                # Start next bar at current price p
                bar_open = p
                bar_high = p
                bar_low = p
                bar_start_ts = item.timestamp
                acc_volume = 0.0
            else:
                bar_high = candidate_high
                bar_low = candidate_low
                acc_volume += item.volume

    return range_bars


def bollinger_metrics(
    values: Sequence[float],
    period: int = 20,
    std_dev: float = 2.0,
) -> List[dict[str, Optional[float]]]:
    """Compute SMA, upper/lower Bollinger Bands, Bandwidth, and %B."""
    if period <= 0:
        raise ValueError("period must be positive.")

    results: List[dict[str, Optional[float]]] = []
    for i in range(len(values)):
        if i + 1 < period:
            results.append({
                "middle": None,
                "upper": None,
                "lower": None,
                "bandwidth": None,
                "percent_b": None,
            })
            continue

        window = values[i + 1 - period : i + 1]
        mean = sum(window) / period
        variance = sum((x - mean) ** 2 for x in window) / period
        std = math.sqrt(variance)

        upper = mean + std_dev * std
        lower = mean - std_dev * std
        bandwidth = ((upper - lower) / mean) if mean != 0 else None
        band_span = upper - lower
        percent_b = ((values[i] - lower) / band_span) if band_span != 0 else None

        results.append({
            "middle": mean,
            "upper": upper,
            "lower": lower,
            "bandwidth": bandwidth,
            "percent_b": percent_b,
        })

    return results


def synchronize_dual_chart(
    ha_bias_candles: Sequence[Candle],
    range_trigger_bars: Sequence[Candle],
) -> List[SyncedTriggerEvent]:
    """Align each Range bar with the latest HA candle whose timestamp <= bar timestamp."""
    synced: List[SyncedTriggerEvent] = []
    ha_idx = 0
    n_ha = len(ha_bias_candles)

    for r_bar in range_trigger_bars:
        while ha_idx + 1 < n_ha and ha_bias_candles[ha_idx + 1].timestamp <= r_bar.timestamp:
            ha_idx += 1

        if n_ha == 0 or ha_bias_candles[ha_idx].timestamp > r_bar.timestamp:
            synced.append(
                SyncedTriggerEvent(
                    range_bar=r_bar,
                    ha_bias_candle=None,
                    ha_direction=0,
                )
            )
            continue

        ha_c = ha_bias_candles[ha_idx]
        if ha_c.close > ha_c.open:
            direction = 1
        elif ha_c.close < ha_c.open:
            direction = -1
        else:
            direction = 0

        synced.append(
            SyncedTriggerEvent(
                range_bar=r_bar,
                ha_bias_candle=ha_c,
                ha_direction=direction,
            )
        )

    return synced


if __name__ == "__main__":
    sample_raw = [
        Candle(1, 100.0, 102.0, 99.0, 101.5),
        Candle(2, 101.5, 104.0, 101.0, 103.5),
        Candle(3, 103.5, 105.0, 102.5, 103.0),
        Candle(4, 103.0, 103.5, 100.5, 101.0),
    ]
    ha_series = to_heikin_ashi(sample_raw)
    range_series = build_range_bars(sample_raw, range_size=1.5)
    aligned = synchronize_dual_chart(ha_series, range_series)
    bb = bollinger_metrics([c.close for c in ha_series], period=2, std_dev=2.0)

    print(f"HA count: {len(ha_series)}, Range bars: {len(range_series)}, Synced events: {len(aligned)}")
    print("Last BB metric:", bb[-1] if bb else None)
