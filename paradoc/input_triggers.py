from typing import *
from typing import IO # ???
import sys

# TODO: I'm closing the file after finishing reading from it so that I can read
# all from stdin exactly once, even if it's empty, while avoiding keeping track
# of my own state.

# If mypy were not a concern, I would extract
#
#     try: ... except ValueError: return
#
# into a decorator, but there aren't optional arguments yet, so rip.

def char(file: IO[str] = sys.stdin) -> Optional[str]:
    try:
        res = file.read(1)
        if not res:
            file.close()
            return None
        return res
    except ValueError: return None

def word(file: IO[str] = sys.stdin) -> Optional[str]:
    try:
        c = file.read(1)
        # Skip space
        while c.isspace(): c = file.read(1)

        res = [] # type: List[str]

        while not c.isspace():
            res.append(c)
            c = file.read(1)
            if not c:
                file.close()
                return None

        return ''.join(res)
    except ValueError: return None

def value(file: IO[str] = sys.stdin) -> Optional[Union[str, int, float]]:
    w = word(file)
    if w is None: return w
    try:
        return int(w)
    except ValueError:
        try:
            return float(w)
        except ValueError:
            return w

def line(file: IO[str] = sys.stdin) -> Optional[str]:
    try:
        ret = file.readline()
        if ret:
            # TODO: does this work on Windows?
            assert ret[-1] == '\n'
            return ret[:-1]
        else:
            # empty string means EOF
            file.close()
            return None
    except ValueError: return None

def all(file: IO[str] = sys.stdin) -> Optional[str]:
    try:
        ret = file.read()
        file.close()
        return ret
    except ValueError: return None
