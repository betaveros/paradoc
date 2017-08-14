# coding: utf-8
# vim:set expandtab fdm=marker:
from typing import *
import paradoc.num as num
from paradoc.objects import PdObject
from paradoc.builtins.case import Case, CasedBuiltIn

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
