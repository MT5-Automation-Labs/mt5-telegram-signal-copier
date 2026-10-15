from copier.sizing import SymbolSpec, lot_for_risk, round_volume, split_volume

FX = SymbolSpec(tick_size=0.00001, tick_value=1.0, volume_min=0.01, volume_max=100, volume_step=0.01)
GOLD = SymbolSpec(tick_size=0.01, tick_value=1.0, volume_min=0.01, volume_max=50, volume_step=0.01)


def test_fx_one_percent_50_pips():
    # 10k * 1% = 100 USD; 50 pips = 500 ticks * $1 = $500/lot -> 0.20 lot
    assert lot_for_risk(10_000, 1.0, 1.1000, 1.0950, FX) == 0.20


def test_gold():
    # $10 SL distance = 1000 ticks * $1 = $1000/lot ; risk $50 -> 0.05
    assert lot_for_risk(5_000, 1.0, 2350, 2340, GOLD) == 0.05


def test_rounds_down_and_caps():
    assert lot_for_risk(10_000, 1.0, 1.1, 1.0997, FX, max_lot=1.5) == 1.5
    assert round_volume(0.239, FX) == 0.23


def test_too_small_returns_zero():
    assert lot_for_risk(50, 0.5, 1.1, 1.0, FX) == 0.0
    assert lot_for_risk(1000, 1, 1.1, 1.1, FX) == 0.0


def test_split():
    legs = split_volume(1.0, [0.5, 0.3, 0.2], FX)
    assert legs == [0.5, 0.3, 0.2]
    legs = split_volume(0.02, [0.5, 0.3, 0.2], FX)
    assert abs(sum(legs) - 0.02) < 1e-9 and all(l >= 0.01 for l in legs)
