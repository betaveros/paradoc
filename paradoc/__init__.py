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
from paradoc.builtins import initialize_builtins
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

# bool is whether the result is "reluctant"
def act_on_trailer_token(outer_env: Environment, token: str, b0: PdObject) -> Tuple[PdObject, bool]:
    # print("act_on_trailer_token", token, b0)
    assert token

    if isinstance(b0, Block):
        b = b0 # type: Block

        if token == "a" or token == "_anti":
            def anti_b(env: Environment) -> None:
                e2, e1 = env.pop2()
                env.push(e2, e1)
                b(env)
            return (BuiltIn(b.code_repr() + "_anti", anti_b), True)

        elif token == "b" or token == "_bind":
            e = outer_env.pop()
            def bind_b(env: Environment) -> None:
                env.push(e)
                b(env)
            return (BuiltIn(b.code_repr() + "_bind", bind_b), True)

        elif token == "d" or token == "_double":
            def double_b(env: Environment) -> None:
                shadow = env.bracketed_shadow()
                b(shadow)
                b(env)
                env.push_env(shadow)
            return (BuiltIn(b.code_repr() + "_double", double_b), False)

        elif token == "e" or token == "_each":
            def each_b(env: Environment) -> None:
                lst = objects.pd_to_list_range(env.pop())
                objects.pd_foreach(env, b, lst)
            return (BuiltIn(b.code_repr() + "_each", each_b), False)

        elif token == "f" or token == "_filter" or token == "_select":
            return (BuiltIn(b.code_repr() + "_filter",
                    lambda env: apply_pd_list_op(env, b, objects.pd_filter)), False)

        elif token == "g" or token == "_get":
            return (BuiltIn(b.code_repr() + "_get",
                    lambda env: apply_pd_list_op(env, b, objects.pd_get)), False)

        elif token == "h" or token == "_high":
            return (BuiltIn(b.code_repr() + "_high",
                    lambda env: apply_pd_list_op(env, b, objects.pd_get_index_last)), False)

        elif token == "i" or token == "_index":
            return (BuiltIn(b.code_repr() + "_index",
                    lambda env: apply_pd_list_op(env, b, objects.pd_get_index)), False)

        elif token == "k" or token == "_keep":
            def keep_b(env: Environment) -> None:
                shadow = env.keep_shadow()
                b(shadow)
                env.push_env(shadow)
            return (BuiltIn(b.code_repr() + "_keep", keep_b), False)

        elif token == "l" or token == "_last":
            return (BuiltIn(b.code_repr() + "_last",
                    lambda env: apply_pd_list_op(env, b, objects.pd_get_last)), False)

        elif token == "m" or token == "_map":
            return (BuiltIn(b.code_repr() + "_map",
                    lambda env: apply_pd_list_op(env, b, objects.pd_map)), False)

        elif token == "o" or token == "_onemap":
            return (BuiltIn(b.code_repr() + "_onemap",
                    lambda env: apply_pd_list_op(env, b, objects.pd_map, coerce_start=1)), False)

        elif token == "r" or token == "_reduce" or token == "_fold":
            return (BuiltIn(b.code_repr() + "_reduce",
                    lambda env: apply_pd_list_op(env, b, objects.pd_reduce)), False)

        elif token == "q" or token == "_keepunder":
            def keepunder_b(env: Environment) -> None:
                shadow = env.keep_shadow()
                b(shadow)
                env.push_keep_shadow_env_under(shadow)
            return (BuiltIn(b.code_repr() + "_keepunder", keepunder_b), False)

        elif token == "u" or token == "_under":
            def under_b(env: Environment) -> None:
                t = env.pop()
                b(env)
                env.push(t)
            return (BuiltIn(b.code_repr() + "_under", under_b), False)

        elif token == "x" or token == "_xloop":
            def xloop_b(env: Environment) -> None:
                lst = objects.pd_to_list_range(env.pop())
                objects.pd_foreach_x_only(env, b, lst)
            return (BuiltIn(b.code_repr() + "_xloop", xloop_b), False)

        elif token == "z" or token == "_zip":
            def zip_b(env: Environment) -> None:
                lst_b = objects.pd_to_list_range(env.pop())
                lst_a = objects.pd_to_list_range(env.pop())
                env.push(objects.pd_zip(env, b, lst_a, lst_b))
            return (BuiltIn(b.code_repr() + "_zip", zip_b), False)

        elif token == "â" or token == "_all":
            def all_b(env: Environment) -> None:
                lst = objects.pd_to_list_range(env.pop())
                env.push(int(all(
                    objects.pd_map(env, b, lst))))
            return (BuiltIn(b.code_repr() + "_all", all_b), False)

        elif token == "ê" or token == "_exists":
            def exists_b(env: Environment) -> None:
                lst = objects.pd_to_list_range(env.pop())
                env.push(int(any(
                    objects.pd_map(env, b, lst))))
            return (BuiltIn(b.code_repr() + "_exists", all_b), False)

        elif token == "ä" or token == "_autozip":
            def autozip_b(env: Environment) -> None:
                lst_a = objects.pd_to_list_range(env.pop())
                env.push(objects.pd_zip(env, b, lst_a, lst_a[1:]))
            return (BuiltIn(b.code_repr() + "_autozip", autozip_b), False)
        elif token == "ë" or token == "_enumap":
            def enumap_b(env: Environment) -> None:
                lst_a = objects.pd_to_list_range(env.pop())
                env.push(objects.pd_zip(env, b, range(len(lst_a)), lst_a))
            return (BuiltIn(b.code_repr() + "_enumap", enumap_b), False)
        elif token == "š" or token == "_mapsum":
            return (BuiltIn(b.code_repr() + "_mapsum",
                    lambda env: apply_pd_list_op(env, b, objects.pd_mapsum)), False)


        raise NotImplementedError("unknown trailer token " + token + " on blocklike " + b.code_repr())
    elif isinstance(b0, str):
        s = b0 # type: str
        if token == "i" or token == "_interpolate":
            def interpolate_s(env: Environment) -> None:
                env.push(simple_interpolate(env, s, '%'))
            return (BuiltIn(objects.pd_repr(s) + "_interpolate", interpolate_s), False)
        elif token == "o" or token == "_interoutput":
            def interoutput_s(env: Environment) -> None:
                print(simple_interpolate(env, s, '%'), end="")
            return (BuiltIn(objects.pd_repr(s) + "_interoutput", interoutput_s), False)
        elif token == "n" or token == "_interprint":
            def interprint_s(env: Environment) -> None:
                env.print_output_record(simple_interpolate(env, s, '%'))
            return (BuiltIn(objects.pd_repr(s) + "_interprint", interprint_s), False)
        elif token == "_debug":
            def debug_s(env: Environment) -> None:
                print(s, 'dump:',  env.debug_dump(), file=sys.stderr)
            return (BuiltIn(objects.pd_repr(s) + "_debug", debug_s), False)

        raise NotImplementedError("unknown trailer token " + token + " on string")
    elif isinstance(b0, int):
        i = b0 # type: int
        if token == "m" or token == "_minus":
            return (-i, False)
        elif token == "h" or token == "_hundred":
            return (i * 100, False)
        elif token == "k" or token == "_thousand":
            return (i * 1000, False)
        elif token == "u" or token == "_under":
            def under_i(env: Environment) -> None:
                t = env.pop()
                env.push(i)
                env.push(t)
            return (BuiltIn(str(i) + "_under", under_i), False)
        elif token == "_force":
            def force_i(env: Environment) -> None:
                xs = env.pop_n(i)
                env.push(*xs)
            return (BuiltIn(str(i) + "_force", force_i), False)
        elif token == "a" or token == "_array":
            def array_i(env: Environment) -> None:
                env.push(env.pop_n(i))
            return (BuiltIn(str(i) + "_array", array_i), False)
        elif token == "z" or token == "_zip":
            def zip_i(env: Environment) -> None:
                env.push(objects.pd_zip_as_list(*env.pop_n(i)))
            return (BuiltIn(str(i) + "_zip", zip_i), False)
        elif token == "b" or token == "_bits":
            i_bits = base.to_base_digits_at_least_two(2, i)
            def bits_i(env: Environment) -> None:
                env.push(*i_bits)
            return (BuiltIn(str(i) + "_bits", bits_i), False)

        raise NotImplementedError("unknown trailer token " + token + " on integer")
    raise NotImplementedError("unknown trailer token " + token + " on unknown thing")

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
                env.stack_trigger = input_triggers.all
            elif trailer_token == 'l' or trailer_token == '_lines':
                env.stack_trigger = input_triggers.line
            elif trailer_token == 'w' or trailer_token == '_words':
                env.stack_trigger = input_triggers.word
            elif trailer_token == 'v' or trailer_token == '_value':
                env.stack_trigger = input_triggers.value
            elif trailer_token == 'c' or trailer_token == '_chars':
                env.stack_trigger = input_triggers.char

            elif trailer_token == 'f' or trailer_token == '_for':
                set_executor(make_for_loop_over(
                        env.capture_stack_as_iterable()))
            elif trailer_token == 'z' or trailer_token == '_zerofor':
                try:
                    n = env.pop()
                    assert isinstance(n, (int, float, str))
                    set_executor(make_for_loop_over(range(int(n))))
                except PdEmptyStackException:
                    set_executor(make_for_loop_over(itertools.count(0)))
            elif trailer_token == 'o' or trailer_token == '_onefor':
                try:
                    n = env.pop()
                    assert isinstance(n, (int, float, str))
                    set_executor(make_for_loop_over(range(1, int(n)+1)))
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

def initialized_environment() -> Environment:
    env = Environment(basic_evaluator)
    initialize_builtins(env)
    return env

def pd_simple_eval(code: str) -> List[PdObject]:
    env = initialized_environment()
    env.evaluate(code)
    return env._stack

def main_with_code(code: str) -> None:
    env = initialized_environment()
    env.evaluate(code)
    print(env.pd_str(env._stack))

def paradoc_repl() -> None:
    env = initialized_environment()
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
    args = parser.parse_args()

    try:
        if args.e is not None:
            main_with_code(args.e)
        elif args.prog_file is not None:
            if args.prog_file.endswith('.cp1252.prdc'):
                import codecs
                with codecs.open(args.prog_file, 'r', 'cp1252') as prog_file:
                    main_with_code(prog_file.read())
            else:
                with open(args.prog_file, 'r') as prog_file:
                    main_with_code(prog_file.read())
        else:
            paradoc_repl()
    except PdAbortException as e:
        sys.exit(e.code)

if __name__ == "__main__": main()
