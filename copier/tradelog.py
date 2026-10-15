import csv
import json
import os
from datetime import datetime, timezone

FIELDS = ["time", "event", "symbol", "side", "volume", "price", "sl", "tp", "ticket", "dry_run", "note"]


class TradeLog:
    def __init__(self, directory: str = "logs"):
        os.makedirs(directory, exist_ok=True)
        self.csv_path = os.path.join(directory, "trades.csv")
        self.json_path = os.path.join(directory, "trades.jsonl")

    def write(self, **row):
        row.setdefault("time", datetime.now(timezone.utc).isoformat())
        rec = {k: row.get(k, "") for k in FIELDS}
        new = not os.path.exists(self.csv_path)
        with open(self.csv_path, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            if new:
                w.writeheader()
            w.writerow(rec)
        with open(self.json_path, "a") as f:
            f.write(json.dumps(rec) + "\n")
