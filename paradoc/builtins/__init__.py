# coding: utf-8
# vim:set expandtab fdm=marker:
from paradoc.objects import *
# import paradoc.objects
import paradoc.num as num
import paradoc.base as base
import sys, math, collections
from paradoc.builtins.case import Case, CasedBuiltIn

def second_or_error(x: Tuple[object, Optional[PdObject]], error_msg: str) -> PdObject:
    t, t2 = x
    if t2 is None:
        raise AssertionError(error_msg)
    return t2

def initialize_builtins(env: Environment) -> None:

    def put(*ss: str) -> Callable[[Callable[[Environment], None]], None]:
        def inner_put(f: Callable[[Environment], None]) -> None:
            for s in ss:
                env.put(s, BuiltIn(s, f))
        return inner_put

    def cput(name: str, extra_names: List[str], cases: List[Case]) -> None:
        builtin = CasedBuiltIn(name, cases)
        env.put(name, builtin)
        for xname in extra_names: env.put(xname, builtin)

    # Default variables {{{
    env.put('N', '\n')
    env.put(u'Ì', -1)
    env.put(u'Í', 1)
    env.put(u'T', 10)
    env.put(u'E', 11)
    env.put(u'Ñ', '')
    env.put(u'–', ' ')
    env.put('Ee', math.e)
    env.put('Pi', math.pi)
    # }}}
    # Universal functions: stack stuff, list stuff {{{

    @put('Nop', ' ', '\t', '\n', '\r')
    def nop(env: Environment) -> None: pass

    # @put('Dup', ':')
    # def dup(env: Environment) -> None:
    #     a = env.pop()
    #     env.push(a, a)
    cput('Dup', [':'], [Case.any(lambda env, x: [x, x])])
    cput('Dup_pair', ['Dp', '¦'], [Case.any2(lambda env, x, y: [x, y, x, y])])
    cput('Swap', ['\\'], [Case.any2(lambda env, a, b: [b, a])])
    cput('Rotate', ['Rot', '@'], [Case.any3(lambda env, a, b, c: [b, a])])
    cput('Pop', [';'], [Case.any(lambda env, x: [])])
    cput('Pop_under', ['¸'], [Case.any2(lambda env, x, y: [y])])
    cput('Repr', ['`'], [Case.any(lambda env, x: [pd_repr(x)])])
    @put('[', 'Mark')
    def mark(env: Environment) -> None:
        env.mark_stack()
    @put(']', 'Pack')
    def pack(env: Environment) -> None:
        env.push(env.pop_until_stack_marker())
    @put(']_case', ']c')
    def stack_marker_case(env: Environment) -> None:
        case_list = env.pop_until_stack_marker()
        target = env.pop()
        for case in case_list:
            if isinstance(case, list):
                if case:
                    condition, *result = case
                    # TODO: more lenient matching
                    if target == condition:
                        env.push_or_eval(*result)
                        break
                else:
                    raise AssertionError('Empty case')
            else:
                raise AssertionError('Non-list case')
    @put(']_stream', ']s')
    def stack_marker_stream(env: Environment) -> None:
        case_list = env.pop_until_stack_marker()
        target = env.pop()
        for condition, result in zip(case_list[::2], case_list[1::2]):
            # TODO: more lenient matching
            if target == condition:
                env.push_or_eval(result)
                break
    cput('†', [], [Case.any(lambda env, x: [[x]])])
    cput('‡', [], [Case.any2(lambda env, x, y: [[x, y]])])
    # }}}
    # Not {{{
    cput('Not', ['!'], [Case.any(lambda env, x: [int(not x)])])
    # }}}
    # "Arithmetic" inc Octothorpe {{{

    cput('Plus', ['+'], [
        Case.number2(lambda env, a, b: [num.pd_add(a, b)]),
        Case.list2_singleton(lambda env, a, b: [list(a) + list(b)]),
        Case.seq2_singleton(lambda env, a, b: [env.pd_str(a) + env.pd_str(b)]),
        Case.block_seq_range(lambda env, block, seq: [pd_filter(env, block, seq)]),
    ])
    cput('Minus', ['-'], [
        Case.number2(lambda env, a, b: [num.pd_sub(a, b)]),
        # TODO: filter not in
        Case.block_seq_range(lambda env, block, seq: [pd_filter(env, block, seq, negate=True)]),
    ])
    cput('Mul', ['*'], [
        Case.number2(lambda env, a, b: [num.pd_mul(a, b)]),
        Case.number_seq(lambda env, n, seq: [pd_mul_seq(seq, n)]),
        Case.block_seq_range(lambda env, block, seq:
            pd_foreach_x_only_then_empty_list(env, block, seq)),
    ])
    cput('Slash', ['/'], [
        Case.number2(lambda env, a, b: [num.pd_div(a, b)]),
        Case.number_seq(lambda env, n, seq: [pd_split_seq(seq, n, include_leftover=True)]),
        # TODO: split
        Case.block_seq_range(lambda env, block, seq:
            pd_foreach_then_empty_list(env, block, seq)),
    ])
    cput('Intdiv', ['÷'], [
        Case.number2(lambda env, a, b: [num.pd_intdiv(a, b)]),
        Case.number_seq(lambda env, n, seq: [pd_split_seq(seq, n, include_leftover=False)]),
    ])
    cput('Percent', ['%'], [
        Case.number2(lambda env, a, b: [num.pd_mod(a, b)]),
        Case.number_seq(lambda env, n, seq: [seq[::num.intify(n)]]),
        # TODO: split by
        Case.block_seq_range(lambda env, block, seq: [pd_map(env, block, seq)]),
    ])
    cput('Octothorpe', ['#'], [
        Case.number2(lambda env, a, b: [num.pd_pow(a, b)]),
        Case.block_seq_range(lambda env, block, seq:
            [second_or_error(pd_find_entry(env, block, seq),
                "Entry not found in Percent")]),
    ])
    cput('Abs_diff', ['Ad', '±'], [
        Case.number2(lambda env, a, b: [num.pd_abs(num.pd_sub(a, b))]),
    ])
    # }}}
    # Conversions C, F, I, S {{{
    cput('To_char', ['C'], [
        Case.value(lambda env, a: [pd_to_char(a)]),
    ])
    cput('To_float', ['F'], [
        Case.value(lambda env, a: [pd_to_float(a)]),
    ])
    cput('To_int', ['I'], [
        Case.value(lambda env, a: [pd_to_int(a)]),
    ])
    cput('To_string', ['S'], [
        Case.value(lambda env, a: [env.pd_str(a)]),
    ])
    # }}}
    # Sort, $ {{{
    cput('Sort', [], [
        Case.str_(lambda env, s: [''.join(sorted(s))]),
        Case.list_(lambda env, x: [list(sorted(x))]),
    ])
    cput('Dollar', ['$'], [
        Case.number(lambda env, n: [env.index_stack(int(n))]),
        Case.str_(lambda env, s: [''.join(sorted(s))]),
        Case.list_(lambda env, x: [list(sorted(x))]),
    ])
    # }}}
    # Range/enumerate; Comma, J {{{
    range_case = Case.number(lambda env, n: [range(num.intify(n))])
    cput('Range', [], [range_case])
    range_one_case = Case.number(lambda env, n: [range(1, num.intify(n) + 1)])
    cput('Range_one', [], [range_one_case])

    enumerate_case = Case.seq(lambda env, seq: [pd_enumerate(seq)])
    cput('Enumerate', [], [enumerate_case])
    enumerate_one_case = Case.seq(lambda env, seq: [pd_enumerate(seq, start=1)])
    cput('Enumerate_one', [], [enumerate_one_case])
    filter_indexes_case = Case.block_seq_range(lambda env, block, seq: [pd_filter_indexes(env, block, seq)])
    cput('Filter_indexes', [], [filter_indexes_case])

    cput('Comma', [','], [
        range_case,
        enumerate_case,
        filter_indexes_case,
    ])
    cput('J', [], [
        range_one_case,
        enumerate_one_case,
        Case.block_seq_range(lambda env, block, seq: [pd_filter_indexes(env, block, seq, negate=True)]),
    ])
    # }}}
    # Binary operators &|^ {{{
    cput('Vertical_bar', ['|'], [
        Case.number2(lambda env, a, b: [num.pd_or(a, b)]),
        Case.seq2_range(lambda env, a, b: [pd_seq_union(a, b)]),
        Case.condition_block(lambda env, cond, block:
            pd_if_then_empty_list(env, cond, block, negate=True)),
    ])
    cput('Ampersand', ['&'], [
        Case.number2(lambda env, a, b: [num.pd_and(a, b)]),
        Case.seq2_range(lambda env, a, b: [pd_seq_intersection(a, b)]),
        Case.condition_block(lambda env, cond, block:
            pd_if_then_empty_list(env, cond, block)),
    ])
    cput('Exclusive_or', ['^'], [
        Case.number2(lambda env, a, b: [num.pd_xor(a, b)]),
        Case.seq2_range(lambda env, a, b: [pd_seq_symmetric_difference(a, b)]),
    ])
    @put('?', 'If')
    def pd_if(env: Environment) -> None:
        c, b, a = env.pop3()
        if pytruth_eval(env, a):
            # print('True!')
            env.push_or_eval(b)
        else:
            # print('False!')
            env.push_or_eval(c)
    # }}}

    cput('Base', ['B'], [
        Case.number2(lambda env, n, b: [base.to_base_digits(num.intify(b), num.intify(n))]),
        Case.list_number(lambda env, lst, b: [base.from_base_digits(num.intify(b), lst)]),
        Case.str_number(lambda env, s, b: [int(s, b)]),
    ])
    cput('Reduce', ['R'], [
        Case.seq2_singleton(lambda env, seq, joiner: [pd_join(env, seq, joiner)]),
        Case.block_seq_range(lambda env, block, seq: [pd_reduce(env, block, seq)]),
    ])

    # Comparators <=> Max Min {{{
    cput('Equal', ['Eq'], [
        Case.number2(lambda env, a, b: [int(num.numerify(a) == num.numerify(b))]),
        Case.str2(lambda env, a, b: [int(a == b)]),
        Case.list2(lambda env, a, b: [int(list(a) == list(b))]),
    ])
    cput('Equal_sign', ['='], [
        Case.number2(lambda env, a, b: [int(num.numerify(a) == num.numerify(b))]),
        Case.str2(lambda env, a, b: [int(a == b)]),
        Case.list2(lambda env, a, b: [int(list(a) == list(b))]),
        Case.number_seq(lambda env, n, seq: [pd_index(seq, num.intify(n))]),
        Case.block_seq_range(lambda env, block, seq: [pd_get_index(env, block, seq)]),
    ])
    cput('Lt', ['<'], [
        Case.number2(lambda env, a, b: [int(num.numerify(a) < num.numerify(b))]),
        Case.str2(lambda env, a, b: [int(a < b)]),
        Case.list2(lambda env, a, b: [int(list(a) < list(b))]),
        Case.number_seq(lambda env, n, seq: [seq[:num.intify(n)]]),
    ])
    cput('Gt', ['>'], [
        Case.number2(lambda env, a, b: [int(num.numerify(a) > num.numerify(b))]),
        Case.str2(lambda env, a, b: [int(a > b)]),
        Case.list2(lambda env, a, b: [int(list(a) > list(b))]),
        Case.number_seq(lambda env, n, seq: [seq[num.intify(n):]]),
    ])
    cput('Leq', ['<e'], [
        Case.number2(lambda env, a, b: [int(num.numerify(a) <= num.numerify(b))]),
        Case.str2(lambda env, a, b: [int(a <= b)]),
        Case.list2(lambda env, a, b: [int(list(a) <= list(b))]),
        Case.number_seq(lambda env, n, seq: [seq[:num.intify(n)+1]]),
    ])
    cput('Geq', ['>e'], [
        Case.number2(lambda env, a, b: [int(num.numerify(a) >= num.numerify(b))]),
        Case.str2(lambda env, a, b: [int(a >= b)]),
        Case.list2(lambda env, a, b: [int(list(a) >= list(b))]),
        Case.number_seq(lambda env, n, seq: [seq[num.intify(n):]]), # TODO: ?
    ])
    cput('Min', ['<m', 'Õ'], [
        Case.any2(lambda env, a, b: [min(a, b)]), # TODO
    ])
    cput('Max', ['>m', 'Ã'], [
        Case.any2(lambda env, a, b: [max(a, b)]), # TODO
    ])
    cput('List_min', ['<l', 'Œ'], [
        Case.seq(lambda env, e: [min(pd_iterable(e))]),
    ])
    cput('List_max', ['>l', 'Æ'], [
        Case.seq(lambda env, e: [max(pd_iterable(e))]),
    ])
    # }}}
    # «»‹› {{{
    cput('Double_left', ['«'], [
        Case.number(lambda env, a: [num.pd_add_const(a, -2)]),
        Case.seq(lambda env, a: [a[:-1]]),
    ])
    cput('Double_right', ['»'], [
        Case.number(lambda env, a: [num.pd_add_const(a, 2)]),
        Case.seq(lambda env, a: [a[1:]]),
    ])
    head_case = Case.seq(lambda env, a: [pd_index(a, 0)])
    cput('Head', [], [head_case])
    cput('Single_left', ['‹'], [
        Case.number(lambda env, a: [num.pd_floor(a)]),
        head_case,
    ])
    last_case = Case.seq(lambda env, a: [pd_index(a, -1)])
    cput('Last', [], [last_case])
    cput('Single_right', ['›'], [
        Case.number(lambda env, a: [num.pd_ceil(a)]),
        last_case,
    ])
    # }}}
    # Uncons, Unsnoc, Parens() {{{
    decr_case = Case.number(lambda env, a: [num.pd_add_const(a, -1)])
    cput('Decr', [], [decr_case])
    incr_case = Case.number(lambda env, a: [num.pd_add_const(a, 1)])
    cput('Incr', [], [incr_case])
    uncons_case = Case.seq(lambda env, a: [a[1:], pd_index(a, 0)])
    cput('Uncons', [], [uncons_case])
    unsnoc_case = Case.seq(lambda env, a: [a[:-1], pd_index(a, -1)])
    cput('Unsnoc', [], [unsnoc_case])
    cput('(', [], [decr_case, unsnoc_case])
    cput(')', [], [incr_case, uncons_case])
    # }}}
    cput('Sum', ['Š'], [
        Case.list_int_range(lambda env, x: [sum(x)]),
    ])
    cput('Product', ['Þ'], [
        Case.list_int_range(lambda env, x: [functools.reduce(operator.mul, x, 1)]),
    ])

    cput('M', [], [
        Case.number(lambda env, a: [num.pd_mul_div_const(a, -1, 1)]),
        Case.value_seq(lambda env, x, y: [pd_mold(x, y)]),
    ])
    cput('U', [], [
        Case.number(lambda env, a: [num.pd_signum(a)]),
        Case.seq(lambda env, a: [pd_seq_uniquify(a)]),
    ])
    cput('H', [], [
        Case.number2(lambda env, a, b: [num.pd_count_multiplicity_in(b, a)]),
        Case.seq_value(lambda env, s, x: [pd_count_in(env, x, s)]),
    ])
    cput('Reverse', ['Down', 'D'], [
        Case.seq_range(lambda env, a: [a[::-1]]),
    ])
    cput('Zip', [], [
        Case.seq2_range(lambda env, a, b: [pd_zip_as_list(a, b)]),
    ])

    cput('Â', [], [
        Case.number(lambda env, a: [int(num.numerify(a) > 0)]),
        Case.seq(lambda env, a: [int(all(pd_iterable(a)))]),
    ])
    cput('Ê', [], [
        Case.number(lambda env, a: [int(num.numerify(a) % 2 == 0)]),
        Case.seq(lambda env, a: [int(any(pd_iterable(a)))]),
    ])
    cput('Î', [], [
        Case.number(lambda env, a: [int(num.numerify(a) == 1)]),
        Case.seq(lambda env, a: [int(pd_seq_is_identical(a))]),
    ])
    cput('Ô', [], [
        Case.number(lambda env, a: [int(num.numerify(a) % 2 == 1)]),
        Case.seq(lambda env, a: [int(not any(pd_iterable(a)))]),
    ])
    cput('Û', [], [
        Case.number(lambda env, a: [int(num.numerify(a) < 0)]),
        Case.seq(lambda env, a: [int(pd_seq_is_unique(a))]),
    ])
    @put('~')
    def tilde(env: Environment) -> None:
        a = env.pop()
        if isinstance(a, Block):
            a(env)
        elif isinstance(a, str):
            env.evaluate(a)
        elif isinstance(a, (list, range)):
            env.push(*a)
        elif isinstance(a, int):
            env.push(~a)
        else:
            raise NotImplementedError


    @put('Eval')
    def pd_eval(env: Environment) -> None:
        a = env.pop()
        if isinstance(a, str):
            env.evaluate(a)
        else:
            raise NotImplementedError


    # Output and Print {{{
    @put('Output', 'O')
    def pd_output(env: Environment) -> None:
        a = env.pop()
        print(env.pd_str(a), end="")

    @put('Print', 'P')
    def pd_print(env: Environment) -> None:
        a = env.pop()
        print(env.pd_str(a))
    # }}}

    # Abort, Break, Continue {{{
    @put('Abort', 'A')
    def abort(env: Environment) -> None:
        raise PdAbortException("Abort")
    @put('Abort_with', 'Aw')
    def abort_with(env: Environment) -> None:
        e = env.pop()
        if isinstance(e, (int, float, Char)):
            raise PdAbortException("Abort", num.intify(e))
        else:
            print("Abort: " + str(e), file=sys.stderr)
            raise PdAbortException(str(e), 1)

    @put('Break', 'Quit_loop', 'Q')
    def break_(env: Environment) -> None:
        raise PdBreakException('Break')
    @put('Continue', 'Keep_going', 'K')
    def continue_(env: Environment) -> None:
        raise PdContinueException('Continue')
    # }}}

    @put('Fc', 'Factorial')
    def factorial(env: Environment) -> None:
        a = env.pop()
        assert isinstance(a, (float, int))
        p = 1
        for x in range(1, int(a) + 1): p *= x
        env.push(p)

    # Square, Cube {{{
    @put('Square', 'Sq', '²')
    def square(env: Environment) -> None:
        a = env.pop()
        assert isinstance(a, (Char, float, int))
        env.push(num.pd_power_const(a, 2))

    @put('Cube', 'Cb', '³')
    def cube(env: Environment) -> None:
        a = env.pop()
        assert isinstance(a, (Char, int, float))
        env.push(num.pd_power_const(a, 3))
    # }}}

    @put('Ao', 'Antirange_one')
    def antirange_one(env: Environment) -> None:
        a = env.pop()
        assert isinstance(a, int)
        env.push(range(a, 0, -1))


    @put('¤', 'Currency')
    def pd_currency(env: Environment) -> None:
        a = env.pop()
        if isinstance(a, (Char, int, float)):
            b = pd_to_list_range(env.pop())
            env.push(b[:num.intify(a)], b[num.intify(a):])
        elif isinstance(a, (str, list, range)):
            env.push(a[:len(a)//2], a[len(a)//2:])
        else:
            raise NotImplementedError(repr(a))

    # Constant fractions {{{
    def pd_constant_fraction_cases(p: int, q: int) -> List[Case]:
        # Cannot sensibly handle improper fractions p/q > 1 if q > 1.
        return [
            Case.number(lambda env, a: [num.pd_mul_div_const(a, p, q)]),
            Case.seq(lambda env, a: [a[:len(a)*p//q] if p <= q else pd_mul_seq(a, p)]),
            Case.block(lambda env, b:
                pd_run_with_probability_then_empty_list(env, b, p/q)
                if p <= q else
                pd_foreach_x_only_then_empty_list(env, b, range(p))
            ),
        ]
    cput('Halve', ['½'], pd_constant_fraction_cases(1, 2))
    cput('Quarter', ['¼'], pd_constant_fraction_cases(1, 4))
    cput('Three_quarters', ['¾'], pd_constant_fraction_cases(3, 4))
    cput('Double', ['×'], pd_constant_fraction_cases(2, 1))
    # }}}

    @put('L', 'Length')
    def pd_ell(env: Environment) -> None:
        a = env.pop()
        if isinstance(a, (int, float)):
            env.push(abs(a))
        elif isinstance(a, (str, list, range)):
            env.push(len(a))
        else:
            raise NotImplementedError

    @put('Od', 'Odd')
    def pd_odd(env: Environment) -> None:
        a = env.pop()
        assert not isinstance(a, Block)
        env.push(pynumber_length(a) % 2 != 0)
    @put('Ev', 'Even')
    def pd_even(env: Environment) -> None:
        a = env.pop()
        assert not isinstance(a, Block)
        env.push(pynumber_length(a) % 2 == 0)

    # Other predicates {{{
    cput('Positive',         ['+p'], [Case.value(lambda env, x: [pd_deepmap_n2n(lambda e: int(e >  0), x)])])
    cput('Negative',         ['-p'], [Case.value(lambda env, x: [pd_deepmap_n2n(lambda e: int(e <  0), x)])])
    cput('Positive_or_zero', ['+o'], [Case.value(lambda env, x: [pd_deepmap_n2n(lambda e: int(e >= 0), x)])])
    cput('Negative_or_zero', ['-o'], [Case.value(lambda env, x: [pd_deepmap_n2n(lambda e: int(e <= 0), x)])])
    # }}}
    # Dumping Python's math {{{
    cput('Sin',     ['Sn'], [Case.value(lambda env, x: [pd_deepmap_n2n(math.sin  , x)])])
    cput('Cos',     ['Cs'], [Case.value(lambda env, x: [pd_deepmap_n2n(math.cos  , x)])])
    cput('Tan',     ['Tn'], [Case.value(lambda env, x: [pd_deepmap_n2n(math.tan  , x)])])
    cput('Asin',    ['As'], [Case.value(lambda env, x: [pd_deepmap_n2n(math.asin , x)])])
    cput('Acos',    ['Ac'], [Case.value(lambda env, x: [pd_deepmap_n2n(math.acos , x)])])
    cput('Atan',    ['At'], [Case.value(lambda env, x: [pd_deepmap_n2n(math.atan , x)])])
    cput('Log_e',   ['Ln'], [Case.value(lambda env, x: [pd_deepmap_n2n(math.log  , x)])])
    cput('Log_ten', ['Lt'], [Case.value(lambda env, x: [pd_deepmap_n2n(math.log10, x)])])
    cput('Log_two', ['Lg'], [Case.value(lambda env, x: [pd_deepmap_n2n(math.log2 , x)])])
    # }}}

    cput('Replicate', ['ˆ'], [
        Case.any_number(lambda env, x, n: [pd_replicate(x, num.intify(n))]),
    ])
    cput('Signed_replicate', ['Sr'], [
        Case.any_any_number(lambda env, x, y, n: [
            pd_replicate(y, num.intify(n))
            if num.intify(n) >= 0 else
            pd_replicate(x, -num.intify(n))
        ]),
    ])

    cput('Key_new', ['Kn'], [
        Case.list_list_singleton_value(lambda env, kvs, dims, filler: [pd_new_array(kvs, dims, filler)]),
    ])
    cput('Key_map', ['Km'], [
        Case.list_list_block(lambda env, arr, ks, func: [pd_array_keys_map(env, arr, ks, func)]),
    ])
    cput('Key_get', ['Kg'], [
        Case.list_list_singleton(lambda env, arr, k: [pd_array_key_get(arr, k)]),
    ])

    cput('Space_join', ['Sj'], [
        Case.seq_range(lambda env, seq: [' '.join(env.pd_str(e) for e in pd_iterable(seq))]),
    ])

    cput('Permutations', ['¡'], [
        Case.number(lambda env, n: [num.pd_factorial(n)]),
        Case.seq(lambda env, seq:
            [list(itertools.permutations(pd_iterable(seq)))]),
        Case.block_seq_range(lambda env, block, seq:
            [pd_map_iterable(env, block,
                map(list, itertools.permutations(pd_iterable(seq))))]),
    ])
    cput('Subsequences', ['¿'], [
        Case.number(lambda env, n: [2 ** num.numerify(n)]),
        Case.seq(lambda env, seq: [pd_subsequences_list(seq)]),
        Case.block_seq_range(lambda env, block, seq:
            [pd_map_iterable(env, block,
                pd_subsequences(seq))]),
    ])

    @put('Debug', 'Dump')
    def dump(env: Environment) -> None:
        print('Dump:', env.debug_dump(), file=sys.stderr)

