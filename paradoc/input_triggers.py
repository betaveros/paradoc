# vim:set ts=4 sw=4 et:
from typing import IO, List, Optional, Tuple, Union
import sys

# I'm closing the file after finishing reading from it so that I can read all
# from stdin exactly once, even if it's empty, while avoiding keeping track
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

# bool is if eof was encountered *before* this read
def word_eof(file: IO[str] = sys.stdin) -> Tuple[Optional[str], bool]:
    try:
        c = file.read(1)
        # Skip space
        while c.isspace(): c = file.read(1)

        res: List[str] = []

        while not c.isspace():
            res.append(c)
            c = file.read(1)
            # so this assumes the file ends with some whitespace I guess...
            # seems questionable FIXME maybe
            if not c:
                file.close()
                return (None, False)

        return (''.join(res), False)
    except ValueError: return (None, True)

def word(file: IO[str] = sys.stdin) -> Optional[str]:
    return word_eof(file)[0]

def value_eof(file: IO[str] = sys.stdin) -> Tuple[Optional[Union[str, int, float]], bool]:
    w, eof = word_eof(file)
    if w is None: return w, eof
    try:
        return int(w), eof
    except ValueError:
        try:
            return float(w), eof
        except ValueError:
            return w, eof

def value(file: IO[str] = sys.stdin) -> Optional[Union[str, int, float]]:
    return value_eof(file)[0]

# bool is if eof was encountered *before* this read
def line_eof(file: IO[str] = sys.stdin) -> Tuple[Optional[str], bool]:
    try:
        ret = file.readline()
        if ret:
            # TODO: does this work on Windows?
            assert ret[-1] == '\n'
            return (ret[:-1], False)
        else:
            # empty string means EOF
            file.close()
            return (None, False)
    except ValueError: return (None, True)

def line(file: IO[str] = sys.stdin) -> Optional[str]:
    return line_eof(file)[0]

def all_lines(file: IO[str] = sys.stdin) -> Optional[List[str]]:
    ret: List[str] = []
    while True:
        nextline, eof = line_eof(file)
        if eof: return None
        if nextline is None: return ret
        ret.append(nextline)

def all_values(file: IO[str] = sys.stdin) -> Optional[List[Union[str, int, float]]]:
    ret: List[Union[str, int, float]] = []
    while True:
        nextvalue, eof = value_eof(file)
        if eof: return None
        if nextvalue is None: return ret
        ret.append(nextvalue)
    return ret

def record(file: IO[str] = sys.stdin) -> Optional[Union[str, int, float]]:
    w = line(file)
    if w is None: return w
    try:
        return int(w)
    except ValueError:
        try:
            return float(w)
        except ValueError:
            return w

def all(file: IO[str] = sys.stdin) -> Optional[str]:
    try:
        ret = file.read()
        file.close()
        return ret
    except ValueError: return None

# vim:set tabstop=4 shiftwidth=4 expandtab fdm=marker:
