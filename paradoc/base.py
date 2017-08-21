# coding: utf-8
# Pure base manipulation utilities.
from typing import List, Iterable
import string

def to_base_digits(base: int, num: int) -> List[int]:
    if num == 0: return [0]

    sign = 1
    if num < 0: num = -num; sign = -1
    acc = []
    while num > 0:
        acc.append(num % base)
        num //= base
    return [sign * digit for digit in reversed(acc)]

def to_base_digits_at_least_two(base: int, num: int) -> List[int]:
    ret = to_base_digits(base, num)
    return [0] * max(0, 2 - len(ret)) + ret

def from_base_digits(base: int, digits: Iterable[int]) -> int:
    acc = 0
    for digit in digits:
        acc = base * acc + digit
    return acc

digits_lower = string.digits + string.ascii_lowercase
digits_upper = string.digits + string.ascii_uppercase
def to_base_digits_lower(base: int, num: int) -> str:
    return ''.join(digits_lower[d] for d in to_base_digits(base, num))
def to_base_digits_upper(base: int, num: int) -> str:
    return ''.join(digits_upper[d] for d in to_base_digits(base, num))

# vim:set tabstop=4 shiftwidth=4 expandtab fdm=marker:
