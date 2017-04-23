# coding: utf-8
import typing
from typing import *
import re
import string

def is_nop_or_comment(token: str) -> bool:
    # (Only the special starting lexer would parse #!whatever as a single
    # token and not two separate ones)
    return (token.isspace() or
            token.startswith('..') or
            token.startswith('——') or
            token.startswith('#!'))
lowers = string.ascii_lowercase + "àáâãäåæçèéêëìíîïñòóôõöøùúûüýþÿœšžªºƒ"
lower_underscore_set = set(lowers + "_")
def is_trailer(char_or_token: str) -> bool:
    return char_or_token[0] in lower_underscore_set

# Blocks are not bunched at the lexing stage.
# So they're not really string literals.
numeric_literal_token_pattern = re.compile(r"""
    ^
    —?[0-9]+(?:\.[0-9]+)?(?:e[0-9]+)? # number
    |
    —?\.[0-9]+(?:e[0-9]+)? # number starting with a decimal point
    $
    """, re.VERBOSE)
pd_token_pattern = re.compile(r"""
    (?:\.\.|——)[^\n\r]* # comment
    |
    ( # main token
      "(?:\\\"|\\\\|[^"])*" # string
      |
      '. # char
      |
      —?[0-9]+(?:\.[0-9]+)?(?:e[0-9]+)? # number
      |
      —?\.[0-9]+(?:e[0-9]+)? # number starting with a decimal point
      |
      [^"'0-9{lowers}_]  # operator or uppercase letter
    )
    ([{lowers}_]*) # trail
    """.format(**locals()), re.VERBOSE)

trailer_token_pattern = re.compile('[{lowers}]|_[{lowers}]*'.format(**locals()))
trailer_token_or_starting_comment_pattern = re.compile(r"""
    [{lowers}]|_[{lowers}]*
    |
    \.\.[^\n\r]* # comment
    |
    \#![^\n\r]* # shebang
    """.format(**locals()), re.VERBOSE)

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
    # sad, you can't reverse enumerate
    for ri, c in enumerate(reversed(s)):
        if not is_trailer(c):
            n = len(s)
            return (s[:n-ri], s[n-ri:])
    raise Exception(s + " Token is all trailer!?")

def is_numeric_literal_token(token: str) -> bool:
    return bool(numeric_literal_token_pattern.match(token))

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

