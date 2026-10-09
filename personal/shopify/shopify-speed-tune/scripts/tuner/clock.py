"""The program's timestamps, as the ledger and the machine lock keep them."""

from datetime import datetime


def now():
    """This moment as local time with its offset, to the second: `2026-10-08T06:00:38+08:00`."""
    return datetime.now().astimezone().isoformat(timespec="seconds")
