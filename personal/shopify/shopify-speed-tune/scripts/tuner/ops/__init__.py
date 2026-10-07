"""One module per operation.

Each module defines `register(subparsers)`, which adds its sub-command and sets
`run` to the function that carries it out, plus an optional `ORDER` that places
it in `--help`. `tuner.cli` imports every module in this package, so a new
operation is a new file here and nothing else.
"""
