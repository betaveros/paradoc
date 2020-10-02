from typing import List, Optional, Union

def str_class(s: str) -> str:
    """Expand a string of character ranges.

    Example: str_class("a-cx0-9") = "abcx0123456789"
    """
    i = 0
    n = len(s)
    ret: List[str] = []
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

# https://tools.ietf.org/html/rfc1924
rfc1924_base85_alphabet = str_class('0-9A-Za-z') + '!#$%&()*+-;<=>?@^_`{|}~'
assert len(rfc1924_base85_alphabet) == 85
rfc1924_base85_dict = {c: i for i, c in enumerate(rfc1924_base85_alphabet)}
# omitted: " ' , . / : [ ] \ (and space)

def base85_parse(s: str) -> List[Union[int, float]]:
    ret: List[Union[int, float]] = []
    acc: Union[int, float] = 0
    fp_places: Optional[int] = None

    def flush() -> None:
        if fp_places is None:
            ret.append(acc)
        else:
            ret.append(acc / (85 ** fp_places))

    for c in s:
        if c == ' ':
            flush()
            acc = 0
            fp_places = 0
        elif c == ':': flush()
        elif c == ',': acc = -acc
        elif c == '/': acc = 1 / acc
        elif c == '.': fp_places = 0
        elif c == '‹': acc -= 1
        elif c == '›': acc += 1
        elif c == '«': acc -= 2
        elif c == '»': acc += 2
        elif c in rfc1924_base85_dict:
            acc = acc * 85 + rfc1924_base85_dict[c]
            if fp_places is not None:
                fp_places += 1
        else:
            raise ValueError('unsupported base85 character: ' + repr(c))
    flush()
    return ret

# vim:set tabstop=4 shiftwidth=4 expandtab fdm=marker:
