# MT5 Telegram Signal Copier

Listens to Telegram channels you choose, parses trade signals, validates them against live prices and copies them to MetaTrader 5 with risk-based position sizing.

## Features
- **Telethon listener** for any number of channels/groups (user account session).
- **Tolerant parser**: BUY/SELL/LONG/SHORT, symbol aliases (GOLD, XAUUSD, US30...), entry or entry range, SL, multiple TPs, emojis, comma decimals, multi-line or single-line formats.
- **Validation**: symbol mapping to broker names, signal age, entry deviation vs current tick, TP1 already passed, SL on wrong side, duplicate detection window.
- **Risk sizing**: lots computed from balance x risk % and SL distance using tick size/value; respects broker min/max/step.
- **Partial TPs**: volume split across TP legs (`tp_split`), remaining legs moved to **breakeven** after TP1 (configurable).
- **Trade log** in `logs/trades.csv` and `logs/trades.jsonl`.
- **Dry-run mode** (default) logs what would be traded without sending orders.
- Unit tests (pytest) for parser, validator, sizing and broker logic with a mocked MT5 module.

## Requirements
- Windows with MetaTrader 5 terminal installed and logged in (the `MetaTrader5` Python package is Windows-only).
- Python 3.10+
- Telegram API ID / hash from https://my.telegram.org

## Install
```bash
git clone https://github.com/MT5-Automation-Labs/mt5-telegram-signal-copier.git
cd mt5-telegram-signal-copier
pip install -r requirements.txt
copy .env.example .env      # then fill in your values
```
Edit `config.yaml`, then run:
```bash
python -m copier.main            # uses dry_run from config.yaml
python -m copier.main --dry-run  # force dry-run
```
The first start asks for your Telegram phone number and login code; the session file is stored locally (ignored by git).

## Configuration
**.env**: `TG_API_ID`, `TG_API_HASH`, `TG_SESSION`, optional `MT5_LOGIN`, `MT5_PASSWORD`, `MT5_SERVER`, `MT5_PATH` (leave empty to use the running terminal).

**config.yaml**
| Key | Meaning |
|---|---|
| `channels` | Channel usernames or numeric IDs to listen to |
| `dry_run` | `true` = never send orders |
| `risk.percent_per_trade` | % of balance lost if SL is hit (all legs combined) |
| `risk.max_lot` | Upper cap on total lot size |
| `symbols` | Signal symbol -> broker symbol (e.g. `GOLD: XAUUSD.m`) |
| `validation.max_entry_deviation_pct` | Reject if price moved further than this from the signal entry |
| `validation.max_signal_age_sec` | Reject messages older than this |
| `validation.duplicate_window_sec` | Ignore identical signals within this window |
| `validation.require_sl` | Reject signals without stop loss |
| `execution.use_market_orders` | `true` = market now, `false` = pending order at entry |
| `execution.tp_split` | Volume share per TP leg |
| `execution.breakeven_after_tp` | Move remaining legs to entry after N legs closed (0 = off) |
| `execution.magic`, `deviation_points`, `monitor_interval_sec` | Order settings |

## Tests
```bash
pip install pytest pyyaml python-dotenv
python -m pytest -q
```
Tests do not need MT5 or Telegram.

## Project layout
```
copier/parser.py     signal text -> Signal
copier/validator.py  symbol map, staleness, duplicates
copier/sizing.py     lot size and TP splitting
copier/broker.py     MetaTrader5 wrapper, partial TPs, breakeven
copier/tradelog.py   CSV / JSONL log
copier/main.py       Telegram listener and entry point
```

## Disclaimer

Trading forex, metals, indices and CFDs on margin carries a high level of risk and can result in losses greater than your deposit. This software is provided for educational purposes, without any warranty, and is not financial advice. Past or backtested performance does not guarantee future results. Always test on a demo account first and use it at your own risk.

## License
MIT © 2026 StanleyDaniels

## Contact

Telegram: [t.me/teraus111](https://t.me/teraus111)
