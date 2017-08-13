# coding: utf-8
from typing import *
import paradoc.num as num
from paradoc.objects import PdObject
from paradoc.builtins.case import Case, CasedBuiltIn
from paradoc.builtins.acutegrave import ag_convert

# Paradoc has a few large families of built-in variables that are easier to
# generate lazily (?).

def arithmetic_literal_trigger(varname: str) -> Optional[PdObject]:
    if len(varname) == 1:
        pi = 'ÝÁÉÍÓÚ'.find(varname)
        if pi != -1: return pi # 0, 1 .. 5

        ni = 'ÀÈÌÒÙ'.find(varname)
        if ni != -1: return -1 - ni # -1 .. -5

        return None
    elif len(varname) == 2:
        c1, c2 = varname
        if c2 not in 'áéíóúàèìòùý': return None
        if 'A' <= c1 <= 'Z':
            n = ord(c1) - ord('A') + 10
        elif c1 in 'ÄËÏÖÜŸ':
            n = 2 ** (6 + 'ÄËÏÖÜŸ'.index(c2)) # 64, 128 .. 2048
        else:
            return None

        return ag_convert(c2, n, varname)
    else:
        return None

# vim:set expandtab fdm=marker:
