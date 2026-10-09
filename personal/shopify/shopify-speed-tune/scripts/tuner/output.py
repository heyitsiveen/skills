"""Fixed, greppable output lines, and the two ways an operation stops early.

Every line the program prints starts with an upper-case tag. A refusal is a
guard saying no before anything changed; a failure is something going wrong
part-way. Both exit 1, and both name a short code a script can match.
"""

import sys


def say(tag, *parts):
    print(" ".join([tag] + [str(p) for p in parts if p is not None and p != ""]))
    sys.stdout.flush()


def note(text):
    say("NOTE", text)


class Stop(Exception):
    tag = "FAILED"

    def __init__(self, code, message, *notes):
        super().__init__("%s: %s" % (code, message))
        self.code = code
        self.message = message
        self.notes = notes

    def report(self):
        say(self.tag, "%s: %s" % (self.code, self.message))
        for text in self.notes:
            note(text)


class Refused(Stop):
    """A guard said no. Nothing was changed."""
    tag = "REFUSED"


class Failed(Stop):
    """Something went wrong part-way. The ledger says what already exists."""
    tag = "FAILED"
