from typing import *
import string

def str_class(s: str) -> str:
    """Expand a string of character ranges.

    Example: str_class("a-cx0-9") = "abcx0123456789"
    """
    i = 0
    n = len(s)
    ret = [] # type: List[str]
    while i < n:
        if i + 2 < n and s[i+1] == '-':
            lo = ord(s[i])
            hi = ord(s[i+2])
            if lo > hi: lo, hi = hi, lo
            for mo in range(lo, hi + 1):
                ret.append(chr(mo))
            i += 3
        else:
            ret.append(s[i])
            i += 1
    return ''.join(ret)

def case_double(s: str) -> str:
    return s.upper() + s.lower()
