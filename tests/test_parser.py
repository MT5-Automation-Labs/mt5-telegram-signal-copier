import pytest
from copier.parser import parse_signal


def test_basic_buy():
    s = parse_signal("GOLD BUY NOW @ 2350.5  SL 2340  TP1 2355 TP2 2360")
    assert (s.side, s.symbol, s.entry, s.sl, s.tps) == ("BUY", "GOLD", 2350.5, 2340, [2355, 2360])


def test_multiline_sell_range():
    s = parse_signal("Sell EURUSD 1.0850-1.0860\nStop loss: 1.0900\nTake profit 1: 1.0800\nTake profit 2: 1.0750")
    assert s.side == "SELL" and s.symbol == "EURUSD"
    assert s.entry == 1.0850 and s.entry_high == 1.0860
    assert s.sl == 1.09 and s.tps == [1.08, 1.075]


def test_emoji_and_list_tps():
    s = parse_signal("🔥 xauusd buy limit 2345 / sl: 2338 / tp: 2352, 2360")
    assert s.side == "BUY" and s.symbol == "XAUUSD" and s.entry == 2345
    assert s.sl == 2338 and s.tps == [2352, 2360]


def test_long_short_aliases_and_comma_decimal():
    s = parse_signal("SHORT GBPUSD at 1,2700 SL 1,2750 TP 1,2650")
    assert s.side == "SELL" and s.entry == 1.27 and s.sl == 1.275


def test_market_without_entry():
    s = parse_signal("BUY US30\nSL 38000\nTP 39000")
    assert s.entry is None and s.sl == 38000 and s.tps == [39000]


@pytest.mark.parametrize("txt", ["", "good morning traders", "EURUSD looking strong", "BUY now!"])
def test_non_signals(txt):
    assert parse_signal(txt) is None


def test_wrong_side_sl_rejected():
    assert parse_signal("BUY EURUSD 1.1000 SL 1.1050 TP 1.1100") is None
