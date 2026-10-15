"""Risk-based position sizing, independent of MT5 so it can be unit tested."""
import math
from dataclasses import dataclass


@dataclass
class SymbolSpec:
    tick_size: float
    tick_value: float      # account currency per 1 lot per tick
    volume_min: float
    volume_max: float
    volume_step: float


def round_volume(vol: float, spec: SymbolSpec) -> float:
    steps = math.floor(vol / spec.volume_step + 1e-9)
    v = steps * spec.volume_step
    v = min(v, spec.volume_max)
    decimals = max(0, -int(math.floor(math.log10(spec.volume_step)))) if spec.volume_step < 1 else 0
    return round(v, decimals)


def lot_for_risk(balance: float, risk_pct: float, entry: float, sl: float,
                 spec: SymbolSpec, max_lot: float = float("inf")) -> float:
    """Return lot size so that hitting SL loses ~risk_pct of balance. 0 if too small."""
    if balance <= 0 or risk_pct <= 0:
        return 0.0
    distance = abs(entry - sl)
    if distance <= 0 or spec.tick_size <= 0 or spec.tick_value <= 0:
        return 0.0
    loss_per_lot = distance / spec.tick_size * spec.tick_value
    raw = balance * risk_pct / 100.0 / loss_per_lot
    vol = round_volume(min(raw, max_lot), spec)
    return vol if vol >= spec.volume_min else 0.0


def split_volume(total: float, shares, spec: SymbolSpec):
    """Split total into legs by shares; legs below min are merged into the last leg."""
    if not shares:
        return [total]
    s = sum(shares)
    legs = [round_volume(total * x / s, spec) for x in shares]
    legs = [l for l in legs if l >= spec.volume_min]
    if not legs:
        return [total] if total >= spec.volume_min else []
    rest = round_volume(total - sum(legs), spec)
    if rest > 0:
        legs[-1] = round_volume(legs[-1] + rest, spec)
    return legs
