# coding: utf-8
# vim:set expandtab fdm=marker:
import typing
from typing import *
import sys
from paradoc.num import Char, Num, PdNum
import paradoc.num as num
import collections
import random
import itertools

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
            func: Callable[['Environment'], None]) -> None:
        self.name = name
        self.func = func

    def __call__(self, env: 'Environment') -> None:
        self.func(env)

    def code_repr(self) -> str:
        return self.name
# }}}

PdSeq = Union[str, list, range]
PdValue = Union[PdNum, PdSeq]
PdObject = Union[PdValue, Block]

# exceptions {{{
class PdEmptyStackException(Exception): pass
class PdEndOfFileException(Exception): pass
class PdAbortException(Exception): pass
class PdBreakException(Exception): pass
class PdContinueException(Exception): pass
# }}}
# x_index {{{
def x_index(token: str) -> Optional[int]:
    if token == 'X': return 0
    elif token == 'Y': return 1
    elif token == 'Z': return 2
    else: return None
# }}}
class Environment: # {{{
    def __init__(self,
            evaluator: Callable[['Environment', str], None],
            stack_trigger: Callable[[], Optional[PdObject]] = lambda: None,
            stack: Optional[List[PdObject]] = None,
            x_stack: Optional[List[PdObject]] = None,
            vars_delegate: Optional['Environment'] = None) -> None:
        self.evaluator = evaluator
        self.stack_trigger = stack_trigger
        self.vars = dict() # type: Dict[str, PdObject]
        self._stack   =   stack or [] # type: List[PdObject]
        self._x_stack = x_stack or [0, [], ''] # type: List[PdObject]
        self.STACK_TRIGGER_X = 2 # ???
        self.vars_delegate = vars_delegate
        self.marker_stack = [] # type: List[int]

    def evaluate(self, code: str) -> None:
        self.evaluator(self, code)

    def index_x(self, index: int) -> PdObject:
        return self._x_stack[-1-index]

    def set_x(self, index: int, val: PdObject) -> None:
        self._x_stack[-1-index] = val

    def push_x(self, obj: PdObject) -> None:
        self._x_stack.append(obj)

    def push_yx(self) -> None:
        # y
        self._x_stack.append('INTERNAL Y FILLER -- YOU SHOULD NOT SEE THIS')
        # x
        self._x_stack.append('INTERNAL X FILLER -- YOU SHOULD NOT SEE THIS')

    def pop_yx(self) -> None:
        self._x_stack.pop()
        self._x_stack.pop()

    def set_yx(self, y: PdObject, x: PdObject) -> None:
        self._x_stack[-1] = x
        self._x_stack[-2] = y

    def set_x_top(self, obj: PdObject) -> None:
        self._x_stack[-1] = obj

    def get(self, token: str) -> PdObject:
        xi = x_index(token)
        if xi is not None:
            return self.index_x(xi)
        elif self.vars_delegate is None:
            return self.vars[token]
        else:
            return self.vars_delegate.get(token)

    def get_or_none(self, token: str) -> Optional[PdObject]:
        xi = x_index(token)
        if xi is not None:
            return self.index_x(xi)
        if self.vars_delegate is None:
            return self.vars.get(token)
        else:
            return self.vars_delegate.get_or_none(token)

    def get_or_else(self, token: str, other: PdObject) -> PdObject:
        ret = self.get_or_none(token)
        if ret is None: return other
        else: return ret

    def put(self, token: str, val: PdObject) -> None:
        xi = x_index(token)
        if xi is not None:
            self.set_x(xi, val)
        elif self.vars_delegate is None:
            self.vars[token] = val
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

    def push_or_eval(self, val: PdObject) -> None:
        if isinstance(val, Block):
            val(self)
        else:
            self.push(val)

    def pop_or_none(self) -> Optional[PdObject]:
        try:
            return self._stack.pop()
        except IndexError:
            res = self.stack_trigger()
            if res is None:
                return None
            else:
                self._x_stack[self.STACK_TRIGGER_X] = res
                return res

    def pop(self) -> PdObject:
        res = self.pop_or_none()
        if res is None:
            raise PdEmptyStackException('Empty stack')
        else:
            return res

    def pop_n(self, n: int) -> List[PdObject]:
        acc = [] # type: List[PdObject]
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

    def print_output_record(self, s: str, outfile: typing.IO[str] = sys.stdout) -> None:
        print(s, end=self.get_output_record_separator(), file=outfile)

    def pd_str(self, obj: PdObject) -> str:
        if isinstance(obj, (list, range)):
            return self.join_output_fields(self.pd_str(e) for e in obj)
        else: # includes str, int, float etc.
            return str(obj)

    def pop_stack_marker(self) -> int:
        if self.marker_stack:
            return self.marker_stack.pop()
        else:
            return 0
    def pop_until_stack_marker(self) -> List[PdObject]:
        marker = self.pop_stack_marker()
        ret = self._stack[marker:]
        self._stack = self._stack[:marker]
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
        return 'Stack dump: {}\nX-stack: {}'.format(repr(self._stack), repr(self._x_stack))

    def bracketed_shadow(self) -> 'Environment':
        env = Environment(
                evaluator=self.evaluator,
                stack=[],
                vars_delegate=self,
                stack_trigger=self.pop_or_none)
        env.mark_stack()
        return env

    def keep_shadow(self) -> 'KeepShadowEnvironment':
        return KeepShadowEnvironment(self)

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

class KeepShadowEnvironment(Environment):
    def __init__(self, shadow_parent: Environment) -> None:
        Environment.__init__(self,
                evaluator = shadow_parent.evaluator,
                stack_trigger = self.shadow_keep_trigger,
                vars_delegate = shadow_parent)
        self.shadow_parent = shadow_parent
        self.shadow_i = 0

    def shadow_keep_trigger(self) -> Optional[PdObject]:
        self.shadow_parent.try_ensure_length(self.shadow_i + 1)
        ret = self.shadow_parent.index_stack_or_none(self.shadow_i)
        self.shadow_i += 1
        return ret
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
# deep actions {{{
# copy a thing recursively, fully structured as mutable lists
def pd_deep_copy_to_list(obj: PdValue) -> PdValue:
    if isinstance(obj, (Char, int, float)):
        return obj
    else:
        acc = []
        for e in pd_iterable(obj):
            acc.append(pd_deep_copy_to_list(e))
        return acc
# deeply map a Python num -> num function (no Char preservation)
def pd_deepmap_n2n(func: Callable[[Union[int, float]], PdNum], obj: PdValue) -> PdValue:
    if isinstance(obj, (Char, int, float)):
        return func(num.numerify(obj))
    else:
        acc = []
        for e in pd_iterable(obj):
            acc.append(pd_deepmap_n2n(func, e))
        return acc
# }}}
# iteration wrappers {{{
def pd_iterable(seq: PdSeq) -> Iterable[PdObject]:
    if isinstance(seq, str):
        return (Char(ord(c)) for c in seq)
    return seq

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
def pd_join(env: Environment, seq: PdSeq, joiner: PdSeq) -> PdObject:
    if isinstance(seq, (list, range)) and isinstance(joiner, (list, range)):
        acc = [] # type: List[PdObject]
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
def pd_replicate(atom: PdObject, n: int) -> PdSeq:
    if isinstance(atom, Char):
        return chr(atom.ord) * n
    else:
        return [atom] * n
def pd_build_like(orig: PdSeq, result: List[PdObject]) -> PdSeq:
    if isinstance(orig, str) and all(isinstance(c, (Char, int)) for c in result):
        return (
            ''.join(
                chr(c.ord if isinstance(c, Char) else c) # type: ignore
                for c in result
            )
        )
    else:
        return result
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
def pd_zip_as_list(seq1: PdSeq, seq2: PdSeq) -> PdObject:
    return [[e1, e2] for e1, e2 in zip(pd_iterable(seq1), pd_iterable(seq2))]
# }}}
# pd_find_entry et al. (wow code duplication much) {{{
def pd_find_entry(env: Environment, func: Block, seq: PdSeq) -> Tuple[Optional[int], Optional[PdObject]]:
    for i, e in py_enumerate(seq):
        if pd_truthy(env, func, [e]): return (i, e)
    return (None, None)

def pd_find_last_entry(env: Environment, func: Block, seq: PdSeq) -> Tuple[Optional[int], Optional[PdObject]]:
    for i, e in py_reversed_enumerate(seq):
        if pd_truthy(env, func, [e]): return (i, e)
    return (None, None)

def pd_count_in(env: Environment, e: PdValue, seq: PdSeq) -> int:
    if isinstance(seq, str):
        if isinstance(e, Char):
            return seq.count(chr(e.ord))
        elif isinstance(e, (int, float)):
            return seq.count(chr(int(e)))
        else:
            return seq.count(env.pd_str(e))
    elif isinstance(seq, range):
        # whatever, it's ok to count whatever is in a range
        return seq.count(e) # type: ignore
    else:
        return seq.count(e)

def pd_map(env: Environment, func: Block, seq: PdSeq) -> PdSeq:
    env.push_yx()
    acc = [] # type: List[PdObject]
    try:
        for i, element in py_enumerate(seq):
            env.set_yx(i, element)
            try:
                acc.extend(pd_sandbox(env, func, [element]))
            except PdContinueException: pass
    except PdBreakException: pass
    env.pop_yx()
    return pd_build_like(seq, acc)

def pd_mapsum(env: Environment, func: Block, seq: PdSeq) -> PdObject:
    env.push_yx()
    acc = [] # type: List[PdObject]
    try:
        for i, element in py_enumerate(seq):
            env.set_yx(i, element)
            try:
                acc.extend(pd_sandbox(env, func, [element]))
            except PdContinueException: pass
    except PdBreakException: pass
    env.pop_yx()
    return sum(acc)

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
    env.pop_yx()

def pd_foreach_then_empty_list(env: Environment, func: Block, seq: PdSeq) -> List[PdObject]:
    pd_foreach(env, func, seq)
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
    env.pop_yx()

def pd_foreach_x_only_then_empty_list(env: Environment, func: Block, seq: PdSeq) -> List[PdObject]:
    pd_foreach_x_only(env, func, seq)
    return []

def pd_run_with_probability_then_empty_list(env: Environment, func: Block, prob: float) -> List[PdObject]:
    if random.random() < prob: func(env)
    return []

def pd_filter(env: Environment, func: Block, seq: PdSeq, negate: bool = False) -> PdSeq:
    env.push_yx()
    acc = [] # type: List[PdObject]
    for i, element in enumerate(pd_iterable(seq)):
        env.set_yx(i, element)
        if pd_truthy(env, func, [element]) ^ negate:
            acc.append(element)
    env.pop_yx()
    return pd_build_like(seq, acc)

def pd_filter_indexes(env: Environment, func: Block, seq: PdSeq, negate: bool = False) -> List[int]:
    env.push_yx()
    acc = [] # type: List[int]
    for i, element in py_enumerate(seq):
        env.set_yx(i, element)
        if pd_truthy(env, func, [element]) ^ negate:
            acc.append(i)
    env.pop_yx()
    return acc

def pd_get(env: Environment, func: Block, seq: PdSeq) -> PdObject:
    _, e = pd_find_entry(env, func, seq)
    if e is None:
        raise AssertionError('pd_get: no element satisfying predicate found')
    else:
        return e

def pd_get_index(env: Environment, func: Block, seq: PdSeq) -> int:
    i, e = pd_find_entry(env, func, seq)
    if i is None:
        raise AssertionError('pd_get_index: no element satisfying predicate found')
    else:
        return i

def pd_get_last(env: Environment, func: Block, seq: PdSeq) -> PdObject:
    _, e = pd_find_last_entry(env, func, seq)
    if e is None:
        raise AssertionError('pd_getlast: no element satisfying predicate found')
    else:
        return e

def pd_get_index_last(env: Environment, func: Block, seq: PdSeq) -> int:
    i, e = pd_find_last_entry(env, func, seq)
    if i is None:
        raise AssertionError('pd_get_index_last: no element satisfying predicate found')
    else:
        return i
# }}}
# reduce, zip {{{
def pd_reduce(env: Environment, func: Block, seq: PdSeq) -> PdObject:
    acc = None # type: Optional[PdObject]
    for element in pd_iterable(seq):
        if acc is None:
            acc = element
        else:
            acc = pd_sandbox(env, func, [acc, element])[-1]
    if acc is None:
        raise AssertionError('pd_reduce on empty list')
    return acc

def pd_zip(env: Environment,
        func: Block,
        iterable1: Iterable[PdObject],
        iterable2: Iterable[PdObject]) -> PdObject:
    acc = [] # type: List[PdObject]
    for e1, e2 in zip(iterable1, iterable2):
        acc.extend(pd_sandbox(env, func, [e1, e2]))
    return acc
# }}}
# string conversions {{{
def basic_pd_str(obj: PdObject) -> str:
    if isinstance(obj, (list, range)):
        return ''.join(basic_pd_str(e) for e in obj)
    else: # includes str, int, float etc.
        return str(obj)

def pd_repr(obj: PdObject) -> str:
    if isinstance(obj, (list, range)):
        if isinstance(obj, list) and all(isinstance(e, str) for e in obj):
            # TODO fix string
            return repr(obj)
        return '[' + ' '.join(pd_repr(e) for e in obj) + ']'
    elif isinstance(obj, Block):
        return obj.code_repr()
    else:
        return repr(obj)
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
    acc = [] # type: List[PdObject]
    for element in pd_iterable(a):
        if counter[element] > 0:
            acc.append(element)
            counter[element] -= 1
    return pd_build_like(a, acc)
def pd_seq_union(a: PdSeq, b: PdSeq) -> PdSeq:
    acc = list(pd_iterable(a)) # type: List[PdObject]
    counter = collections.Counter(pd_iterable(a))
    for element in pd_iterable(b):
        if counter[element] > 0:
            counter[element] -= 1
        else:
            acc.append(element)
    return pd_build_like(a, acc)
def pd_seq_symmetric_difference(a: PdSeq, b: PdSeq) -> PdSeq:
    set_a = collections.Counter(pd_iterable(a))
    set_b = collections.Counter(pd_iterable(b))
    acc = [] # type: List[PdObject]
    for element in pd_iterable(a):
        if element not in set_b:
            acc.append(element)
    for element in pd_iterable(b):
        if element not in set_a:
            acc.append(element)
    return pd_build_like(a, acc)

def pd_seq_uniquify(a: PdSeq) -> PdSeq:
    s = set() # type: Set[PdObject]
    acc = [] # type: List[PdObject]
    for element in pd_iterable(a):
        if element not in s:
            acc.append(element)
            s.add(element)
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
    s = set() # type: Set[PdObject]
    for element in pd_iterable(a):
        if element in s:
            return False
        else:
            s.add(element)
    return True

def pd_if_then_empty_list(env: Environment, condition: PdObject, body: Block, negate: bool = False) -> List[PdObject]:
    if pytruth_eval(env, condition) ^ negate: body(env)
    return []
# }}}

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
def pd_array_keys_map(env: Environment, arr: list, ks: list, func: Block) -> list:
    arr_new = pd_deep_copy_to_list(arr)
    for key in ks:
        try:
            target = arr_new
            for i in key[:-1]: target = target[i]
            target[key[-1]] = pd_sandbox(env, func, [target[key[-1]]])[-1]
        except IndexError as e:
            raise AssertionError('could not index {} into {}'.format(key, arr_new)) from e
    return arr_new

def pd_array_key_get(arr: list, k: list) -> PdObject:
    target = arr
    for sk in k:
        target = target[sk]
    return target
# }}}
