"""Tolerant signal parser.

Accepts many common layouts, e.g.:
  "GOLD BUY NOW @ 2350.5  SL 2340  TP1 2355 TP2 2360"
  "Sell EURUSD 1.0850-1.0860\nStop loss: 1.0900\nTake profit 1: 1.0800"
  "🔥 XAUUSD buy limit 2345 / sl: 2338 / tp: 2352, 2360"
"""
import re
from typing import Optional

from .models import Signal

_NUM = r"(\d+(?:[.,]\d+)?)"
_SIDE = re.compile(r"\b(BUY|SELL|LONG|SHORT)\b", re.I)
_SYMBOL = re.compile(r"\b([A-Z]{6}|XAUUSD|XAGUSD|GOLD|SILVER|US30|NAS100|US100|SPX500|GER40|BTCUSD|ETHUSD|USOIL|UKOIL)\b", re.I)
_SL = re.compile(r"\b(?:SL|S\.L\.?|STOP\s*LOSS|STOP)\b\s*[:=@\-]?\s*" + _NUM, re.I)
_TP_LINE = re.compile(r"\b(?:TP|T\.P\.?|TAKE\s*PROFIT|TARGET)\s*(?:\d(?![\d.,]))?\s*[:=@\-]?\s*((?:\d+(?:[.,]\d+)?(?:\s*[,/&|]\s*|\s+(?=\d)))*\d+(?:[.,]\d+)?)", re.I)
_ENTRY = re.compile(r"(?:@|\bENTRY\b|\bAT\b|\bPRICE\b|\b(?:BUY|SELL|LONG|SHORT)(?:\s+(?:LIMIT|STOP|NOW))?\b)\s*[:=]?\s*(?:[A-Z]{3,6}\s+)?" + _NUM + r"(?:\s*[-~]\s*" + _NUM + ")?", re.I)
_SIDE_MAP = {"BUY": "BUY", "LONG": "BUY", "SELL": "SELL", "SHORT": "SELL"}


def _f(s: str) -> float:
    return float(s.replace(",", "."))


def parse_signal(text: str) -> Optional[Signal]:
    if not text:
        return None
    clean = re.sub(r"[^\w\s.,:@/\-=~&|]", " ", text)
    side_m = _SIDE.search(clean)
    sym_m = _SYMBOL.search(clean)
    if not side_m or not sym_m:
        return None
    side = _SIDE_MAP[side_m.group(1).upper()]
    symbol = sym_m.group(1).upper()

    sl_m = _SL.search(clean)
    sl = _f(sl_m.group(1)) if sl_m else None

    tps = []
    for m in _TP_LINE.finditer(clean):
        for n in re.findall(r"\d+(?:[.,]\d+)?", m.group(1)):
            v = _f(n)
            if v not in tps:
                tps.append(v)

    entry = entry_high = None
    # strip SL/TP fragments so their numbers aren't taken as entry
    body = _TP_LINE.sub(" ", _SL.sub(" ", clean))
    body = _SYMBOL.sub(" ", body)
    em = _ENTRY.search(body)
    if em and em.group(1):
        entry = _f(em.group(1))
        if em.group(2):
            entry_high = _f(em.group(2))
            entry, entry_high = min(entry, entry_high), max(entry, entry_high)

    # sanity: SL must be on the losing side of entry
    ref = entry
    if ref is not None and sl is not None:
        if side == "BUY" and sl >= ref or side == "SELL" and sl <= ref:
            return None
    # order TPs nearest-first
    if tps:
        tps.sort(reverse=(side == "SELL"))
    return Signal(side=side, symbol=symbol, entry=entry, sl=sl, tps=tps,
                  entry_high=entry_high, raw=text)
