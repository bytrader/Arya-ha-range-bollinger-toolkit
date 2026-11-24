from toolkit import (
    Candle,
    to_heikin_ashi,
    build_range_bars,
    bollinger_metrics,
    synchronize_dual_chart,
)


def test_heikin_ashi_and_sync():
    raw = [
        Candle(1, 100.0, 102.0, 99.0, 101.5),
        Candle(2, 101.5, 104.0, 101.0, 103.5),
        Candle(3, 103.5, 105.0, 102.5, 103.0),
    ]
    ha = to_heikin_ashi(raw)
    assert len(ha) == 3
    assert ha[0].open == 100.75
    assert ha[0].close == 101.25

    bars = build_range_bars(raw, range_size=1.5)
    assert len(bars) >= 1

    synced = synchronize_dual_chart(ha, bars)
    assert len(synced) == len(bars)

    bb = bollinger_metrics([c.close for c in ha], period=2)
    assert bb[0]["middle"] is None
    assert bb[1]["middle"] is not None
