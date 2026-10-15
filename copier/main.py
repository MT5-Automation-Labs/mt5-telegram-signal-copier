import asyncio
import logging
import os

import yaml
from dotenv import load_dotenv

from .broker import Broker
from .parser import parse_signal
from .tradelog import TradeLog
from .validator import Validator

log = logging.getLogger("copier")


def load_config(path="config.yaml"):
    with open(path) as f:
        return yaml.safe_load(f)


async def run(cfg):
    from telethon import TelegramClient, events

    dry = bool(cfg.get("dry_run", True))
    tlog = TradeLog(cfg.get("log", {}).get("dir", "logs"))
    broker = Broker(cfg, tlog, dry_run=dry)
    if not broker.connect(os.getenv("MT5_LOGIN"), os.getenv("MT5_PASSWORD"),
                          os.getenv("MT5_SERVER"), os.getenv("MT5_PATH")):
        raise SystemExit("Cannot connect to MT5 terminal")
    val = Validator(cfg.get("symbols", {}), cfg.get("validation", {}))
    client = TelegramClient(os.getenv("TG_SESSION", "copier"),
                            int(os.environ["TG_API_ID"]), os.environ["TG_API_HASH"])

    @client.on(events.NewMessage(chats=cfg["channels"]))
    async def handler(event):
        sig = parse_signal(event.raw_text)
        if not sig:
            return
        symbol = val.map_symbol(sig.symbol)
        bid, ask = broker.tick(symbol) if symbol else (0.0, 0.0)
        ok, why = val.validate(sig, bid, ask, event.date.timestamp())
        log.info("signal %s -> %s", sig.key(), why)
        if not ok:
            tlog.write(event="rejected", symbol=sig.symbol, side=sig.side, note=why, dry_run=dry)
            return
        broker.place(sig, symbol)

    async def monitor():
        while True:
            try:
                broker.manage()
            except Exception:  # keep the loop alive
                log.exception("manage failed")
            await asyncio.sleep(cfg.get("execution", {}).get("monitor_interval_sec", 5))

    await client.start()
    log.info("Listening on %s (dry_run=%s)", cfg["channels"], dry)
    asyncio.create_task(monitor())
    await client.run_until_disconnected()


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    load_dotenv()
    import argparse
    ap = argparse.ArgumentParser(description="Copy Telegram trade signals to MT5")
    ap.add_argument("-c", "--config", default="config.yaml")
    ap.add_argument("--dry-run", action="store_true", help="force dry-run")
    a = ap.parse_args()
    cfg = load_config(a.config)
    if a.dry_run:
        cfg["dry_run"] = True
    asyncio.run(run(cfg))


if __name__ == "__main__":
    main()
