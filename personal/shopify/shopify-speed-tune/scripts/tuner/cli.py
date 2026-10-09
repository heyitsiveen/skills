"""The command line: every operation module in tuner/ops/, behind one parser."""

import argparse
import importlib
import pkgutil
import traceback

from tuner import ops
from tuner.output import Stop, say


def operation_modules():
    found = [importlib.import_module("tuner.ops." + info.name)
             for info in pkgutil.iter_modules(ops.__path__)]
    return sorted(found, key=lambda m: (getattr(m, "ORDER", 100), m.__name__))


def build_parser():
    parser = argparse.ArgumentParser(
        prog="speed_tune.py",
        description="The decision program behind the shopify-speed-tune skill. "
                    "Run every operation from the client theme repo.")
    sub = parser.add_subparsers(dest="op", required=True, metavar="<operation>")
    for module in operation_modules():
        module.register(sub)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        return args.run(args) or 0
    except Stop as stop:
        stop.report()
        return 1
    except Exception as error:  # a bug, not a verdict: say so on the fixed line, then show it
        say("FAILED", "internal: %s: %s" % (type(error).__name__, error))
        traceback.print_exc()
        return 1
