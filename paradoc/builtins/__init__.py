# coding: utf-8
# vim:set expandtab fdm=marker:
from paradoc.objects import *
# import paradoc.objects
import paradoc.num as num
import sys, math, collections
from paradoc.builtins.case import Case, CasedBuiltIn

def initialize_builtins(env: Environment) -> None:

    def put(*ss: str) -> Callable[[Callable[[Environment], None]], None]:
        def inner_put(f: Callable[[Environment], None]) -> None:
            for s in ss:
                env.put(s, BuiltIn(s, f))
        return inner_put

    def cput(name: str, extra_names: List[str], cases: List[Case]):
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
    # }}}
    # Universal functions: stack stuff, list stuff {{{

    @put('Nop', ' ', '\t', '\n', '\r')
    def nop(env: Environment) -> None: pass

    # @put('Dup', ':')
    # def dup(env: Environment) -> None:
    #     a = env.pop()
    #     env.push(a, a)

    cput('Dup', [':'], [
        Case.any(lambda x: [x, x])
    ])

    @put('Swap', '\\')
    def swap(env: Environment) -> None:
        b, a = env.pop2()
        env.push(b, a)
    @put('Rotate', 'Rot', '@')
    def rotate(env: Environment) -> None:
        c, b, a = env.pop3()
        env.push(b, c, a)
    @put('Pop', ';')
    def pop(env: Environment) -> None:
        env.pop()
    @put('Repr', '`')
    def repr_builtin(env: Environment) -> None:
        a = env.pop()
        env.push(pd_repr(a))
    @put('[', 'Mark')
    def mark(env: Environment) -> None:
        env.mark_stack()
    @put(']', 'Pack')
    def pack(env: Environment) -> None:
        env.push(env.pop_until_stack_marker())
    # }}}
    # Not {{{
    @put('!', 'Not')
    def pd_not(env: Environment) -> None:
        a = env.pop()
        env.push(int(not a))
    # }}}
    # "Arithmetic" inc Octothorpe {{{

    @put('Plus', '+')
    def plus(env: Environment) -> None:
        b, a = env.pop2()
        if isinstance(a, (Char, int, float)) and isinstance(b, (Char, int, float)):
            env.push(num.pd_add(a, b))
        elif isinstance(a, (list, range)) and isinstance(b, (list, range)):
            env.push(list(a) + list(b))
        elif isinstance(a, (str, list)) and isinstance(b, (str, list)):
            env.push(env.pd_str(a) + env.pd_str(b))
        elif isinstance(a, Block) and isinstance(b, (str, list, range)):
            env.push(pd_filter(env, a, b))
        elif isinstance(b, Block) and isinstance(a, (str, list, range)):
            env.push(pd_filter(env, b, a))
        else:
            raise NotImplementedError(repr(('Plus', a, b)))

    @put('-', 'Minus')
    def minus(env: Environment) -> None:
        b, a = env.pop2()
        if isinstance(a, (Char, int, float)) and isinstance(b, (Char, int, float)):
            env.push(num.pd_sub(a, b))
        elif isinstance(a, Block) and isinstance(b, (str, list, range)):
            env.push(pd_filter_not(env, a, b))
        elif isinstance(b, Block) and isinstance(a, (str, list, range)):
            env.push(pd_filter_not(env, b, a))
        else:
            raise NotImplementedError

    @put('*', 'Mul')
    def mul(env: Environment) -> None:
        b, a = env.pop2()
        if isinstance(a, (Char, int, float)) and isinstance(b, (Char, int, float)):
            env.push(num.pd_mul(a, b))
        elif isinstance(a, (Char, int, float)) and isinstance(b, (str, list, range)):
            env.push(pd_mul_seq(b, a))
        elif isinstance(b, (Char, int, float)) and isinstance(a, (str, list, range)):
            env.push(pd_mul_seq(a, b))
        elif isinstance(b, Block):
            lst = pd_to_list_range(a)
            pd_foreach_x_only(env, b, lst)
        elif isinstance(a, Block):
            lst = pd_to_list_range(b)
            pd_foreach_x_only(env, a, lst)
        else:
            raise NotImplementedError(repr(('*', a, b)))

    @put('/', 'Slash')
    def slash(env: Environment) -> None:
        b, a = env.pop2()
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            env.push(num.pd_div(a, b))
        elif isinstance(a, Block) and isinstance(b, (list, str, range)):
            pd_foreach(env, a, b)
        elif isinstance(b, Block) and isinstance(a, (list, str, range)):
            pd_foreach(env, b, a)
        else:
            raise NotImplementedError(repr(a) + repr(b))

    @put('%')
    def percent(env: Environment) -> None:
        b, a = env.pop2()
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            env.push(a % b)
        elif isinstance(a, Block):
            env.push(pd_map(env, a, pd_to_list_range(b)))
        elif isinstance(b, Block):
            env.push(pd_map(env, b, pd_to_list_range(a)))
        else:
            raise NotImplementedError(repr(a) + repr(b))

    @put('#')
    def octothorpe(env: Environment) -> None:
        b, a = env.pop2()
        if isinstance(a, (float, int)) and isinstance(b, (float, int)):
            env.push(a ** b)
        elif isinstance(a, Block) and isinstance(b, (list, str, range)):
            i, e = pd_find_entry(env, a, b)
            assert e is not None
            env.push(e)
        elif isinstance(b, Block) and isinstance(a, (list, str, range)):
            i, e = pd_find_entry(env, b, a)
            assert e is not None
            env.push(e)
        else:
            raise NotImplementedError
    # }}}

    # Sort, $ {{{
    @put('Sort')
    def pd_sort(env: Environment) -> None:
        a = env.pop()
        if isinstance(a, str):
            env.push(''.join(sorted(a)))
        elif isinstance(a, (list, range)):
            env.push(list(sorted(a)))
        else:
            raise NotImplementedError

    @put('$')
    def dollar(env: Environment) -> None:
        a = env.pop()
        if isinstance(a, int):
            env.push(env.index_stack(a))
        elif isinstance(a, str):
            env.push(''.join(sorted(a)))
        elif isinstance(a, (list, range)):
            env.push(list(sorted(a)))
        else:
            raise NotImplementedError
    # }}}
    # Comma, J{{{
    @put(',')
    def comma(env: Environment) -> None:
        a = env.pop()
        if isinstance(a, int):
            env.push(range(a))
        elif isinstance(a, (str, list, range)):
            env.push(pd_enumerate(a))
        elif isinstance(a, Block):
            b = env.pop()
            if isinstance(b, (list, str, range)):
                env.push(pd_filter_indexes(env, a, b))
            else:
                raise NotImplementedError
        else:
            raise NotImplementedError
    @put('J')
    def pd_j(env: Environment) -> None:
        a = env.pop()
        if isinstance(a, (float, int)):
            env.push(range(1, int(a) + 1))
        elif isinstance(a, (str, list, range)):
            env.push(pd_enumerate(a, start=1))
        elif isinstance(a, Block):
            b = env.pop()
            if isinstance(b, (list, str, range)):
                env.push(pd_filter_not(env, a, b))
            else:
                raise NotImplementedError
        else:
            raise NotImplementedError
    # }}}
    # Binary operators &|^ {{{
    @put('|')
    def vertical_bar(env: Environment) -> None:
        b, a = env.pop2()
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            env.push(int(a) | int(b))
        elif isinstance(a, (str, range, list)) and isinstance(b, (str, range, list)):
            counter = collections.Counter(pd_iterable(a))
            acc = list(pd_iterable(a)) # type: List[PdObject]
            for element in pd_iterable(b):
                if counter[element] > 0:
                    counter[element] -= 1
                else:
                    acc.append(element)
            env.push(pd_build_like(a, acc))
        elif isinstance(a, Block):
            if not b: a(env)
        elif isinstance(b, Block):
            if not a: b(env)
        else:
            raise NotImplementedError(repr(a) + repr(b))

    @put('&')
    def ampersand(env: Environment) -> None:
        b, a = env.pop2()
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            env.push(int(a) & int(b))
        elif isinstance(a, (str, range, list)) and isinstance(b, (str, range, list)):
            counter = collections.Counter(pd_iterable(b))
            acc = [] # type: List[PdObject]
            for element in pd_iterable(a):
                if counter[element] > 0:
                    acc.append(element)
                    counter[element] -= 1
            env.push(pd_build_like(a, acc))
        elif isinstance(b, Block):
            if pytruth_eval(env, a): b(env)
        elif isinstance(a, Block):
            if pytruth_eval(env, b): a(env)
        else:
            raise NotImplementedError(repr(a) + repr(b))

    @put('^')
    def caret(env: Environment) -> None:
        b, a = env.pop2()
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            env.push(int(a) ^ int(b))
        elif isinstance(a, (str, range, list)) and isinstance(b, (str, range, list)):
            set_a = collections.Counter(pd_iterable(a))
            set_b = collections.Counter(pd_iterable(b))
            acc = [] # type: List[PdObject]
            for element in pd_iterable(a):
                if element not in set_b:
                    acc.append(element)
            for element in pd_iterable(b):
                if element not in set_a:
                    acc.append(element)
            env.push(pd_build_like(a, acc))
        else:
            raise NotImplementedError(repr(a) + repr(b))

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

    # Comparators <=> Max Min {{{

    @put('Eq', 'Equal')
    def equal_builtin(env: Environment) -> None:
        b, a = env.pop2()
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            env.push(int(a == b))
        elif isinstance(a, str) and isinstance(b, str):
            env.push(int(a == b))
        elif isinstance(a, list) and isinstance(b, list):
            env.push(int(a == b))
        else:
            raise NotImplementedError(repr(a) + repr(b))

    @put('=')
    def equal_sign_builtin(env: Environment) -> None:
        b, a = env.pop2()
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            env.push(int(a == b))
        elif isinstance(a, str) and isinstance(b, str):
            env.push(int(a == b))
        elif isinstance(a, list) and isinstance(b, list):
            env.push(int(a == b))
        elif isinstance(a, (list, range)) and isinstance(b, int):
            env.push(a[b])
        elif isinstance(b, (list, range)) and isinstance(a, int):
            env.push(b[a])
        elif isinstance(a, str) and isinstance(b, int):
            env.push(Char(ord(a[b])))
        elif isinstance(b, str) and isinstance(a, int):
            env.push(Char(ord(b[a])))
        elif isinstance(a, Block) and isinstance(b, list):
            i, e = pd_find_entry(env, a, b)
            assert i is not None
            env.push(i)
        elif isinstance(b, Block) and isinstance(a, list):
            i, e = pd_find_entry(env, b, a)
            assert i is not None
            env.push(i)
        else:
            raise NotImplementedError(repr(a) + repr(b))

    @put('<')
    def less_than(env: Environment) -> None:
        b, a = env.pop2()
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            env.push(int(a < b))
        elif isinstance(a, str) and isinstance(b, str):
            env.push(int(a < b))
        elif isinstance(a, list) and isinstance(b, list):
            env.push(int(a < b))
        elif isinstance(a, (int, float)) and isinstance(b, (str, list, range)):
            env.push(b[:int(a)])
        elif isinstance(b, (int, float)) and isinstance(a, (str, list, range)):
            env.push(a[:int(b)])
        else:
            raise NotImplementedError(repr(('<', a, b)))

    @put('>')
    def greater_than(env: Environment) -> None:
        b, a = env.pop2()
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            env.push(int(a > b))
        elif isinstance(a, str) and isinstance(b, str):
            env.push(int(a > b))
        elif isinstance(a, list) and isinstance(b, list):
            env.push(int(a > b))
        elif isinstance(a, (int, float)) and isinstance(b, (str, list, range)):
            env.push(b[int(a):])
        elif isinstance(b, (int, float)) and isinstance(a, (str, list, range)):
            env.push(a[int(b):])
        else:
            raise NotImplementedError(repr(a) + repr(b))

    @put('Min', '<m', 'Õ')
    def pd_min(env: Environment) -> None:
        b, a = env.pop2()
        env.push(min(a, b))

    @put('Max', '>m', 'Ã')
    def pd_max(env: Environment) -> None:
        b, a = env.pop2()
        env.push(max(a, b))

    @put('List_min', '<l', 'Œ')
    def pd_list_min(env: Environment) -> None:
        a = env.pop()
        env.push(min(pd_to_list_range(a)))

    @put('List_max', '>l', 'Æ')
    def pd_list_max(env: Environment) -> None:
        a = env.pop()
        env.push(max(pd_to_list_range(a)))


    # }}}

    # «»‹› {{{
    @put('«')
    def pd_double_left(env: Environment) -> None:
        a = env.pop()
        if isinstance(a, (Char, int, float)):
            env.push(num.pd_add_const(a, -2))
        elif isinstance(a, (str, list, range)):
            env.push(a[:-1])
        else:
            raise NotImplementedError(repr(('«', a)))
    @put('»')
    def pd_double_right(env: Environment) -> None:
        a = env.pop()
        if isinstance(a, (Char, int, float)):
            env.push(num.pd_add_const(a, 2))
        elif isinstance(a, (str, list, range)):
            env.push(a[1:])
        else:
            raise NotImplementedError(repr(('»', a)))
    @put('‹')
    def pd_single_left(env: Environment) -> None:
        a = env.pop()
        if isinstance(a, (Char, int)):
            env.push(a)
        elif isinstance(a, float):
            env.push(int(math.floor(a)))
        elif isinstance(a, (str, list, range)):
            env.push(a[0])
        else:
            raise NotImplementedError(repr(('‹', a)))
    @put('›')
    def pd_single_right(env: Environment) -> None:
        a = env.pop()
        if isinstance(a, (Char, int)):
            env.push(a)
        elif isinstance(a, float):
            env.push(int(math.ceil(a)))
        elif isinstance(a, (str, list, range)):
            env.push(a[-1])
        else:
            raise NotImplementedError(repr(('›', a)))
    # }}}
    # Uncons, Unsnoc {{{
    @put('Uncons')
    def uncons(env: Environment) -> None:
        a = env.pop()
        assert isinstance(a, (str, list, range))
        env.push(a[1:], a[0])
    @put('Unsnoc')
    def unsnoc(env: Environment) -> None:
        a = env.pop()
        assert isinstance(a, (str, list, range))
        env.push(a[:-1], a[-1])
    # }}}

    # Parens () {{{

    @put('(')
    def left_paren(env: Environment) -> None:
        a = env.pop()
        if isinstance(a, (Char, int, float)):
            env.push(num.pd_add_const(a, -1))
        elif isinstance(a, (str, list, range)):
            env.push(a[1:], a[0])
        else:
            raise NotImplementedError

    @put(')')
    def right_paren(env: Environment) -> None:
        a = env.pop()
        if isinstance(a, (Char, int, float)):
            env.push(num.pd_add_const(a, 1))
        elif isinstance(a, (str, list, range)):
            env.push(a[:-1], a[-1])
        else:
            raise NotImplementedError
    # }}}

    @put('~')
    def tilde(env: Environment) -> None:
        a = env.pop()
        if isinstance(a, Block):
            a(env)
        elif isinstance(a, str):
            env.evaluate(a)
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

    @put('Range')
    def pd_range(env: Environment) -> None:
        a = env.pop()
        assert isinstance(a, (float, int))
        env.push(range(int(a)))


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

    @put('Ro', 'Range_one')
    def range_one(env: Environment) -> None:
        a = env.pop()
        assert isinstance(a, (float, int))
        env.push(range(1, int(a) + 1))



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

    @put('Sum', 'Ç')
    def pd_sum(env: Environment) -> None:
        a = env.pop()
        env.push(sum(pd_to_list_range(a)))

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

    def pd_constant_fraction(env: Environment, p: int, q: int) -> None:
        a = env.pop()
        if isinstance(a, (Char, int, float)):
            env.push(num.pd_mul_div_const(a, p, q))
        elif isinstance(a, (str, list, range)):
            if p <= q:
                env.push(a[:len(a)*p//q])
            else:
                assert q == 1
                env.push(pd_mul_seq(a, p))
        elif isinstance(a, Block):
            assert q == 1
            pd_foreach_x_only(env, a, range(p))
        else:
            raise NotImplementedError(repr(a))

    @put('Halve', '½')
    def pd_halve(env: Environment) -> None:
        pd_constant_fraction(env, 1, 2)
    @put('Quarter', '¼')
    def pd_quarter(env: Environment) -> None:
        pd_constant_fraction(env, 1, 4)
    @put('Three_quarters', '¾')
    def pd_three_quarter(env: Environment) -> None:
        pd_constant_fraction(env, 3, 4)
    @put('Double', '•', '∙')
    def pd_bullet_double(env: Environment) -> None:
        pd_constant_fraction(env, 2, 1)

    # }}}

    @put('L')
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

    @put('ˆ', 'Replicate')
    def pd_replicate(env: Environment) -> None:
        a = env.pop()
        if isinstance(a, (Char, int, float)):
            b = env.pop()
            if isinstance(b, Char):
                env.push(num.intify(a) * chr(b.ord))
            else:
                env.push(num.intify(a) * [b])
        else:
            raise NotImplementedError(repr(a))

    @put('Debug', 'Dump')
    def dump(env: Environment) -> None:
        print('Dump:', env.debug_dump(), file=sys.stderr)

