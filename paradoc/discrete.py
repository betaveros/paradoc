# coding: utf-8
# vim:set ts=4 sw=4 et:
from typing import Union, List, Tuple, overload
import math
# Discrete math: combinatorial and number-theoretic functions. Really just
# lazy imports in case you want to grab paradoc and not install sympy; I
# don't know if this is a good idea.

def cint(x: Union[int, float, complex]) -> int:
    return int(x.real)

def is_prime_as_int(n0: Union[int, float, complex]) -> int:
    n = cint(n0)
    if n != n0: return 0
    try:
        from sympy.ntheory.primetest import isprime
    except ModuleNotFoundError:
        raise Exception("Install sympy to use number-theoretic functions!")
    # Note: If it ever matters, nonpositive integers are not prime.
    return int(isprime(n))

def nth_prime(n: int) -> int:
    try:
        from sympy.ntheory.generate import prime
    except ModuleNotFoundError:
        raise Exception("Install sympy to use number-theoretic functions!")
    # prime(1) = 2 etc.
    return prime(n)

def prev_prime(n: Union[int, float, complex]) -> int:
    try:
        from sympy.ntheory.generate import prevprime
    except ModuleNotFoundError:
        raise Exception("Install sympy to use number-theoretic functions!")
    return prevprime(n.real) # exclusive of n

def next_prime(n: Union[int, float, complex]) -> int:
    try:
        from sympy.ntheory.generate import nextprime
    except ModuleNotFoundError:
        raise Exception("Install sympy to use number-theoretic functions!")
    return nextprime(n.real) # exclusive of n

def prime_factorization(n: int) -> List[Tuple[int, int]]:
    try:
        from sympy.ntheory.factor_ import factorint
    except ModuleNotFoundError:
        raise Exception("Install sympy to use number-theoretic functions!")
    factor_dict = factorint(n)
    return sorted(factor_dict.items())

def prime_factorization_wrapped(n: Union[int, float, complex]) -> List[List[int]]:
    return list(list(e) for e in prime_factorization(cint(n)))

def prime_factorization_flat(n: Union[int, float, complex]) -> List[int]:
    return [x for (x, e) in prime_factorization(cint(n)) for _ in range(e)]

def totient(n: Union[int, float, complex]) -> int:
    try:
        import sympy.ntheory.factor_ as f_
    except ModuleNotFoundError:
        raise Exception("Install sympy to use number-theoretic functions!")
    return f_.totient(cint(n))

def jacobi_symbol(m: Union[int, float], n: Union[int, float]) -> int:
    try:
        import sympy.ntheory.residue_ntheory as rn
    except ModuleNotFoundError:
        raise Exception("Install sympy to use number-theoretic functions!")
    return rn.jacobi_symbol(cint(m), cint(n))

@overload
def factorial(n: int) -> int: ...
@overload
def factorial(n: float) -> float: ...
@overload
def factorial(n: complex) -> float: ...

def factorial(n: Union[int, float, complex]) -> Union[int, float, complex]:
    try:
        import sympy.functions.combinatorial.factorials as fs
    except ModuleNotFoundError:
        if isinstance(n, int):
            p = 1
            for i in range(1, n + 1): p *= i
            return p
        elif isinstance(n, float):
            return math.gamma(n + 1)
        else:
            raise Exception("Can't take factorial of complex number (install sympy)")

    if isinstance(n, int):
        return int(fs.factorial(n))
    elif isinstance(n, float):
        return float(fs.factorial(n))
    else:
        return complex(fs.factorial(n)) # type: ignore # seems to work...

def binomial_coefficient(n: Union[int, float, complex], k: Union[int, float, complex]) -> Union[int, float, complex]:
    try:
        import sympy.functions.combinatorial.factorials as fs
    except ModuleNotFoundError:
        if isinstance(n, int) and isinstance(k, int):
            return factorial(n) // factorial(k) // factorial(n-k)
        elif isinstance(n, (int, float)) and isinstance(k, (int, float)):
            return factorial(n) / factorial(k) / factorial(float(n)-float(k))
        else:
            raise Exception("Can't take binomial coefficient of complex number (install sympy)")

    if isinstance(n, int) and isinstance(k, int):
        return int(fs.binomial(n, k))
    elif isinstance(n, (int, float)) and isinstance(k, (int, float)):
        return float(fs.binomial(float(n), k))
    else:
        return complex(fs.binomial(complex(n), k)) # type: ignore # seems to work...

def fibonacci(n: Union[int, float]) -> Union[int, float]:
    try:
        import sympy.functions.combinatorial.numbers as ns
    except ModuleNotFoundError:
        raise Exception("Install sympy to use number-theoretic functions!")
    return ns.fibonacci(n)

# vim:set tabstop=4 shiftwidth=4 expandtab fdm=marker:
