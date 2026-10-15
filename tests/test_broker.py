from types import SimpleNamespace as NS
from unittest.mock import MagicMock

from copier.broker import Broker
from copier.models import Signal


def fake_mt5():
    m = MagicMock()
    m.symbol_info_tick.return_value = NS(bid=2349.8, ask=2350.0)
    m.symbol_info.return_value = NS(trade_tick_size=0.01, trade_tick_value=1.0,
                                    volume_min=0.01, volume_max=50, volume_step=0.01)
    m.account_info.return_value = NS(balance=10_000)
    m.TRADE_RETCODE_DONE, m.TRADE_RETCODE_PLACED = 10009, 10008
    tickets = iter(range(1, 10))
    m.order_send.side_effect = lambda req: NS(retcode=10009, order=next(tickets), price=req.get("price"), comment="")
    return m


CFG = {"risk": {"percent_per_trade": 1.0}, "execution": {"tp_split": [0.5, 0.5], "breakeven_after_tp": 1}}


def test_place_splits_legs_and_breakeven():
    m, log = fake_mt5(), MagicMock()
    b = Broker(CFG, log, mt5_module=m, dry_run=False)
    t = b.place(Signal("BUY", "GOLD", None, 2340.0, [2355.0, 2360.0]), "XAUUSD")
    assert t == [1, 2]
    vols = [c.args[0]["volume"] for c in m.order_send.call_args_list]
    assert abs(sum(vols) - 0.10) < 1e-9          # $100 risk / ($10 * 100 ticks)
    m.positions_get.return_value = [NS(ticket=2, tp=2360.0)]  # TP1 leg closed
    b.manage()
    last = m.order_send.call_args.args[0]
    assert last["position"] == 2 and last["sl"] == 2350.0


def test_dry_run_sends_nothing():
    m, log = fake_mt5(), MagicMock()
    b = Broker(CFG, log, mt5_module=m, dry_run=True)
    b.place(Signal("BUY", "GOLD", None, 2340.0, [2355.0]), "XAUUSD")
    m.order_send.assert_not_called()
    assert log.write.call_args.kwargs["event"] == "dry_open"
