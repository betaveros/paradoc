# coding: utf-8
# Started in the early morning of 2017-04-09 or thereabouts.
# Paradoc is a stack-based language suitable for golfing in the GolfScript
# tradition, with inspiration from CJam and many others.

# Like 05AB1E, Paradoc uses builtins named with the latin1 encoding, but all
# its builtins can also be accessed with ASCII names at the expense of some
# brevity.

# Drawing some inspiration from rhoScript and resisting the change towards CJam
# and other languages like Pyth, Paradoc is designed to be writeable in a
# literate manner as well as a golfed format.
from typing import *
import itertools
from paradoc.lex import is_nop_or_comment, is_trailer, lex_trailer, lex_code, break_trailer, is_numeric_literal_token, name_trailer_dissections
from paradoc.num import Char, PdNum
from paradoc.objects import Block, BuiltIn, PdObject, Environment, PdSeq, PdEmptyStackException, PdAbortException, PdBreakException, PdContinueException
import paradoc.objects as objects
import paradoc.base as base
import paradoc.input_triggers as input_triggers
from paradoc.trailer import TrailerFunc, Trailer
from paradoc.builtins import initialize_builtins
from paradoc.builtins.acutegrave import ag_convert
import sys
import argparse

def simple_interpolate(env: Environment, content: str, target: str) -> str:
    literal_fragments = [] # type: List[str]
    i = 0
    while True:
        ti = content.find(target, i)
        if ti == -1: break
        literal_fragments.append(content[i:ti])
        i = ti + len(target)
    # note the double inversion
    vals = [] # type: List[PdObject]
    for _ in literal_fragments:
        vals.append(env.pop())
    res = [] # type: List[str]
    for frag in literal_fragments:
        res.append(frag)
        res.append(env.pd_str(vals.pop()))
    return ''.join(res + [content[i:]])

def apply_pd_list_op(
        env: Environment, b: Block,
        op: Callable[[Environment, Block, PdSeq], PdObject],
        coerce_start: int = 0,
        ) -> None:

    lst = objects.pd_to_list_range(env.pop(), coerce_start)
    env.push(op(env, b, lst))

T = TypeVar('T')

TrailerPutter = Callable[[TrailerFunc[T]], Trailer[T]]

def trailer_putter(d: Dict[str, Trailer[T]], names: Tuple[str, ...]) -> TrailerPutter:
    def inner(f: TrailerFunc[T]) -> Trailer[T]:
        t = Trailer(names[0], f, aliases=list(names))
        for name in names:
            assert name not in d
            d[name] = t
        return t
    return inner

