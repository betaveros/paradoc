# coding: utf-8
# vim:set expandtab fdm=marker:
from typing import *
import paradoc.num as num
from paradoc.objects import PdObject
from paradoc.builtins.case import Case, CasedBuiltIn

def ag_convert(c: str, n: int, varname: str) -> PdObject:
    if c == 'á':
        return CasedBuiltIn(varname, [
            Case.number(lambda env, a: [num.pd_add(a, n)]),
        ])
    elif c == 'à':
        return CasedBuiltIn(varname, [
            Case.number(lambda env, a: [num.pd_sub(a, n)]),
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
            Case.number(lambda env, a: [num.pd_mul(a, n)]),
            Case.seq(lambda env, seq: [pd_mul_seq(seq, n)]),
            Case.block(lambda env, block:
                pd_foreach_x_only_then_empty_list(env, block, range(n))),
        ])
    elif c == 'ò':
        return CasedBuiltIn(varname, [
            Case.number(lambda env, a: [num.pd_div(a, n)]),
            Case.seq(lambda env, seq: [pd_split_seq(seq, n, include_leftover=True)]),
            Case.block(lambda env, block:
                pd_foreach_then_empty_list(env, block, seq)),
        ])
    elif c == 'ú':
        return CasedBuiltIn(varname, [
            Case.number(lambda env, a: [num.pd_mod(a, n)]),
            Case.seq(lambda env, seq: [seq[::num.intify(n)]]),
            Case.block(lambda env, block: [pd_map(env, block, range(n))]),
        ])
    elif c == 'ù':
        raise NotImplementedError('acutegrave: ù not implemented yet')
    elif c == 'ý':
        return 10 ** n

    raise NotImplementedError('unrecognized acute/grave letter ' + repr(c))
