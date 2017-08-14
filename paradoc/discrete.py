# coding: utf-8
from typing import *
import math
# Discrete math: combinatorial and number-theoretic functions. Really just
# lazy imports in case you want to grab paradoc and not install sympy; I
# don't know if this is a good idea.

def is_prime_as_int(n0: Union[int, float]) -> int:
    n = int(n0)
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

def prev_prime(n: Union[int, float]) -> int:
    try:
        from sympy.ntheory.generate import prevprime
    except ModuleNotFoundError:
        raise Exception("Install sympy to use number-theoretic functions!")
    return prevprime(n) # exclusive of n

def next_prime(n: Union[int, float]) -> int:
    try:
        from sympy.ntheory.generate import nextprime
    except ModuleNotFoundError:
        raise Exception("Install sympy to use number-theoretic functions!")
    return nextprime(n) # exclusive of n

def prime_factorization(n: int) -> List[Tuple[int, int]]:
    try:
        from sympy.ntheory.factor_ import factorint
    except ModuleNotFoundError:
        raise Exception("Install sympy to use number-theoretic functions!")
    factor_dict = factorint(n)
    return sorted(factor_dict.items())

def prime_factorization_wrapped(n: Union[int, float]) -> List[List[int]]:
    return list(list(e) for e in prime_factorization(int(n)))

def prime_factorization_flat(n: Union[int, float]) -> List[int]:
    return [x for (x, e) in prime_factorization(int(n)) for _ in range(e)]

def totient(n: Union[int, float]) -> int:
    try:
        import sympy.ntheory.factor_ as f_
    except ModuleNotFoundError:
        raise Exception("Install sympy to use number-theoretic functions!")
    return f_.totient(int(n))

def jacobi_symbol(m: Union[int, float], n: Union[int, float]) -> int:
    try:
        import sympy.ntheory.residue_ntheory as rn
    except ModuleNotFoundError:
        raise Exception("Install sympy to use number-theoretic functions!")
    return rn.jacobi_symbol(int(m), int(n))

@overload
def factorial(n: int) -> int: ...
@overload
def factorial(n: float) -> float: ...

def factorial(n: Union[int, float]) -> Union[int, float]:
    try:
        import sympy.functions.combinatorial.factorials as fs
    except ModuleNotFoundError:
        if isinstance(n, int):
            p = 1
            for i in range(1, n + 1): p *= n
            return p
        else:
            return math.gamma(n + 1)

    return fs.factorial(n)

def binomial_coefficient(n: Union[int, float], k: Union[int, float]) -> Union[int, float]:
    try:
        import sympy.functions.combinatorial.factorials as fs
    except ModuleNotFoundError:
        if isinstance(n, int) and isinstance(k, int):
            return factorial(n) // factorial(k) // factorial(n-k)
        else:
            return factorial(n) / factorial(k) / factorial(float(n)-float(k))

    if isinstance(n, int) and isinstance(k, int):
        return fs.binomial(n, k)
    else:
        return fs.binomial(float(n), k)

def fibonacci(n: Union[int, float]) -> Union[int, float]:
    try:
        import sympy.functions.combinatorial.numbers as ns
    except ModuleNotFoundError:
        raise Exception("Install sympy to use number-theoretic functions!")
    return ns.fibonacci(n)
