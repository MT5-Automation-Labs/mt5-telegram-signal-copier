import time
from typing import Dict, Optional, Tuple

from .models import Signal


class Validator:
    def __init__(self, symbol_map: Dict[str, str], cfg: dict, clock=time.time):
        self.symbol_map = {k.upper(): v for k, v in (symbol_map or {}).items()}
        self.cfg = cfg or {}
        self.clock = clock
        self._seen: Dict[str, float] = {}

    def map_symbol(self, raw: str) -> Optional[str]:
        return self.symbol_map.get(raw.upper())

    def is_duplicate(self, sig: Signal) -> bool:
        now = self.clock()
        win = self.cfg.get("duplicate_window_sec", 600)
        self._seen = {k: t for k, t in self._seen.items() if now - t < win}
        k = sig.key()
        if k in self._seen:
            return True
        self._seen[k] = now
        return False

    def validate(self, sig: Signal, bid: float, ask: float,
                 msg_time: Optional[float] = None) -> Tuple[bool, str]:
        if self.map_symbol(sig.symbol) is None:
            return False, f"unmapped symbol {sig.symbol}"
        if self.cfg.get("require_sl", True) and sig.sl is None:
            return False, "missing SL"
        if msg_time is not None:
            age = self.clock() - msg_time
            if age > self.cfg.get("max_signal_age_sec", 120):
                return False, f"signal too old ({age:.0f}s)"
        price = ask if sig.side == "BUY" else bid
        if sig.sl is not None:
            if sig.side == "BUY" and sig.sl >= price:
                return False, "SL above current price"
            if sig.side == "SELL" and sig.sl <= price:
                return False, "SL below current price"
        if sig.tps:
            first = sig.tps[0]
            if sig.side == "BUY" and first <= price or sig.side == "SELL" and first >= price:
                return False, "TP1 already passed (stale)"
        if sig.entry is not None and price > 0:
            ref = sig.entry if sig.entry_high is None else (sig.entry + sig.entry_high) / 2
            dev = abs(price - ref) / price * 100
            if dev > self.cfg.get("max_entry_deviation_pct", 0.5):
                return False, f"price moved {dev:.2f}% from entry"
        if self.is_duplicate(sig):
            return False, "duplicate"
        return True, "ok"
