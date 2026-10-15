"""Thin wrapper around the MetaTrader5 package. Pass `mt5_module` to inject a mock."""
import logging

from .sizing import SymbolSpec, lot_for_risk, split_volume

log = logging.getLogger(__name__)


class Broker:
    def __init__(self, cfg: dict, tradelog, mt5_module=None, dry_run=True):
        if mt5_module is None:
            import MetaTrader5 as mt5_module  # noqa: N813  (Windows only)
        self.mt5 = mt5_module
        self.cfg = cfg
        self.exe = cfg.get("execution", {})
        self.risk = cfg.get("risk", {})
        self.log = tradelog
        self.dry_run = dry_run
        self.managed = {}   # group_id -> dict(entry, side, symbol, tickets, be_done)

    def connect(self, login=None, password=None, server=None, path=None) -> bool:
        kw = {}
        if path:
            kw["path"] = path
        if login:
            kw.update(login=int(login), password=password, server=server)
        ok = self.mt5.initialize(**kw)
        if not ok:
            log.error("MT5 initialize failed: %s", self.mt5.last_error())
        return bool(ok)

    def tick(self, symbol):
        self.mt5.symbol_select(symbol, True)
        t = self.mt5.symbol_info_tick(symbol)
        return (t.bid, t.ask) if t else (0.0, 0.0)

    def spec(self, symbol) -> SymbolSpec:
        i = self.mt5.symbol_info(symbol)
        return SymbolSpec(i.trade_tick_size, i.trade_tick_value, i.volume_min, i.volume_max, i.volume_step)

    def place(self, sig, symbol):
        bid, ask = self.tick(symbol)
        price = ask if sig.side == "BUY" else bid
        entry = price if (self.exe.get("use_market_orders", True) or sig.entry is None) else sig.entry
        spec = self.spec(symbol)
        balance = self.mt5.account_info().balance
        total = lot_for_risk(balance, self.risk.get("percent_per_trade", 1.0), entry, sig.sl,
                             spec, self.risk.get("max_lot", float("inf")))
        if total <= 0:
            self.log.write(event="skip", symbol=symbol, side=sig.side, note="lot below minimum")
            return []
        tps = sig.tps or [None]
        legs = split_volume(total, self.exe.get("tp_split", [1.0])[:len(tps)], spec)
        tickets = []
        for i, vol in enumerate(legs):
            tp = tps[min(i, len(tps) - 1)]
            tickets.append(self._send(sig.side, symbol, vol, entry, sig.sl, tp))
        tickets = [t for t in tickets if t is not None]
        if tickets:
            self.managed[tickets[0]] = dict(entry=entry, side=sig.side, symbol=symbol,
                                            tickets=tickets, be_done=False)
        return tickets

    def _send(self, side, symbol, vol, price, sl, tp):
        m = self.mt5
        market = self.exe.get("use_market_orders", True)
        if market:
            otype = m.ORDER_TYPE_BUY if side == "BUY" else m.ORDER_TYPE_SELL
            action = m.TRADE_ACTION_DEAL
        else:
            bid, ask = self.tick(symbol)
            if side == "BUY":
                otype = m.ORDER_TYPE_BUY_LIMIT if price < ask else m.ORDER_TYPE_BUY_STOP
            else:
                otype = m.ORDER_TYPE_SELL_LIMIT if price > bid else m.ORDER_TYPE_SELL_STOP
            action = m.TRADE_ACTION_PENDING
        req = {"action": action, "symbol": symbol, "volume": vol, "type": otype, "price": price,
               "sl": sl or 0.0, "tp": tp or 0.0, "deviation": self.exe.get("deviation_points", 20),
               "magic": self.exe.get("magic", 0), "comment": "tg-copier",
               "type_time": m.ORDER_TIME_GTC, "type_filling": m.ORDER_FILLING_IOC}
        if self.dry_run:
            self.log.write(event="dry_open", symbol=symbol, side=side, volume=vol, price=price,
                           sl=sl, tp=tp, dry_run=True)
            return None
        res = m.order_send(req)
        if res is None or res.retcode not in (m.TRADE_RETCODE_DONE, m.TRADE_RETCODE_PLACED):
            self.log.write(event="error", symbol=symbol, side=side, volume=vol,
                           note=str(getattr(res, "comment", m.last_error())))
            return None
        self.log.write(event="open", symbol=symbol, side=side, volume=vol, price=res.price or price,
                       sl=sl, tp=tp, ticket=res.order)
        return res.order

    def manage(self):
        """Move remaining legs to breakeven after N TP legs have closed."""
        need = self.exe.get("breakeven_after_tp", 1)
        if not need:
            return
        m = self.mt5
        for gid, g in list(self.managed.items()):
            open_pos = {p.ticket: p for p in (m.positions_get(symbol=g["symbol"]) or [])}
            alive = [t for t in g["tickets"] if t in open_pos]
            if not alive:
                del self.managed[gid]
                continue
            closed = len(g["tickets"]) - len(alive)
            if closed >= need and not g["be_done"]:
                for t in alive:
                    p = open_pos[t]
                    req = {"action": m.TRADE_ACTION_SLTP, "symbol": g["symbol"], "position": t,
                           "sl": g["entry"], "tp": p.tp}
                    r = m.order_send(req)
                    self.log.write(event="breakeven", symbol=g["symbol"], ticket=t, sl=g["entry"],
                                   note=str(getattr(r, "retcode", "")))
                g["be_done"] = True
