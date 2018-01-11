# coding: utf-8
import typing
from typing import (
        Callable, Dict, Generator, Match, Iterable, Iterator, List, Optional,
        Set, Tuple, TypeVar, Union, overload,
        )
import sys
import math
from paradoc.num import Char, PdNum
import paradoc.num as num
import collections
import random
import itertools

T = TypeVar('T')

# Objects in the Paradoc runtime (type PdObject).

# Block, BuiltIn {{{
# Probably un-Pythonic superclass to allow isinstance and mypy tests:
class Block:
    def __call__(self, env: 'Environment') -> None:
        raise NotImplementedError
    def code_repr(self) -> str:
        raise NotImplementedError

class BuiltIn(Block):
    def __init__(self,
            name: str,
            func: Callable[['Environment'], None],
            aliases: Optional[List[str]] = None,
            docs: Optional[str] = None,
            stability: str = "unknown") -> None:
        self.name = name
        self.aliases: List[str] = aliases or [name]
        self.func = func
        self.docs = docs
        self.stability = stability

    def __call__(self, env: 'Environment') -> None:
        self.func(env)

    def code_repr(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return '<BuiltIn {}>'.format(self.name)
# }}}

PdSeq = Union[str, list, range]
PdValue = Union[PdNum, PdSeq]
PdObject = Union[PdValue, Block]

PdKey = Union[PdNum, str, tuple, range]

# exceptions {{{
class PdEmptyStackException(Exception): pass
class PdEndOfFileException(Exception): pass
class PdAbortException(Exception):
    def __init__(self, msg: str, code: int = 0) -> None:
        super(Exception, self).__init__(msg)
        self.code = code
class PdBreakException(Exception): pass
class PdContinueException(Exception): pass
# }}}
# x_index {{{
def x_index(token: str) -> Optional[int]:
    if token == 'X': return 0
    elif token == 'Y': return 1
    elif token == 'Z': return 2
    # TODO it's pretty unclear if this is actually what we want
    elif token == 'Xx' or token == 'Ž': return 3
    elif token == 'Xy': return 4
    elif token == 'Xz': return 5
    elif token == 'Yx': return 6
    elif token == 'Yy': return 7
    elif token == 'Yz': return 8
    elif token == 'Zx': return 6
    elif token == 'Zy': return 7
    elif token == 'Zz': return 8
    else: return None
# }}}
class Environment: # {{{
    def __init__(self,
            evaluator: Callable[['Environment', str], None],
            input_trigger: Optional[Callable[[], Optional[PdObject]]] = None,
            stack_trigger: Callable[[], Optional[PdObject]] = lambda: None,
            stack: Optional[List[PdObject]] = None,
            x_stack: Optional[List[PdObject]] = None,
            vars_delegate: Optional['Environment'] = None,
            lazy_var_triggers: Optional[List[Callable[[str], Optional[PdObject]]]] = None) -> None:
        self.evaluator = evaluator
        self.input_trigger = input_trigger
        self.stack_trigger = stack_trigger
        self.vars:          Dict[str, PdObject] = dict()
        self.var_docs:      Dict[str, str]      = dict()
        self.var_stability: Dict[str, str]      = dict()
        self._stack:   List[PdObject] =   stack or []
        self._x_stack: List[PdObject] = x_stack or [0, [], '']
        self.STACK_TRIGGER_X = 2 # ???
        self.vars_delegate = vars_delegate
        self.lazy_var_triggers: List[Callable[[str], Optional[PdObject]]] = lazy_var_triggers or []
        self.marker_stack: List[int] = []

    def evaluate(self, code: str) -> None:
        self.evaluator(self, code)

    def run_input_trigger(self) -> Optional[PdObject]:
        if self.input_trigger is None:
            return None
        else:
            return self.input_trigger()

    def index_x(self, index: int) -> PdObject:
        if self.vars_delegate is None:
            return self._x_stack[-1-index]
        else:
            return self.vars_delegate.index_x(index)

    def set_x(self, index: int, val: PdObject) -> None:
        if self.vars_delegate is None:
            self._x_stack[-1-index] = val
        else:
            self.vars_delegate.set_x(index, val)

    def push_x(self, obj: PdObject) -> None:
        if self.vars_delegate is None:
            self._x_stack.append(obj)
        else:
            self.vars_delegate.push_x(obj)

    def pop_x(self) -> PdObject:
        if self.vars_delegate is None:
            return self._x_stack.pop()
        else:
            return self.vars_delegate.pop_x()

    def push_yx(self,
            y: str = 'INTERNAL Y FILLER -- YOU SHOULD NOT SEE THIS',
            x: str = 'INTERNAL X FILLER -- YOU SHOULD NOT SEE THIS') -> None:
        self.push_x(y)
        self.push_x(x)

    def pop_yx(self) -> None:
        self.pop_x()
        self.pop_x()

    def set_yx(self, y: PdObject, x: PdObject) -> None:
        self.set_x(0, x)
        self.set_x(1, y)

    def set_x_top(self, obj: PdObject) -> None:
        self.set_x(0, obj)

    def x_stack_repr(self) -> str:
        if self.vars_delegate is None:
            return repr(self._x_stack)
        else:
            return self.vars_delegate.x_stack_repr()

    def get_or_none(self, token: str) -> Optional[PdObject]:
        xi = x_index(token)
        if xi is not None:
            return self.index_x(xi)
        if self.vars_delegate is None:
            ret = self.vars.get(token)
            if ret is None:
                for lvt in self.lazy_var_triggers:
                    ret = lvt(token)
                    if ret is not None: return ret
            return ret
        else:
            return self.vars_delegate.get_or_none(token)

    def get(self, token: str) -> PdObject:
        ret = self.get_or_none(token)
        if ret is None:
            raise Exception('No variable with name ' + repr(token))
        else: return ret

    def get_or_else(self, token: str, other: PdObject) -> PdObject:
        ret = self.get_or_none(token)
        if ret is None: return other
        else: return ret

    def put(self, token: str, val: PdObject,
            docs: Optional[str] = None,
            stability: Optional[str] = None,
            fail_if_overwrite: bool = False) -> None:
        xi = x_index(token)
        if xi is not None:
            self.set_x(xi, val)
        elif self.vars_delegate is None:
            if fail_if_overwrite and token in self.vars:
                raise AssertionError('Failing on overwriting ' + repr(token))
            self.vars[token] = val
            if docs is not None:
                self.var_docs[token] = docs
            if stability is not None:
                self.var_stability[token] = stability
        else:
            self.vars_delegate.put(token, val)

    def push(self, *vals: PdObject) -> None:
        for val in vals:
            self._stack.append(val)

    def push_env(self, other: 'Environment') -> None:
        self.push(*other._stack)

    def push_keep_shadow_env_under(self, other: 'KeepShadowEnvironment') -> None:
        shadow_temp = self.pop_n(other.shadow_i)
        self.push(*other._stack)
        self.push(*shadow_temp)

    def push_or_eval(self, *vals: PdObject) -> None:
        for val in vals:
            if isinstance(val, Block):
                val(self)
            else:
                self.push(val)

    def pop_or_none(self) -> Optional[PdObject]:
        try:
            ret = self._stack.pop()
            stack_len = len(self._stack)
            for i in range(len(self.marker_stack) - 1, -1, -1):
                if self.marker_stack[i] > stack_len:
                    self.marker_stack[i] = stack_len
                else:
                    break
            return ret
        except IndexError:
            res = self.stack_trigger()
            if res is None:
                return None
            else:
                if self.vars_delegate is None:
                    self._x_stack[self.STACK_TRIGGER_X] = res
                return res

    def pop(self) -> PdObject:
        res = self.pop_or_none()
        if res is None:
            raise PdEmptyStackException('Empty stack')
        else:
            return res

    def pop_n(self, n: int) -> List[PdObject]:
        acc: List[PdObject] = []
        for _ in range(n):
            acc.append(self.pop())
        return acc[::-1]

    def try_ensure_length(self, n: int) -> None:
        if len(self._stack) < n:
            diff = n - len(self._stack)
            acc = []
            for _ in range(diff):
                trig = self.stack_trigger()
                if trig is None: break
                acc.append(trig)
            self._stack = acc[::-1] + self._stack

    def maximize_length(self) -> None:
        acc = []
        while True:
            trig = self.stack_trigger()
            if trig is None: break
            acc.append(trig)
        self._stack = acc[::-1] + self._stack

    def peek(self) -> PdObject:
        return self._stack[-1]

    def pop2(self) -> Tuple[PdObject, PdObject]:
        return (self.pop(), self.pop())

    def pop3(self) -> Tuple[PdObject, PdObject, PdObject]:
        return (self.pop(), self.pop(), self.pop())

    def mark_stack(self) -> None:
        self.marker_stack.append(len(self._stack))

    def get_output_field_separator(self) -> str:
        return basic_pd_str(self.get_or_else('Ñ', ''))

    def get_output_record_separator(self) -> str:
        return basic_pd_str(self.get_or_else('N', ''))

    def join_output_fields(self, ss: Iterable[str]) -> str:
        return self.get_output_field_separator().join(ss)

    def print_output_record(self, s: str = "", outfile: typing.IO[str] = sys.stdout) -> None:
        print(s, end=self.get_output_record_separator(), file=outfile)

    def get_epsilon(self) -> float:
        ret = self.get_or_none('Ep')
        if ret is None:
            raise Exception('No variable named Ep (epsilon)')
        elif isinstance(ret, (int, float)):
            return float(ret)
        else:
            raise Exception('Ep (epsilon) is not numeric')

    def pd_str(self, obj: PdObject) -> str:
        if isinstance(obj, (list, range)):
            return self.join_output_fields(self.pd_str(e) for e in obj)
        else: # includes str, int, float etc.
            return basic_pd_str(obj)

    def pop_stack_marker(self) -> Optional[int]:
        if self.marker_stack:
            return self.marker_stack.pop()
        else:
            return None

    def pop_until_stack_marker(self) -> List[PdObject]:
        marker = self.pop_stack_marker()
        if marker is None:
            self.maximize_length()
            ret = self._stack
            self._stack = []
        else:
            ret = self._stack[marker:]
            self._stack = self._stack[:marker]
        return ret

    def pop_stack_ignoring_markers_and_triggers(self) -> List[PdObject]:
        self.marker_stack = []
        ret = self._stack
        self._stack = []
        return ret

    def index_stack(self, index: int) -> PdObject:
        self.try_ensure_length(index + 1)
        return self._stack[-1-index]

    def index_stack_or_none(self, index: int) -> Optional[PdObject]:
        self.try_ensure_length(index + 1)
        if 0 <= index < len(self._stack):
            return self._stack[-1-index]
        else:
            return None

    def debug_dump(self) -> str:
        return '\n  Stack dump: {}\n  X-stack: {}\n  Markers: {}'.format(
                repr(self._stack), repr(self.x_stack_repr()), repr(self.marker_stack))

    def bracketed_shadow(self) -> 'BracketedShadowEnvironment':
        return BracketedShadowEnvironment(self)

    def keep_shadow(self) -> 'KeepShadowEnvironment':
        return KeepShadowEnvironment(self)

    def tracking_shadow(self) -> 'TrackingShadowEnvironment':
        return TrackingShadowEnvironment(self)

    def capture_stack_as_iterable(self) -> Iterable[PdObject]:
        captured_stack = self._stack
        self._stack = []
        trigger = self.stack_trigger
        self.stack_trigger = lambda: None

        def inner_generator() -> Generator[PdObject, None, None]:
            while captured_stack:
                yield captured_stack.pop()
            try:
                while True:
                    res = trigger()
                    if res is None: break
                    yield res
            except PdEmptyStackException:
                pass
        return inner_generator()

class BracketedShadowEnvironment(Environment):
    def __init__(self, shadow_parent: Environment) -> None:
        Environment.__init__(self,
                evaluator = shadow_parent.evaluator,
                input_trigger = shadow_parent.input_trigger,
                stack_trigger = self.shadow_trigger,
                vars_delegate = shadow_parent)
        self.shadow_parent = shadow_parent
        self.shadow_i = 0
        self.mark_stack()

    def shadow_trigger(self) -> Optional[PdObject]:
        res = self.shadow_parent.pop_or_none()
        if res is not None:
            self.shadow_i += 1
        return res

class KeepShadowEnvironment(BracketedShadowEnvironment):
    def __init__(self, shadow_parent: Environment) -> None:
        BracketedShadowEnvironment.__init__(self, shadow_parent)

    def shadow_trigger(self) -> Optional[PdObject]:
        self.shadow_parent.try_ensure_length(self.shadow_i + 1)
        ret = self.shadow_parent.index_stack_or_none(self.shadow_i)
        if ret is not None:
            self.shadow_i += 1
        return ret

class TrackingShadowEnvironment(BracketedShadowEnvironment):
    def __init__(self, shadow_parent: Environment) -> None:
        BracketedShadowEnvironment.__init__(self, shadow_parent)
        self._shadow_acc: List[PdObject] = []

    def shadow_trigger(self) -> Optional[PdObject]:
        ret = self.shadow_parent.pop_or_none()
        if ret is not None:
            self._shadow_acc.append(ret)
            self.shadow_i += 1
        return ret

    @property
    def popped_objects(self) -> List[PdObject]:
        return self._shadow_acc[::-1]
# }}}
# truthiness {{{
def pytruth(x: PdValue) -> bool:
    if isinstance(x, Char):
        return bool(x.ord)
    else:
        return bool(x)

def pytruth_eval(env: Environment, x: PdObject) -> bool:
    if isinstance(x, Block):
        x(env)
        res = env.pop()
        assert not isinstance(res, Block)
        return pytruth(res)
    else:
        return pytruth(x)

def pd_bool(obj: PdObject) -> bool:
    if isinstance(obj, str):
        return bool(ord(obj))
    else:
        return bool(obj)

def pd_truthy(env: Environment, func: Block, lst: List[PdObject]) -> bool:
    try:
        return bool(pd_sandbox(env, func, lst)[-1])
    except IndexError:
        raise Exception("sandboxed truthiness lacked return value")
# }}}
# coercion {{{
def pynumber_length(x: PdValue) -> Union[int, float]:
    if isinstance(x, (str, list, range)):
        return len(x)
    elif isinstance(x, Char):
        return x.ord
    else:
        return x

def pd_to_list_range(obj: PdObject, coerce_start: int = 0) -> Union[list, range]:
    if isinstance(obj, (list, range)):
        return obj
    elif isinstance(obj, str):
        return [Char(ord(c)) for c in obj]
    elif isinstance(obj, Char):
        return range(coerce_start, coerce_start + obj.ord)
    elif isinstance(obj, int):
        return range(coerce_start, coerce_start + obj)
    else:
        raise AssertionError(repr(obj) + " cannot be converted to list")

# Returns Hashable, but typing that doesn't really work...
def pykey(obj: PdObject) -> PdKey:
    if isinstance(obj, (Char, int, float, str, range)): return obj
    elif isinstance(obj, list): return tuple(pykey(x) for x in obj)
    else:
        raise TypeError(repr(obj) + " cannot be converted to key")

# }}}
# sandbox {{{
def pd_sandbox(env: Environment, func: Block, lst: List[PdObject]) -> List[PdObject]:
    # There are a bunch of reasonable ways to define/implement this...
    shadow = env.bracketed_shadow()
    shadow.push(*lst)
    func(shadow)
    return shadow._stack
    # env.mark_stack()
    # env.push(*lst)
    # func(env)
    # return env.pop_until_stack_marker()
    # temp_env = Environment(env.evaluator, vars_delegate=env)
    # temp_env.push(*lst)
    # func(temp_env)
    # return temp_env.stack
# }}}
# comparisons {{{
def to_comparable_list(a: PdValue) -> list:
    if isinstance(a, list): return a
    elif isinstance(a, (Char, int, float)): return [a]
    else: return list(pd_iterable(a))

def pd_cmp(a: PdObject, b: PdObject) -> int:
    if isinstance(a, (Char, int)) and isinstance(b, (Char, int)):
        return num.any_cmp(num.intify(a), num.intify(b))
    elif isinstance(a, (Char, int, float)) and isinstance(b, (Char, int, float)):
        return num.any_cmp(num.floatify(a), num.floatify(b))
    elif isinstance(a, (list, range)) and isinstance(b, (list, range)):
        return num.any_cmp(list(a), list(b))
    elif isinstance(a, str) and isinstance(b, str):
        return num.any_cmp(a, b)
    elif isinstance(a, (Char, str)) and isinstance(b, (Char, str)):
        return num.any_cmp(basic_pd_str(a), basic_pd_str(b))
    elif isinstance(a, Block) or isinstance(b, Block):
        raise TypeError('cannot compare blocks')
    else:
        return num.any_cmp(to_comparable_list(a), to_comparable_list(b))

def pd_less_than(a: PdObject, b: PdObject) -> bool:
    return pd_cmp(a, b) < 0
def pd_lte(a: PdObject, b: PdObject) -> bool:
    return pd_cmp(a, b) <= 0

def pd_minmax(a: PdObject, b: PdObject, ef: Optional[Tuple[Environment, Block]] = None) -> Tuple[PdObject, PdObject]:
    if ef is None:
        ar = a
        br = b
    else:
        e, f = ef
        ar = pd_sandbox(e, f, [a])
        br = pd_sandbox(e, f, [b])
    return (a, b) if pd_less_than(ar, br) else (b, a)
def pd_min(a: PdObject, b: PdObject, ef: Optional[Tuple[Environment, Block]] = None) -> PdObject:
    return pd_minmax(a, b, ef)[0]
def pd_max(a: PdObject, b: PdObject, ef: Optional[Tuple[Environment, Block]] = None) -> PdObject:
    return pd_minmax(a, b, ef)[1]
def pd_median_of_three(a: PdObject, b: PdObject, c: PdObject, ef: Optional[Tuple[Environment, Block]] = None) -> PdObject:
    if ef is None:
        ar = a
        br = b
        cr = c
    else:
        e, f = ef
        ar = pd_sandbox(e, f, [a])
        br = pd_sandbox(e, f, [b])
        cr = pd_sandbox(e, f, [c])
    if pd_less_than(ar, br): a, b, ar, br = b, a, br, ar
    if pd_less_than(br, cr): b, c, br, cr = c, b, cr, br
    if pd_less_than(ar, br): a, b = b, a
    return b
def pd_min_of_seq(a: PdSeq, ef: Optional[Tuple[Environment, Block]] = None) -> PdObject:
    if isinstance(a, str) and ef is None: return min(pd_iterable(a))
    cur: Optional[PdObject] = None
    cur_key: Optional[PdObject] = None
    for e in pd_iterable(a):
        if ef is None:
            e_key = e
        else:
            env, f = ef
            e_key = pd_sandbox(env, f, [e])
        if cur_key is None or pd_less_than(e_key, cur_key):
            cur, cur_key = e, e_key
    if cur is None:
        raise ValueError("Cannot take min of empty sequence")
    return cur
def pd_max_of_seq(a: PdSeq, ef: Optional[Tuple[Environment, Block]] = None) -> PdObject:
    if isinstance(a, str) and ef is None: return max(pd_iterable(a))
    cur: Optional[PdObject] = None
    cur_key: Optional[PdObject] = None
    for e in pd_iterable(a):
        if ef is None:
            e_key = e
        else:
            env, f = ef
            e_key = pd_sandbox(env, f, [e])
        if cur_key is None or not pd_less_than(e_key, cur_key):
            cur, cur_key = e, e_key
    if cur is None:
        raise ValueError("Cannot take max of empty sequence")
    return cur
def pd_sort(a: PdSeq, ef: Optional[Tuple[Environment, Block]] = None) -> PdSeq:
    if ef is None:
        if isinstance(a, str):
            return ''.join(sorted(a))
        else:
            return list(sorted(a))
    else:
        env, f = ef
        keyed = [(pd_sandbox(env, f, [elt]), elt) for elt in pd_iterable(a)]
        return pd_build_like(a, [se for sk, se in sorted(keyed)])
# }}}
# deep actions {{{
# copy a thing recursively, fully structured as mutable lists
def pd_deep_copy_to_list(obj: PdValue) -> PdValue:
    if isinstance(obj, (Char, int, float)):
        return obj
    else:
        acc: List[PdValue] = []
        for e in pd_iterable(obj):
            if isinstance(e, Block):
                raise AssertionError("can't deep copy Block")
            else:
                acc.append(pd_deep_copy_to_list(e))
        return acc
# deeply map a Python num -> PdValue function (no Char preservation)
def pd_deepmap_n2v(func: Callable[[Union[int, float]], PdValue], obj: PdValue) -> PdValue:
    if isinstance(obj, (Char, int, float)):
        return func(num.numerify(obj))
    else:
        acc = []
        for e in pd_iterable(obj):
            if isinstance(e, Block):
                raise AssertionError("can't map numeric function across Block")
            else:
                acc.append(pd_deepmap_n2v(func, e))
        return acc
# deeply map a Python str -> str function on strs, Chars, numbers
def pd_deepmap_s2s(func: Callable[[str], str], obj: PdValue, whole_str_ok: bool = True) -> PdValue:
    if isinstance(obj, str):
        if whole_str_ok:
            return func(obj)
        else:
            return ''.join(func(c) for c in obj)
    elif isinstance(obj, Char):
        return Char(func(obj.chr))
    elif isinstance(obj, (int, float)):
        return Char(func(chr(num.intify(obj))))
    else:
        acc = []
        for e in pd_iterable(obj):
            if isinstance(e, Block):
                raise AssertionError("can't map string function across Block")
            else:
                acc.append(pd_deepmap_s2s(func, e))
        return acc
# deeply map a Python str -> PdValue function on strs, Chars, numbers
# The difference from above is no Char/string preservation, and multi-character
# strings are never kept and mapped together
def pd_deepmap_s2v(func: Callable[[str], PdNum], obj: PdValue) -> PdValue:
    if isinstance(obj, (Char, int, float)):
        return func(chr(num.intify(obj)))
    else:
        acc = []
        for e in pd_iterable(obj):
            if isinstance(e, Block):
                raise AssertionError("can't map string function across Block")
            else:
                acc.append(pd_deepmap_s2v(func, e))
        return acc

# deeply vectorize a (Num, Num) -> Value function
def pd_deepvectorize_nn2v(func: Callable[[PdNum, PdNum], PdValue],
        obj1: PdObject, obj2: PdObject) -> PdValue:
    if isinstance(obj1, Block):
        raise TypeError('Cannot deeply vectorize over block ' + repr(obj1))
    if isinstance(obj2, Block):
        raise TypeError('Cannot deeply vectorize over block ' + repr(obj2))
    if (    isinstance(obj1, (Char, int, float)) and
            isinstance(obj2, (Char, int, float))):
        return func(obj1, obj2)
    else:
        n = max(pd_len_singleton(obj1), pd_len_singleton(obj2))

        acc: List[PdObject] = [pd_deepvectorize_nn2v(func, e1, e2)
                for e1, e2
                in zip(pd_cycle_to_len(n, obj1), pd_cycle_to_len(n, obj2))
        ]
        if ((isinstance(obj1, str) or isinstance(obj2, str)) and
                isinstance(obj1, (Char, int, str)) and
                isinstance(obj2, (Char, int, str))):
            return pd_maybe_build_str(acc)
        else:
            return acc
def pd_deep_stats(obj: PdObject) -> Tuple[int, Union[int, float], Union[int, float]]:
    """Return the count, sum, and sum of squares, deeply accumulated over the
    object."""
    if isinstance(obj, Block):
        raise TypeError('Cannot deeply accumulate stats over block ' +
                repr(obj))
    if isinstance(obj, (Char, int, float)):
        v = num.numerify(obj)
        return (1, v, v**2)
    else:
        c: int               = 0
        s: Union[int, float] = 0
        q: Union[int, float] = 0
        for e in pd_iterable(obj):
            c1, s1, q1 = pd_deep_stats(e)
            c += c1
            s += s1 # type: ignore
            q += q1 # type: ignore
        return (c, s, q)

def pd_deep_length(obj: PdObject) -> int:
    return pd_deep_stats(obj)[0]
def pd_deep_sum(obj: PdObject) -> Union[int, float]:
    return pd_deep_stats(obj)[1]
def pd_deep_hypotenuse(obj: PdObject) -> float:
    return math.sqrt(pd_deep_stats(obj)[2])
def pd_deep_average(obj: PdObject) -> float:
    c, s, _ = pd_deep_stats(obj)
    return s / c
def pd_deep_standard_deviation(obj: PdObject) -> float:
    c, s, q = pd_deep_stats(obj)
    return math.sqrt((q - s**2 / c) / (c - 1))

def pd_deep_product(obj: PdObject) -> Union[int, float]:
    if isinstance(obj, Block):
        raise TypeError('Cannot deeply compute product over block ' +
                repr(obj))
    if isinstance(obj, (Char, int, float)):
        return num.numerify(obj)
    else:
        p: Union[int, float] = 1
        for e in pd_iterable(obj):
            p *= pd_deep_product(e) # type: ignore
        return p
def pd_deepmap_block(env: Environment, func: Block, seq: PdSeq) -> PdObject:
    env.push_yx()
    i = 0
    # The boolean is True if we need to break
    def process(obj: PdValue) -> Tuple[bool, List[PdObject]]:
        nonlocal i
        if isinstance(obj, (Char, int, float)):
            env.set_yx(i, obj)
            i += 1
            try:
                return (False, pd_sandbox(env, func, [obj]))
            except PdContinueException:
                return (False, [])
            except PdBreakException:
                return (True, [])
        else:
            acc = []
            for e in pd_iterable(obj):
                if isinstance(e, Block):
                    raise AssertionError("can't deep-map across Block")
                else:
                    flag, res = process(e)
                    acc.extend(res)
                    if flag:
                        return (True, [acc])
            return (False, [acc])

    try:
        _, [res] = process(seq)
        return res
    finally:
        env.pop_yx()
# }}}
# iteration wrappers {{{
def pd_iterable(seq: PdSeq) -> Iterable[PdObject]:
    if isinstance(seq, str):
        return (Char(ord(c)) for c in seq)
    return seq

def pd_len_singleton(v: PdValue) -> int:
    if isinstance(v, (Char, int, float)):
        return 1
    else:
        return len(v)

def pd_cycle_to_len(n: int, obj: PdValue) -> Iterable[PdObject]:
    if isinstance(obj, (Char, int, float)):
        return itertools.repeat(obj, n)
    elif isinstance(obj, str):
        n0 = len(obj)
        return (Char(ord(obj[i % n0])) for i in range(n))
    else:
        n0 = len(obj)
        return (obj[i % n0] for i in range(n))

def pd_reversed_iterable(seq: PdSeq) -> Iterable[PdObject]:
    if isinstance(seq, str):
        return (Char(ord(c)) for c in reversed(seq))
    return reversed(seq)

def pd_deep_generator(obj: PdObject) -> Generator[PdValue, None, None]:
    if isinstance(obj, (Char, int, float)):
        yield obj
    elif isinstance(obj, str):
        yield from (Char(ord(c)) for c in obj)
    elif isinstance(obj, (list, range)):
        for e in obj:
            yield from pd_deep_generator(e)
    else:
        raise NotImplementedError('can\'t deep-iterate across ' + repr(obj))

def py_enumerate(seq: PdSeq, start: int = 0) -> Iterable[Tuple[int, PdObject]]:
    return enumerate(pd_iterable(seq), start=start)

def py_reversed_enumerate(seq: PdSeq, start: int = 0) -> Iterable[Tuple[int, PdObject]]:
    return enumerate(pd_reversed_iterable(seq), start=start)

def pd_enumerate(seq: PdSeq, start: int = 0) -> List[list]:
    return [list(t) for t in py_enumerate(seq, start=start)]
# }}}
# list operations (index, "arithmetic", build_like) {{{
def pd_index(seq: PdSeq, n: PdNum) -> PdObject:
    if isinstance(seq, str):
        return Char(ord(seq[num.intify(n)]))
    else:
        return seq[num.intify(n)]
def pd_modify_index(env: Environment, func: Block, seq: PdSeq, n: int) -> PdObject:
    if isinstance(seq, str): seq = list(pd_iterable(seq))
    before = list(seq[:n])
    after  = [] if n == -1 else list(seq[n+1:])
    return before + pd_sandbox(env, func, [seq[n]]) + after
def pd_join(env: Environment, seq: PdSeq, joiner: PdSeq) -> PdObject:
    if isinstance(seq, (list, range)) and isinstance(joiner, (list, range)):
        acc: List[PdObject] = []
        started = False
        for e in seq:
            if started:
                acc.extend(joiner)
            started = True
            if isinstance(e, (list, range)):
                acc.extend(e)
            else:
                acc.append(e)
        return acc
    else:
        return env.pd_str(joiner).join(env.pd_str(s) for s in pd_iterable(seq))
def pd_mul_seq(seq: PdSeq, n: PdNum) -> PdSeq:
    n_int = num.intify(n)
    if isinstance(seq, (str, list)):
        return seq * n_int
    else:
        return list(seq) * n_int

def pd_cartesian_product_seq_matrix(seq1: PdSeq, seq2: PdSeq) -> List[List[list]]:
    return [[[e1, e2]
        for e2 in pd_iterable(seq2)]
        for e1 in pd_iterable(seq1)]

def pd_cartesian_product_seq_matrix_3(seq1: PdSeq, seq2: PdSeq, seq3: PdSeq) -> List[List[List[list]]]:
    return [[[[e1, e2, e3]
        for e3 in pd_iterable(seq3)]
        for e2 in pd_iterable(seq2)]
        for e1 in pd_iterable(seq1)]

def pd_pow_seq(seq: PdSeq, n: PdNum) -> PdSeq:
    n_int = num.intify(n)
    if isinstance(seq, str):
        return [''.join(e) for e in itertools.product(seq, repeat=n_int)]
    else:
        return [list(e) for e in itertools.product(pd_iterable(seq), repeat=n_int)]

def pd_split_seq_int_gen(seq: PdSeq, n: int, include_leftover: bool) -> Generator[PdSeq, None, None]:
    for i in range(0, len(seq), n):
        if i + n <= len(seq) or include_leftover:
            yield seq[i:i+n]

def pd_split_seq(seq: PdSeq, n: PdNum, include_leftover: bool) -> List[PdSeq]:
    return list(pd_split_seq_int_gen(seq, num.intify(n), include_leftover))

def pd_split_seq_by_gen(seq: PdSeq, tok: PdSeq) -> Generator[PdSeq, None, None]:
    i = 0
    cur_start = 0
    seqlen = len(seq)
    toklen = len(tok)
    while True:
        if i + toklen > seqlen:
            # No more breaks are possible.
            yield seq[cur_start:]
            return
        elif list(seq[i:i+toklen]) == list(tok):
            yield seq[cur_start:i]
            i += toklen
            cur_start = i
        else:
            i += 1

def pd_split_seq_by(seq: PdSeq, tok: PdSeq) -> List[PdSeq]:
    if isinstance(seq, str):
        # Python is probably faster than we are. And less error-prone :)
        # Ignoring types to pretend List is covariant
        if isinstance(tok, str):
            return seq.split(tok) # type: ignore
        elif isinstance(tok, Char):
            return seq.split(tok.chr) # type: ignore
        # TODO: Special case for list of Chars?
    return list(pd_split_seq_by_gen(seq, tok))

def pd_sliding_window_seq_int_gen(seq: PdSeq, n: int) -> Generator[PdSeq, None, None]:
    for i in range(len(seq) + 1 - n):
        yield seq[i:i+n]

def pd_sliding_window_seq(seq: PdSeq, n: PdNum) -> List[PdSeq]:
    return list(pd_sliding_window_seq_int_gen(seq, num.intify(n)))

def pd_replicate(atom: PdObject, n: int) -> PdSeq:
    if isinstance(atom, Char):
        return chr(atom.ord) * n
    else:
        return [atom] * n

def pd_maybe_build_str(result: List[PdObject]) -> PdSeq:
    if all(isinstance(c, (Char, int)) for c in result):
        return (
            ''.join(
                chr(c.ord if isinstance(c, Char) else c) # type: ignore
                for c in result
            )
        )
    else:
        return result

def pd_build_like(orig: PdSeq, result: List[PdObject]) -> PdSeq:
    if isinstance(orig, str):
        return pd_maybe_build_str(result)
    else:
        return result

def pd_flatten_once(val: PdValue) -> PdValue:
    if isinstance(val, (Char, int, float, str, range)):
        return val
    else: # list
        if all(isinstance(e, (Char, str)) for e in val):
            return ''.join(
                    e.chr if isinstance(e, Char) else e # type: ignore
                    for e in val
                    )
        else:
            acc: List[PdObject] = []
            for e in val:
                if isinstance(e, str):
                    acc.extend(Char(c) for c in e)
                elif isinstance(e, (list, range)):
                    acc.extend(e)
                else:
                    acc.append(e)
            return acc

@overload
def pd_flatten(val: range) -> range: ...
@overload
def pd_flatten(val: list) -> Union[list, str]: ...
@overload
def pd_flatten(val: Char) -> Char: ...
@overload
def pd_flatten(val: int) -> int: ...
@overload
def pd_flatten(val: float) -> float: ...
@overload
def pd_flatten(val: str) -> str: ...

def pd_flatten(val: PdValue) -> PdValue:
    if isinstance(val, (Char, int, float, str, range)):
        return val
    else: # list
        acc: List[PdObject] = []
        for e in val:
            if isinstance(e, str):
                acc.extend(Char(c) for c in e)
            elif isinstance(e, (list, range)):
                acc.extend(pd_flatten(e))
            else:
                acc.append(e)
        if all(isinstance(e, (Char, str)) for e in acc):
            return ''.join(
                    e.chr if isinstance(e, Char) else e # type: ignore
                    for e in acc)
        else:
            return acc

def pd_group_by_function(seq: PdSeq, proj: Callable[[PdObject], PdObject]) -> list:
    result = []
    current_group = []
    current_group_proj = None
    for e in pd_iterable(seq):
        e_proj = proj(e)
        if current_group_proj is None or current_group_proj == e_proj:
            current_group.append(e)
        else:
            result.append(pd_build_like(seq, current_group))
            current_group = [e]
        current_group_proj = e_proj

    if current_group:
        result.append(pd_build_like(seq, current_group))
    return result

def pd_group(seq: PdSeq) -> list:
    return pd_group_by_function(seq, lambda x: x)

def pd_group_by(env: Environment, func: Block, seq: PdSeq) -> list:
    # Should we use the entire sandbox as the key?
    return pd_group_by_function(seq, lambda x: pd_sandbox(env, func, [x]))

def pd_mold_from(value_iterable: Iterator[PdValue], template: PdObject) -> PdObject:
    if isinstance(template, (Char, int, float)): return next(value_iterable)
    elif isinstance(template, (str, list, range)):
        acc = []
        for te in pd_iterable(template):
            acc.append(pd_mold_from(iter(value_iterable), te))
        return pd_build_like(template, acc)
    else:
        raise AssertionError('can\'t mold like ' + repr(template))

def pd_mold(el_source: PdValue, template: PdSeq) -> PdObject:
    if isinstance(el_source, (Char, int, float)):
        return pd_mold_from(
                (num.pd_add_const(el_source, i) for i in itertools.count(0)),
                template)
    else:
        return pd_mold_from(pd_deep_generator(el_source), template)
def pd_mold_fill(e: PdValue, template: PdSeq) -> PdObject:
    return pd_mold_from(itertools.repeat(e), template)

def pd_zip_as_list(*seq: PdSeq) -> PdObject:
    return [list(es) for es in zip(*(pd_iterable(s) for s in seq))]
def pd_ziplongest_as_list(*seq: PdSeq) -> PdObject:
    return [[e for e in es if e is not None] for es in itertools.zip_longest(
        *(pd_iterable(s) for s in seq))]

def tagged_cycle(iterable: Iterable[T]) -> Iterable[Tuple[bool, T]]:
    saved = []
    for element in iterable:
        yield (False, element)
        saved.append(element)
    while saved:
        for element in saved: yield (True, element)
def loopzip(*iterables: Iterable[T]) -> Iterable[Tuple[T, ...]]:
    for values in zip(*(tagged_cycle(iterable) for iterable in iterables)):
        if all(tag for tag, _ in values): break
        yield tuple(val for _, val in values)

def pd_loopzip_as_list(*seq: PdSeq) -> PdObject:
    return [list(es) for es in loopzip(*(pd_iterable(s) for s in seq))]

def pd_str_subsequences_gen(seq: str) -> Generator[str, None, None]:
    if not seq:
        yield seq
    else:
        yield from pd_str_subsequences_gen(seq[1:])
        fst = seq[0]
        for s in pd_str_subsequences_gen(seq[1:]):
            yield fst + s

def pd_lst_subsequences_gen(seq: list) -> Generator[list, None, None]:
    if not seq:
        yield []
    else:
        yield from pd_lst_subsequences_gen(seq[1:])
        fst = [seq[0]]
        for s in pd_lst_subsequences_gen(seq[1:]):
            yield fst + s

def pd_subsequences(seq: PdSeq) -> Iterable[PdSeq]:
    if isinstance(seq, str):
        return pd_str_subsequences_gen(seq)
    elif isinstance(seq, range):
        return pd_lst_subsequences_gen(list(seq))
    else:
        return pd_lst_subsequences_gen(seq)

def pd_subsequences_list(seq: PdSeq) -> List[PdSeq]:
    return list(pd_subsequences(seq))

def pd_palindromize(seq: PdSeq) -> PdSeq:
    if isinstance(seq, range):
        return list(seq[:-1]) + list(seq[::-1])
    elif isinstance(seq, str):
        return seq[:-1] + seq[::-1]
    else:
        return seq[:-1] + seq[::-1]

def pd_rectangularize_fill(matrix: PdSeq, filler: PdObject) -> List[list]:
    n = 0
    for row0 in pd_iterable(matrix):
        if isinstance(row0, (str, list, range)):
            n = max(n, len(row0))
        else:
            n = max(n, 1)

    acc: List[list] = []
    for row0 in pd_iterable(matrix):
        if isinstance(row0, (str, list, range)):
            row = list(pd_iterable(row0))
        else:
            row = [row0]
        acc.append(row + [filler] * (n - len(row)))
    return acc

def pd_transpose(matrix: PdSeq) -> List[list]:
    res: List[list] = []
    for row0 in pd_iterable(matrix):
        if isinstance(row0, (str, list, range)):
            row = pd_iterable(row0)
        else:
            row = [row0]
        for i, e in enumerate(row):
            if len(res) <= i:
                res.append([e])
            else:
                res[i].append(e)
    return res

def pd_transpose_fill(matrix: PdSeq, filler: PdObject) -> List[list]:
    res: List[list] = []
    for ri, row0 in py_enumerate(matrix):
        if isinstance(row0, (str, list, range)):
            row = pd_iterable(row0)
        else:
            row = [row0]
        for i, e in enumerate(row):
            if len(res) <= i:
                res.append([filler] * ri + [e])
            else:
                res[i].append(e)
        i += 1
        while i < len(res):
            res[i].append(filler)
            i += 1
    return res
# }}}
# pd_find_entry et al. (wow code duplication much) {{{
def pd_find_index(env: Environment, needle: PdObject, haystack: PdSeq) -> int:
    for i, e in py_enumerate(haystack):
        if e == needle: return i
    return -1

def pd_find_substring_index(env: Environment, needle: PdSeq, haystack: PdSeq) -> int:
    if isinstance(needle, str) and isinstance(haystack, str):
        try:
            return haystack.index(needle)
        except ValueError:
            return -1
    else:
        nn = len(needle)
        needle = list(needle)
        for i in range(len(haystack) - nn + 1):
            # TODO: Is this the correct way to compare slices? Probably make a
            # utility function, there are some comparisons elsewhere that seem
            # problematic.
            if list(haystack[i:i + nn]) == needle:
                return i
        return -1

def pd_find_entry(env: Environment, func: Block, seq: PdSeq) -> Tuple[int, Optional[PdObject]]:
    for i, e in py_enumerate(seq):
        if pd_truthy(env, func, [e]): return (i, e)
    return (-1, None)

def pd_find_last_entry(env: Environment, func: Block, seq: PdSeq) -> Tuple[int, Optional[PdObject]]:
    for i, e in py_reversed_enumerate(seq):
        if pd_truthy(env, func, [e]): return (i, e)
    return (-1, None)

def pd_take_drop_while(env: Environment, func: Block, seq: PdSeq) -> Tuple[PdSeq, PdSeq]:
    for i, e in py_enumerate(seq):
        if not pd_truthy(env, func, [e]): return (seq[:i], seq[i:])
    return (seq, [])

def pd_count_in(env: Environment, e: PdValue, seq: PdSeq) -> int:
    if isinstance(seq, str):
        if isinstance(e, Char):
            return seq.count(e.chr)
        elif isinstance(e, (int, float)):
            return seq.count(chr(int(e)))
        else:
            return seq.count(env.pd_str(e))
    elif isinstance(seq, range):
        # whatever, it's ok to count whatever is in a range
        return seq.count(e) # type: ignore
    else:
        return seq.count(e)

def pd_map_iterable(env: Environment, func: Block, it: Iterable[PdObject]) -> List[PdObject]:
    env.push_yx()
    acc: List[PdObject] = []
    try:
        for i, element in enumerate(it):
            env.set_yx(i, element)
            try:
                acc.extend(pd_sandbox(env, func, [element]))
            except PdContinueException: pass
    except PdBreakException: pass
    finally:
        env.pop_yx()
    return acc

def pd_map_fold_into(env: Environment, func: Block, seq: PdSeq,
        f: Callable[[Optional[List[PdObject]]], Optional[T]]) -> T:
    # Couldn't come up with a great name for this. Runs the block on successive
    # elements of the sequence and calls f on the result, and finally call f
    # with None, until it returns a non-None element, which we return. It may
    # be helpful for f to be stateful, and it should return a non-None answer
    # when given None.
    env.push_yx()
    ret: Optional[T] = None
    try:
        for i, element in enumerate(pd_iterable(seq)):
            env.set_yx(i, element)
            try:
                ret = f(pd_sandbox(env, func, [element]))
            except PdContinueException: pass
            if ret is not None: break
    except PdBreakException: pass
    finally:
        env.pop_yx()
    if ret is None:
        ret = f(None)
        if ret is None:
            raise AssertionError("pd_map_fold_into: function(None) should return non-None")
    return ret

def pd_map(env: Environment, func: Block, seq: PdSeq) -> PdSeq:
    return pd_build_like(seq,
        pd_map_iterable(env, func, pd_iterable(seq)))

def pd_map_singleton(seq: PdSeq) -> List[PdObject]:
    acc: List[PdObject] = []
    for e in pd_iterable(seq):
        if isinstance(e, Char):
            acc.append(e.chr)
        else:
            acc.append([e])
    return acc

def pd_map_reverse_singleton(seq: PdSeq) -> List[PdObject]:
    acc: List[PdObject] = []
    for e in pd_iterable(seq):
        if isinstance(e, Block):
            raise TypeError("Can't map reverse over block")
        elif isinstance(e, Char):
            acc.append(e.chr)
        elif isinstance(e, (int, float)):
            acc.append([e])
        else:
            acc.append(e[::-1])
    return acc

def pd_map_product(env: Environment, func: Block, seq1: PdSeq, seq2: PdSeq) -> list:
    # Approximately: (f : a -> b -> c) -> (seq1 : [a]) -> (seq2 : [b]) -> [[c]]
    env.push_yx()
    outer: list = []
    try:
        for i, e1 in py_enumerate(seq1):
            env.set_yx(i, e1)

            env.push_yx()
            inner: List[PdObject] = []
            try:
                for j, e2 in py_enumerate(seq2):
                    env.set_yx(j, e2)
                    try:
                        inner.extend(pd_sandbox(env, func, [e1, e2]))
                    except PdContinueException:
                        pass
            finally:
                env.pop_yx()

            outer.append(pd_build_like(seq2, inner))
    except PdBreakException:
        pass
    finally:
        env.pop_yx()

    return outer

def pd_mapsum(env: Environment, func: Block, seq: PdSeq) -> PdObject:
    env.push_yx()
    acc: List[PdObject] = []
    try:
        for i, element in py_enumerate(seq):
            env.set_yx(i, element)
            try:
                acc.extend(pd_sandbox(env, func, [element]))
            except PdContinueException: pass
    except PdBreakException: pass
    finally:
        env.pop_yx()
    return sum(acc)

def pd_translate_entries(source: PdSeq, target: PdSeq) -> Generator[Tuple[PdKey, PdObject], None, None]:
    t0: Optional[PdObject] = None
    for s, t in itertools.zip_longest(pd_iterable(source), pd_iterable(target)):
        if t is not None:
            t0 = t # loop the last element of the target
        if t0 is None:
            raise ValueError("Cannot translate with empty target")
        yield pykey(s), t0

def pd_translate(operand: PdSeq, source: PdSeq, target: PdSeq) -> PdSeq:
    td = dict(pd_translate_entries(source, target))
    return pd_build_like(operand, [td.get(pykey(e), e) for e in pd_iterable(operand)])

def pd_one_time_translate(operand: PdSeq, source: PdSeq, target: PdSeq) -> PdSeq:
    td: Dict[PdKey, List[PdObject]] = dict()
    for k, v in pd_translate_entries(source, target):
        if k not in td: td[k] = []
        td[k].append(v)
    for k in td:
        td[k].reverse()
    def translate(k: PdObject) -> PdObject:
        v = td.get(pykey(k))
        if v is None or len(v) == 0:
            return k
        else:
            return v.pop()
    return pd_build_like(operand, [translate(e) for e in pd_iterable(operand)])

def pd_foreach(env: Environment, func: Block, seq: PdSeq) -> None:
    env.push_yx()
    try:
        for i, element in py_enumerate(seq):
            env.set_yx(i, element)
            env.push(element)
            try:
                func(env)
            except PdContinueException as e: pass
    except PdBreakException as e: pass
    finally:
        env.pop_yx()

def pd_foreach_then_empty_list(env: Environment, func: Block, seq: PdSeq) -> List[PdObject]:
    pd_foreach(env, func, seq)
    return []

def pd_forever_then_empty_list(env: Environment, func: Block) -> List[PdObject]:
    env.push_yx()
    try:
        for i in itertools.count(0):
            # TODO: X-stack treatment is consistent design, but two seems
            # wasteful.
            env.set_yx(i, i)
            try:
                func(env)
            except PdContinueException: pass
    except PdBreakException: pass
    finally:
        env.pop_yx()
    return []

def pd_foreach_x_only(env: Environment, func: Block, seq: PdSeq) -> None:
    env.push_yx()
    try:
        for i, element in py_enumerate(seq):
            env.set_yx(i, element)
            try:
                func(env)
            except PdContinueException: pass
    except PdBreakException: pass
    finally:
        env.pop_yx()

def pd_foreach_x_only_then_empty_list(env: Environment, func: Block, seq: PdSeq) -> List[PdObject]:
    pd_foreach_x_only(env, func, seq)
    return []

def pd_run_with_probability_then_empty_list(env: Environment, func: Block, prob: float) -> List[PdObject]:
    if random.random() < prob: func(env)
    return []

def pd_filter_entries(env: Environment, func: Block, seq: PdSeq,
        negate: bool = False) -> List[Tuple[int, PdObject]]:
    env.push_yx()
    acc: List[Tuple[int, PdObject]] = []
    try:
        for i, element in enumerate(pd_iterable(seq)):
            env.set_yx(i, element)
            if pd_truthy(env, func, [element]) ^ negate:
                acc.append((i, element))
    finally:
        env.pop_yx()
    return acc

def pd_filter(env: Environment, func: Block, seq: PdSeq, negate: bool = False) -> PdSeq:
    return pd_build_like(seq,
            [e for (i, e) in pd_filter_entries(env, func, seq, negate)])
def pd_filter_indexes(env: Environment, func: Block, seq: PdSeq, negate: bool = False) -> List[int]:
    return [i for (i, e) in pd_filter_entries(env, func, seq, negate)]

def pd_mask(seq1: PdSeq, seq2: PdSeq, negate: bool = False) -> PdObject:
    return pd_build_like(seq1, [e
                for (e, p) in zip(pd_iterable(seq1), pd_iterable(seq2))
                if bool(p) ^ negate])

def pd_count(env: Environment, func: Block, seq: PdSeq, negate: bool = False) -> int:
    return len(pd_filter_entries(env, func, seq, negate))

def pd_get(env: Environment, func: Block, seq: PdSeq) -> PdObject:
    _, e = pd_find_entry(env, func, seq)
    if e is None:
        raise AssertionError('pd_get: no element satisfying predicate found')
    else:
        return e

def pd_get_index(env: Environment, func: Block, seq: PdSeq) -> int:
    return pd_find_entry(env, func, seq)[0]

def pd_get_last(env: Environment, func: Block, seq: PdSeq) -> PdObject:
    _, e = pd_find_last_entry(env, func, seq)
    if e is None:
        raise AssertionError('pd_getlast: no element satisfying predicate found')
    else:
        return e

def pd_get_index_last(env: Environment, func: Block, seq: PdSeq) -> int:
    return pd_find_last_entry(env, func, seq)[0]

def pd_do_then_empty_list(env: Environment, body: Block,
        peek: bool = False, negate: bool = False) -> List[PdObject]:
    try:
        while True:
            try:
                body(env)
            except PdContinueException: pass
            if peek:
                condition = env.peek()
            else:
                condition = env.pop()
            if not (bool(condition) ^ negate):
                break
    except PdBreakException as e: pass
    return []

def pd_while_then_empty_list(env: Environment, cond: Block, body: Block,
        negate: bool = False) -> List[PdObject]:
    try:
        while True:
            cond(env)
            if bool(env.pop()) ^ negate:
                try:
                    body(env)
                except PdContinueException as e: pass
            else:
                break
    except PdBreakException as e: pass
    return []
# }}}
# reduce, zip {{{
def pd_reduce(env: Environment, func: Block, seq: PdSeq) -> PdObject:
    acc: Optional[PdObject] = None
    for element in pd_iterable(seq):
        if acc is None:
            acc = element
        else:
            acc = pd_sandbox(env, func, [acc, element])[-1]
    if acc is None:
        raise AssertionError('pd_reduce on empty list')
    return acc

def pd_scan(env: Environment, func: Block, seq: PdSeq) -> List[PdObject]:
    acc: Optional[PdObject] = None
    res: List[PdObject] = []
    for element in pd_iterable(seq):
        if acc is None:
            acc = element
        else:
            acc = pd_sandbox(env, func, [acc, element])[-1]
        res.append(acc)
    return res

def pd_zip(env: Environment, func: Block, *iterables: Iterable[PdObject]) -> List[PdObject]:
    arity = len(iterables)
    for i in range(arity + 1):
        env.push_x("INTERNAL ZIP FILLER -- YOU SHOULD NOT SEE THIS")
    acc: List[PdObject] = []
    try:
        for i, es in enumerate(zip(*iterables)):
            for j, e in enumerate(es):
                env.set_x(j, e)
            env.set_x(arity, i)
            try:
                acc.extend(pd_sandbox(env, func, list(es)))
            except PdContinueException: pass
    except PdBreakException: pass
    finally:
        for i in range(len(iterables) + 1):
            env.pop_x()
    return acc

def pd_autozip(env: Environment, func: Block, obj: PdObject) -> List[PdObject]:
    lst = pd_to_list_range(obj)
    return pd_zip(env, func, lst, lst[1:])

def pd_ziplongest(env: Environment,
        func: Block,
        iterable1: Iterable[PdObject],
        iterable2: Iterable[PdObject]) -> PdObject:
    for i in range(3):
        env.push_x("INTERNAL ZIP FILLER -- YOU SHOULD NOT SEE THIS")
    acc: List[PdObject] = []
    try:
        for i, (e1, e2) in enumerate(itertools.zip_longest(iterable1, iterable2)):
            try:
                if e1 is not None and e2 is not None:
                    env.set_x(0, e1)
                    env.set_x(1, e2)
                    env.set_x(2, i)
                    acc.extend(pd_sandbox(env, func, [e1, e2]))
                else:
                    acc.extend(e for e in (e1, e2) if e is not None)
            except PdContinueException: pass
    except PdBreakException: pass
    finally:
        for i in range(3):
            env.pop_x()
    return acc

def pd_loopzip(env: Environment,
        func: Block,
        iterable1: Iterable[PdObject],
        iterable2: Iterable[PdObject]) -> PdObject:
    for i in range(3):
        env.push_x("INTERNAL ZIP FILLER -- YOU SHOULD NOT SEE THIS")
    acc: List[PdObject] = []
    try:
        for i, (e1, e2) in enumerate(loopzip(iterable1, iterable2)):
            try:
                env.set_x(0, e1)
                env.set_x(1, e2)
                env.set_x(2, i)
                acc.extend(pd_sandbox(env, func, [e1, e2]))
            except PdContinueException: pass
    except PdBreakException: pass
    finally:
        for i in range(3):
            env.pop_x()
    return acc
# }}}
# function iteration {{{
def pd_iterate(env: Environment, func: Block) -> Tuple[List[PdObject], PdObject]:
    """Iterate a block, peeking at the stack top at the start and after each
    iteration, until a value repeats. Pop that value. Returns the list of (all
    distinct) elements peeked along the way and the final repeated value."""
    acc: List[PdObject] = []
    seen: Set[PdKey] = set()
    while True:
        obj = env.peek()
        key = pykey(obj)
        if key in seen:
            env.pop()
            return (acc, obj)

        acc.append(obj)
        seen.add(key)
        func(env)
# }}}
# string conversions {{{
def basic_pd_str(obj: PdObject) -> str:
    if isinstance(obj, (list, range)):
        return ''.join(basic_pd_str(e) for e in obj)
    elif isinstance(obj, Char):
        return obj.chr
    else: # includes str, int, float etc.
        return str(obj)

def pd_repr(obj: PdObject) -> str:
    if isinstance(obj, (list, range)):
        return '[' + ' '.join(pd_repr(e) for e in obj) + ']'
    elif isinstance(obj, Block):
        return obj.code_repr()
    elif isinstance(obj, Char):
        return "'" + obj.chr
    elif isinstance(obj, str):
        return '"' + ''.join(
            '\\"' if c == '"' else '\\\\' if c == '\\' else c
            for c in obj) + '"'
    elif isinstance(obj, int):
        return repr(obj)
    elif isinstance(obj, float):
        return repr(obj).replace('-', '—')
# }}}
# other conversions {{{
def pd_to_char(val: PdValue) -> Char:
    if isinstance(val, (list, range)):
        if not val:
            raise AssertionError('converting empty list/range to char')
        else:
            return pd_to_char(val[0])
    elif isinstance(val, str):
        if not val:
            raise AssertionError('converting empty string to char')
        else:
            return Char(ord(val[0]))
    elif isinstance(val, Char):
        return val
    else:
        assert isinstance(val, (int, float)) # https://github.com/python/mypy/issues/3196
        return Char(int(val))

def pd_to_float(val: PdValue) -> float:
    if isinstance(val, (list, range)):
        if not val:
            raise AssertionError('converting empty list/range to float')
        else:
            return pd_to_float(val[0])
    elif isinstance(val, str):
        if not val:
            raise AssertionError('converting empty string to float')
        else:
            return float(val)
    elif isinstance(val, Char):
        return float(val.ord)
    else:
        assert isinstance(val, (int, float)) # https://github.com/python/mypy/issues/3196
        return float(val)

def pd_to_int(val: PdValue) -> int:
    if isinstance(val, (list, range)):
        if not val:
            raise AssertionError('converting empty list/range to int')
        else:
            return pd_to_int(val[0])
    elif isinstance(val, str):
        if not val:
            raise AssertionError('converting empty string to int')
        else:
            return int(val)
    elif isinstance(val, Char):
        return val.ord
    else:
        assert isinstance(val, (int, float)) # https://github.com/python/mypy/issues/3196
        return int(val)
# }}}
# collection & | ^ {{{
def pd_seq_intersection(a: PdSeq, b: PdSeq) -> PdSeq:
    counter = collections.Counter(pd_iterable(b))
    acc: List[PdObject] = []
    for element in pd_iterable(a):
        if counter[element] > 0:
            acc.append(element)
            counter[element] -= 1
    return pd_build_like(a, acc)
def pd_seq_union(a: PdSeq, b: PdSeq) -> PdSeq:
    acc: List[PdObject] = list(pd_iterable(a))
    counter = collections.Counter(pd_iterable(a))
    for element in pd_iterable(b):
        if counter[element] > 0:
            counter[element] -= 1
        else:
            acc.append(element)
    return pd_build_like(a, acc)
def pd_seq_difference(a: PdSeq, b: PdSeq) -> PdSeq:
    set_b = collections.Counter(pd_iterable(b))
    acc: List[PdObject] = []
    for element in pd_iterable(a):
        if element in set_b and set_b[element]:
            set_b[element] -= 1
        else:
            acc.append(element)
    return pd_build_like(a, acc)
def pd_seq_symmetric_difference(a: PdSeq, b: PdSeq) -> PdSeq:
    set_a = collections.Counter(pd_iterable(a))
    set_b = collections.Counter(pd_iterable(b))
    acc: List[PdObject] = []
    for element in pd_iterable(a):
        if element not in set_b:
            acc.append(element)
    for element in pd_iterable(b):
        if element not in set_a:
            acc.append(element)
    return pd_build_like(a, acc)

def pd_seq_uniquify(a: PdSeq) -> PdSeq:
    s: Set[PdKey] = set()
    acc: List[PdObject] = []
    for element in pd_iterable(a):
        key = pykey(element)
        if key not in s:
            acc.append(element)
            s.add(key)
    return pd_build_like(a, acc)

def pd_seq_is_identical(a: PdSeq) -> bool:
    obj = None
    for element in pd_iterable(a):
        if obj is None:
            obj = element
        elif obj != element:
            return False
    return True

def pd_seq_is_unique(a: PdSeq) -> bool:
    s: Set[PdKey] = set()
    for element in pd_iterable(a):
        key = pykey(element)
        if key in s:
            return False
        else:
            s.add(key)
    return True

def pd_if_then_empty_list(env: Environment, condition: PdObject, body: PdObject, negate: bool = False) -> List[PdObject]:
    if pytruth_eval(env, condition) ^ negate:
        env.push_or_eval(body)
    return []
# }}}

class MemoizedBlock(Block):
    def __init__(self, block: Block) -> None:
        self.block = block
        self.arity: Optional[int] = None
        self.memo: Dict[PdKey, List[PdObject]] = dict()
    def __call__(self, env: 'Environment') -> None:
        # TODO Lots of X-stack things should be reconsidered.
        env.push_x(self)
        try:
            if self.arity is None:
                tshadow = env.tracking_shadow()
                self.block(tshadow)
                self.arity = tshadow.shadow_i
                key = pykey(tshadow.popped_objects)
                self.memo[key] = list(tshadow._stack)
                env.push_env(tshadow)
            else:
                args = env.pop_n(self.arity)
                key = pykey(args)
                if key in self.memo:
                    env.push(*self.memo[key])
                else:
                    bshadow = env.bracketed_shadow()
                    bshadow.push(*args)
                    self.block(bshadow)
                    self.memo[key] = list(bshadow._stack)
                    env.push_env(bshadow)
        finally:
            env.pop_x()
    def code_repr(self) -> str:
        return self.block.code_repr() + '_memo'

# key/array operations {{{
def new_array_of_dims(dims: List[int], filler: PdValue) -> list:
    if len(dims) == 1:
        return [filler] * dims[0]
    else:
        return [new_array_of_dims(dims[1:], filler) for _ in range(dims[0])]

def pd_new_array(kvs: list, dims: list, filler: PdValue) -> list:
    arr = new_array_of_dims(dims, filler)
    # TODO: do it lazily so we can loop last value
    for key, value in kvs:
        target = arr
        for i in key[:-1]: target = target[i]
        target[key[-1]] = value
    return arr

# def pd_sandbox(env: Environment, func: Block, lst: List[PdObject]) -> List[PdObject]:
def pd_array_keys_map(env: Environment, arr: list, ks: list, func: Block) -> PdValue:
    arr_new = pd_deep_copy_to_list(arr)
    for key in ks:
        try:
            target: PdObject = arr_new
            for i in key[:-1]:
                if isinstance(target, (str, list, range)):
                    target = pd_index(target, i)
                else:
                    raise AssertionError(
                        'could not index {} into {}: {} not indexable'.format(
                        repr(key), repr(arr_new), i, repr(target)))
            if isinstance(target, list):
                target[key[-1]] = pd_sandbox(env, func, [target[key[-1]]])[-1]
            else:
                raise AssertionError(
                    'could not assign into index {} of {}: {} not list'.format(
                    repr(key), repr(arr_new), repr(target)))
        except IndexError as e:
            raise AssertionError('could not index {} into {}: IndexError'.format(key, arr_new)) from e
    return arr_new

def pd_array_key_get(arr: Union[list, range], k: Union[list, range]) -> PdObject:
    target = arr
    for sk in k:
        target = target[sk]
    return target
# }}}
# regex {{{
def match_to_pd(m: Optional[Match]) -> PdObject:
    if m is None:
        return []
    else:
        return [m.group(0)] + [g for g in m.groups() if g is not None]
# }}}
# vim:set tabstop=4 shiftwidth=4 expandtab fdm=marker:
