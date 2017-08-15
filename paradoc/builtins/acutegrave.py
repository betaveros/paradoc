# coding: utf-8
# vim:set expandtab fdm=marker:
from typing import *
import paradoc.num as num
from paradoc.objects import PdObject
from paradoc.builtins.case import Case, CasedBuiltIn

note = """

NOTE: This trailer also works on capital letters, interpreted as
base-36 constants (A = 10 until Z = 35). This is not a syntax special
case; essentially you can imagine there's a family of built-ins with
the right names."""

def ag_document(c: str) -> str:

    if c == 'á':
        return "Add this constant. Deeply vectorizes." + note
    elif c == 'à':
        return "Subtract this constant. Deeply vectorizes." + note
    elif c == 'é':
        return "Takes 2 to the power of this constant." + note
    elif c == 'è':
        return "Squares this constant." + note
    elif c == 'í':
        return "Inverts this constant." + note
    elif c == 'ì':
        return "Negates this constant." + note
    elif c == 'ó':
        return "Multiply by this constant. Deeply vectorizes." + note
    elif c == 'ò':
        return "Divide by this constant. Deeply vectorizes." + note
    elif c == 'ú':
        return "Mod by this constant. Deeply vectorizes." + note
    elif c == 'ù':
        return "Not implemented yet." + note
    elif c == 'ý':
        return "Takes 10 to the power of this constant." + note

    raise NotImplementedError

def ag_convert(c: str, n: int, varname: str) -> PdObject:
    if c == 'á':
        return CasedBuiltIn(varname, [
            Case.value_n2v(lambda e: num.pd_add(e, n)),
        ])
    elif c == 'à':
        return CasedBuiltIn(varname, [
            Case.value_n2v(lambda e: num.pd_sub(e, n)),
        ])
    elif c == 'é':
        return 2 ** n
    elif c == 'è':
        return n ** 2
    elif c == 'í':
        return 1 / n
    elif c == 'ì':
        return -n
    elif c == 'ó':
        return CasedBuiltIn(varname, [
            Case.value_n2v(lambda e: num.pd_mul(e, n)),
            Case.block(lambda env, block:
                pd_foreach_x_only_then_empty_list(env, block, range(n))),
        ])
    elif c == 'ò':
        return CasedBuiltIn(varname, [
            Case.value_n2v(lambda e: num.pd_div(e, n)),
            Case.block(lambda env, block:
                pd_foreach_then_empty_list(env, block, range(n))),
        ])
    elif c == 'ú':
        return CasedBuiltIn(varname, [
            Case.value_n2v(lambda e: num.pd_mod(e, n)),
            Case.block(lambda env, block: [pd_map(env, block, range(n))]),
        ])
    elif c == 'ù':
        raise NotImplementedError('acutegrave: ù not implemented yet')
    elif c == 'ý':
        return 10 ** n

    raise NotImplementedError('unrecognized acute/grave letter ' + repr(c))
