from copier.models import Signal
from copier.validator import Validator

CFG = {"max_entry_deviation_pct": 0.5, "max_signal_age_sec": 120, "duplicate_window_sec": 600}


def mk(clock=lambda: 1000.0):
    return Validator({"GOLD": "XAUUSD"}, CFG, clock=clock)


def sig(**kw):
    d = dict(side="BUY", symbol="GOLD", entry=2350.0, sl=2340.0, tps=[2360.0])
    d.update(kw)
    return Signal(**d)


def test_ok():
    assert mk().validate(sig(), 2349.8, 2350.0, 990) == (True, "ok")


def test_unmapped():
    assert not mk().validate(sig(symbol="EURUSD"), 1, 1)[0]


def test_stale_price_and_tp_passed():
    assert "moved" in mk().validate(sig(tps=[2400.0]), 2369, 2370)[1]
    assert "TP1" in mk().validate(sig(), 2361, 2361.2)[1]


def test_old_message():
    assert "old" in mk().validate(sig(), 2349.8, 2350, msg_time=500)[1]


def test_duplicate():
    v = mk()
    assert v.validate(sig(), 2349.8, 2350)[0]
    assert v.validate(sig(), 2349.8, 2350)[1] == "duplicate"
