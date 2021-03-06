from typing import Any, Callable, Union, Optional
import math
import operator

# A custom Char type, and lifted arithmetic functions that preserve
# Char-ness.

class Char:
    def __init__(self, arg: Union[int, str]) -> None:
        assert isinstance(arg, (int, str))
        if isinstance(arg, int):
            self.ord = arg
        else:
            self.ord = ord(arg)
    @property
    def chr(self) -> str:
        return chr(self.ord)
    def __bool__(self) -> bool:
        return bool(self.ord)
    def __lt__(self, other: Any) -> bool:
        if isinstance(other, Char):
            return self.ord < other.ord
        elif isinstance(other, int):
            # when equal let's say Char < int
            return self.ord <= other
        else:
            raise NotImplementedError
    def __gt__(self, other: Any) -> bool:
        if isinstance(other, Char):
            return self.ord > other.ord
        elif isinstance(other, int):
            # when equal let's say Char < int
            return self.ord > other
        else:
            raise NotImplementedError
    def __eq__(self, other: Any) -> bool:
        return isinstance(other, Char) and self.ord == other.ord
    def __ne__(self, other: Any) -> bool:
        return not (self == other)
    def __str__(self) -> str:
        return "'" + self.chr
    def __repr__(self) -> str:
        return "Char(" + repr(self.chr) + ")"
    def __hash__(self) -> int:
        return hash(self.ord)

Num = Union[int, float, complex]
PdNum = Union[Char, int, float, complex]

def numerify(x: PdNum) -> Num:
    if isinstance(x, Char):
        return x.ord
    else:
        return x

def realify(x: PdNum) -> Union[int, float]:
    return numerify(x).real

def floatify(x: PdNum) -> float:
    return float(realify(x))

def intify(x: PdNum) -> int:
    return int(realify(x))

def intify_opt(x: Optional[PdNum]) -> Optional[int]:
    if x is None:
        return None
    else:
        return intify(x)

def lift_numerify1(f: Callable[[Num], Num]) -> Callable[[PdNum], PdNum]:
    def inner(a: PdNum) -> PdNum:
        if isinstance(a, Char):
            res = f(a.ord)
            assert isinstance(res, int)
            return Char(res)
        else:
            return f(a)
    return inner

def lift_numerify(f: Callable[[Num, Num], Num]) -> Callable[[PdNum, PdNum], PdNum]:
    def inner(a: PdNum, b: PdNum) -> PdNum:
        if isinstance(a, Char) and isinstance(b, Char):
            res = f(a.ord, b.ord)
            assert isinstance(res, int)
            return Char(res)
        else:
            return f(numerify(a), numerify(b))
    return inner

def lift_realify(f: Callable[[Union[int, float], Union[int, float]], Union[int, float]]) -> Callable[[PdNum, PdNum], PdNum]:
    def inner(a: PdNum, b: PdNum) -> PdNum:
        if isinstance(a, Char) and isinstance(b, Char):
            res = f(a.ord, b.ord)
            assert isinstance(res, int)
            return Char(res)
        else:
            return f(realify(a), realify(b))
    return inner

def lift_intify(f: Callable[[int, int], int]) -> Callable[[PdNum, PdNum], Union[int, Char]]:
    def inner(a: PdNum, b: PdNum) -> Union[int, Char]:
        if isinstance(a, Char) and isinstance(b, Char):
            return Char(f(a.ord, b.ord))
        else:
            return f(intify(a), intify(b))
    return inner

def any_cmp(a: Any, b: Any) -> int:
    return int(a > b) - int(a < b)

def pd_num_cmp(a0: PdNum, b0: PdNum) -> int:
    a = a0.ord if isinstance(a0, Char) else a0
    b = b0.ord if isinstance(b0, Char) else b0
    if isinstance(a, int) and isinstance(b, int):
        return int(a > b) - int(a < b)
    else:
        af, bf = float(a.real), float(b.real)
        rc = int(af > bf) - int(af < bf)
        if rc: return rc

        ai, bi = float(a.imag), float(b.imag)
        return int(ai > bi) - int(ai < bi)

pd_add = lift_numerify(operator.add)
pd_sub = lift_numerify(operator.sub)
pd_mul = lift_numerify(operator.mul)
pd_div = lift_numerify(operator.truediv) # float division!
pd_mod = lift_realify(operator.mod)
pd_pow = lift_numerify(operator.pow)

pd_intdiv = lift_realify(operator.floordiv)

def positive_biased_balanced_mod(a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
    mod = a % b
    if abs(mod) > abs(b) / 2: mod -= abs(b)
    if abs(mod) <= -abs(b) / 2: mod += abs(b)
    return mod

def negative_biased_balanced_mod(a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
    mod = a % b
    if abs(mod) >= abs(b) / 2: mod -= abs(b)
    if abs(mod) < -abs(b) / 2: mod += abs(b)
    return mod

pd_positive_biased_balanced_mod = lift_realify(positive_biased_balanced_mod)
pd_negative_biased_balanced_mod = lift_realify(negative_biased_balanced_mod)

pd_and = lift_intify(operator.and_)
pd_or  = lift_intify(operator.or_)
pd_xor = lift_intify(operator.xor)

pd_lshift = lift_intify(operator.lshift)
pd_rshift = lift_intify(operator.rshift)

def int_gcd(a: int, b: int) -> int:
    return a if b == 0 else int_gcd(b, a % b)

def int_lcm(a: int, b: int) -> int:
    return a * b // int_gcd(a, b)

pd_gcd = lift_intify(int_gcd)
pd_lcm = lift_intify(int_lcm)

pd_ceil   = lift_numerify1(lambda x: int(math.ceil(x.real)))
pd_floor  = lift_numerify1(lambda x: int(math.floor(x.real)))
pd_round  = lift_numerify1(lambda x: round(x.real))
pd_abs    = lift_numerify1(abs)

def pd_signum(x: PdNum) -> PdNum:
    if isinstance(x, Char):
        return Char(int(x > 0))
    elif isinstance(x, complex):
        a = abs(x)
        return x / a if a else complex(0.0)
    else:
        return (x > 0) - (x < 0)

def pd_add_const(a: PdNum, const: int) -> PdNum:
    if isinstance(a, Char):
        return Char(a.ord + const)
    else:
        return a + const

def pd_mul_div_const(a: PdNum, mul: int, div: int, to_int: bool = False) -> PdNum:
    if isinstance(a, Char):
        return Char(a.ord * mul // div)
    elif to_int:
        return int((a * mul).real // div)
    elif div == 1:
        return a * mul
    else:
        return a * mul / div

def pd_mod_const(a: PdNum, const: int) -> PdNum:
    if isinstance(a, Char):
        return Char(a.ord % const)
    else:
        return a.real % const

def pd_xor_const(a: PdNum, const: int) -> PdNum:
    if isinstance(a, Char):
        return Char(a.ord ^ const)
    else:
        return intify(a) ^ const

def pd_power_const(a: PdNum, const: int) -> PdNum:
    if isinstance(a, Char):
        return Char(a.ord ** const) # really?
    else:
        return a ** const

def pd_count_multiplicity_in(a0: PdNum, b0: PdNum) -> int:
    a = intify(a0)
    b = intify(b0)
    c = 0
    if b == 0: return -1 # ???
    while b % a == 0:
        b //= a
        c += 1
    return c

matching_dict = {
    '(': ')', ')': '(',
    '[': ']', ']': '[',
    '<': '>', '>': '<',
    '{': '}', '}': '{',
}

nest_dict = {
    '(': 1, ')': -1,
    '[': 1, ']': -1,
    '<': 1, '>': -1,
    '{': 1, '}': -1,
}

value_dict = {
    '+': 1, '-': -1,
    '<': -1, '>': 1,
    '0': 0, '1': 1, '2': 2, '3': 3, '4': 4,
    '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
}

def int_of_alpha(s: str) -> int:
    if 'A' <= s <= 'Z': return ord(s) - ord('A') + 1
    if 'a' <= s <= 'z': return ord(s) - ord('a') + 1
    return 0

def lower_of_int(n: int) -> Char:
    if 1 <= n <= 26: return Char(ord('a') - 1 + n)
    return Char(' ')

def upper_of_int(n: int) -> Char:
    if 1 <= n <= 26: return Char(ord('A') - 1 + n)
    return Char(' ')

# vim:set tabstop=4 shiftwidth=4 expandtab fdm=marker:
