# coding: utf-8
from paradoc.objects import *
from typing import Callable, List, Optional, Tuple
import itertools
import paradoc.num as num
import paradoc.base as base
import paradoc.assign as assign
import sys, math
import time, datetime
import random
import operator, functools
from paradoc.builtins.case import Case, CasedBuiltIn
from paradoc.builtins.lazy_vars import arithmetic_literal_trigger
from paradoc.string import str_class, case_double
import paradoc.discrete as discrete

def second_or_error(x: Tuple[object, Optional[PdObject]], error_msg: str) -> PdObject:
    t, t2 = x
    if t2 is None:
        raise AssertionError(error_msg)
    return t2

def initialize_builtins(env: Environment, sandboxed: bool, debug: bool) -> None:

    def put(*ss: str,
            docs: Optional[str] = None,
            stability: str = "unstable") -> Callable[[Callable[[Environment], None]], None]:
        name = ss[0]
        aliases = list(ss)
        def inner_put(f: Callable[[Environment], None]) -> None:
            for s in ss:
                env.put(s, BuiltIn(name, f, aliases=aliases,
                    docs=docs, stability=stability), fail_if_overwrite=True)
        return inner_put

    def cput(name: str,
            extra_names: List[str],
            cases: List[Case],
            docs: Optional[str] = None,
            stability: str = "unstable") -> None:
        builtin = CasedBuiltIn(name, cases, aliases = [name] + extra_names,
                docs=docs, stability=stability)
        env.put(name, builtin, fail_if_overwrite=True)
        for xname in extra_names: env.put(xname, builtin, fail_if_overwrite=True)

    # Default variables {{{
    env.put('N', '\n', docs="Output record separator", stability="stable")
    env.put(u'T', 10, docs="Utility constant: ten", stability="stable")
    env.put(u'E', 11, docs="Utility constant: eleven", stability="stable")
    env.put(u'Ñ', '', docs="Output field separator", stability="stable")
    env.put('Ee', math.e, stability="beta")
    env.put('Ep', 1e-9, docs="Epsilon for approximate tests", stability="beta")
    env.put('Pi', math.pi, stability="stable")

    golden_ratio = (1 + math.sqrt(5)) / 2
    env.put('Ph',  golden_ratio, docs="Golden ratio", stability="alpha")
    env.put('Phi', golden_ratio, stability="alpha")

    env.put('Da', str_class('0-9'), docs="Digit alphabet", stability="alpha")
    env.put('Ua', str_class('A-Z'), docs="Uppercase alphabet", stability="alpha")
    env.put('La', str_class('a-z'), docs="Lowercase alphabet", stability="alpha")
    env.put('Aa', str_class('A-Za-z'), docs="Alphabet", stability="alpha")

    # Non-breaking space (U+00A0)
    env.put('\xa0', ' ', docs="Utility constant: space", stability="alpha")
    env.put('␣', ' ', docs="Utility constant: space", stability="alpha")

    env.put('Å', str_class('A-Z'), docs="Uppercase alphabet alias", stability="alpha")
    env.put('Åa', str_class('a-zA-Z'), stability="alpha")
    env.put('Åb', case_double('BCDFGHJKLMNPQRSTVWXZ'), stability="alpha")
    env.put('Åc', case_double('BCDFGHJKLMNPQRSTVWXYZ'), stability="alpha")
    env.put('Åd', str_class('9-0'), stability="alpha")
    env.put('Åf', str_class('A-Za-z0-9+/'), stability="alpha")
    env.put('Åh', str_class('0-9A-F'), stability="alpha")
    env.put('Åi', str_class('A-Za-z0-9_'), stability="alpha")
    env.put('Åj', str_class('a-zA-Z0-9_'), stability="alpha")
    env.put('Ål', str_class('z-a'), stability="alpha")
    env.put('Åm', '()<>[]{}', stability="alpha")
    env.put('Åp', str_class(' -~'), stability="alpha")
    env.put('Åq', case_double('QWERTYUIOP'), stability="alpha")
    env.put('Ås', case_double('ASDFGHJKL'), stability="alpha")
    env.put('Åu', str_class('Z-A'), stability="alpha")
    env.put('Åv', case_double('AEIOU'), stability="alpha")
    env.put('Åx', case_double('ZXCVBNM'), stability="alpha")
    env.put('Åy', case_double('AEIOUY'), stability="alpha")
    env.put('Åz', str_class('z-aZ-A'), stability="alpha")

    env.put('Debug', int(debug),
            docs="""A variable tested to see whether debugging output in the
            program should be enabled.""",
            stability="alpha")

    env.put('\x00', 0, stability="unstable")
    env.put('\x01', 1, stability="unstable")

    env.put('Hw', 'Hello, World!', stability="unstable")

    BULLET = '•'

    env.put(BULLET, 0,
            docs="""A utility variable assigned to by {{ 'Assign_bullet'|b }}
            and {{ 'Assign_bullet_destructive'|b }}. Initialized to 0.""",
            stability="alpha")
    # }}}
    # Universal functions: stack stuff, list stuff {{{

    @put('Nop', ' ', '\t', '\n', '\r',
            docs="Do nothing.", stability="stable")
    def nop(env: Environment) -> None: pass

    # @put('Dup', ':')
    # def dup(env: Environment) -> None:
    #     a = env.pop()
    #     env.push(a, a)
    cput('Dup', [':'], [Case.any(lambda env, x: [x, x])],
            docs="""Duplicate the top element of the stack.

            ex: 1 2 3 : => 1 2 3 3""",
            stability="stable")
    cput('Dup_pair', [':p', '¦'], [Case.any2(lambda env, a, b: [a, b, a, b])],
            docs="""Duplicate the top two elements of the stack: a b -> a b a b

            ex: 1 2 3 :p => 1 2 3 2 3""",
            stability="beta")
    cput('Dup_around', [':a'], [Case.any2(lambda env, a, b: [a, b, a])],
            docs="""Duplicate the second element of the stack onto the top: a b
            -> a b a

            ex: 1 2 3 :a => 1 2 3 2""",
            stability="alpha")
    cput('Swap', ['\\'], [Case.any2(lambda env, a, b: [b, a])],
            docs="""Swap the top two elements of the stack.

            ex: 1 2 3\ => 1 3 2""",
            stability="stable")
    cput('Swap_around', ['\\a'], [Case.any3(lambda env, a, b, c: [c, b, a])],
            docs="""Swap the first and third elements of the stack (swap
            "around" the second one).

            ex: 1 2 3\\a => 3 2 1""",
            stability="alpha")
    cput('Rotate', ['Rot', 'Ro'], [Case.any3(lambda env, a, b, c: [b, c, a])],
            docs="""Rotate the top three elements of the stack so that the 3rd
            from the top is now on top: a b c -> b c a

            ex: 1 2 3Ro => 2 3 1""",
            stability="beta")
    cput('Unrotate', ['Unrot', 'Ur'], [Case.any3(lambda env, a, b, c: [c, a, b])],
            docs="""Rotate the top three elements of the stack so that the
            top is now on bottom: a b c -> c a b

            ex: 1 2 3Ur => 3 1 2""",
            stability="beta")
    cput('Pop', [';'], [Case.any(lambda env, x: [])],
            docs="""Pop the top element of the stack.

            ex: 1 2 3; => 1 2""",
            stability="stable")
    cput('Pop_under', ['¸'], [Case.any2(lambda env, x, y: [y])],
            docs="""Pop the second from the top element of the stack.

            ex: 1 2 3¸ => 1 3""",
            stability="beta")
    cput('Repr', ['`'], [Case.any(lambda env, x: [pd_repr(x)])],
            docs="Push the string Paradoc representation of the top element.",
            stability="beta")
    @put('[', 'Mark', docs="Mark the stack.", stability="stable")
    def mark(env: Environment) -> None:
        env.mark_stack()
    @put(']', 'Pack',
            docs="Pack the elements above the last stack mark into a list.",
            stability="stable")
    def pack(env: Environment) -> None:
        env.push(env.pop_until_stack_marker())
    @put('¬', 'Pack_reverse', 'Pack_down',
            docs="""Pack the elements above the last stack mark into a list in
            reverse order.

            ex: [1 2 3¬ => [3 2 1]""",
            stability="beta")
    def pack_reverse(env: Environment) -> None:
        env.push(env.pop_until_stack_marker()[::-1])
    @put(']_case', ']c', stability="beta")
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
    @put(']_stream', ']s', stability="alpha")
    def stack_marker_stream(env: Environment) -> None:
        case_list = env.pop_until_stack_marker()
        target = env.pop()
        for condition, result in zip(case_list[::2], case_list[1::2]):
            # TODO: more lenient matching
            if target == condition:
                env.push_or_eval(result)
                break
    cput('†', [], [Case.any(lambda env, x: [[x]])],
            docs="""Pack the top element of the stack into a list by itself.

            ASCII alternative: 1_array; see {{ 'array'|it }}.

            ex: 1 2 3† => 1 2 [3]""",
            stability="beta")
    cput('‡', [], [Case.any2(lambda env, x, y: [[x, y]])],
            docs="""Pack the top two elements of the stack into a list.

            ASCII alternative: 2_array; see {{ 'array'|it }}.

            ex: 1 2 3‡ => 1 [2 3]""",
            stability="beta")
    # }}}
    # Not {{{
    cput('Not', ['!'], [Case.any(lambda env, x: [int(not x)])],
            docs="""Logical NOT: 0 and empty lists/strings yield 1, everything else yields 0.

            ex: 0! => 1
            1! => 0
            2! => 0
            []! => 1
            [0]! => 0""",
            stability="stable")
    # }}}
    # "Arithmetic" {{{

    cput('Plus_or_filter', ['+'], [
        Case.number2(lambda env, a, b: [num.pd_add(a, b)]),
        Case.list2_singleton(lambda env, a, b: [list(a) + list(b)]),
        Case.seq2_singleton(lambda env, a, b: [env.pd_str(a) + env.pd_str(b)]),
        Case.block_seq_range(lambda env, block, seq: [pd_filter(env, block, seq)]),
    ],
            docs="""Addition on numbers. Concatenation on lists and strings
            (numbers coerce to single-element lists or to strings). Filter on
            block and list (numbers coerce to ranges).""",
            stability="stable")

    cput('Minus_or_reject', ['-'], [
        Case.number2(lambda env, a, b: [num.pd_sub(a, b)]),
        Case.seq2_singleton(lambda env, a, b: [pd_seq_difference(a, b)]),
        Case.block_seq_range(lambda env, block, seq: [pd_filter(env, block, seq, negate=True)]),
    ],
            docs="""Subtraction on numbers. Filter-not-in on lists and strings
            (numbers coerce to single-element lists). Filter-not on block and
            list (numbers coerce to ranges). See also {{ 'Antiminus'|b }}.""",
            stability="stable")

    cput('Antiminus', ['¯'], [
        Case.number2(lambda env, a, b: [num.pd_sub(b, a)]),
        Case.seq2_singleton(lambda env, a, b: [pd_seq_difference(b, a)]),
        Case.block_seq_range(lambda env, block, seq: [pd_filter(env, block, seq, negate=True)]),
    ],
            docs="""Reversed subtraction. Compare
            {{ 'Minus_or_reject'|b }}.""",
            stability="beta")

    cput('Mul_or_xloop', ['*'], [
        Case.number2(lambda env, a, b: [num.pd_mul(a, b)]),
        Case.number_seq(lambda env, n, seq: [pd_mul_seq(seq, n)]),
        Case.seq2(lambda env, a, b: [pd_cartesian_product_seq_matrix(a, b)]),
        Case.block_seq_range(lambda env, block, seq:
            pd_foreach_x_only_then_empty_list(env, block, seq)),
    ],
            docs="""Multiplication on numbers. Repetition on sequences with
            numbers. Cartesian product on two sequences. X-loop on blocks and
            sequences (numbers coerce to ranges, so, if you don't use the
            variable X, it's just repeating a block some number of times.)

            See also {{ 'xloop'|bt }}.

            ex: 3 {2*} 4* => 48
            {X} 4* => 0 1 2 3
            [2 3 5 7] {2X#} * => 4 8 32 128""",
            stability="stable")

    cput('Div_or_split_or_each', ['/'], [
        Case.number2(lambda env, a, b: [num.pd_div(a, b)]),
        Case.number_seq(lambda env, n, seq: [pd_split_seq(seq, n, include_leftover=True)]),
        Case.seq2(lambda env, seq, tok: [pd_split_seq_by(seq, tok)]),
        Case.block_seq_range(lambda env, block, seq:
            pd_foreach_then_empty_list(env, block, seq)),
    ],
            docs="""Float division on numbers. On a sequence and number, split
            the sequence into chunks of size equal to the number, including
            leftovers if any. On two sequences, split the first sequence around
            occurrences of the second sequence. For-each on blocks and
            sequences (numbers coerce to ranges).

            See also {{ 'Intdiv_or_split_discard'|b }}.

            ex:
            [1 2 3 4]2/ => [[1 2][3 4]]
            [1 2 3 4 5]2/ => [[1 2][3 4][5]]
            "tweedledee""e"% => ["tw" "" "dl" "d" "" ""]
            """,
            stability="stable")

    cput('Intdiv_or_split_discard', ['÷'], [
        Case.number2(lambda env, a, b: [num.pd_intdiv(a, b)]),
        Case.number_seq(lambda env, n, seq: [pd_split_seq(seq, n, include_leftover=False)]),
    ],
            docs="""Integer division on numbers. On a sequence and number,
            split the sequence into chunks of size equal to the number,
            discarding leftovers.

            ex: [1 2 3 4]2/ => [[1 2][3 4]]
            [1 2 3 4 5]2/ => [[1 2][3 4]]
            """,
            stability="beta")

    cput('Mod_or_slice_mod_or_split_nonempty_or_map', ['%'], [
        Case.number2(lambda env, a, b: [num.pd_mod(a, b)]),
        Case.number_seq(lambda env, n, seq: [seq[::num.intify(n)]]),
        Case.seq2(lambda env, seq, tok: [[s for s in pd_split_seq_by(seq, tok) if s]]),
        Case.block_seq_range(lambda env, block, seq: [pd_map(env, block, seq)]),
    ],
            docs="""Modulus on numbers. On a sequence and number, slice
            elements at indices equal to 0 mod the number, just like Python
            s[::n] (negative numbers reverse the sequence). On two sequences,
            split the first sequence around occurrences of the second sequence,
            discarding empty tokens. Map on blocks and sequences (numbers
            coerce to ranges).

            ex: "tweedledee""e"% => ["tw" "dl" "d"]
            """,
            stability="stable")

    cput('Divmod_or_map_product', ['‰', '%p'], [
        Case.number2(lambda env, a, b: [num.pd_intdiv(a, b), num.pd_mod(a, b)]),
        Case.seq2_range_block(lambda env, seq1, seq2, block:
            [pd_map_product(env, block, seq1, seq2)])
    ],
            docs="""On integers, integer division and modulus. On a block, map
            over the Cartesian product of the previous two sequences (numbers
            coerce to ranges).""",
            stability="unstable")

    cput('Power', ['ˆ', '*p'], [
        Case.number2(lambda env, a, b: [num.pd_pow(a, b)]),
        Case.number_seq(lambda env, n, s: [pd_pow_seq(s, n)]),
    ],
            docs="""On numbers, power/exponentiate. On a list and a number,
            exponentiate the list by making a list of all lists of that length
            composed of elements from the original list (possibly repeating).
            """,
            stability="alpha")

    cput('Int_sqrt', ['Si'], [
        Case.number(lambda env, a: [int(num.numerify(a) ** 0.5)]),
    ],
            docs="""Integer square root.""",
            stability="alpha")

    cput('Find_index', ['@'], [
        Case.number_seq(lambda env, n, seq:
            [pd_find_index(env, n, seq)]),
        Case.seq2(lambda env, haystack, needle:
            [pd_find_substring_index(env, needle, haystack)]),
        Case.block_seq_range(lambda env, block, seq:
            [pd_get_index(env, block, seq)]),
    ],
            docs="""Inside a sequence (numbers coerce to ranges), find the
            first index of an element, a substring, or something satisfying a
            block. Mnemonic: finds where the element is AT.""",
            stability="alpha")

    cput('Abs_diff', ['Ad', '±'], [
        Case.number2(lambda env, a, b: [num.pd_abs(num.pd_sub(a, b))]),
    ],
            docs="""Absolute difference.""",
            stability="stable")

    cput('Plus_ints', ['+i'], [
        Case.int2_coerce(lambda env, a, b: [a + b]),
    ],
            docs="""Add two things after coercing both to integers. """,
            stability="alpha")
    cput('Plus_lengths', ['+l'], [
        Case.number2_len(lambda env, a, b: [num.pd_add(a, b)]),
    ],
            docs="""Subtract two things after coercing both to ints or floats,
            sequences by taking their length.""",
            stability="unstable")
    cput('Minus_ints', ['-i'], [
        Case.int2_coerce(lambda env, a, b: [a - b]),
    ],
            docs="""Subtract two things after coercing both to integers.""",
            stability="unstable")
    cput('Minus_lengths', ['-l'], [
        Case.number2_len(lambda env, a, b: [num.pd_sub(a, b)]),
    ],
            docs="""Subtract two things after coercing both to ints or floats,
            sequences by taking their length.""",
            stability="unstable")

    cput('Translate', ['Tr'], [
        Case.seq3_singleton(lambda env, seq, src, tgt: [pd_translate(seq, src, tgt)]),
    ],
            docs="""Translate the first argument using a mapping obtained by
            zipping the second and third, repeading the last element of the
            third as necessary.""",
            stability="alpha")
    # }}}
    # Acute/grave vowels {{{
    cput('Plus_deep_vectorizing', ['Á'], [
        Case.value2(lambda env, a, b: [pd_deepvectorize_nn2v(num.pd_add, a, b)]),
    ],
            docs="""Addition on numbers; deeply vectorizes.""",
            stability="unstable")
    cput('Minus_deep_vectorizing', ['À'], [
        Case.value2(lambda env, a, b: [pd_deepvectorize_nn2v(num.pd_sub, a, b)]),
    ],
            docs="""Subraction on numbers; deeply vectorizes.""",
            stability="unstable")
    cput('Two_power_vectorizing', ['É'], [Case.value_n2v(lambda e: 2**e)],
            docs="""Two to the power of numbers. Deeply vectorizes.""",
            stability="alpha")
    cput('Square_deep', ['È'], [Case.value_n2v(lambda e: e**2)],
            docs="""Square of numbers. Deeply vectorizes.""",
            stability="alpha")
    cput('Inverse', ['Í'], [Case.value_n2v(lambda e: 1/e)],
            docs="""Inverse (reciprocal) of numbers. Deeply vectorizes.""",
            stability="alpha")
    cput('Negate_deep', ['Ì'], [Case.value_n2v(lambda e: -e)],
            docs="""Negate numbers. Deeply vectorizes.""",
            stability="alpha")
    cput('Multiply_deep_vectorizing', ['Ó'], [
        Case.value2(lambda env, a, b: [pd_deepvectorize_nn2v(num.pd_mul, a, b)]),
    ],
            docs="""Multiplication on numbers; deeply vectorizes.""",
            stability="unstable")
    cput('Divide_deep_vectorizing', ['Ò'], [
        Case.value2(lambda env, a, b: [pd_deepvectorize_nn2v(num.pd_div, a, b)]),
    ],
            docs="""Division on numbers; deeply vectorizes.""",
            stability="unstable")
    cput('Modulus_deep_vectorizing', ['Ú'], [
        Case.value2(lambda env, a, b: [pd_deepvectorize_nn2v(num.pd_mod, a, b)]),
    ],
            docs="""Modulus on numbers; deeply vectorizes.""",
            stability="unstable")
    # }}}
    # Conversions / loopy things: C, F, I, S {{{
    to_char_case   = Case.value(lambda env, a: [pd_to_char(a)])
    to_float_case  = Case.value(lambda env, a: [pd_to_float(a)])
    to_int_case    = Case.value(lambda env, a: [pd_to_int(a)])
    to_string_case = Case.value(lambda env, a: [env.pd_str(a)])

    cput('To_char',   [   ], [to_char_case  ], docs="Convert to char",   stability="beta")
    cput('To_float',  [   ], [to_float_case ], docs="Convert to float",  stability="beta")
    cput('To_int',    [   ], [to_int_case   ], docs="Convert to int",    stability="beta")
    cput('To_string', ['S'], [to_string_case], docs="Convert to string", stability="beta")

    peekdo_case      = Case.block(lambda env, body: pd_do_then_empty_list(env, body, peek=True))
    iterate_case     = Case.block(lambda env, body: [pd_iterate(env, body)[0]])
    fixed_point_case = Case.block(lambda env, body: [pd_iterate(env, body)[1]])

    cput('Peekdo', [], [peekdo_case],
            docs="""Like {{ 'Doloop'|b }} except the condition is peeked
            instead of popped.""",
            stability="beta")
    cput('Fixed_point', [], [fixed_point_case],
            docs="""Iterate a block, peeking at the stack between iterations,
            until a value repeats. Pushes that value. (This is more general
            than a "fixed point" as usually defined since it doesn't require a
            value to repeat after just one iteration.)""",
            stability="alpha")
    cput('Iterate', [], [iterate_case],
            docs="""Iterate a block, peeking at the stack between iterations,
            until a value repeats. Pushes all values peeked until (excluding)
            the repeated value.""",
            stability="unstable")

    cput('To_char_or_peekloop', ['C'], [to_char_case, peekdo_case],
            docs="""On a non-block value, {{ 'To_char'|b }}; on a block,
            {{ 'Peekdo'|b }}. Mnemonic: "C" is right next to "D" and it's a
            homophone of "see", which is a synonym of "peek".""",
            stability="alpha")

    cput('To_float_or_fixed_point', ['F'], [to_float_case, fixed_point_case],
            docs="""On a non-block value, {{ 'To_float'|b }}; on a block,
            {{ 'Fixed_point'|b }}.""",
            stability="beta")
    cput('To_int_or_iterate', ['I'], [to_int_case, iterate_case],
            docs="""On a non-block value, {{ 'To_float'|b }}; on a block,
            {{ 'Iterate'|b }}.""",
            stability="beta")
    # }}}
    # Sort, $; test for sortedness; order_statistic {{{
    cput('Sort', [], [
        Case.str_(lambda env, s: [''.join(sorted(s))]),
        Case.list_(lambda env, x: [list(sorted(x))]),
    ], docs="Sort", stability="stable")
    cput('Sort_or_stack_select', ['$'], [
        Case.number(lambda env, n: [env.index_stack(int(n))]),
        Case.str_(lambda env, s: [''.join(sorted(s))]),
        Case.list_(lambda env, x: [list(sorted(x))]),
    ], docs="Sort or select from stack", stability="beta")
    cput('Order_statistic', ['¢'], [
        Case.list_number(lambda env, x, i: [sorted(x)[num.intify(i)]]),
        Case.str_number(lambda env, s, i: [Char(sorted(s)[num.intify(i)])]),
    ], docs="Order statistic (zero-indexed)", stability="alpha")
    cput('Is_sorted', ['$p'], [
        Case.seq(lambda env, s: [int(all(a <= b for a, b in zip(s, s[1:])))]),
    ], docs="Test if sorted", stability="alpha")
    cput('Is_strictly_increasing', ['<p'], [
        Case.seq(lambda env, s: [int(all(a < b for a, b in zip(s, s[1:])))]),
    ], docs="Test if strictly increasing", stability="alpha")
    cput('Is_strictly_decreasing', ['>p'], [
        Case.seq(lambda env, s: [int(all(a > b for a, b in zip(s, s[1:])))]),
    ], docs="Test if strictly decreasing", stability="alpha")
    # }}}
    # Range/enumerate/flatten; Comma, J {{{
    range_case = Case.number(lambda env, n: [range(num.intify(n))])
    cput('Range', [], [range_case],
            docs="Range (half-open from 0)", stability="beta")
    range_one_case = Case.number(lambda env, n: [range(1, num.intify(n) + 1)])
    cput('Range_one', [], [range_one_case],
            docs="Range, inclusive from 1", stability="beta")

    enumerate_case = Case.seq(lambda env, seq: [pd_enumerate(seq)])
    cput('Enumerate', [], [enumerate_case],
            docs="Zip with indices from 0", stability="beta")
    enumerate_one_case = Case.seq(lambda env, seq: [pd_enumerate(seq, start=1)])
    cput('Enumerate_one', [], [enumerate_one_case],
            docs="Zip with indices from 1", stability="beta")
    filter_indexes_case = Case.block_seq_range(lambda env, block, seq: [pd_filter_indexes(env, block, seq)])
    cput('Filter_indexes', [], [filter_indexes_case],
            docs="List indices at which block is true", stability="beta")

    cput('Range_enumerate_or_filter_indices', [','], [
        range_case,
        enumerate_case,
        filter_indexes_case,
    ],
            docs="""Range on numbers. Enumerate (zip with indices from 0) on
            sequences. On block and sequence, list indices at which block is
            true.

            Compare {{ 'Range_enumerate_one_or_reject_indices'|b }}.
            """, stability="beta")

    cput('Range_enumerate_one_or_reject_indices', ['J'], [
        range_one_case,
        enumerate_one_case,
        Case.block_seq_range(lambda env, block, seq: [pd_filter_indexes(env, block, seq, negate=True)]),
    ],
            docs="""Range, inclusive from 1, on numbers. Enumerate from 1 (zip
            with indices from 1) on sequences. On block and sequence, list
            indices at which block is false.

            Compare {{ 'Range_enumerate_or_filter_indices'|b }}.
            """, stability="beta")

    range_til_case = Case.number2(lambda env, lo, hi: [range(num.intify(lo), num.intify(hi))])
    range_to_case  = Case.number2(lambda env, lo, hi: [range(num.intify(lo), num.intify(hi) + 1)])
    cput('Exclusive_range', ['Tl'], [range_til_case],
            stability="beta")
    cput('Inclusive_range', ['To'], [range_to_case],
            stability="beta")
    flatten_once_case = Case.seq(lambda env, seq: [pd_flatten_once(seq)])
    flatten_case      = Case.seq(lambda env, seq: [pd_flatten(seq)])
    cput('Flatten_once', [], [flatten_once_case],
            stability="beta")
    cput('Flatten',      [], [flatten_case],
            stability="beta")
    # Note: The dots are the opposite convention of Ruby, where .. is inclusive
    # and ... is exclusive. I don't particularly like that convention. The
    # three-dot range having one more element than the two-dot range makes
    # sense to me.
    cput('Exclusive_range_or_flatten_once', ['¨'], [flatten_once_case, range_til_case],
            stability="beta")
    cput('Inclusive_range_or_flatten',      ['…'], [flatten_case,      range_to_case],
            stability="beta")

    cput('Range_one_down', ['Dj'], [
        Case.number(lambda env, n: [range(num.intify(n), 0, -1)])
    ],
            docs="Range, inclusive downward from 1", stability="alpha")
    cput('Range_odds_exclusive', ['Or'], [
        Case.number(lambda env, n: [range(1, num.intify(n), 2)])
    ],
            docs="Range, odds, from 1, exclusive", stability="unstable")
    cput('Range_evens_exclusive', ['Er'], [
        Case.number(lambda env, n: [range(0, num.intify(n), 2)])
    ],
            docs="Range, evens, from 0, exclusive", stability="unstable")
    cput('Range_odds_inclusive', ['Oj'], [
        Case.number(lambda env, n: [range(1, num.intify(n) + 1, 2)])
    ],
            docs="Range, odds, from 1, inclusive", stability="unstable")
    cput('Range_evens_inclusive', ['Ej'], [
        Case.number(lambda env, n: [range(2, num.intify(n) + 1, 2)])
    ],
            docs="Range, evens, from 2, inclusive", stability="unstable")
    # }}}
    # Binary operators &|^ {{{
    cput('Bin_or_or_union_or_unless', ['|'], [
        Case.number2(lambda env, a, b: [num.pd_or(a, b)]),
        Case.seq2_range(lambda env, a, b: [pd_seq_union(a, b)]),
        Case.condition_block(lambda env, cond, block:
            pd_if_then_empty_list(env, cond, block, negate=True)),
    ],
            docs="""Binary OR on numbers. Union on sequences. One-branch unless
            on blocks.""", stability="beta")
    cput('Bin_and_or_intersection_or_if', ['&'], [
        Case.number2(lambda env, a, b: [num.pd_and(a, b)]),
        Case.seq2_range(lambda env, a, b: [pd_seq_intersection(a, b)]),
        Case.condition_block(lambda env, cond, block:
            pd_if_then_empty_list(env, cond, block)),
    ],
            docs="""Binary AND on numbers. Intersection on sequences.
            One-branch if on blocks.""", stability="beta")
    cput('Exclusive_or_or_symmetric_difference_or_find_last', ['^'], [
        Case.number2(lambda env, a, b: [num.pd_xor(a, b)]),
        Case.seq2_range(lambda env, a, b: [pd_seq_symmetric_difference(a, b)]),
        Case.block_seq_range(lambda env, block, seq:
            [second_or_error(pd_find_last_entry(env, block, seq),
                "Entry not found in Exclusive_or_or_symmetric_difference_or_find_last")]),
    ],
            docs="""Binary XOR on numbers. Symmetric difference on sequences.
            Find last on block and sequence.
            """, stability="beta")
    cput('If', [], [
        Case.any2(lambda env, cond, body:
            pd_if_then_empty_list(env, cond, body)),
    ],
            docs="""Single-branch if.""", stability="alpha")
    cput('Unless', ['Ul'], [
        Case.any2(lambda env, cond, body:
            pd_if_then_empty_list(env, cond, body, negate=True)),
    ],
            docs="""Single-branch unless.""", stability="alpha")
    @put('If_else', '?',
            docs="""If-else.

            ex: 1 "True!" "False" ? => "True!"
            """, stability="beta")
    def pd_if(env: Environment) -> None:
        c, b, a = env.pop3()
        if pytruth_eval(env, a):
            # print('True!')
            env.push_or_eval(b)
        else:
            # print('False!')
            env.push_or_eval(c)
    # }}}
    # Base {{{
    cput('Base', ['B'], [
        Case.number2(lambda env, n, b: [base.to_base_digits(num.intify(b), num.intify(n))]),
        Case.list_number(lambda env, lst, b: [base.from_base_digits(num.intify(b), lst)]),
        Case.str_number(lambda env, s, b: [int(s, num.intify(b))]),
    ],
            docs="""Base. On two numbers, converts the first to a list of
            digits in the radix of the second. On a list or a string and a
            number, interprets the sequence as digits (numbers if a list, digit
            characters if a string) in the radix of the number and converts to
            a number.""", stability="beta")
    cput('Lower_base', ['Lb'], [
        Case.number2(lambda env, n, b: [base.to_base_digits_lower(num.intify(b), num.intify(n))]),
    ],
            docs="""Converts the first number to a string of digits in the
            radix of the second, using lowercase digits.""", stability="beta")
    cput('Upper_base', ['Ub'], [
        Case.number2(lambda env, n, b: [base.to_base_digits_upper(num.intify(b), num.intify(n))]),
    ],
            docs="""Converts the first number to a string of digits in the
            radix of the second, using uppercase digits.""", stability="beta")
    # }}}
    # Comparators <=> Max Min {{{
    cput('Equal', ['Eq'], [
        Case.number2(lambda env, a, b: [int(num.numerify(a) == num.numerify(b))]),
        Case.str2(lambda env, a, b: [int(a == b)]),
        Case.list2(lambda env, a, b: [int(list(a) == list(b))]),
    ],
            stability="beta")
    cput('Equal_identity', ['Is'], [
        Case.number2(lambda env, a, b: [int(a is b)]),
    ],
            docs="Test for Python identity (is)",
            stability="alpha")
    cput('Equal_or_index_or_find', ['='], [
        Case.number2(lambda env, a, b: [int(num.numerify(a) == num.numerify(b))]),
        Case.str2(lambda env, a, b: [int(a == b)]),
        Case.list2(lambda env, a, b: [int(list(a) == list(b))]),
        Case.number_seq(lambda env, n, seq: [pd_index(seq, num.intify(n))]),
        Case.block_seq_range(lambda env, block, seq:
            [second_or_error(pd_find_entry(env, block, seq),
                "Entry not found in Equal_or_index_or_find")]),
    ],
            docs="""On two numbers, two strings, or two lists, compare for
            equality. On a number and a sequence, index into the sequence. On a
            block and a sequence (numbers coerce to ranges), find the first
            element satisfying the block.""", stability="beta")
    cput('Lt_or_slice', ['<'], [
        Case.number2(lambda env, a, b: [int(num.pd_cmp(a, b) < 0)]),
        Case.str2(lambda env, a, b: [int(a < b)]),
        Case.list2(lambda env, a, b: [int(list(a) < list(b))]),
        Case.number_seq(lambda env, n, seq: [seq[:num.intify(n)]]),
        Case.block_seq_range(lambda env, block, seq:
            [pd_take_drop_while(env, block, seq)[0]]),
    ],
            docs="""On two numbers, two strings, or two lists, compare if the
            first is less than the second. On a number and a sequence, slice
            elements with index less than the number, as Python s[:n]. On a
            sequence (numbers coerce to ranges) and a block, "take while", or
            return the longest prefix of elements that all satisfy the
            block.""",
            stability="beta")
    cput('Gt_or_slice', ['>'], [
        Case.number2(lambda env, a, b: [int(num.pd_cmp(a, b) > 0)]),
        Case.str2(lambda env, a, b: [int(a > b)]),
        Case.list2(lambda env, a, b: [int(list(a) > list(b))]),
        Case.number_seq(lambda env, n, seq: [seq[num.intify(n):]]),
        Case.block_seq_range(lambda env, block, seq:
            [pd_take_drop_while(env, block, seq)[1]]),
    ],
            docs="""On two numbers, two strings, or two lists, compare if the
            first is greater than the second. On a number and a sequence, slice
            elements with index greater than or equal to the number, as Python
            s[n:]. On a sequence (numbers coerce to ranges) and a block, "drop
            while", or return the suffix starting with the first element that
            fails to satisfy the block.""",
            stability="beta")
    cput('Leq_or_slice', ['<e'], [
        Case.number2(lambda env, a, b: [int(num.pd_cmp(a, b) <= 0)]),
        Case.str2(lambda env, a, b: [int(a <= b)]),
        Case.list2(lambda env, a, b: [int(list(a) <= list(b))]),
        Case.number_seq(lambda env, n, seq: [seq[:num.intify(n)+1]]),
    ],
            docs="""Less than or equal to.""",
            stability="beta")
    cput('Geq_or_slice', ['>e'], [
        Case.number2(lambda env, a, b: [int(num.pd_cmp(a, b) >= 0)]),
        Case.str2(lambda env, a, b: [int(a >= b)]),
        Case.list2(lambda env, a, b: [int(list(a) >= list(b))]),
        Case.number_seq(lambda env, n, seq: [seq[num.intify(n):]]), # TODO: ?
    ],
            docs="""Greater than or equal to.""",
            stability="beta")
    cput('Lt_approx', ['<a'], [
        Case.number2(lambda env, a, b:
            [int(num.numerify(a) - num.numerify(b) < env.get_epsilon())]), # type: ignore
    ],
            docs="""Approximately less than; tolerance is given by Ep,
            epsilon""",
            stability="alpha")
    cput('Gt_approx', ['>a'], [
        Case.number2(lambda env, a, b:
            [int(num.numerify(b) - num.numerify(a) < env.get_epsilon())]), # type: ignore
    ],
            docs="""Approximately greater than; tolerance is given by Ep,
            epsilon""",
            stability="alpha")
    cput('Eq_approx', ['=a'], [
        Case.number2(lambda env, a, b:
            [int(abs(num.numerify(a) - num.numerify(b)) < env.get_epsilon())]), # type: ignore
    ],
            docs="""Approximately equal than; tolerance is given by Ep,
            epsilon""",
            stability="alpha")
    cput('Min', ['<m', 'Õ'], [
        Case.any2(lambda env, a, b: [min(a, b)]), # TODO
    ],
            docs="""Minimum of two values""",
            stability="beta")
    cput('Max', ['>m', 'Ã'], [
        Case.any2(lambda env, a, b: [max(a, b)]), # TODO
    ],
            docs="""Maximum of two values""",
            stability="beta")
    cput('Array_min', ['<r', 'Œ'], [
        Case.seq(lambda env, e: [min(pd_iterable(e))]),
    ],
            docs="""Minimum of array""",
            stability="alpha")
    cput('Array_max', ['>r', 'Æ'], [
        Case.seq(lambda env, e: [max(pd_iterable(e))]),
    ],
            docs="""Maximum of array""",
            stability="alpha")
    cput('Array_median', ['=r'], [
        # TODO: True median should try to take the average of two elements
        Case.list_(lambda env, x: [sorted(x)[len(x)//2]]),
        Case.str_(lambda env, s: [Char(sorted(s)[len(s)//2])]),
    ], docs="Median of array", stability="alpha")
    cput('Compare', ['˜'], [
        Case.number2(lambda env, a, b: [num.pd_cmp(a, b)]),
        Case.str2(lambda env, a, b: [num.any_cmp(a, b)]),
        Case.list2(lambda env, a, b: [num.any_cmp(list(a), list(b))]),
    ],
            docs="""Compare (-1, 0, or 1)""",
            stability="unstable")

    cput('Lt_length', ['<l'], [
        Case.number2_len(lambda env, a, b: [int(num.pd_cmp(a, b) < 0)]),
    ],
            docs="""Less than, after coercing two arguments to ints or floats,
            sequences by taking their length.""",
            stability="unstable")
    cput('Gt_length', ['>l'], [
        Case.number2_len(lambda env, a, b: [int(num.pd_cmp(a, b) > 0)]),
    ],
            docs="""Greater than, after coercing two arguments to ints or
            floats, sequences by taking their length.""",
            stability="unstable")
    cput('Eq_length', ['=l'], [
        Case.number2_len(lambda env, a, b: [int(a == b)]),
    ],
            docs="""Equal to, after coercing two arguments to ints or floats,
            sequences by taking their length.""",
            stability="unstable")
    cput('Leq_length', ['<el'], [
        Case.number2_len(lambda env, a, b: [int(num.pd_cmp(a, b) <= 0)]),
    ],
            docs="""Less than or equal to, after coercing two arguments to
            ints or floats, sequences by taking their length.""",
            stability="unstable")
    cput('Geq_length', ['>el'], [
        Case.number2_len(lambda env, a, b: [int(num.pd_cmp(a, b) >= 0)]),
    ],
            docs="""Greater than or equal to, after coercing two arguments to
            ints or floats, sequences by taking their length.""",
            stability="unstable")
    # }}}
    # Shifting and slicing {{{
    left_shift_case  = Case.number2(lambda env, a, b: [num.pd_lshift(a, b)])
    right_shift_case = Case.number2(lambda env, a, b: [num.pd_rshift(a, b)])
    cput('Left_shift', [], [left_shift_case],
            docs="""Bitwise left shift""",
            stability="beta")
    cput('Right_shift', [], [right_shift_case],
            docs="""Bitwise right shift""",
            stability="beta")
    nonempty_left_slices_case  = Case.seq(
            lambda env, seq: [[seq[:n+1] for n in range(len(seq))]])
    nonempty_right_slices_case = Case.seq(
            lambda env, seq: [[seq[n:] for n in range(len(seq) - 1, -1, -1)]])
    from_empty_left_slices_case  = Case.seq(
            lambda env, seq: [[seq[:n] for n in range(len(seq) + 1)]])
    from_empty_right_slices_case = Case.seq(
            lambda env, seq: [[seq[n:] for n in range(len(seq), -1, -1)]])
    def nonempty_slices_func(env: Environment, seq: PdSeq) -> List[PdObject]:
        return [[seq[lo:hi]
                for lo in range(len(seq))
                for hi in range(lo + 1, len(seq) + 1)]]
    nonempty_slices_case = Case.seq(nonempty_slices_func)

    cput('Left_slices', [], [nonempty_left_slices_case],
            docs="""Left slices (nonempty, by increasing length)""",
            stability="alpha")
    cput('Right_slices', [], [nonempty_right_slices_case],
            docs="""Right slices (nonempty, by increasing length)""",
            stability="alpha")

    cput('Left_shift_or_slices', ['<s'], [
        nonempty_left_slices_case, left_shift_case,
    ],
            docs="""{{ 'Left_shift'|b }} on numbers, {{ 'Left_slices'|b }} on a
            sequence""",
            stability="alpha")

    cput('Right_shift_or_slices', ['>s'], [
        nonempty_right_slices_case, left_shift_case,
    ],
            docs="""{{ 'Right_shift'|b }} on numbers, {{ 'Right_slices'|b }} on
            a sequence""",
            stability="alpha")

    cput('From_empty_left_slices', ['«s'], [
        from_empty_left_slices_case,
    ],
            docs="""Left slices (including the empty one, by increasing
            length)""",
            stability="alpha")

    cput('From_empty_right_slices', ['»s'], [
        from_empty_right_slices_case,
    ],
            docs="""Right slices (including the empty one, by increasing
            length)""",
            stability="alpha")

    nonempty_slices_range_case = Case.seq_range(nonempty_slices_func)

    cput('All_slices', ['=s', '§'], [nonempty_slices_range_case],
            docs="""All slices of a sequence (numbers coerce to ranges).""",
            stability="unstable")
    # }}}
    # Incr/Decr/First/Last/Uncons/Unsnoc/Parens: «»‹›() {{{
    def case_add_const(i: int) -> Case:
        return Case.number(lambda env, a: [num.pd_add_const(a, i)])

    decr_case  = case_add_const(-1)
    incr_case  = case_add_const(1)
    decr2_case = case_add_const(-2)
    incr2_case = case_add_const(2)

    cput('Decr',     [], [decr_case ], docs="Decrease by 1.", stability="beta")
    cput('Incr',     [], [incr_case ], docs="Increase by 1.", stability="beta")
    cput('Decr_two', [], [decr2_case], docs="Decrease by 2.", stability="beta")
    cput('Incr_two', [], [incr2_case], docs="Increase by 2.", stability="beta")

    uncons_case = Case.seq(lambda env, a: [a[1:], pd_index(a, 0)])
    cput('Uncons', [], [uncons_case],
            docs="""Split into tail and first.

            ex: [1 2 3]Uncons => [2 3]1""", stability="beta")
    unsnoc_case = Case.seq(lambda env, a: [a[:-1], pd_index(a, -1)])
    cput('Unsnoc', [], [unsnoc_case],
            docs="""Split into init and last.

            ex: [1 2 3]Uncons => [1 2]3""", stability="beta")
    cput('Decr_or_uncons', ['('], [decr_case, uncons_case],
            docs="Decr or Uncons.", stability="beta")
    cput('Incr_or_unsnoc', [')'], [incr_case, unsnoc_case],
            docs="Incr or Unsnoc.", stability="beta")

    first_case = Case.seq(lambda env, a: [pd_index(a,  0)])
    last_case  = Case.seq(lambda env, a: [pd_index(a, -1)])
    butlast_case  = Case.seq(lambda env, a: [a[:-1]])
    butfirst_case = Case.seq(lambda env, a: [a[1: ]])
    first_and_last_case = Case.seq(lambda env, a: [pd_index(a, 0), pd_index(a, -1)])

    cput('First',    [], [first_case], docs="First of sequence", stability="stable")
    cput('Last',     [], [last_case],  docs="Last of sequence",  stability="stable")
    cput('Butlast',  [], [butlast_case],  docs="All but last of sequence",  stability="beta")
    cput('Butfirst', [], [butfirst_case], docs="All but first of sequence", stability="beta")
    cput('First_and_last', [], [first_and_last_case], docs="First and last of sequence",
            stability="alpha")

    floor_case = Case.number(lambda env, a: [num.pd_floor(a)])
    ceil_case  = Case.number(lambda env, a: [num.pd_ceil(a)])
    round_case = Case.number(lambda env, a: [num.pd_round(a)])

    cput('Floor',   ['<i'], [floor_case], docs="Round down to the nearest integer.", stability="beta")
    cput('Ceiling', ['>i'], [ceil_case ], docs="Round up to the nearest integer.",   stability="beta")
    cput('Round',   ['=i'], [round_case], docs="Round to the nearest integer; follows Python's rules.",
            stability="alpha")

    cput('Floor_or_first', ['‹'], [floor_case, first_case],
            docs="""{{ 'Floor'|b }} or {{ 'First'|b }} of sequence""",
            stability="alpha")
    cput('Ceiling_or_last', ['›'], [ceil_case, last_case],
            docs="""{{ 'Ceiling'|b }} or {{ 'Last'|b }} of sequence""",
            stability="alpha")

    cput('Decr_two_or_but_last',  ['«'], [decr2_case, butlast_case],
            docs="""Decrease by two, or all but last""",
            stability="alpha")

    cput('Incr_two_or_but_first', ['»'], [incr2_case, butfirst_case],
            docs="""Increase by two, or all but first (tail)""",
            stability="alpha")

    cput('Round_or_first_and_last', ['¤' ], [round_case, first_and_last_case],
            stability="alpha")
    # }}}
    # Sum, Product, etc {{{
    cput('Sum', ['Š'], [
        Case.seq_range(lambda env, x: [pd_deep_sum(x)]),
    ],
            docs="Sum (coerces numbers to range).", stability="beta")
    cput('Product', ['Þ'], [
        Case.seq_range(lambda env, x: [pd_deep_product(x)]),
    ],
            docs="Product (coerces numbers to range!?).", stability="alpha")
    cput('Deep_length', ['Dl'], [
        Case.value(lambda env, x: [pd_deep_length(x)]),
    ],
            docs="Deep length.", stability="unstable")
    cput('Average', ['Av'], [
        Case.seq_range(lambda env, x: [pd_deep_average(x)]),
    ],
            docs="Average (deep).", stability="alpha")
    cput('Standard_deviation', ['Sg'], [
        Case.seq_range(lambda env, x: [pd_deep_standard_deviation(x)]),
    ],
            docs="Standard deviation (deep). Mnemonic: sigma", stability="alpha")
    # }}}
    # M for Minus (negate) and Mold {{{
    negate_case = Case.number(lambda env, a: [num.pd_mul_div_const(a, -1, 1)])
    mold_case = Case.value_seq(lambda env, x, y: [pd_mold(x, y)])
    cput('Negate', [], [negate_case],
            docs="Negate a number.", stability="beta")
    cput('Mold', [], [mold_case],
            docs="Mold the first sequence like the second.", stability="alpha")
    cput('Negate_or_mold', ['M'], [negate_case, mold_case],
            docs="{{ 'Negate'|b }} a number, or {{ 'Mold'|b }} a sequence like another.",
            stability="alpha")
    # }}}
    # U for Signum, Uniquify, Until {{{
    signum_case = Case.number(lambda env, a: [num.pd_signum(a)])
    uniquify_case = Case.seq(lambda env, a: [pd_seq_uniquify(a)])
    until_case = Case.block2(lambda env, cond, body:
            pd_while_then_empty_list(env, cond, body, negate=True))
    cput('Signum', [], [signum_case],
            docs="Signum of a number (-1, 0, 1) by sign.", stability="beta")
    cput('Uniquify', [], [uniquify_case],
            docs="""Uniquify a sequence: drop all but first occurrence of each
            element""",
            stability="alpha")
    cput('Until', [], [until_case],
            docs="""Until loop: Execute first block, pop, stop if true, execute
            second block, repeat.""",
            stability="alpha")
    cput('Signum_or_uniquify_or_until', ['U'], [signum_case, uniquify_case, until_case],
            docs="Signum or uniquify or until. Mnemonic: U for Unit",
            stability="alpha")
    # }}}
    # Has as factor / count {{{
    cput('Count_maybe_factors', ['#'], [
        Case.number2(lambda env, a, b: [num.pd_count_multiplicity_in(b, a)]),
        Case.seq_value(lambda env, s, x: [pd_count_in(env, x, s)]),
        Case.block_seq_range(lambda env, b, s: [pd_count(env, b, s)]),
    ],
            docs="""Count factor multiplicity, frequency, or number satisfying
            predicate. Mnemonic: number sign.""",
            stability="alpha")
    # }}}
    # Down/Do, Transpose, Zip {{{
    reverse_case = Case.seq_range(lambda env, a: [a[::-1]])
    doloop_case  = Case.block(lambda env, body: pd_do_then_empty_list(env, body))
    cput('Reverse', ['Down'], [reverse_case, doloop_case],
            docs="""Reverse a sequence (coerces numbers to range).""",
            stability="beta")
    cput('Doloop', [], [doloop_case],
            docs="""Do loop: execute the block, then pop an element, and repeat
            until the popped element is falsy.""",
            stability="beta")
    cput('Reverse_or_doloop', ['Down_or_doloop', 'D'], [reverse_case, doloop_case],
            docs="""On a number of a sequence, {{ 'Reverse'|b }}; on a block,
            {{ 'Doloop'|b }}.""",
            stability="beta")
    cput('Reverse_one_or_map', ['Ð'], [
        Case.number(lambda env, n: [range(num.intify(n), 0, -1)]),
        Case.seq_range(lambda env, a: [pd_map_reverse_singleton(a)]),
    ],
            docs="""On numbers, reverse inclusive range from that number to
            1. On sequences, reverse each element (numbers coerce to length-1
            lists, and characters coerce to length-1 strings, so you can also
            use this to wrap each element of a flat list into a list).
            (Heavily inspired by studying 05AB1E.)""",
            stability="unstable")
    cput('Transpose', ['Tt', '™'], [
        Case.seq(lambda env, a: [pd_transpose(a)]),
    ],
            docs="""Transpose a matrix, or list of lists.""",
            stability="alpha")
    cput('Transpose_fill', ['Tf'], [
        Case.seq_value(lambda env, a, f: [pd_transpose_fill(a, f)]),
    ],
            docs="""Given a filler element, transpose a matrix, or list of
            lists, with the filler element repeated as necessary until the
            matrix is rectangular.""",
            stability="alpha")
    cput('Zip', ['Zp', 'Ž'], [
        Case.seq2_range(lambda env, a, b: [pd_zip_as_list(a, b)]),
        Case.seq2_range_block(lambda env, a, b, block: [pd_zip(env, block, a, b)]),
    ],
            docs="""Zip two sequences (numbers coerce to ranges), returning a
            list of length-2 lists; or zip them with a block, which operates on
            corresponding pairs of the two lists. Truncates to the length of
            the shorter input sequence. Also see {{ 'zip'|it }}.""",
            stability="alpha")
    cput('Ziplongest', ['Zl'], [
        Case.seq2_range(lambda env, a, b: [pd_ziplongest_as_list(a, b)]),
        Case.seq2_range_block(lambda env, a, b, block: [pd_ziplongest(env, block, a, b)]),
    ],
            docs="""Zip two sequences (numbers coerce to ranges), returning a
            list of length-2 or (at indices between their lengths, if the
            sequences are of unequal length) length-1 lists; or zip them with a
            block, which operates on corresponding pairs of the two lists,
            where elements of the longer list are collected unmodified. The
            result has length equal to that of the longest list.""",
            stability="alpha")
    # }}}
    # Reduce/join {{{
    cput('Reduce', ['R'], [
        Case.seq2_singleton(lambda env, seq, joiner: [pd_join(env, seq, joiner)]),
        Case.block_seq_range(lambda env, block, seq: [pd_reduce(env, block, seq)]),
    ],
            stability="beta")
    line_join_case = Case.seq_range(lambda env, seq:
            ['\n'.join(env.pd_str(e) for e in pd_iterable(seq))])
    cput('Line_join', ['\nr', '\\nr'], [line_join_case],
            docs="Join with newlines",
            stability="beta")
    cput('Ŋ', ['\x0e'], [line_join_case],
            docs="Unstable aliases for {{ 'Line_join'|b }}.",
            stability="unstable")
    cput('Space_join', [' r'], [
        Case.seq_range(lambda env, seq: [' '.join(env.pd_str(e) for e in pd_iterable(seq))]),
    ],
            stability="beta")
    # }}}
    # G for Gcd or group, and friends {{{
    cput('Group', [], [
        Case.seq(lambda env, seq: [pd_group(seq)]),
    ],
            stability="beta")
    cput('Group_by', [], [
        Case.block_seq_range(lambda env, block, seq: [pd_group_by(env, block, seq)]),
    ],
            stability="beta")
    cput('Gcd', [], [
        Case.number2(lambda env, a, b: [num.pd_gcd(a, b)]),
    ],
            stability="beta")
    cput('Group_maybe_by', ['G'], [
        Case.seq(lambda env, seq: [pd_group(seq)]),
        Case.number2(lambda env, a, b: [num.pd_gcd(a, b)]),
        Case.block_seq_range(lambda env, block, seq: [pd_group_by(env, block, seq)]),
    ],
            docs="""GCD; group like elements of a sequence, possibly under a
            mapping.""",
            stability="beta")
    cput('Lcm', ['µ'], [
        Case.number2(lambda env, a, b: [num.pd_lcm(a, b)]),
    ],
            stability="unstable")
    # }}}
    # Circumflexed vowels {{{
    even_case = Case.number(lambda env, n: [int(num.numerify(n) % 2 == 0)])
    odd_case  = Case.number(lambda env, n: [int(num.numerify(n) % 2 == 1)])
    cput('Even', ['Ev'], [even_case], stability="alpha")
    cput('Odd',  ['Od'], [odd_case],  stability="alpha")
    def all_fold_f(es: Optional[List[PdObject]]) -> Optional[bool]:
        if es is None:
            return True
        else:
            for e in es:
                if not e: return False
            return None
    def any_fold_f(es: Optional[List[PdObject]]) -> Optional[bool]:
        if es is None:
            return False
        else:
            for e in es:
                if e: return True
            return None
    def make_all_and_exists_fold_f() -> Callable[[Optional[List[PdObject]]], Optional[bool]]:
        exists = False
        def f(es: Optional[List[PdObject]]) -> Optional[bool]:
            nonlocal exists
            if es is None:
                return exists
            else:
                for e in es:
                    if not e: return False
                    exists = True
                return None
        return f
    def make_unique_fold_f() -> Callable[[Optional[List[PdObject]]], Optional[bool]]:
        s = set() # type: Set[PdObject]
        def f(es: Optional[List[PdObject]]) -> Optional[bool]:
            if es is None:
                return True
            else:
                for e in es:
                    if e in s: return False
                    else: s.add(e)
                return None
        return f
    def make_identical_fold_f() -> Callable[[Optional[List[PdObject]]], Optional[bool]]:
        obj = None # type: Optional[PdObject]
        def f(es: Optional[List[PdObject]]) -> Optional[bool]:
            nonlocal obj
            if es is None:
                return True
            else:
                for e in es:
                    if obj is None: obj = e
                    elif obj != e: return False
                return None
        return f
    def all_and_exists(seq: Iterable[object]) -> bool:
        exists = False
        for e in seq:
            if not e: return False
            exists = True
        return exists
    all_cases = [
        Case.seq(lambda env, a: [int(all(pd_iterable(a)))]),
        Case.block_seq_range(lambda env, block, seq:
            [int(pd_map_fold_into(env, block, seq, all_fold_f))]),
    ]
    any_cases = [
        Case.seq(lambda env, a: [int(any(pd_iterable(a)))]),
        Case.block_seq_range(lambda env, block, seq:
            [int(pd_map_fold_into(env, block, seq, any_fold_f))]),
    ]
    all_and_exists_cases = [
        Case.seq(lambda env, a: [int(all_and_exists(pd_iterable(a)))]),
        Case.block_seq_range(lambda env, block, seq:
            [int(pd_map_fold_into(env, block, seq, make_all_and_exists_fold_f()))]),
    ]
    not_all_cases = [
        Case.seq(lambda env, a: [int(not all(pd_iterable(a)))]),
        Case.block_seq_range(lambda env, block, seq:
            [int(not pd_map_fold_into(env, block, seq, all_fold_f))]),
    ]
    not_any_cases = [
        Case.seq(lambda env, a: [int(not any(pd_iterable(a)))]),
        Case.block_seq_range(lambda env, block, seq:
            [int(not pd_map_fold_into(env, block, seq, any_fold_f))]),
    ]
    identical_cases = [
        Case.seq(lambda env, a: [int(pd_seq_is_identical(a))]),
        Case.block_seq_range(lambda env, block, seq:
            [int(pd_map_fold_into(env, block, seq, make_identical_fold_f()))]),
    ]
    unique_cases = [
        Case.seq(lambda env, a: [int(pd_seq_is_unique(a))]),
        Case.block_seq_range(lambda env, block, seq:
            [int(pd_map_fold_into(env, block, seq, make_unique_fold_f()))]),
    ]
    cput('All', ['For_all', 'Fa'], all_cases, stability="beta")
    cput('Any', ['There_exists', 'Te'], any_cases, stability="beta")
    cput('All_and_exists', ['Ae'], all_and_exists_cases, stability="alpha")
    cput('Not_all', ['Na'], not_all_cases, stability="beta")
    cput('Not_any', ['Not_exists', 'Ne'], not_any_cases, stability="beta")
    cput('Identical', ['=p'], identical_cases, stability="beta")
    cput('Unique', [], unique_cases, stability="beta")
    cput('Above_zero_or_all', ['Â'], [
        Case.number(lambda env, a: [int(num.numerify(a) > 0)])
    ] + all_cases,
            docs="Above zero or All", stability="beta")
    cput('Even_or_any', ['Ê'], [even_case] + any_cases,
            docs="Even or Any (Exists)", stability="beta")
    cput('Equals_one_or_identical', ['Î'], [
        Case.number(lambda env, a: [int(num.numerify(a) == 1)]),
    ] + identical_cases,
            docs="Identity (equals 1) or Identical", stability="beta")
    cput('Odd_or_not_any', ['Ô'], [odd_case] + not_any_cases,
            docs="Odd or Not_any", stability="beta")
    cput('Under_zero_or_is_unique', ['Û'], [
        Case.number(lambda env, a: [int(num.numerify(a) < 0)]),
    ] + unique_cases,
            docs="Under zero or Unique (test)", stability="beta")
    # }}}
    # Tilde and Eval {{{
    @put('Compl_or_eval_or_expand', '~',
            docs="""Bitwise complement of integers. Expand lists or strings
            onto the stack, pushing each element separately in order. Eval on a
            block.""",
            stability="beta")
    def tilde(env: Environment) -> None:
        a = env.pop()
        if isinstance(a, Block):
            a(env)
        elif isinstance(a, (str, list, range)):
            env.push(*pd_iterable(a))
        elif isinstance(a, int):
            env.push(~a)
        else:
            raise NotImplementedError

    @put('Eval', 'Pd', docs="Evaluate a string as Paradoc code", stability="alpha")
    def pd_eval(env: Environment) -> None:
        a = env.pop()
        if isinstance(a, str):
            env.evaluate(a)
        else:
            raise NotImplementedError
    # }}}
    # Input, output, and debugging {{{
    @put('Read_input', 'V',
            docs="""Read something from standard input, as determined by the
            current input trigger.""",
            stability="alpha")
    def read_input(env: Environment) -> None:
        e = env.input_trigger()
        if e is None:
            raise Exception('No more input!')
        else:
            env.push(e)

    @put('Output', 'O',
            docs="""Output to standard output.""",
            stability="beta")
    def pd_output(env: Environment) -> None:
        a = env.pop()
        print(env.pd_str(a), end="")

    @put('Print', 'P',
            docs="""Output to standard output, followed by an output record
            separator.""",
            stability="beta")
    def pd_print(env: Environment) -> None:
        a = env.pop()
        env.print_output_record(env.pd_str(a))

    @put('Printkeep', 'Ƥ', '\x10',
            docs="""Pop something, output to standard output followed by an
            output record separator, then push it back. Pretty much just {{
            'Print'|b }}_{{ 'keep'|bt }}.""",
            stability="unstable")
    def pd_printkeep(env: Environment) -> None:
        a = env.pop()
        env.print_output_record(env.pd_str(a))
        env.push(a)

    @put('Space_output', ' o',
            docs="Output a space.", stability="beta")
    def pd_space_output(env: Environment) -> None:
        print(' ', end="")
    @put('Newline_output', '\no', '\\no',
            docs="Output a newline.", stability="beta")
    def pd_newline_output(env: Environment) -> None:
        print()

    @put('Dump', 'Pdebug',
            docs="""Print debugging information about the environment and
            stack.""",
            stability="alpha")
    def dump(env: Environment) -> None:
        if env.get('Debug'):
            print('Dump:', env.debug_dump(), file=sys.stderr)
    # }}}
    # Abort, Break, Continue {{{
    @put('Abort', 'A',
            docs="""Abort the current program.""",
            stability="beta")
    def abort(env: Environment) -> None:
        raise PdAbortException("Abort")

    @put('Abort_with', 'Aw',
            docs="""Abort the current program with the specified exit code or
            message.""",
            stability="beta")
    def abort_with(env: Environment) -> None:
        e = env.pop()
        if isinstance(e, (int, float, Char)):
            raise PdAbortException("Abort", num.intify(e))
        else:
            print("Abort: " + str(e), file=sys.stderr)
            raise PdAbortException(str(e), 1)

    @put('Break', 'Quit_loop', 'Q',
            docs="""Break out of the current loop.""",
            stability="beta")
    def break_(env: Environment) -> None:
        raise PdBreakException('Break')
    @put('Continue', 'Keep_going', 'K',
            docs="""Skip to the next iteration of the current loop.""",
            stability="beta")
    def continue_(env: Environment) -> None:
        raise PdContinueException('Continue')
    # }}}
    # Constant powers and fractions {{{
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
    cput('Halve', ['½', 'Hf'], pd_constant_fraction_cases(1, 2), stability="alpha")
    cput('Quarter', ['¼', 'Qt'], pd_constant_fraction_cases(1, 4), stability="alpha")
    cput('Three_quarters', ['¾', 'Tq'], pd_constant_fraction_cases(3, 4), stability="alpha")
    cput('Double', ['×'], pd_constant_fraction_cases(2, 1), stability="beta")

    cput('Halve_int', ['Hi'], [
        Case.number(lambda env, a: [num.pd_mul_div_const(a, 1, 2, to_int=True)]),
    ], stability="unstable")

    cput('Square', ['²'], [
        Case.number(lambda env, n: [num.pd_power_const(n, 2)]),
        Case.seq(lambda env, s: [pd_cartesian_product_seq_matrix(s, s)]),
        Case.block_seq_range(lambda env, block, seq: [pd_map_product(env, block, seq, seq)]),
    ],
            stability="beta")
    cput('Cube', ['³'], [
        Case.number(lambda env, n: [num.pd_power_const(n, 3)]),
        Case.seq(lambda env, s: [pd_cartesian_product_seq_matrix_3(s, s, s)]),
    ],
            stability="beta")
    cput('Power_of_ten', ['€'], [Case.number(lambda env, n: [10 ** num.numerify(n)])],
            stability="alpha")
    # }}}
    # Len, abs, loop {{{
    abs_case = Case.number(lambda env, n: [num.pd_abs(n)])
    len_case = Case.seq(lambda env, seq: [len(seq)])
    loop_case = Case.block(lambda env, block: [pd_forever_then_empty_list(env, block)])
    cput('Len', [], [len_case],
            docs="""Length of a sequence.""",
            stability="stable")
    cput('Abs', [], [abs_case],
            docs="""Absolute value of a number.""",
            stability="stable")
    cput('Loop', [], [loop_case],
            docs="""Loop forever (until {{ 'Break'|b }} or other error.)""",
            stability="alpha")
    cput('Abs_or_len_or_loop', ['L'], [abs_case, len_case, loop_case],
            docs="""{{ 'Abs'|b }} on numbers; {{ 'Len'|b }} on sequences; {{
            'Loop'|b }} on blocks.""",
            stability="alpha")
    # }}}
    # Other numeric predicates {{{
    cput('Positive',         ['+p'], [Case.value_n2v(lambda e: int(e >  0))], stability="beta")
    cput('Negative',         ['-p'], [Case.value_n2v(lambda e: int(e <  0))], stability="beta")
    cput('Positive_or_zero', ['+o'], [Case.value_n2v(lambda e: int(e >= 0))], stability="alpha")
    cput('Negative_or_zero', ['-o'], [Case.value_n2v(lambda e: int(e <= 0))], stability="alpha")
    # }}}
    # Dumping Python's math {{{
    cput('Sin',     ['Sn'], [Case.value_n2v(math.sin  )], stability="beta")
    cput('Cos',     ['Cs'], [Case.value_n2v(math.cos  )], stability="beta")
    cput('Tan',     ['Tn'], [Case.value_n2v(math.tan  )], stability="beta")
    cput('Asin',    ['As'], [Case.value_n2v(math.asin )], stability="beta")
    cput('Acos',    ['Ac'], [Case.value_n2v(math.acos )], stability="beta")
    cput('Atan',    ['At'], [Case.value_n2v(math.atan )], stability="beta")
    cput('Sec',     ['Sc'], [Case.value_n2v(lambda t: 1/math.cos(t))], stability="alpha")
    cput('Csc',     ['Cc'], [Case.value_n2v(lambda t: 1/math.sin(t))], stability="alpha")
    cput('Cot',     ['Ct'], [Case.value_n2v(lambda t: 1/math.tan(t))], stability="alpha")
    cput('Exp',     ['Ex'], [Case.value_n2v(math.exp  )], stability="beta")
    cput('Log_e',   ['Ln'], [Case.value_n2v(math.log  )], stability="beta")
    cput('Log_ten', ['Lt'], [Case.value_n2v(math.log10)], stability="alpha")
    cput('Log_two', ['Lg'], [Case.value_n2v(math.log2 )], stability="alpha")
    # }}}
    # Character conversion and predicates (letter-case etc) {{{
    cput('Lowercase', ['Lc'], [Case.value(lambda env, x: [pd_deepmap_s2s(lambda e: e.lower() , x)])], stability="beta")
    cput('Uppercase', ['Uc'], [Case.value(lambda env, x: [pd_deepmap_s2s(lambda e: e.upper() , x)])], stability="beta")
    cput('Exchange_case', ['Xc'], [Case.value(lambda env, x: [pd_deepmap_s2s(lambda e: e.swapcase(), x)])], stability="alpha")
    # TODO: this doesn't work on, say, lists of chars
    cput('Title_case', ['Tc'], [Case.value(lambda env, x: [pd_deepmap_s2s(lambda e: e.title(), x)])], stability="alpha")
    cput('Matching_character', ['Mc'], [
        Case.value(lambda env, x: [pd_deepmap_s2s(
            lambda e: num.matching_dict.get(e, e), x, whole_str_ok=False)])
    ],
        stability="alpha")

    cput('Is_alpha', ['Ap'], [Case.value(lambda env, x: [pd_deepmap_s2v(lambda e: int(e.isalpha()), x)])], stability="beta")
    cput('Is_lower', ['Lp'], [Case.value(lambda env, x: [pd_deepmap_s2v(lambda e: int(e.islower()), x)])], stability="beta")
    cput('Is_upper', ['Up'], [Case.value(lambda env, x: [pd_deepmap_s2v(lambda e: int(e.isupper()), x)])], stability="beta")
    cput('Is_space', ['Wp'], [Case.value(lambda env, x: [pd_deepmap_s2v(lambda e: int(e.isspace()), x)])], stability="alpha")
    cput('Value_of_character', ['Vc'], [
        Case.value(lambda env, x: [pd_deepmap_s2v(lambda e: num.value_dict.get(e, 0), x)])
    ],
            stability="alpha")
    cput('Nest_of_character', ['Nc'], [
        Case.value(lambda env, x: [pd_deepmap_s2v(lambda e: num.nest_dict.get(e, 0), x)])
    ],
            stability="alpha")
    # }}}
    # Replicate, fill/pad {{{

    cput('Replicate', ['°', 'Rp'], [
        Case.any_number(lambda env, x, n: [pd_replicate(x, num.intify(n))]),
    ],
            docs="""Make a list by repeating an element some number of
            times.""",
            stability="beta")

    cput('Signed_replicate', ['Sr'], [
        Case.any_any_number(lambda env, x, y, n: [
            pd_replicate(y, num.intify(n))
            if num.intify(n) >= 0 else
            pd_replicate(x, -num.intify(n))
        ]),
    ],
            docs="""Make a list by repeating one of two elements some number of
            times, the first one if negative and the second one if
            positive.""",
            stability="unstable")

    # Left-padding is right-justifying and vice versa...

    def char_biased_pad_cases(
            f: Callable[[str, int], str]) -> List[Case]:
        return [
            Case.char_number(lambda env, c, n: [f(env.pd_str(c), num.intify(n))]),
            Case.value_number(lambda env, c, n: [f(env.pd_str(c), num.intify(n))]),
        ]

    cput('Zero_fill',  ['Zf'],
        char_biased_pad_cases(lambda s, n: s.rjust(n, '0')),
            docs="""Given a value and a length, convert the value to a string
            if necessary and left-pad it with zeroes until at least the
            length.""",
            stability="unstable")
    cput('Left_fill',  ['<f'],
        char_biased_pad_cases(lambda s, n: s.rjust(n)),
            docs="""Given a value and a length, convert the value to a string
            if necessary and left-pad it with spaces until at least the
            length.""",
            stability="unstable")
    cput('Right_fill', ['>f'],
        char_biased_pad_cases(lambda s, n: s.ljust(n)),
            docs="""Given a value and a length, convert the value to a string
            if necessary and right-pad it with spaces until at least the
            length.""",
            stability="unstable")
    cput('Center_fill', ['=f'],
        char_biased_pad_cases(lambda s, n: s.center(n)),
            docs="""Given a value and a length, convert the value to a string
            if necessary and pad it with equally many spaces on either side
            until at least the length.""",
            stability="unstable")
    cput('Left_add_spaces',  ['«f'],
        char_biased_pad_cases(lambda s, n: ' ' * n + s),
            docs="""Given a value and a length, convert the value to a string
            if necessary and prepend that many spaces.""",
            stability="unstable")
    cput('Right_add_spaces', ['»f'],
        char_biased_pad_cases(lambda s, n: s + ' ' * n),
            docs="""Given a value and a length, convert the value to a string
            if necessary and append that many spaces.""",
            stability="unstable")

    cput('Space_repeat', [' x'], [
        Case.int_len(lambda env, n: [' ' * n]),
    ],
            stability="alpha")

    cput('Newline_repeat', ['\nx', '\\nx'], [
        Case.int_len(lambda env, n: ['\n' * n]),
    ],
            stability="alpha")
    # }}}
    # Key_* functions, for big arrays {{{
    cput('Key_new', ['Kn'], [
        Case.list_list_singleton_value(lambda env, kvs, dims, filler: [pd_new_array(kvs, dims, filler)]),
    ],
            docs="""Make an array given a starting list of key-value pairs,
            dimensions, and filler.""",
            stability="alpha")
    cput('Key_map', ['Km'], [
        Case.list_list_block(lambda env, arr, ks, func: [pd_array_keys_map(env, arr, ks, func)]),
    ],
            docs="""Map over keys of an array.""",
            stability="alpha")
    cput('Key_get', ['Kg'], [
        Case.list_list_singleton(lambda env, arr, k: [pd_array_key_get(arr, k)]),
    ],
            docs="""Access value corresponding to a key in an array.""",
            stability="alpha")
    # }}}
    # W for Window and W for Words {{{
    words_case  = Case.seq(lambda env, seq: [pd_split_seq_by(seq, ' ')])
    window_case = Case.number_seq(lambda env, n, seq: [pd_sliding_window_seq(seq, n)])
    while_case = Case.block2(lambda env, cond, body:
            pd_while_then_empty_list(env, cond, body))
    cput('Window', [], [window_case], stability="alpha")
    cput('Space_split', ['Words'], [words_case, window_case], stability="alpha")
    cput('While', [], [while_case],
            docs="""While loop: Execute first block, pop, break if false, execute
            second block, repeat.""",
            stability="alpha")
    cput('Window_or_words_or_while', ['W'], [words_case, window_case, while_case],
            docs="""Words (split by spaces) or Window (sliding window of size
            given by number) or While loop.""",
            stability="alpha")
    # }}}
    # Combinatorics {{{
    factorial_case = Case.number(
            lambda env, n: [discrete.factorial(num.numerify(n))]
    )
    permutation_cases = [
        Case.seq(lambda env, seq:
            [list(itertools.permutations(pd_iterable(seq)))]),
        Case.block_seq_range(lambda env, block, seq:
            [pd_map_iterable(env, block,
                map(list, itertools.permutations(pd_iterable(seq))))]),
    ]
    cput('Permutations', [], permutation_cases, stability="beta")
    cput('Factorial', [], [factorial_case], stability="beta")
    cput('Permutations_or_factorial', ['¡', '!p'],
            [factorial_case] + permutation_cases,
            stability="beta")
    binomial_coefficient_case = (
        Case.number2(lambda env, n, k: [discrete.binomial_coefficient(
            num.numerify(n), num.numerify(k))])
    )
    cput('Binomial_coefficient', ['Bc'], [binomial_coefficient_case],
            stability="beta")
    cput('Ç', [], [binomial_coefficient_case],
            docs="Unstable alias for {{ 'Binomial_coefficient'|b }}.",
            stability="unstable")
    # TODO: choose
    cput('Subsequences', ['¿'], [
        Case.number(lambda env, n: [2 ** num.numerify(n)]),
        Case.seq(lambda env, seq: [pd_subsequences_list(seq)]),
        Case.block_seq_range(lambda env, block, seq:
            [pd_map_iterable(env, block,
                pd_subsequences(seq))]),
    ],
            stability="beta")
    cput('Fibonacci', ['Fb'], [Case.number(
            lambda env, n: [discrete.fibonacci(num.numerify(n))]
    )],
            stability="beta")
    # }}}
    # Number theory (primes etc) {{{
    cput('Is_prime', ['Pp', '¶'], [
        Case.value_n2v(discrete.is_prime_as_int),
    ],
            docs="""Test if this is prime.""",
            stability="alpha")
    cput('Prev_prime', ['(p'], [
        Case.value_n2v(discrete.prev_prime),
    ],
            docs="""Find the largest prime smaller than this.""",
            stability="alpha")
    cput('Next_prime', [')p'], [
        Case.value_n2v(discrete.next_prime),
    ],
            docs="""Find the smallest prime larger than this.""",
            stability="alpha")
    cput('Factorize', ['Fc'], [
        Case.value_n2v(discrete.prime_factorization_wrapped),
    ],
            docs="""Factorize as a list of pairs of primes and exponents""",
            stability="alpha")
    cput('Factorize_flat', ['Ff'], [
        Case.value_n2v(discrete.prime_factorization_flat),
    ],
            docs="""Factorize as a flat list of possibly repeating prime
            factors""",
            stability="alpha")
    cput('Totient', ['Et'], [
        Case.value_n2v(discrete.totient),
    ],
            docs="Euler's totient function", stability="alpha")
    cput('Ø', [], [
        Case.value_n2v(discrete.totient),
    ],
            docs="Euler's {{ 'Totient'|b }} function (unstable alias)",
            stability="unstable")
    cput('Jacobi_symbol', ['Js'], [
        Case.number2(lambda env, m, n: [discrete.jacobi_symbol(num.numerify(m), num.numerify(n))]),
    ],
            docs="""Jacobi symbol of two numbers""",
            stability="unstable")
    # }}}
    # Time {{{
    cput('Now_time', ['Nt'], [Case.void(lambda env: [time.time()])], stability="alpha")
    now = datetime.datetime.now
    fromtimestamp = datetime.datetime.fromtimestamp

    cput('Now_minute',       ['Nb'], [Case.void     (lambda _: [           now().minute             ])], docs="Get the current minute", stability="alpha")
    cput('Time_minute',      ['Tb'], [Case.value_n2v(lambda e:  fromtimestamp(e).minute              )], docs="Get the minute from a timestamp", stability="alpha")
    cput('Now_day',          ['Nd'], [Case.void     (lambda _: [           now().day                ])], docs="Get the current day", stability="alpha")
    cput('Time_day',         ['Td'], [Case.value_n2v(lambda e:  fromtimestamp(e).day                 )], docs="Get the day from a timestamp", stability="alpha")
    cput('Now_hour',         ['Nh'], [Case.void     (lambda _: [           now().hour               ])], docs="Get the current hour", stability="alpha")
    cput('Time_hour',        ['Th'], [Case.value_n2v(lambda e:  fromtimestamp(e).hour                )], docs="Get the hour from a timestamp", stability="alpha")
    cput('Now_twelve_hour',  ['Ni'], [Case.void     (lambda _: [          (now().hour - 1) % 12 + 1 ])], docs="Get the current hour, as a number from 1 to 12", stability="alpha")
    cput('Time_twelve_hour', ['Ti'], [Case.value_n2v(lambda e: (fromtimestamp(e).hour - 1) % 12 + 1  )], docs="Get the hour, as a number from 1 to 12 from a timestamp", stability="alpha")
    cput('Now_day_of_year',  ['Nj'], [Case.void     (lambda _: [           now().timetuple().tm_yday])], docs="Get the current day of year", stability="alpha") # type: ignore
    cput('Time_day_of_year', ['Tj'], [Case.value_n2v(lambda e:  fromtimestamp(e).timetuple().tm_yday )], docs="Get the day of year from a timestamp", stability="alpha") # type: ignore
    cput('Now_month',        ['Nm'], [Case.void     (lambda _: [           now().month              ])], docs="Get the current month", stability="alpha")
    cput('Time_month',       ['Tm'], [Case.value_n2v(lambda e:  fromtimestamp(e).month               )], docs="Get the month from a timestamp", stability="alpha")
    cput('Now_second',       ['Ns'], [Case.void     (lambda _: [           now().second             ])], docs="Get the current second", stability="alpha")
    cput('Time_second',      ['Ts'], [Case.value_n2v(lambda e:  fromtimestamp(e).second              )], docs="Get the second from a timestamp", stability="alpha")
    cput('Now_iso_weekday',  ['Nv'], [Case.void     (lambda _: [           now().isoweekday()       ])], docs="Get the current ISO weekday (Monday is 1, Sunday is 7)", stability="alpha")
    cput('Time_iso_weekday', ['Tv'], [Case.value_n2v(lambda e:  fromtimestamp(e).isoweekday()        )], docs="Get the ISO weekday (Monday is 1, Sunday is 7) from a timestamp", stability="alpha")
    cput('Now_weekday',      ['Nw'], [Case.void     (lambda _: [           now().weekday()          ])], docs="Get the current weekday (Monday is 0, Sunday is 6)", stability="alpha")
    cput('Time_weekday',     ['Tw'], [Case.value_n2v(lambda e:  fromtimestamp(e).weekday()           )], docs="Get the weekday (Monday is 0, Sunday is 6) from a timestamp", stability="alpha")
    cput('Now_year',         ['Ny'], [Case.void     (lambda _: [           now().year               ])], docs="Get the current year", stability="alpha")
    cput('Time_year',        ['Ty'], [Case.value_n2v(lambda e:  fromtimestamp(e).year                )], docs="Get the year from a timestamp", stability="alpha")
    # }}}
    # Randomness {{{
    cput('Random_float', ['Rf'], [Case.void(lambda env: [random.random()])],
            stability="alpha")
    cput('Random_gaussian', ['Rg'], [
        Case.void(lambda env: [random.gauss(0, 1)])
    ],
            stability="alpha")
    cput('Random_int', ['Ri'], [
        Case.number(lambda env, n: [random.randrange(num.intify(n))])
    ],
            stability="alpha")
    cput('Random_choice', ['Rc'], [
        Case.seq(lambda env, seq: [random.choice(seq)])
    ],
            stability="alpha")
    @put('Random_seed', stability="alpha")
    def random_seed(env: Environment) -> None:
        e = env.pop()
        if isinstance(e, (Char, int, float)):
            random.seed(num.intify(e))
        elif isinstance(e, str):
            random.seed(e)
        else:
            raise AssertionError("Can't seed random with non-numeric non-string value " + repr(e))
    # }}}
    # Stack functions {{{
    @put('Reverse_stack', 'Down_stack', 'Ds',
            stability="beta")
    def reverse_stack(env: Environment) -> None:
        env.push(*env.pop_until_stack_marker()[::-1])
    @put('Length_stack', 'Ls',
            stability="beta")
    def length_stack(env: Environment) -> None:
        env.push(len(env.pop_until_stack_marker()))
    @put('Sum_stack', 'Šs',
            stability="beta")
    def sum_stack(env: Environment) -> None:
        env.push(pd_deep_sum(env.pop_until_stack_marker()))
    @put('Product_stack', 'Þs',
            stability="beta")
    def product_stack(env: Environment) -> None:
        # TODO: make this a deepmap or something?
        env.push(pd_deep_product(env.pop_until_stack_marker()))
    @put('Force_stack', 'Fs',
            stability="alpha")
    def force_stack(env: Environment) -> None:
        env.maximize_length()
    @put('Output_stack', 'Os',
            stability="beta")
    def output_stack(env: Environment) -> None:
        print(env.pd_str(env.pop_until_stack_marker()), end="")
    @put('Print_stack', 'Ps',
            stability="beta")
    def print_stack(env: Environment) -> None:
        env.print_output_record(env.pd_str(env.pop_until_stack_marker()))
    # }}}
    # Bullet assignment {{{
    @put('Assign_bullet', '·', docs="Assign to the variable •",
            stability="alpha")
    def assign_bullet(env: Environment) -> None:
        e = env.pop()
        env.push(e)
        env.put(BULLET, e)
    @put('Assign_bullet_destructive', '–', docs="Pop and assign to the variable •",
            stability="alpha")
    def assign_bullet_destructive(env: Environment) -> None:
        e = env.pop()
        env.put(BULLET, e)
    @put('Append_to_bullet', '©', docs="Pop and append to the variable •",
            stability="alpha")
    def append_to_bullet(env: Environment) -> None:
        assign.append_func(env, BULLET)
    @put('Retrieve_bullet', '®',
            docs="""Push the current value of the variable •, then reset that
            variable to 0.""",
            stability="alpha")
    def retrieve_bullet(env: Environment) -> None:
        assign.retrieve_func(env, BULLET)
    # }}}
    # unsafe metacomputing {{{
    @put('Sleep', 'Sl', docs="Sleep for some number of seconds.",
            stability="alpha")
    def sleep(env: Environment) -> None:
        e = env.pop()
        assert isinstance(e, (Char, int, float))
        time.sleep(num.numerify(e))

    if sandboxed:
        @put('Python', 'Py',
                docs="""Evaluate arbitrary Python code. Push the result if
                non-None.

                Disabled in sandbox mode.""",
                stability="alpha")
        def python_eval_disabled(env: Environment) -> None:
            raise Exception('Python eval disabled in sandbox mode')

        @put('Shell', 'Sh',
                docs="""Evaluate shell code. If given a string, executes it
                through the shell; if given a list, executes the first element
                as the executable with the following elements of the list as
                arguments. Pushes the stdout of the subprocess.

                Disabled in sandbox mode.""",
                stability="alpha")
        def shell_eval_disabled(env: Environment) -> None:
            raise Exception('Shell eval disabled in sandbox mode')
    else:

        @put('Python', 'Py',
                docs="""Evaluate arbitrary Python code. Push the result if
                non-None. Unsafe!""",
                stability="alpha")
        def python_eval(env: Environment) -> None:
            e = env.pop()
            res = eval(env.pd_str(e))
            if res is not None:
                env.push(res)

        @put('Shell', 'Sh',
                docs="""Evaluate arbitrary shell code. Push the result if
                non-None. Unsafe!""",
                stability="alpha")
        def shell_eval(env: Environment) -> None:
            import subprocess
            e = env.pop()
            if isinstance(e, list):
                proc = subprocess.Popen([env.pd_str(x) for x in e],
                        stdout=subprocess.PIPE)
            elif isinstance(e, str):
                proc = subprocess.Popen(e, shell=True, stdout=subprocess.PIPE)
            else:
                raise Exception("Cannot evaluate non-list non-str as Shell")
            env.push(proc.communicate()[0])

    # }}}
    env.lazy_var_triggers.append(arithmetic_literal_trigger)

# vim:set tabstop=4 shiftwidth=4 expandtab fdm=marker:
