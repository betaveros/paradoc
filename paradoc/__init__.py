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
from typing import Callable, Iterable, List, Optional, Union
import itertools
from paradoc.lex import is_nop_or_comment, is_trailer, lex_trailer, lex_trailers, lex_code, break_trailer, is_numeric_literal_token, name_trailer_dissections
from paradoc.num import Char
from paradoc.objects import Block, Hoard, BuiltIn, PdObject, Environment, PdEmptyStackException, PdExitException, PdBreakException, PdContinueException
import paradoc.objects as objects
import paradoc.input_triggers as input_triggers
import paradoc.trailers as trailers
from paradoc.builtins import initialize_builtins
from paradoc.builtins.case import CasedBuiltIn
import sys
import argparse
import codecs

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
        obj, reluctant = trailers.act_on_trailer_token(env, trailer_token, obj)
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
        raise TypeError('Non-numeric non-string ' + repr(n) + ' cannot be used as forloop limit')

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

short_block_starters = {
    'β'   : 2,
    '\x02': 2,
    'γ'   : 3,
    '\x03': 3,
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
        # How many levels of block nesting we're in, counting both curly-brace
        # blocks and short blocks. Note that we don't care about tracking the
        # block structure below the first level, except insofar as we need it
        # to know when we emerge back into level 0. (It's not clear if this was
        # a good idea.)
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
            elif trailer_token == 'v' or trailer_token == '_values':
                env.input_trigger = input_triggers.value
            elif trailer_token == 'r' or trailer_token == '_records':
                env.input_trigger = input_triggers.record
            elif trailer_token == 'c' or trailer_token == '_chars':
                env.input_trigger = input_triggers.char

            elif trailer_token == 'a' or trailer_token == '_linearray':
                env.input_trigger = input_triggers.all_lines
            elif trailer_token == 'y' or trailer_token == '_valuearray':
                env.input_trigger = input_triggers.all_values

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
                    set_executor(make_each_loop_over(i for i in itertools.count(0)))
            elif trailer_token == 'o' or trailer_token == '_onefor':
                try:
                    n = to_int_for_forloop(env.pop())
                    set_executor(make_each_loop_over(range(1, n+1)))
                except PdEmptyStackException:
                    set_executor(make_each_loop_over(i for i in itertools.count(1)))
            elif trailer_token == 's' or trailer_token == '_space':
                env.put('Ñ', ' ')
            elif trailer_token == 'n' or trailer_token == '_newline':
                env.put('Ñ', '\n')
            else:
                raise NotImplementedError('unknown global trailer token ' + repr(trailer_token))

        # This is not None when assignment is active:
        active_assign_token: Optional[str] = None
        # This is nonempty when a short block is active; ticks down when we
        # parse anything not outside a curly-brace block. From our point of
        # view, we don't need to worry about any short blocks inside
        # curly-brace blocks. Its length should always <= block_level.
        # Theoretically, I think we could get by with a single int that goes up
        # and down if we parse nested short blocks not in any long blocks, but
        # that seems harder to debug.
        short_block_countdown: List[int] = []
        # A flat list of tokens accumulated into the block. As described above,
        # we don't keep track of inner block structure.
        block_acc: List[str] = []

        for token0 in self.tokens[body_start:]:
            token, trailer = break_trailer(token0)
            # print('in body', repr(token), repr(trailer), file=sys.stderr)
            try:
                if active_assign_token is not None:
                    # this is only not None if we're actually executing an
                    # assignment (in the outermost level, not in a block).
                    # Otherwise it just gets parsed into the block as a
                    # separate token
                    assert block_level == 0
                    # Digits should have been parsed as part of the same
                    # token.
                    assert not token0[0].isdigit()

                    if token.startswith('{') or token in block_starters or token in short_block_starters:
                        raise NotImplementedError("Assigning to a block is reserved syntax")
                    elif token.startswith("'") or token.startswith('"'):
                        raise NotImplementedError("Assigning to a string or char is reserved syntax")
                    elif active_assign_token in ('.', '⇒'):
                        env.put(token0, env.peek())
                    elif active_assign_token in ('—', '→'):
                        env.put(token0, env.pop())
                    else:
                        raise Exception("Unexpected assign token: " + repr(active_assign_token))

                    active_assign_token = None
                elif block_level == 0:
                    if token.startswith('}'):
                        raise RuntimeError("closing curly brace out of nowhere")
                    elif token in block_starters:
                        assert block_prefix_trailer is None
                        block_prefix_trailer = block_starters[token]
                        block_level += 1
                        if trailer: block_acc.append(trailer) # goes at start
                        # of block so i guess it'll set executors and stuff??
                    elif token in short_block_starters:
                        assert block_prefix_trailer is None
                        block_prefix_trailer = trailer
                        block_level += 1
                        short_block_countdown.append(short_block_starters[token])
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
                    elif token in ('.', '—', '→', '⇒'):
                        if trailer:
                            if token == '.':
                                act_after_trailer_tokens(env, env.pop(), lex_trailer(trailer))
                            else:
                                raise NotImplementedError("Using an em dash or arrow with trailers is reserved syntax")
                        else:
                            active_assign_token = token
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
                    # active_assign_token is None and block_level > 0

                    # Should this token go into block_acc?
                    should_accumulate = False

                    should_countdown = False

                    if token.startswith('}'):
                        if block_level == len(short_block_countdown):
                            raise Exception("Cannot terminate short block with curly brace")
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
                            should_accumulate = True
                            should_countdown = True
                    else:
                        should_accumulate = True
                        should_countdown = True
                        if token in block_starters:
                            block_level += 1
                        elif block_level == len(short_block_countdown) and token in short_block_starters:
                            # Only track the structure of short blocks not in
                            # any long blocks.
                            block_level += 1
                            short_block_countdown.append(short_block_starters[token])
                            should_countdown = False

                    if should_accumulate:
                        # We're still in a block.
                        block_acc.append(token0)
                        if block_level == len(short_block_countdown) and should_countdown:
                            # We're not in any long blocks, i.e. we're in one
                            # or more nested short blocks.
                            while short_block_countdown and short_block_countdown[-1] == 1:
                                # We finished a short block.
                                block_level -= 1
                                short_block_countdown.pop()

                            assert block_level == len(short_block_countdown)

                            if short_block_countdown:
                                short_block_countdown[-1] -= 1
                            else:
                                # We concluded a short block in the outermost scope.
                                assert block_prefix_trailer is not None
                                act_after_trailer_tokens(env,
                                        CodeBlock(block_acc),
                                        lex_trailers(block_prefix_trailer), # trailer is NOT included!
                                        reluctant=True, post_executor=executor)
                                block_prefix_trailer = None
                                block_acc = []
                                executor = None
            except PdExitException: raise
            except PdBreakException: raise
            except PdContinueException: raise
            except Exception as ex:
                msg = 'Error while interpreting token {} caused by exception: {}\n{}'.format(token + trailer, ex, env.debug_dump())
                raise Exception(msg) from ex
            # print('generic debug dump', env.debug_dump(), file=sys.stderr)
        if active_assign_token is not None:
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
    def __repr__(self) -> str:
        return 'CodeBlock({})'.format(repr("".join(self.tokens)))

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
    env.evaluate(code, set_quine=True)
    return env._stack

def main_with_code(code: str, sandboxed: bool, debug: bool) -> None:
    env = initialized_environment(sandboxed, debug)
    env.evaluate(code, set_quine=True)
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
            env.evaluate(code, set_quine=True)
            print(env.pd_str(env._stack))
            print(objects.pd_repr(env._stack))
        except EOFError:
            break
        except PdExitException:
            raise
        except Exception as e:
            print(e, file=sys.stderr)

def list_builtins(name_filter: Callable[[str], bool]) -> None:
    env = initialized_environment(sandboxed=True, debug=True)
    for name, obj in sorted(env.vars.items()):
        if name_filter(name):
            print(name, repr(obj))

def autogolf(code: str) -> str:
    ret: List[str] = []
    started = False
    env = initialized_environment(sandboxed=True, debug=True)
    for token0 in lex_code(code):
        if is_nop_or_comment(token0): continue

        token, trailer = break_trailer(token0)

        if (
            is_trailer(token) or token.startswith('"') or token.startswith("'")
            or token.startswith('{') or token.startswith('}') or token in block_starters
            or is_numeric_literal_token(token) or token.startswith('.') or token.startswith('—')
            ):
            # can't do much
            if ret:
                last_token = ret[-1]
                if last_token and last_token[-1].isnumeric() and last_token != '0' and token0[0].isnumeric():
                    ret.append(' ')
            ret.append(token0)
        else:
            val: Optional[PdObject] = None
            trailer_tokens = None
            for name, ts in name_trailer_dissections(token, trailer):
                val = env.get_or_none(name)
                if val is not None:
                    trailer_tokens = ts
                    break
            if (isinstance(val, BuiltIn) or isinstance(val, CasedBuiltIn)) and trailer_tokens is not None:
                # sys.stderr.write(str(val))
                ret.append(min([val.name] + val.aliases + val.golf_aliases, key=len) + ''.join(trailer_tokens))
            else:
                # give up, maybe it's a constant or hoard, maybe it's a custom
                # variable
                ret.append(token0)
    return ''.join(ret)

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
    parser.add_argument('--autogolf', action='store_true')
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
                ('Block', trailers.block_trailer_dict),
                ('String', trailers.string_trailer_dict),
                ('Int', trailers.int_trailer_dict),
                ('Float', trailers.float_trailer_dict),
                ('Hoard', trailers.hoard_trailer_dict),
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
                    source = cp1252_prog_file.read()
            elif args.prog_file.endswith('.enc.prdc'):
                import paradoc.codepage
                with codecs.open(args.prog_file, 'rb') as prdc_prog_file:
                    source = codecs.decode(prdc_prog_file.read(), 'paradoc'), # type: ignore
            else:
                with open(args.prog_file, 'r') as prog_file:
                    source = prog_file.read()

            if args.autogolf:
                print(autogolf(source))
            else:
                main_with_code(source, sandboxed=args.sandboxed, debug=args.debug)
        elif args.autogolf:
            print(autogolf(sys.stdin.read()))
        else:
            paradoc_repl(sandboxed=args.sandboxed, debug=args.debug)
    except PdExitException as e:
        sys.exit(e.code)

if __name__ == "__main__": main()

# vim:set tabstop=4 shiftwidth=4 expandtab fdm=marker:
