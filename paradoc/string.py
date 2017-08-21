from typing import List

def str_class(s: str) -> str:
    """Expand a string of character ranges.

    Example: str_class("a-cx0-9") = "abcx0123456789"
    """
    i = 0
    n = len(s)
    ret = [] # type: List[str]
    while i < n:
        if i + 2 < n and s[i+1] == '-':
            start = ord(s[i])
            end = ord(s[i+2])
            if start <= end:
                ret.extend(chr(c) for c in range(start, end + 1))
            else:
                ret.extend(chr(c) for c in range(start, end - 1, -1))
            i += 3
        else:
            ret.append(s[i])
            i += 1
    return ''.join(ret)

def case_double(s: str) -> str:
    return s.upper() + s.lower()

# vim:set tabstop=4 shiftwidth=4 expandtab fdm=marker:
