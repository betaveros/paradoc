from typing import *
import math
import operator

# A custom Char type, and lifted arithmetic functions that preserve
# Char-ness.

class Char:
    def __init__(self, ord: int) -> None:
        assert isinstance(ord, int)
        self.ord = ord
    def __nonzero__(self) -> bool:
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
        return "'" + chr(self.ord)
    def __hash__(self) -> int:
        return hash(self.ord)

Num = Union[int, float]
PdNum = Union[Char, int, float]

def numerify(x: PdNum) -> Union[int, float]:
    if isinstance(x, Char):
        return x.ord
    else:
        return x

def intify(x: PdNum) -> int:
    if isinstance(x, Char):
        return x.ord
    else:
        return int(x)

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

def lift_intify(f: Callable[[int, int], int]) -> Callable[[PdNum, PdNum], PdNum]:
    def inner(a: PdNum, b: PdNum) -> PdNum:
        if isinstance(a, Char) and isinstance(b, Char):
            return Char(f(a.ord, b.ord))
        else:
            return f(intify(a), intify(b))
    return inner

pd_add = lift_numerify(operator.add)
pd_sub = lift_numerify(operator.sub)
pd_mul = lift_numerify(operator.mul)
pd_div = lift_numerify(operator.truediv) # float division!
pd_mod = lift_numerify(operator.mod)
pd_pow = lift_numerify(operator.pow)

pd_intdiv = lift_numerify(operator.floordiv)

pd_and = lift_intify(operator.and_)
pd_or  = lift_intify(operator.or_)
pd_xor = lift_intify(operator.xor)

pd_ceil   = lift_numerify1(lambda x: int(math.ceil(x)))
pd_floor  = lift_numerify1(lambda x: int(math.floor(x)))
pd_abs    = lift_numerify1(abs) # type: ignore
pd_signum = lift_numerify1(lambda x: (x > 0) - (x < 0))

def pd_add_const(a: PdNum, const: int) -> PdNum:
    if isinstance(a, Char):
        return Char(a.ord + const)
    else:
        return a + const

def pd_mul_div_const(a: PdNum, mul: int, div: int) -> PdNum:
    if isinstance(a, Char):
        return Char(a.ord * mul // div)
    else:
        return a * mul / div

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

def pd_factorial(a: PdNum) -> PdNum:
    if isinstance(a, Char):
        return pd_factorial(a.ord)
    elif isinstance(a, int):
        p = 1
        for i in range(1, a + 1): p *= a
        return p
    else:
        return math.gamma(a + 1)
