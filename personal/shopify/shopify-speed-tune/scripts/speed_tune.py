#!/usr/bin/env python3
"""
speed_tune.py — the decision program behind the `shopify-speed-tune` skill.

Every number and every decision in an invocation is made here, so nothing that
decides keep, remove or stop rests on a model's reading of a transcript. The
program owns the invocation's ledger, takes and records Samples, computes each
Measurement's median and range, and refuses whatever its guards forbid.

Run it from the client theme repo:

    python3 <skill>/scripts/speed_tune.py <operation> [flags]
    python3 <skill>/scripts/speed_tune.py --help

Each operation lives in its own module under tuner/ops/ and registers itself;
this file only finds them, so adding an operation edits nothing here.

Output is one fact per line, each starting with a fixed upper-case tag
(START, PAGE, SAMPLE, MEASUREMENT, REFUSED, FAILED, NOTE …) so a person or a
script can grep it. Exit status: 0 done, 1 refused or failed, 2 bad usage.

Python standard library only (3.11+). It shells out to `git`, `curl`, the
Shopify CLI and `pnpm`, and nothing is installed globally.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tuner.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
