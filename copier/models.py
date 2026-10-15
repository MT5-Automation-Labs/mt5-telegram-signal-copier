from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Signal:
    side: str                 # "BUY" or "SELL"
    symbol: str               # raw symbol as written in the message
    entry: Optional[float]    # None = market
    sl: Optional[float]
    tps: List[float] = field(default_factory=list)
    entry_high: Optional[float] = None   # for "entry 1900-1905" ranges
    raw: str = ""

    def key(self) -> str:
        return f"{self.side}|{self.symbol}|{self.entry}|{self.sl}|{','.join(map(str, self.tps))}"
