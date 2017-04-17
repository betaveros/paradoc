Paradoc
=======

*Because there aren't enough golfing languages already™*

Paradoc is a golfing language in the stack-based lineage of GolfScript, heavily inspired by it and CJam. Other inspirations include 05AB1E, Jelly, Pyth, and rhoScript.

Like many of these other things, Paradoc is a work in progress. There will be documentation later :) In the meantime, here are some short snippets:

Hello, world! (unterminated strings are on the TODO list)

    "Hello, world!"

Print squares from 0 to 100, separated by spaces

    sE²m                 .. 4 bytes (if encoded as CP1252)
    sESqm                .. 5 ASCII characters
    _space 11 Square_map .. Expanded version

Print Fibonacci numbers from 0 to 89, separated by spaces (there will definitely be a 2-byte way to push the initial 0 and 1, but I haven't locked it down yet):

    s0 1T+kx .. 8 bytes / ASCII characters

    _space 0 1 10 +_keep_xloop .. Expanded version

Usage
=====

Paradoc is written in Python 3 (and uses [mypy (optional static typing) annotations](http://mypy-lang.org/) extensively). REPL:

    python3 -m paradoc

Run a file:

    python3 -m paradoc source_file.prdc

Evaluate a command:

    python3 -m paradoc -e "sESqm"
