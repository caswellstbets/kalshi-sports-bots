from __future__ import annotations

import argparse
import os

from . import engine
from .config import BotConfig


def main(cfg: BotConfig) -> None:
    ap = argparse.ArgumentParser(description=f"{cfg.title} paper-trading bot (Kalshi, pre-game only)")
    ap.add_argument("--dry-run", action="store_true", help="price the slate and print picks, save nothing")
    ap.add_argument("--no-ai", action="store_true", help="skip the AI step")
    ap.add_argument("--window-hours", type=float, help="override the entry window (testing)")
    ap.add_argument("--root", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    a = ap.parse_args()
    engine.run(cfg, a.root, dry=a.dry_run, use_ai=not a.no_ai, window_hours=a.window_hours)
    if not a.dry_run:
        from . import report
        report.build(a.root)
