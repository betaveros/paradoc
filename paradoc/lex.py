# coding: utf-8
import typing
from typing import *
import re

def is_nop_or_comment(token: str) -> bool:
    # (Only the special starting lexer would parse #!whatever as a single
    # token and not two separate ones)
    return (token.isspace() or
            token.startswith('..') or
            token.startswith('#!'))
def is_trailer(char_or_token: str) -> bool:
    char = char_or_token[0]
    return char.islower() or char == '_'

# Blocks are not bunched at the lexing stage.
# So they're not really string literals.
pd_token_pattern = re.compile(r"""
    \.\.[^\n\r]* # comment
    |
    ( # main token
      "(?:\\\"|\\\\|[^"])*" # string
      |
      '. # char
      |
      [0-9]+(?:\.[0-9]+)?(?:e[0-9]+)? # number. No negatives... for now
      |
      \.[0-9]+(?:e[0-9]+)? # number starting with a decimal point
      |
      [^"'0-9a-z_]  # operator or uppercase letter
    )
    ([a-z_]*) # trail
    """, re.VERBOSE)

trailer_token_pattern = re.compile('[a-z]|_[a-z]*')
trailer_token_or_starting_comment_pattern = re.compile(r"""
    [a-z]|_[a-z]*
    |
    \.\.[^\n\r]* # comment
    |
    \#![^\n\r]* # shebang
    """, re.VERBOSE)

def lex(code: str,
        patterns: Iterable[typing.Pattern[str]],
        start_index: int = 0) -> Generator[str, None, None]:

    index = start_index
    for pattern in patterns:
        while True:
            match_obj = pattern.match(code, index)
            if match_obj:
                yield match_obj.group()
                index = match_obj.end()
            else:
                break

def lex_trailer(trailer: str) -> Generator[str, None, None]:
    return lex(trailer, [trailer_token_pattern])

def lex_code(code: str) -> Generator[str, None, None]:
    return lex(code, [trailer_token_or_starting_comment_pattern, pd_token_pattern])

def break_trailer(s: str) -> Tuple[str, str]:
    if s[0] == "'":
        return (s[:2], s[2:])
    for i in range(len(s) - 1, -1, -1):
        if not is_trailer(s[i]):
            return (s[:i+1], s[i+1:])
    raise Exception(s + " Token is all trailer!?")

# Given an uppercase or symbol token and its trailer,
# generate dissections into token and trailer to look up.
def name_trailer_dissections(token: str, trailer: str) -> Generator[Tuple[str, Iterable[str]], None, None]:
    yield (token + trailer, [])

    index = len(trailer)

    while index >= 0:
        next_index = trailer.rfind('_', 0, index)
        if next_index == -1:
            index -= 1
        else:
            index = next_index

        yield (token + trailer[:index], lex_trailer(trailer[index:]))