def build_block_trailer_dict() -> Dict[str, Trailer[Block]]: # {{{
    ret = dict() # type: Dict[str, Trailer[Block]]
    def put(*names: str) -> TrailerPutter[Block]:
        return trailer_putter(ret, names)

    @put("reluctant", "") # will be called as a trailing _
    def make_reluctant(env: Environment, b: Block) -> Tuple[Block, bool]:
        return (b, True)

    @put("anti", "a")
    def anti_trailer(outer_env: Environment, b: Block) -> Tuple[Block, bool]:
        def anti_b(env: Environment) -> None:
            e2, e1 = env.pop2()
            env.push(e2, e1)
            b(env)
        return (BuiltIn(b.code_repr() + "_anti", anti_b), True)

    @put("bind", "b")
    def bind_trailer(outer_env: Environment, b: Block) -> Tuple[Block, bool]:
        e = outer_env.pop()
        def bind_b(env: Environment) -> None:
            env.push(e)
            b(env)
        return (BuiltIn(b.code_repr() + "_bind", bind_b), True)

    @put("double", "d")
    def double_trailer(outer_env: Environment, b: Block) -> Tuple[Block, bool]:
        def double_b(env: Environment) -> None:
            shadow = env.bracketed_shadow()
            b(shadow)
            b(env)
            env.push_env(shadow)
        return (BuiltIn(b.code_repr() + "_double", double_b), False)

    @put("each", "e")
    def each_trailer(outer_env: Environment, b: Block) -> Tuple[Block, bool]:
        def each_b(env: Environment) -> None:
            lst = objects.pd_to_list_range(env.pop())
            objects.pd_foreach(env, b, lst)
        return (BuiltIn(b.code_repr() + "_each", each_b), False)

    @put("filter", "select", "f")
    def filter_trailer(outer_env: Environment, b: Block) -> Tuple[Block, bool]:
        return (BuiltIn(b.code_repr() + "_filter",
                lambda env: apply_pd_list_op(env, b, objects.pd_filter)), False)

    @put("get", "g")
    def get_trailer(outer_env: Environment, b: Block) -> Tuple[Block, bool]:
        return (BuiltIn(b.code_repr() + "_get",
                lambda env: apply_pd_list_op(env, b, objects.pd_get)), False)

    @put("high", "h")
    def high_trailer(outer_env: Environment, b: Block) -> Tuple[Block, bool]:
        return (BuiltIn(b.code_repr() + "_high",
                lambda env: apply_pd_list_op(env, b, objects.pd_get_index_last)), False)

    @put("index", "i")
    def index_trailer(outer_env: Environment, b: Block) -> Tuple[Block, bool]:
        return (BuiltIn(b.code_repr() + "_index",
                lambda env: apply_pd_list_op(env, b, objects.pd_get_index)), False)

    @put("keep", "k")
    def keep_trailer(outer_env: Environment, b: Block) -> Tuple[Block, bool]:
        def keep_b(env: Environment) -> None:
            shadow = env.keep_shadow()
            b(shadow)
            env.push_env(shadow)
        return (BuiltIn(b.code_repr() + "_keep", keep_b), False)

    @put("last", "l")
    def last_trailer(outer_env: Environment, b: Block) -> Tuple[Block, bool]:
        return (BuiltIn(b.code_repr() + "_last",
                lambda env: apply_pd_list_op(env, b, objects.pd_get_last)), False)

    @put("map", "m")
    def map_trailer(outer_env: Environment, b: Block) -> Tuple[Block, bool]:
        return (BuiltIn(b.code_repr() + "_map",
                lambda env: apply_pd_list_op(env, b, objects.pd_map)), False)

    @put("onemap", "o")
    def onemap_trailer(outer_env: Environment, b: Block) -> Tuple[Block, bool]:
            return (BuiltIn(b.code_repr() + "_onemap",
                    lambda env: apply_pd_list_op(env, b, objects.pd_map, coerce_start=1)), False)

    @put("reduce", "fold", "r")
    def reduce_trailer(outer_env: Environment, b: Block) -> Tuple[Block, bool]:
            return (BuiltIn(b.code_repr() + "_reduce",
                    lambda env: apply_pd_list_op(env, b, objects.pd_reduce)), False)

    @put("keepunder", "q")
    def keepunder_trailer(outer_env: Environment, b: Block) -> Tuple[Block, bool]:
            def keepunder_b(env: Environment) -> None:
                shadow = env.keep_shadow()
                b(shadow)
                env.push_keep_shadow_env_under(shadow)
            return (BuiltIn(b.code_repr() + "_keepunder", keepunder_b), False)

    @put("under", "u")
    def under_trailer(outer_env: Environment, b: Block) -> Tuple[Block, bool]:
            def under_b(env: Environment) -> None:
                t = env.pop()
                b(env)
                env.push(t)
            return (BuiltIn(b.code_repr() + "_under", under_b), False)

    @put("xloop", "x")
    def xloop_trailer(outer_env: Environment, b: Block) -> Tuple[Block, bool]:
            def xloop_b(env: Environment) -> None:
                lst = objects.pd_to_list_range(env.pop())
                objects.pd_foreach_x_only(env, b, lst)
            return (BuiltIn(b.code_repr() + "_xloop", xloop_b), False)

    @put("zip", "z")
    def zip_trailer(outer_env: Environment, b: Block) -> Tuple[Block, bool]:
            def zip_b(env: Environment) -> None:
                lst_b = objects.pd_to_list_range(env.pop())
                lst_a = objects.pd_to_list_range(env.pop())
                env.push(objects.pd_zip(env, b, lst_a, lst_b))
            return (BuiltIn(b.code_repr() + "_zip", zip_b), False)

    @put("all", "â")
    def all_trailer(outer_env: Environment, b: Block) -> Tuple[Block, bool]:
            def all_b(env: Environment) -> None:
                lst = objects.pd_to_list_range(env.pop())
                env.push(int(all(
                    objects.pd_map(env, b, lst))))
            return (BuiltIn(b.code_repr() + "_all", all_b), False)

    @put("exists", "ê")
    def exists_trailer(outer_env: Environment, b: Block) -> Tuple[Block, bool]:
            def exists_b(env: Environment) -> None:
                lst = objects.pd_to_list_range(env.pop())
                env.push(int(any(
                    objects.pd_map(env, b, lst))))
            return (BuiltIn(b.code_repr() + "_exists", exists_b), False)

    @put("autozip", "ä")
    def autozip_trailer(outer_env: Environment, b: Block) -> Tuple[Block, bool]:
            def autozip_b(env: Environment) -> None:
                lst_a = objects.pd_to_list_range(env.pop())
                env.push(objects.pd_zip(env, b, lst_a, lst_a[1:]))
            return (BuiltIn(b.code_repr() + "_autozip", autozip_b), False)
    @put("enumap", "ë")
    def enumap_trailer(outer_env: Environment, b: Block) -> Tuple[Block, bool]:
            def enumap_b(env: Environment) -> None:
                lst_a = objects.pd_to_list_range(env.pop())
                env.push(objects.pd_zip(env, b, range(len(lst_a)), lst_a))
            return (BuiltIn(b.code_repr() + "_enumap", enumap_b), False)
    @put("mapsum", "š")
    def mapsum_trailer(outer_env: Environment, b: Block) -> Tuple[Block, bool]:
            return (BuiltIn(b.code_repr() + "_mapsum",
                    lambda env: apply_pd_list_op(env, b, objects.pd_mapsum)), False)

    @put("vectorize", "bindmap", "v")
    def vectorize_trailer(outer_env: Environment, b: Block) -> Tuple[Block, bool]:
            e = outer_env.pop()
            def bind_b(env: Environment) -> None:
                env.push(e)
                b(env)
            return (BuiltIn(b.code_repr() + "_bindmap",
                    lambda env: apply_pd_list_op(env,
                        BuiltIn(b.code_repr() + "_bind", bind_b),
                        objects.pd_map)), False)

    return ret
block_trailer_dict = build_block_trailer_dict()
# }}}
def build_string_trailer_dict() -> Dict[str, Trailer[str]]: # {{{
    ret = dict() # type: Dict[str, Trailer[str]]
    def put(*names: str) -> TrailerPutter[str]:
        return trailer_putter(ret, names)

    @put("interpolate", "i")
    def interpolate_trailer(outer_env: Environment, s: str) -> Tuple[PdObject, bool]:
        def interpolate_s(env: Environment) -> None:
            env.push(simple_interpolate(env, s, '%'))
        return (BuiltIn(objects.pd_repr(s) + "_interpolate", interpolate_s), False)

    @put("interoutput", "o")
    def interoutput_trailer(outer_env: Environment, s: str) -> Tuple[PdObject, bool]:
        def interoutput_s(env: Environment) -> None:
            print(simple_interpolate(env, s, '%'), end="")
        return (BuiltIn(objects.pd_repr(s) + "_interoutput", interoutput_s), False)

    @put("interprint", "p")
    def interprint_trailer(outer_env: Environment, s: str) -> Tuple[PdObject, bool]:
        def interprint_s(env: Environment) -> None:
            env.print_output_record(simple_interpolate(env, s, '%'))
        return (BuiltIn(objects.pd_repr(s) + "_interprint", interprint_s), False)

    @put("format", "f")
    def format_trailer(outer_env: Environment, s: str) -> Tuple[PdObject, bool]:
        format_count = s.count('%') - 2 * s.count('%%')
        if format_count == 0:
            s = "%" + s
            format_count = 1
        def format_s(env: Environment) -> None:
            format_args = env.pop_n(format_count)
            try:
                format_res = s % tuple(format_args)
            except TypeError:
                # TODO: this is super hacky and awful, but useful, and I
                # guess there's no real way to correctly type-coerce into
                # format strings short of writing our own format parser...
                try:
                    format_res = s % tuple(
                            map(num.intify, format_args)) # type: ignore
                except TypeError:
                    raise Exception('Could not format string ' + repr(s) +
                            ' with arguments ' + repr(format_args))
            env.push(format_res)
        return (BuiltIn(objects.pd_repr(s) + "_format", format_s), False)

    @put("debug")
    def debug_trailer(outer_env: Environment, s: str) -> Tuple[PdObject, bool]:
        def debug_s(env: Environment) -> None:
            print(s, 'dump:', env.debug_dump(), file=sys.stderr)
        return (BuiltIn(objects.pd_repr(s) + "_debug", debug_s), False)

    return ret
string_trailer_dict = build_string_trailer_dict()
# }}}
def build_int_trailer_dict() -> Dict[str, Trailer[int]]: # {{{
    ret = dict() # type: Dict[str, Trailer[int]]
    def put(*names: str) -> TrailerPutter[int]:
        return trailer_putter(ret, names)

    @put("minus", "m")
    def minus_trailer(outer_env: Environment, i: int) -> Tuple[int, bool]:
        return (-i, False)
    @put("hundred", "h")
    def hundred_trailer(outer_env: Environment, i: int) -> Tuple[int, bool]:
        return (i * 100, False)

    @put("thousand", "k")
    def thousand_trailer(outer_env: Environment, i: int) -> Tuple[int, bool]:
        return (i * 1000, False)

    @put("under", "u")
    def under_trailer(outer_env: Environment, i: int) -> Tuple[Block, bool]:
        def under_i(env: Environment) -> None:
            t = env.pop()
            env.push(i)
            env.push(t)
        return (BuiltIn(str(i) + "_under", under_i), False)
    @put("force")
    def force_trailer(outer_env: Environment, i: int) -> Tuple[Block, bool]:
        def force_i(env: Environment) -> None:
            xs = env.pop_n(i)
            env.push(*xs)
        return (BuiltIn(str(i) + "_force", force_i), False)

    @put("array", "a")
    def array_trailer(outer_env: Environment, i: int) -> Tuple[Block, bool]:
        def array_i(env: Environment) -> None:
            env.push(env.pop_n(i))
        return (BuiltIn(str(i) + "_array", array_i), False)

    @put("zip", "z")
    def zip_trailer(outer_env: Environment, i: int) -> Tuple[Block, bool]:
        def zip_i(env: Environment) -> None:
            env.push(objects.pd_zip_as_list(*env.pop_n(i)))
        return (BuiltIn(str(i) + "_zip", zip_i), False)

    @put("bits", "b")
    def bits_trailer(outer_env: Environment, i: int) -> Tuple[Block, bool]:
        i_bits = base.to_base_digits_at_least_two(2, i)
        def bits_i(env: Environment) -> None:
            env.push(*i_bits)
        return (BuiltIn(str(i) + "_bits", bits_i), False)

    @put("power", "p")
    def power_trailer(outer_env: Environment, i: int) -> Tuple[Block, bool]:
        def power_i(env: Environment) -> None:
            v = env.pop()
            if isinstance(v, Block):
                raise Exception('Cannot take power of block')
            else:
                env.push(objects.pd_deepmap_n2v(lambda e: e ** i, v))
        return (BuiltIn(str(i) + "_power", power_i), False)

    @put("root", "r")
    def root_trailer(outer_env: Environment, i: int) -> Tuple[Block, bool]:
        def root_i(env: Environment) -> None:
            v = env.pop()
            if isinstance(v, Block):
                raise Exception('Cannot take root of block')
            else:
                env.push(objects.pd_deepmap_n2v(lambda e: e ** (1/i), v))
        return (BuiltIn(str(i) + "_root", root_i), False)

    for agchar in 'áéíóúàèìòùý':
        @put(agchar)
        def ag_trailer(outer_env: Environment, i: int, agchar: str = agchar) -> Tuple[PdObject, bool]:
            return (ag_convert(agchar, i, str(i) + agchar), False)

    return ret
int_trailer_dict = build_int_trailer_dict()
# }}}
def build_float_trailer_dict() -> Dict[str, Trailer[float]]: # {{{
    ret = dict() # type: Dict[str, Trailer[float]]
    def put(*names: str) -> TrailerPutter[float]:
        return trailer_putter(ret, names)

    @put("minus", "m")
    def minus_trailer(outer_env: Environment, f: float) -> Tuple[float, bool]:
        return (-f, False)
    @put("hundred", "h")
    def hundred_trailer(outer_env: Environment, f: float) -> Tuple[float, bool]:
        return (f * 100, False)

    @put("thousand", "k")
    def thousand_trailer(outer_env: Environment, f: float) -> Tuple[float, bool]:
        return (f * 1000, False)

    return ret
float_trailer_dict = build_float_trailer_dict()
# }}}

def act_on_trailer_token(outer_env: Environment, token: str, b0: PdObject) -> Tuple[PdObject, bool]:
    # print("act_on_trailer_token", token, b0)
    assert token

    if token.startswith("_"): token = token[1:]

    if isinstance(b0, Block):
        b = b0 # type: Block
        try:
            return block_trailer_dict[token](outer_env, b)
        except KeyError:
            raise NotImplementedError("unknown trailer token " + token + " on blocklike " + b.code_repr())
    elif isinstance(b0, str):
        s = b0 # type: str
        try:
            return string_trailer_dict[token](outer_env, s)
        except KeyError:
            raise NotImplementedError("unknown trailer token " + token + " on string " + repr(s))

    elif isinstance(b0, int):
        i = b0 # type: int
        try:
            return int_trailer_dict[token](outer_env, i)
        except KeyError:
            raise NotImplementedError("unknown trailer token " + token + " on int " + repr(i))

    elif isinstance(b0, float):
        f = b0 # type: float
        try:
            return float_trailer_dict[token](outer_env, f)
        except KeyError:
            raise NotImplementedError("unknown trailer token " + token + " on float " + repr(f))

    raise NotImplementedError("unknown trailer token " + token + " on unknown thing " + repr(b0))

BodyExecutor = Callable[[Environment, Block], None]

def act(env: Environment, obj: PdObject, reluctant: bool,
        post_executor: Optional[BodyExecutor]) -> None:

    # print("in act, post_executor", post_executor)

    if isinstance(obj, Block):
        if post_executor is not None:
            post_executor(env, obj)
        elif not reluctant:
            obj(env)
        else:
            env.push(obj)
    else:
        env.push(obj)

def act_after_trailer_tokens(env: Environment,
        obj: PdObject,
        trailer_tokens: Iterable[str],
        reluctant: bool = False,
        post_executor: Optional[BodyExecutor] = None) -> None:

    for trailer_token in trailer_tokens:
        obj, reluctant = act_on_trailer_token(env, trailer_token, obj)
        # print('in act_after_trailer_tokens', trailer_token, obj, reluctant)
    # print('ending act_after_trailer_tokens', obj, reluctant)
    act(env, obj, reluctant, post_executor)

def parse_string_onto(env: Environment, token: str, trailer: str) -> None:
    assert(token[0] == token[-1] == '"')
    backslashed = False
    acc = [] # type: List[str]
    for c in token[1:-1]:
        if backslashed:
            if c not in '\\"': acc.append('\\')
            acc.append(c)
            backslashed = False
        elif c == '\\':
            backslashed = True
        else:
            acc.append(c)
    act_after_trailer_tokens(env, ''.join(acc), lex_trailer(trailer))

def make_for_loop_over(iterable: Iterable[PdObject]) -> BodyExecutor:
    def inner(env: Environment, body: Block) -> None:
        for e in iterable:
            # print("make_for_loop_overpushing", e)
            env.push(e)
            # print("make_for_loop_overrunning")
            body(env)
    return inner

# helping mypy out
def to_int_for_forloop(n: PdObject) -> int:
    if isinstance(n, int):
        return n
    elif isinstance(n, float):
        return int(n)
    elif isinstance(n, str):
        return int(n)
    else:
        raise Exception('Non-numeric non-string ' + repr(n) + ' cannot be used as forloop limit')

space_set = set([' ', '\n', '\r', '\t'])

class CodeBlock(Block):
    def __init__(self, tokens: Iterable[str],
            optimize_comments: bool = True,
            optimize_spaces: bool = True,
            ) -> None:
        self.tokens = [token for token in tokens if
                not (optimize_comments and token.startswith('..'))
                and
                not (optimize_spaces and token in space_set)
                ]

    def code_repr(self) -> str:
        return '{' + ''.join(self.tokens) + '}'

    def __call__(self, env: Environment) -> None:

        # print('entering __call__', self.tokens)

        body_start = 0
        block_level = 0
        executor = None # type: Optional[BodyExecutor]
        def set_executor(executor0: BodyExecutor) -> None:
            nonlocal block_level, executor
            block_level = 1
            executor = executor0
        while body_start < len(self.tokens) and (
                is_trailer(self.tokens[body_start])
                or
                is_nop_or_comment(self.tokens[body_start])
                ):
            trailer_token = self.tokens[body_start]
            body_start += 1
            if is_nop_or_comment(trailer_token): continue
            if trailer_token == 'i' or trailer_token == '_input':
                env.input_trigger = input_triggers.all
            elif trailer_token == 'l' or trailer_token == '_lines':
                env.input_trigger = input_triggers.line
            elif trailer_token == 'w' or trailer_token == '_words':
                env.input_trigger = input_triggers.word
            elif trailer_token == 'v' or trailer_token == '_value':
                env.input_trigger = input_triggers.value
            elif trailer_token == 'c' or trailer_token == '_chars':
                env.input_trigger = input_triggers.char

            elif trailer_token == 'f' or trailer_token == '_for':
                set_executor(make_for_loop_over(
                        env.capture_stack_as_iterable()))
            elif trailer_token == 'z' or trailer_token == '_zerofor':
                try:
                    n = to_int_for_forloop(env.pop())
                    set_executor(make_for_loop_over(range(n)))
                except PdEmptyStackException:
                    set_executor(make_for_loop_over(itertools.count(0)))
            elif trailer_token == 'o' or trailer_token == '_onefor':
                try:
                    n = to_int_for_forloop(env.pop())
                    set_executor(make_for_loop_over(range(1, n+1)))
                except PdEmptyStackException:
                    set_executor(make_for_loop_over(itertools.count(1)))
            elif trailer_token == 's' or trailer_token == '_space':
                env.put('Ñ', ' ')
            elif trailer_token == 'n' or trailer_token == '_newline':
                env.put('Ñ', '\n')
            else:
                raise NotImplementedError('unknown global trailer token ' + repr(trailer_token))

        assign_active = False
        destructive_assign = False
        block_acc = [] # type: List[str]

        for token0 in self.tokens[body_start:]:
            token, trailer = break_trailer(token0)
            # print('in body', repr(token), repr(trailer), file=sys.stderr)
            try:
                if assign_active:
                    assert not token0[0].isdigit()
                    x = env.pop()
                    if not destructive_assign: env.push(x)
                    env.put(token0, x)
                    assign_active = False
                elif block_level == 0:
                    if token.startswith('}'):
                        raise Exception("closing curly brace out of nowhere")
                    elif token.startswith('{'):
                        block_level += 1
                        if trailer: block_acc.append(trailer)
                    elif token.startswith('..') or token.startswith('——'):
                        pass # comment
                    elif token.startswith('"'):
                        parse_string_onto(env, token, trailer)
                    elif token.startswith("'"):
                        env.push(Char(ord(token[1])))
                    elif is_numeric_literal_token(token):
                        r_token = token.replace('—', '-')
                        try:
                            parsed_num = int(r_token) # type: PdNum
                        except ValueError:
                            try:
                                parsed_num = float(r_token)
                            except ValueError:
                                raise ValueError('could not parse number ' + repr(token))
                        act_after_trailer_tokens(env, parsed_num, lex_trailer(trailer))
                    elif token.startswith('.'):
                        assign_active = True
                        destructive_assign = False
                    elif token.startswith('—'):
                        assign_active = True
                        destructive_assign = True
                    else:
                        val = None # type: Optional[PdObject]
                        trailer_tokens = None
                        for name, ts in name_trailer_dissections(token, trailer):
                            # print('name:', name, 'ts:', ts)
                            val = env.get_or_none(name)
                            if val is not None:
                                trailer_tokens = ts
                                break
                        if val is None or trailer_tokens is None:
                            raise NameError('Could not parse ' + repr((token, trailer)))

                        act_after_trailer_tokens(env, val, trailer_tokens)
                else:
                    if token.startswith('}'):
                        block_level -= 1
                        if block_level == 0:
                            act_after_trailer_tokens(env,
                                    CodeBlock(block_acc), lex_trailer(trailer),
                                    reluctant=True, post_executor=executor)
                            block_acc = []
                            executor = None
                        else:
                            block_acc.append(token0)
                    else:
                        if token.startswith('{'):
                            block_level += 1
                        block_acc.append(token0)
            except PdAbortException: raise
            except PdBreakException: raise
            except PdContinueException: raise
            except Exception as ex:
                msg = 'Error while interpreting token {} caused by exception: {}\n{}'.format(token + trailer, ex, env.debug_dump())
                raise Exception(msg) from ex
            # print('generic debug dump', env.debug_dump(), file=sys.stderr)
        while block_level > 0:
            block_level -= 1
            if block_level == 0:
                act_after_trailer_tokens(env,
                        CodeBlock(block_acc), [],
                        reluctant=True, post_executor=executor)
                block_acc = []
                executor = None
            else:
                block_acc.append('}')

def basic_evaluator(env: Environment, code: str) -> None:
    CodeBlock(list(lex_code(code)))(env)

def initialized_environment(sandboxed: bool) -> Environment:
    env = Environment(basic_evaluator,
            stack_trigger = lambda: env.input_trigger())
    initialize_builtins(env, sandboxed)
    return env

simple_eval_env_cache = initialized_environment(sandboxed=True)
def pd_simple_eval(code: str, use_cache: bool = True) -> List[PdObject]:
    if use_cache:
        env = simple_eval_env_cache
        env._stack = []
    else:
        env = initialized_environment(sandboxed=True)
    env.evaluate(code)
    return env._stack

def main_with_code(code: str, sandboxed: bool) -> None:
    env = initialized_environment(sandboxed)
    env.evaluate(code)
    print(env.pd_str(env._stack))

def paradoc_repl(sandboxed: bool) -> None:
    env = initialized_environment(sandboxed)
    while True:
        try:
            code = input("prdc> ")
            env.evaluate(code)
            print(env.pd_str(env._stack))
            print(objects.pd_repr(env._stack))
        except EOFError:
            break
        except PdAbortException:
            raise
        except Exception as e:
            print(e, file=sys.stderr)

def list_builtins(name_filter: Callable[[str], bool]) -> None:
    env = initialized_environment(sandboxed=True)
    for name, obj in sorted(env.vars.items()):
        if name_filter(name):
            print(name, repr(obj))

def main() -> None:
    # code = "3 4+"
    # code = "Eval Pack Uncons Range"
    # code = '''":"{"\n:-"\\')*}64,/'''
    # code = "[3 4 5 7][6 8 2 3])m++r"
    # code = "9 Range_one {Fc}_map +_fold 27 %_persist"
    parser = argparse.ArgumentParser(description='Paradoc interpreter')
    parser.add_argument('prog_file', type=str, metavar='FILE', nargs='?',
            help='Source Paradoc file')
    parser.add_argument('-e', type=str, metavar='EXPR',
            help='Paradoc expression to execute')
    parser.add_argument('--docs', action='store_true')
    parser.add_argument('--version', action='store_true')
    parser.add_argument('--list-builtins', action='store_true')
    parser.add_argument('--list-short-builtins', action='store_true')
    parser.add_argument('--sandboxed', default=False, action='store_true')
    args = parser.parse_args()

    try:
        if args.version:
            from paradoc.__version__ import version
            print("paradoc version " + version)
        elif args.list_builtins:
            list_builtins(lambda _: True)
        elif args.list_short_builtins:
            list_builtins(lambda name: len(name) <= 2)
        elif args.docs:
            from paradoc.docgen import document
            document(initialized_environment(sandboxed=True), [
                ('Block', block_trailer_dict),
                ('String', string_trailer_dict),
                ('Int', int_trailer_dict),
                ('Float', float_trailer_dict),
            ])
        elif args.e is not None:
            main_with_code(args.e, sandboxed=args.sandboxed)
        elif args.prog_file is not None:
            if args.prog_file.endswith('.cp1252.prdc'):
                import codecs
                with codecs.open(args.prog_file, 'r', 'cp1252') as cp1252_prog_file:
                    main_with_code(cp1252_prog_file.read(), sandboxed=args.sandboxed)
            else:
                with open(args.prog_file, 'r') as prog_file:
                    main_with_code(prog_file.read(), sandboxed=args.sandboxed)
        else:
            paradoc_repl(sandboxed=args.sandboxed)
    except PdAbortException as e:
        sys.exit(e.code)

if __name__ == "__main__": main()

# vim:set fdm=marker:
