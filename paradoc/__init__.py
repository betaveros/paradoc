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
from typing import Callable, Dict, Iterable, List, Optional, Tuple, TypeVar, Union
import itertools
from paradoc.lex import is_nop_or_comment, is_trailer, lex_trailer, lex_trailers, lex_code, break_trailer, is_numeric_literal_token, name_trailer_dissections
from paradoc.num import Char
from paradoc.objects import Block, BuiltIn, PdObject, Environment, PdSeq, PdEmptyStackException, PdAbortException, PdBreakException, PdContinueException
import paradoc.num as num
import paradoc.objects as objects
import paradoc.base as base
import paradoc.input_triggers as input_triggers
from paradoc.trailer import TrailerFunc, Trailer
from paradoc.builtins import initialize_builtins
from paradoc.builtins.acutegrave import ag_convert, ag_document
import paradoc.assign as assign
import sys
import argparse
import codecs

def simple_interpolate(env: Environment, content: str, target: str) -> str:
    literal_fragments: List[str] = []
    i = 0
    while True:
        ti = content.find(target, i)
        if ti == -1: break
        literal_fragments.append(content[i:ti])
        i = ti + len(target)
    # note the double inversion
    vals: List[PdObject] = []
    for _ in literal_fragments:
        vals.append(env.pop())
    res: List[str] = []
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

def trailer_putter(d: Dict[str, Trailer[T]],
        names: Tuple[str, ...],
        docs: Optional[str] = None,
        stability: str = "unknown") -> TrailerPutter:
    def inner(f: TrailerFunc[T]) -> Trailer[T]:
        t = Trailer(names[0], f, aliases=list(names),
                docs=docs, stability=stability)
        for name in names:
            assert name not in d
            d[name] = t
        return t
    return inner

def build_block_trailer_dict() -> Dict[str, Trailer[Block]]: # {{{
    ret: Dict[str, Trailer[Block]] = dict()
    def put(*names: str, docs: Optional[str] = None,
            stability: str = "unknown") -> TrailerPutter[Block]:
        return trailer_putter(ret, names, docs=docs, stability=stability)

    @put("reluctant", "", # will be called as a trailing _
            docs="""Make this block reluctant: push it instead of executing
            it.""",
            stability="beta")
    def make_reluctant(env: Environment, b: Block) -> Tuple[Block, bool]:
        return (b, True)

    @put("anti", "a",
            docs="""Swap the top two elements of the stack before running this
            block. Makes the result reluctant.""",
            stability="beta")
    def anti_trailer(outer_env: Environment, b: Block) -> Tuple[Block, bool]:
        def anti_b(env: Environment) -> None:
            e2, e1 = env.pop2()
            env.push(e2, e1)
            b(env)
        return (BuiltIn(b.code_repr() + "_anti", anti_b), True)

    @put("bind", "b",
            docs="""Right now, pop the top element of this stack; before each
            time this block is to be executed, push it. Makes the result
            reluctant.""",
            stability="beta")
    def bind_trailer(outer_env: Environment, b: Block) -> Tuple[Block, bool]:
        e = outer_env.pop()
        def bind_b(env: Environment) -> None:
            env.push(e)
            b(env)
        return (BuiltIn(b.code_repr() + "_bind", bind_b), True)

    @put("double", "d",
            docs="""Apply this block in a bracketed shadow, then apply it again
            on what's underneath. In essence, applies this block to two
            disjoint sets of arguments on the stack.

            ex: 1 2 8 9 +d => 3 17""",
            stability="alpha")
    def double_trailer(outer_env: Environment, b: Block) -> Tuple[Block, bool]:
        def double_b(env: Environment) -> None:
            shadow = env.bracketed_shadow()
            b(shadow)
            b(env)
            env.push_env(shadow)
        return (BuiltIn(b.code_repr() + "_double", double_b), False)

    @put("each", "e",
            docs="""Apply this block to each element of a list (coerces numbers
            to ranges). Compare {{ 'xloop'|bt }}.
            """,
            stability="beta")
    def each_trailer(outer_env: Environment, b: Block) -> Tuple[Block, bool]:
        def each_b(env: Environment) -> None:
            lst = objects.pd_to_list_range(env.pop())
            objects.pd_foreach(env, b, lst)
        return (BuiltIn(b.code_repr() + "_each", each_b), False)

    @put("filter", "select", "f",
            docs="""Apply this block to each element of a list (coerces numbers
            to ranges) and filter elements for which the block gives a truthy
            result.""",
            stability="beta")
    def filter_trailer(outer_env: Environment, b: Block) -> Tuple[Block, bool]:
        return (BuiltIn(b.code_repr() + "_filter",
                lambda env: apply_pd_list_op(env, b, objects.pd_filter)), False)

    @put("get", "g",
            docs="""Find the first element of the list where this block gives a
            truthy result (coerces numbers to ranges).""",
            stability="unstable")
    def get_trailer(outer_env: Environment, b: Block) -> Tuple[Block, bool]:
        return (BuiltIn(b.code_repr() + "_get",
                lambda env: apply_pd_list_op(env, b, objects.pd_get)), False)

    @put("high", "h",
            docs="""Find the last index of the list where this block gives a
            truthy result (coerces numbers to ranges).""",
            stability="unstable")
    def high_trailer(outer_env: Environment, b: Block) -> Tuple[Block, bool]:
        return (BuiltIn(b.code_repr() + "_high",
                lambda env: apply_pd_list_op(env, b, objects.pd_get_index_last)), False)

    @put("index", "i",
            docs="""Find the first index of the list where this block gives a
            truthy result (coerces numbers to ranges).""",
            stability="unstable")
    def index_trailer(outer_env: Environment, b: Block) -> Tuple[Block, bool]:
        return (BuiltIn(b.code_repr() + "_index",
                lambda env: apply_pd_list_op(env, b, objects.pd_get_index)), False)

    @put("keep", "k",
            docs="""Execute this block in a preservation-shadow, so that any
            elements it pops aren't actually popped from the stack (so, "keep"
            those elements around).

            Compare {{ 'keepunder'|bt }}.

            ex:
            10 Uk => 10 1
            5 6 +k => 5 6 11""",
            stability="beta")
    def keep_trailer(outer_env: Environment, b: Block) -> Tuple[Block, bool]:
        def keep_b(env: Environment) -> None:
            shadow = env.keep_shadow()
            b(shadow)
            env.push_env(shadow)
        return (BuiltIn(b.code_repr() + "_keep", keep_b), False)

    @put("last", "l",
            docs="""Find the last index of the list where this block gives a
            truthy result (coerces numbers to ranges).""",
            stability="unstable")
    def last_trailer(outer_env: Environment, b: Block) -> Tuple[Block, bool]:
        return (BuiltIn(b.code_repr() + "_last",
                lambda env: apply_pd_list_op(env, b, objects.pd_get_last)), False)

    @put("loop",
            docs="""Loop this block forever (until an error is thrown).""",
            stability="alpha")

    def loop_trailer(outer_env: Environment, b: Block) -> Tuple[Block, bool]:
        def loop_b(env: Environment) -> None:
            objects.pd_forever_then_empty_list(env, b)
        return (BuiltIn(b.code_repr() + "_loop", loop_b), False)

    @put("map", "m",
            docs="""Apply this block to each element of a list (coerces numbers
            to ranges); collect the results into a new list.""",
            stability="beta")
    def map_trailer(outer_env: Environment, b: Block) -> Tuple[Block, bool]:
        return (BuiltIn(b.code_repr() + "_map",
                lambda env: apply_pd_list_op(env, b, objects.pd_map)), False)

    @put("onemap", "o",
            docs="""Apply this block to each element of a list (coerces numbers
            to 1-indexed ranges); collect the results into a new list.""",
            stability="unstable")
    def onemap_trailer(outer_env: Environment, b: Block) -> Tuple[Block, bool]:
        return (BuiltIn(b.code_repr() + "_onemap",
                lambda env: apply_pd_list_op(env, b, objects.pd_map, coerce_start=1)), False)

    @put("reduce", "fold", "r",
            docs="""Combine all elements in a list into one by repeatedly
            applying a binary block (coerces numbers to 1-indexed ranges), and
            push the final element.

            ex: [10 20 30] +r => 60""",
            stability="beta")
    def reduce_trailer(outer_env: Environment, b: Block) -> Tuple[Block, bool]:
        return (BuiltIn(b.code_repr() + "_reduce",
                lambda env: apply_pd_list_op(env, b, objects.pd_reduce)), False)

    @put("keepunder", "q",
            docs="""Execute this block in a preservation-shadow, so that any
            elements it pops aren't actually popped from the stack. Then push
            its results underneath elements it thinks were popped.

            Compare {{ 'keep'|bt }}.

            Mnemonic: "q" and "k" are phonetically similar and "q" is usually
            followed by a "u".

            ex:
            10 Uq => 1 10
            5 6 +q => 11 5 6""",
            stability="beta")
    def keepunder_trailer(outer_env: Environment, b: Block) -> Tuple[Block, bool]:
        def keepunder_b(env: Environment) -> None:
            shadow = env.keep_shadow()
            b(shadow)
            env.push_keep_shadow_env_under(shadow)
        return (BuiltIn(b.code_repr() + "_keepunder", keepunder_b), False)

    @put("under", "u",
            docs="""Execute this block underneath the top element. That is,
            before executing this block, pop the top element, and after
            executing it, push it back.

            ex:
            5 10 Uu => 1 10
            1 5 9 +u => 6 9""",
            stability="beta")
    def under_trailer(outer_env: Environment, b: Block) -> Tuple[Block, bool]:
        def under_b(env: Environment) -> None:
            t = env.pop()
            b(env)
            env.push(t)
        return (BuiltIn(b.code_repr() + "_under", under_b), False)

    @put("vectorize", "bindmap", "v",
            docs="""Pop the top element of the stack. Then, apply this block to
            each element of the next element of the stack (coerces numbers to
            ranges), pushing that top element before each application; collect
            the results into a new list.

            Basically a {{ 'bind'|bt }} followed by a {{ 'map'|bt }};
            you can imagine it as vectorizing an operator if the top element of
            the stack is a scalar and the one beneath it is a sequence, hence
            the single-letter name. But note that it isn't as eager as bind.

            ex: [1 2 3] 100+v => [101 102 103]""",
            stability="alpha")
    def vectorize_trailer(outer_env: Environment, b: Block) -> Tuple[Block, bool]:
        def bindmap_b(env: Environment) -> None:
            e = env.pop()
            def bind_b(inner_env: Environment) -> None:
                inner_env.push(e)
                b(inner_env)
            apply_pd_list_op(env,
                BuiltIn(b.code_repr() + "_bind", bind_b),
                objects.pd_map)
        return (BuiltIn(b.code_repr() + "_bindmap", bindmap_b), False)

    @put("mapbind", "ß",
            docs="""Pop the second-to-top element of the stack. Then, apply
            this block to each element of the top element of the stack (coerces
            numbers to ranges), pushing what was the second-to-top element
            underneath the top element before each application; collect the
            results into a new list.

            Sort of a reversed {{ 'bindmap'|bt }}.""",
            stability="alpha")
    def mapbind_trailer(outer_env: Environment, b: Block) -> Tuple[Block, bool]:
        def mapbind_b(env: Environment) -> None:
            x = env.pop()
            e = env.pop()
            env.push(x)
            def underbind_b(inner_env: Environment) -> None:
                y = inner_env.pop()
                inner_env.push(e)
                inner_env.push(y)
                b(inner_env)
            apply_pd_list_op(env,
                BuiltIn(b.code_repr() + "_underbind", underbind_b),
                objects.pd_map)
        return (BuiltIn(b.code_repr() + "_mapbind", mapbind_b), False)

    @put("deepmap", "walk", "w",
            docs="""Apply this block to each element of a possibly multi-level
            list (coerces numbers to ranges), as deeply as possible; collect
            the results into a new list with the same shape. Mnemonic: walk,
            as in traversing the entire structure; or upside-down "deeper"
            m.""",
            stability="alpha")
    def deepmap_trailer(outer_env: Environment, b: Block) -> Tuple[Block, bool]:
        return (BuiltIn(b.code_repr() + "_deepmap",
                lambda env: apply_pd_list_op(env, b, objects.pd_deepmap_block)), False)

    @put("xloop", "x",
            docs="""Execute this block once for each element of a list (coerces
            numbers to ranges). Unlike {{ 'each'|bt }}, the element is not
            pushed onto the stack, but is put into the X-stack and can be
            accessed through X.

            See also {{ '*'|b }}.
            """,
            stability="beta")

    def xloop_trailer(outer_env: Environment, b: Block) -> Tuple[Block, bool]:
        def xloop_b(env: Environment) -> None:
            lst = objects.pd_to_list_range(env.pop())
            objects.pd_foreach_x_only(env, b, lst)
        return (BuiltIn(b.code_repr() + "_xloop", xloop_b), False)

    @put("ziplongest", "y",
            docs="""Execute this block once for each corresponding pair of
            elements from two lists (coerces numbers to ranges). Both elements
            are pushed onto the stack. Collect the results into a list, which
            has the same length as the longer of the arguments; if one list is
            shorter, the other list's extra elements are put verbatim into the
            list.""",
            stability="beta")
    def ziplongest_trailer(outer_env: Environment, b: Block) -> Tuple[Block, bool]:
        def ziplongest_b(env: Environment) -> None:
            lst_b = objects.pd_to_list_range(env.pop())
            lst_a = objects.pd_to_list_range(env.pop())
            env.push(objects.pd_ziplongest(env, b, lst_a, lst_b))
        return (BuiltIn(b.code_repr() + "_ziplongest", ziplongest_b), False)

    @put("zip", "z",
            docs="""Execute this block once for each corresponding pair of
            elements from two lists (coerces numbers to ranges). Both elements
            are pushed onto the stack. Collect the results into a list, which
            has the same length as the shorter of the arguments; if one list is
            longer, its extra elements are ignored.""",
            stability="beta")
    def zip_trailer(outer_env: Environment, b: Block) -> Tuple[Block, bool]:
        def zip_b(env: Environment) -> None:
            lst_b = objects.pd_to_list_range(env.pop())
            lst_a = objects.pd_to_list_range(env.pop())
            env.push(objects.pd_zip(env, b, lst_a, lst_b))
        return (BuiltIn(b.code_repr() + "_zip", zip_b), False)

    @put("all", "â",
            docs="""Apply this block to each element of a list (coerces numbers
            to ranges); push whether at least one result is truthy.""",
            stability="alpha")
    def all_trailer(outer_env: Environment, b: Block) -> Tuple[Block, bool]:
        def all_b(env: Environment) -> None:
            lst = objects.pd_to_list_range(env.pop())
            env.push(int(all(
                objects.pd_map(env, b, lst))))
        return (BuiltIn(b.code_repr() + "_all", all_b), False)

    @put("exists", "ê",
            docs="""Apply this block to each element of a list (coerces numbers
            to ranges); push whether at least one result is truthy.""",
            stability="alpha")
    def exists_trailer(outer_env: Environment, b: Block) -> Tuple[Block, bool]:
        def exists_b(env: Environment) -> None:
            lst = objects.pd_to_list_range(env.pop())
            env.push(int(any(
                objects.pd_map(env, b, lst))))
        return (BuiltIn(b.code_repr() + "_exists", exists_b), False)

    @put("autozip", "ä",
            docs="""Execute this block once for each adjacent pair of elements
            from a list (coerces numbers to ranges). Both elements are pushed
            onto the stack.""",
            stability="beta")
    def autozip_trailer(outer_env: Environment, b: Block) -> Tuple[Block, bool]:
        def autozip_b(env: Environment) -> None:
            env.push(objects.pd_autozip(env, b, env.pop()))
        return (BuiltIn(b.code_repr() + "_autozip", autozip_b), False)

    @put("enumap", "ë",
            docs="""Apply this block to each index and element of a list
            (coerces numbers to ranges); collect the results into a new
            list.""",
            stability="alpha")
    def enumap_trailer(outer_env: Environment, b: Block) -> Tuple[Block, bool]:
        def enumap_b(env: Environment) -> None:
            lst_a = objects.pd_to_list_range(env.pop())
            env.push(objects.pd_zip(env, b, range(len(lst_a)), lst_a))
        return (BuiltIn(b.code_repr() + "_enumap", enumap_b), False)

    @put("loopzip", "ö",
            docs="""Execute this block once for each corresponding pair of
            elements from two lists (coerces numbers to ranges). Both elements
            are pushed onto the stack. Collect the results into a list, which
            has the same length as the longer of the arguments; if one list is
            shorter, that list's elements are cycled until it is the same
            length as the longer list.""",
            stability="alpha")
    def loopzip_trailer(outer_env: Environment, b: Block) -> Tuple[Block, bool]:
        def loopzip_b(env: Environment) -> None:
            lst_b = objects.pd_to_list_range(env.pop())
            lst_a = objects.pd_to_list_range(env.pop())
            env.push(objects.pd_loopzip(env, b, lst_a, lst_b))
        return (BuiltIn(b.code_repr() + "_loopzip", loopzip_b), False)

    @put("mapsum", "š",
            docs="""Apply this block to each element of a list (coerces numbers
            to ranges); sum the results.""",
            stability="alpha")
    def mapsum_trailer(outer_env: Environment, b: Block) -> Tuple[Block, bool]:
        return (BuiltIn(b.code_repr() + "_mapsum",
                lambda env: apply_pd_list_op(env, b, objects.pd_mapsum)), False)

    return ret
block_trailer_dict = build_block_trailer_dict()
# }}}
def build_string_trailer_dict() -> Dict[str, Trailer[str]]: # {{{
    ret: Dict[str, Trailer[str]] = dict()
    def put(*names: str, docs: Optional[str] = None,
            stability: str = "unknown") -> TrailerPutter[str]:
        return trailer_putter(ret, names, docs=docs, stability=stability)

    @put("interpolate", "i",
            docs="""Interpolate elements on the stack into % signs in this
            string.""",
            stability="alpha")
    def interpolate_trailer(outer_env: Environment, s: str) -> Tuple[PdObject, bool]:
        def interpolate_s(env: Environment) -> None:
            env.push(simple_interpolate(env, s, '%'))
        return (BuiltIn(objects.pd_repr(s) + "_interpolate", interpolate_s), False)

    @put("interoutput", "o",
            docs="""Interpolate elements on the stack into % signs in this
            string, then outputs the result.""",
            stability="alpha")
    def interoutput_trailer(outer_env: Environment, s: str) -> Tuple[PdObject, bool]:
        def interoutput_s(env: Environment) -> None:
            print(simple_interpolate(env, s, '%'), end="")
        return (BuiltIn(objects.pd_repr(s) + "_interoutput", interoutput_s), False)

    @put("interprint", "p",
            docs="""Interpolate elements on the stack into % signs in this
            string, then outputs the result followed by an output record
            separator.""",
            stability="alpha")
    def interprint_trailer(outer_env: Environment, s: str) -> Tuple[PdObject, bool]:
        def interprint_s(env: Environment) -> None:
            env.print_output_record(simple_interpolate(env, s, '%'))
        return (BuiltIn(objects.pd_repr(s) + "_interprint", interprint_s), False)

    @put("format", "f",
            docs="""Formats elements on the stack with Python % formatting. If
            no % sign is in the string, prepends a %.""",
            stability="alpha")
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

    @put("iftrue", "t",
            docs="""Pop an element; push this string if it's truthy, and an
            empty string if not.""",
            stability="unstable")
    def iftrue_trailer(outer_env: Environment, s: str) -> Tuple[PdObject, bool]:
        def iftrue_s(env: Environment) -> None:
            e = env.pop()
            env.push(s if e else "")
        return (BuiltIn(objects.pd_repr(s) + "_iftrue", iftrue_s), False)

    @put("debug",
            docs="""Print debugging information about the contents of the
            stack.""",
            stability="beta")
    def debug_trailer(outer_env: Environment, s: str) -> Tuple[PdObject, bool]:
        def debug_s(env: Environment) -> None:
            if env.get('Debug'):
                print(s, 'dump:', env.debug_dump(), file=sys.stderr)
        return (BuiltIn(objects.pd_repr(s) + "_debug", debug_s), False)

    return ret
string_trailer_dict = build_string_trailer_dict()
# }}}
def build_int_trailer_dict() -> Dict[str, Trailer[int]]: # {{{
    ret: Dict[str, Trailer[int]] = dict()
    def put(*names: str, docs: Optional[str] = None,
            stability: str = "unknown") -> TrailerPutter[int]:
        return trailer_putter(ret, names, docs=docs, stability=stability)

    @put("minus", "m", docs="Negate.", stability="stable")
    def minus_trailer(outer_env: Environment, i: int) -> Tuple[int, bool]:
        return (-i, False)
    @put("hundred", "h", docs="Multiply by a hundred.", stability="stable")
    def hundred_trailer(outer_env: Environment, i: int) -> Tuple[int, bool]:
        return (i * 100, False)

    @put("thousand", "k", docs="Multiply by a thousand.", stability="stable")
    def thousand_trailer(outer_env: Environment, i: int) -> Tuple[int, bool]:
        return (i * 1000, False)

    @put("under", "u", docs="Push under the top element.", stability="alpha")
    def under_trailer(outer_env: Environment, i: int) -> Tuple[Block, bool]:
        def under_i(env: Environment) -> None:
            t = env.pop()
            env.push(i)
            env.push(t)
        return (BuiltIn(str(i) + "_under", under_i), False)

    @put("force",
            docs="""Pop some number of elements and push them back immediately.
            A no-op except in that it may force input/stack triggers to occur.
            Usually used for debugging.""",
            stability="beta")
    def force_trailer(outer_env: Environment, i: int) -> Tuple[Block, bool]:
        def force_i(env: Environment) -> None:
            xs = env.pop_n(i)
            env.push(*xs)
        return (BuiltIn(str(i) + "_force", force_i), False)

    @put("array", "a",
            docs="""Pop some number of elements and push them back in a new
            array.""",
            stability="beta")
    def array_trailer(outer_env: Environment, i: int) -> Tuple[Block, bool]:
        def array_i(env: Environment) -> None:
            env.push(env.pop_n(i))
        return (BuiltIn(str(i) + "_array", array_i), False)

    @put("zip", "z",
            docs="""Pop some number of elements and zip them together.""",
            stability="beta")
    def zip_trailer(outer_env: Environment, i: int) -> Tuple[Block, bool]:
        def zip_i(env: Environment) -> None:
            if i <= 0:
                raise ValueError('Must zip a positive integer of things')
            args = env.pop_n(i)
            last_arg = args[-1]
            if isinstance(last_arg, Block):
                args = [env.pop()] + args[:-1]
                env.push(objects.pd_zip(env, last_arg,
                    *(objects.pd_to_list_range(e) for e in args)))
            else:
                env.push(objects.pd_zip_as_list(*(
                    objects.pd_to_list_range(e) for e in args)))
        return (BuiltIn(str(i) + "_zip", zip_i), False)

    @put("bits", "b",
            docs="""Interpret this number in binary and push it as a sequence
            of bits.""",
            stability="unstable")
    def bits_trailer(outer_env: Environment, i: int) -> Tuple[Block, bool]:
        i_bits = base.to_base_digits_at_least_two(2, i)
        def bits_i(env: Environment) -> None:
            env.push(*i_bits)
        return (BuiltIn(str(i) + "_bits", bits_i), False)

    @put("power", "p",
            docs="""Raise something to this power.""",
            stability="beta")
    def power_trailer(outer_env: Environment, i: int) -> Tuple[Block, bool]:
        def power_i(env: Environment) -> None:
            v = env.pop()
            if isinstance(v, Block):
                raise Exception('Cannot take power of block')
            else:
                env.push(objects.pd_deepmap_n2v(lambda e: e ** i, v))
        return (BuiltIn(str(i) + "_power", power_i), False)

    @put("root", "r",
            docs="""Take the nth root.""",
            stability="alpha")
    def root_trailer(outer_env: Environment, i: int) -> Tuple[Block, bool]:
        def root_i(env: Environment) -> None:
            v = env.pop()
            if isinstance(v, Block):
                raise Exception('Cannot take root of block')
            else:
                env.push(objects.pd_deepmap_n2v(lambda e: e ** (1/i), v))
        return (BuiltIn(str(i) + "_root", root_i), False)

    @put("get", "g",
            docs="""Index into a sequence.""",
            stability="unstable")
    def get_trailer(outer_env: Environment, i: int) -> Tuple[Block, bool]:
        def get_i(env: Environment) -> None:
            e = env.pop()
            assert isinstance(e, (str, list, range))
            env.push(objects.pd_index(e, i))
        return (BuiltIn(str(i) + "_get", get_i), False)

    @put("last", "l",
            docs="""Index from the end of a sequence.""",
            stability="unstable")
    def last_trailer(outer_env: Environment, i: int) -> Tuple[Block, bool]:
        def last_i(env: Environment) -> None:
            e = env.pop()
            assert isinstance(e, (str, list, range))
            env.push(objects.pd_index(e, -1-i))
        return (BuiltIn(str(i) + "_last", last_i), False)

    for agchar in 'áéíóúàèìòùý':
        @put(agchar, docs=ag_document(agchar), stability="unstable")
        def ag_trailer(outer_env: Environment, i: int, agchar: str = agchar) -> Tuple[PdObject, bool]:
            return (ag_convert(agchar, i, str(i) + agchar), False)

    return ret
int_trailer_dict = build_int_trailer_dict()
# }}}
def build_float_trailer_dict() -> Dict[str, Trailer[float]]: # {{{
    ret: Dict[str, Trailer[float]] = dict()
    def put(*names: str, docs: Optional[str] = None,
            stability: str = "unknown") -> TrailerPutter[int]:
        return trailer_putter(ret, names, docs=docs, stability=stability)

    @put("minus", "m", docs="Negate.", stability="stable")
    def minus_trailer(outer_env: Environment, f: float) -> Tuple[float, bool]:
        return (-f, False)
    @put("hundred", "h", docs="Multiply by a hundred.", stability="alpha")
    def hundred_trailer(outer_env: Environment, f: float) -> Tuple[float, bool]:
        return (f * 100, False)

    @put("thousand", "k", docs="Multiply by a thousand.", stability="alpha")
    def thousand_trailer(outer_env: Environment, f: float) -> Tuple[float, bool]:
        return (f * 1000, False)

    return ret
float_trailer_dict = build_float_trailer_dict()
# }}}
def build_char_trailer_dict() -> Dict[str, Trailer[Char]]: # {{{
    ret: Dict[str, Trailer[Char]] = dict()
    def put(*names: str, docs: Optional[str] = None,
            stability: str = "unknown") -> TrailerPutter[Char]:
        return trailer_putter(ret, names, docs=docs, stability=stability)

    @put("x", docs="Replicate, to get a string.", stability="alpha")
    def char_x_trailer(outer_env: Environment, c: Char) -> Tuple[Block, bool]:
        def char_x_b(env: Environment) -> None:
            v = env.pop()
            s = c.chr
            if isinstance(v, Block):
                raise TypeError('Cannot replicate character by block')
            else:
                env.push(objects.pd_deepmap_n2v(lambda e: s * num.intify(e), v))
        return (BuiltIn(objects.pd_repr(c) + "_x", char_x_b), False)

    return ret
char_trailer_dict = build_char_trailer_dict()
# }}}

def act_on_trailer_token(outer_env: Environment, token: str, b0: PdObject) -> Tuple[PdObject, bool]:
    # print("act_on_trailer_token", token, b0)
    assert token

    if token.startswith("_"): token = token[1:]

    if isinstance(b0, Block):
        b: Block = b0
        try:
            return block_trailer_dict[token](outer_env, b)
        except KeyError:
            raise NotImplementedError("unknown trailer token " + token + " on blocklike " + b.code_repr())
    elif isinstance(b0, str):
        s: str = b0
        try:
            return string_trailer_dict[token](outer_env, s)
        except KeyError:
            raise NotImplementedError("unknown trailer token " + token + " on string " + repr(s))

    elif isinstance(b0, int):
        i: int = b0
        try:
            return int_trailer_dict[token](outer_env, i)
        except KeyError:
            raise NotImplementedError("unknown trailer token " + token + " on int " + repr(i))

    elif isinstance(b0, float):
        f: float = b0
        try:
            return float_trailer_dict[token](outer_env, f)
        except KeyError:
            raise NotImplementedError("unknown trailer token " + token + " on float " + repr(f))

    elif isinstance(b0, Char):
        c: Char = b0
        try:
            return char_trailer_dict[token](outer_env, c)
        except KeyError:
            raise NotImplementedError("unknown trailer token " + token + " on char " + repr(c))

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
    acc: List[str] = []
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

def make_each_loop_over(iterable: Iterable[PdObject],
        eager_printer: Optional[Callable[[str], None]] = None) -> BodyExecutor:
    def inner(env: Environment, body: Block) -> None:
        for e in iterable:
            env.push(e)
            body(env)
            if eager_printer is not None:
                eager_printer(env.pd_str(
                    env.pop_stack_ignoring_markers_and_triggers()))
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

block_starters = {
    '{'   : '',
    'µ'   : '_map',
    'μ'   : '_map',
    '\x05': '_each',
    'ε'   : '_each',
    '\x06': '_filter',
    'φ'   : '_filter',
    '\x18': '_xloop',
    'χ'   : '_xloop',
    '\x1a': '_zip',
    'ζ'   : '_zip',
    '\x1c': '_loop',
    'λ'   : '_loop',
}

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
        block_prefix_trailer: Optional[str] = None

        executor: Optional[BodyExecutor] = None
        def set_executor(executor0: BodyExecutor) -> None:
            nonlocal block_level, block_prefix_trailer, executor
            block_level = 1
            block_prefix_trailer = ''
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

            elif trailer_token == 'e' or trailer_token == '_each':
                if env.input_trigger is None:
                    env.input_trigger = input_triggers.line
                set_executor(make_each_loop_over(
                        env.capture_stack_as_iterable()))
            elif trailer_token == 'm':
                # _each_newline, which is kinda like mapping over lines if by
                # itself
                if env.input_trigger is None:
                    env.input_trigger = input_triggers.line
                env.put('Ñ', '\n')
                set_executor(make_each_loop_over(
                        env.capture_stack_as_iterable()))
            elif trailer_token == 'f' or trailer_token == '_fasteach':
                if env.input_trigger is None:
                    env.input_trigger = input_triggers.line
                set_executor(make_each_loop_over(
                        env.capture_stack_as_iterable(),
                        lambda s: print(s, end="")))
            elif trailer_token == 'p' or trailer_token == '_printeach':
                if env.input_trigger is None:
                    env.input_trigger = input_triggers.line
                set_executor(make_each_loop_over(
                        env.capture_stack_as_iterable(),
                        env.print_output_record))
            elif trailer_token == 'z' or trailer_token == '_zerofor':
                try:
                    n = to_int_for_forloop(env.pop())
                    set_executor(make_each_loop_over(range(n)))
                except PdEmptyStackException:
                    set_executor(make_each_loop_over(itertools.count(0)))
            elif trailer_token == 'o' or trailer_token == '_onefor':
                try:
                    n = to_int_for_forloop(env.pop())
                    set_executor(make_each_loop_over(range(1, n+1)))
                except PdEmptyStackException:
                    set_executor(make_each_loop_over(itertools.count(1)))
            elif trailer_token == 's' or trailer_token == '_space':
                env.put('Ñ', ' ')
            elif trailer_token == 'n' or trailer_token == '_newline':
                env.put('Ñ', '\n')
            else:
                raise NotImplementedError('unknown global trailer token ' + repr(trailer_token))

        # This is not None when assignment is active:
        active_assign_token_trailer: Optional[Tuple[str, str]] = None
        block_acc: List[str] = []

        for token0 in self.tokens[body_start:]:
            token, trailer = break_trailer(token0)
            # print('in body', repr(token), repr(trailer), file=sys.stderr)
            try:
                if active_assign_token_trailer is not None:
                    # this is only not None if we're actually executing an
                    # assignment (in the outermost level, not in a block).
                    # Otherwise it just gets parsed into the block as a
                    # separate token
                    assert block_level == 0
                    # Digits should have been parsed as part of the same
                    # token.
                    assert not token0[0].isdigit()

                    if token.startswith('{'):
                        assert block_prefix_trailer is None
                        _, block_prefix_trailer = active_assign_token_trailer
                        if trailer: block_acc.append(trailer)
                    elif token in block_starters:
                        raise Exception("Cannot combine explicit prefix trailer with block opener with implicit trailer: " +
                                repr(active_assign_token_trailer) + ", " + repr(token))
                    else:
                        a_token, a_trailer = active_assign_token_trailer
                        a_trailer_tokens: Optional[Iterable[str]] = None
                        for v_name, ts in name_trailer_dissections(a_token, a_trailer):
                            variant = assign.variant_dict.get(v_name)
                            if variant is not None:
                                a_trailer_tokens = ts
                                break
                        if variant is None or a_trailer_tokens is None:
                            raise NameError('Could not parse (assignment) ' + repr((a_token, a_trailer)))

                        act_after_trailer_tokens(env, variant.block(token0), a_trailer_tokens)

                    active_assign_token_trailer = None
                elif block_level == 0:
                    if token.startswith('}'):
                        raise Exception("closing curly brace out of nowhere")
                    elif token in block_starters:
                        assert block_prefix_trailer is None
                        block_prefix_trailer = block_starters[token]
                        block_level += 1
                        if trailer: block_acc.append(trailer)
                    elif token.startswith('..') or token.startswith('——'):
                        pass # comment
                    elif token.startswith('"'):
                        parse_string_onto(env, token, trailer)
                    elif token.startswith("'"):
                        act_after_trailer_tokens(env, Char(ord(token[1])),
                                lex_trailer(trailer))
                    elif is_numeric_literal_token(token):
                        r_token = token.replace('—', '-')
                        try:
                            parsed_num: Union[int, float] = int(r_token)
                        except ValueError:
                            try:
                                parsed_num = float(r_token)
                            except ValueError:
                                raise ValueError('could not parse number ' + repr(token))
                        act_after_trailer_tokens(env, parsed_num, lex_trailer(trailer))
                    elif token.startswith('.') or token.startswith('—'):
                        active_assign_token_trailer = (token, trailer)
                    else:
                        val: Optional[PdObject] = None
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
                            # We reached the outermost scope.
                            assert block_prefix_trailer is not None
                            act_after_trailer_tokens(env,
                                    CodeBlock(block_acc),
                                    lex_trailers(block_prefix_trailer, trailer),
                                    reluctant=True, post_executor=executor)
                            block_prefix_trailer = None
                            block_acc = []
                            executor = None
                        else:
                            block_acc.append(token0)
                    else:
                        if token in block_starters:
                            block_level += 1
                        block_acc.append(token0)
            except PdAbortException: raise
            except PdBreakException: raise
            except PdContinueException: raise
            except Exception as ex:
                msg = 'Error while interpreting token {} caused by exception: {}\n{}'.format(token + trailer, ex, env.debug_dump())
                raise Exception(msg) from ex
            # print('generic debug dump', env.debug_dump(), file=sys.stderr)
        if active_assign_token_trailer is not None:
            raise Exception('Assignment with no target')
        while block_level > 0:
            block_level -= 1
            if block_level == 0:
                assert block_prefix_trailer is not None
                act_after_trailer_tokens(env,
                        CodeBlock(block_acc),
                        lex_trailers(block_prefix_trailer),
                        reluctant=True, post_executor=executor)
                block_prefix_trailer = None
                block_acc = []
                executor = None
            else:
                block_acc.append('}')

def basic_evaluator(env: Environment, code: str) -> None:
    CodeBlock(list(lex_code(code)))(env)

def initialized_environment(sandboxed: bool, debug: bool) -> Environment:
    env = Environment(basic_evaluator,
            stack_trigger = lambda: env.run_input_trigger())
    initialize_builtins(env, sandboxed, debug)
    return env

simple_eval_env_cache = initialized_environment(sandboxed=True, debug=True)
def pd_simple_eval(code: str, use_cache: bool = True) -> List[PdObject]:
    if use_cache:
        env = simple_eval_env_cache
        env._stack = []
    else:
        env = initialized_environment(sandboxed=True, debug=True)
    env.evaluate(code)
    return env._stack

def main_with_code(code: str, sandboxed: bool, debug: bool) -> None:
    env = initialized_environment(sandboxed, debug)
    env.evaluate(code)
    print(env.pd_str(env._stack))

def paradoc_repl(sandboxed: bool, debug: bool) -> None:
    env = initialized_environment(sandboxed, debug)
    try:
        import readline
    except ImportError:
        pass
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
    env = initialized_environment(sandboxed=True, debug=True)
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
    parser.add_argument('--no-debug', default=True, action='store_false',
            dest='debug')
    parser.add_argument('--sandboxed', default=False, action='store_true')
    parser.add_argument('--decode', nargs='?', const='')
    parser.add_argument('--encode', nargs='?', const='')
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
            document(initialized_environment(sandboxed=True, debug=True), [
                ('Block', block_trailer_dict),
                ('String', string_trailer_dict),
                ('Int', int_trailer_dict),
                ('Float', float_trailer_dict),
            ])
        elif args.e is not None:
            main_with_code(args.e, sandboxed=args.sandboxed, debug=args.debug)
        elif args.decode is not None:
            import paradoc.codepage
            if args.decode == '':
                sys.stdout.write(
                        codecs.decode(sys.stdin.buffer.read(), 'paradoc'))
            else:
                assert args.decode.endswith('.enc.prdc')
                src_filename = args.decode
                tgt_filename = args.decode[:-10] + '.prdc'
                with codecs.open(src_filename, 'rb') as dec_src_file:
                    with codecs.open(tgt_filename, 'w', 'utf8') as dec_tgt_file:
                        dec_tgt_file.write(
                                codecs.decode(dec_src_file.read(), 'paradoc')) # type: ignore
        elif args.encode is not None:
            import paradoc.codepage
            if args.encode == '':
                sys.stdout.buffer.write(
                        codecs.encode(sys.stdin.read(), 'paradoc'))
            else:
                assert args.encode.endswith('.prdc')
                src_filename = args.encode
                tgt_filename = args.encode[:-5] + '.enc.prdc'
                with codecs.open(src_filename, 'r', 'utf8') as enc_src_file:
                    with codecs.open(tgt_filename, 'wb') as enc_tgt_file:
                        enc_tgt_file.write( # type: ignore
                                codecs.encode(enc_src_file.read(), 'paradoc'))
        elif args.prog_file is not None:
            if args.prog_file.endswith('.cp1252.prdc'):
                with codecs.open(args.prog_file, 'r', 'cp1252') as cp1252_prog_file:
                    main_with_code(cp1252_prog_file.read(),
                            sandboxed=args.sandboxed, debug=args.debug)
            elif args.prog_file.endswith('.enc.prdc'):
                import paradoc.codepage
                with codecs.open(args.prog_file, 'rb') as prdc_prog_file:
                    main_with_code(
                            codecs.decode(prdc_prog_file.read(), 'paradoc'), # type: ignore
                            sandboxed=args.sandboxed, debug=args.debug)
            else:
                with open(args.prog_file, 'r') as prog_file:
                    main_with_code(prog_file.read(),
                            sandboxed=args.sandboxed, debug=args.debug)
        else:
            paradoc_repl(sandboxed=args.sandboxed, debug=args.debug)
    except PdAbortException as e:
        sys.exit(e.code)

if __name__ == "__main__": main()

# vim:set tabstop=4 shiftwidth=4 expandtab fdm=marker:
