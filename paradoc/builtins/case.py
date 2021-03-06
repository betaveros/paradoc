from paradoc.objects import (
        PdObject, Environment, PdSeq, PdValue, PdNum, Char, Block,
        pd_deepmap_n2v, pd_deepmap_r2v, pd_deepmap_rc2v,
        Hoard, PdImmutableSeq, PdEmptyStackException,
        )
from typing import Any, Callable, List, Optional, Tuple, Type, Union

# A "type" of an argument, possibly with a coercion. Loaded with stuff for
# introspective usefulness. Note we don't typecheck coercions! Their argument
# needs to be an existential type or something to avoid false alarms.
class ArgType:
    def __init__(self, coercions: List[Tuple[Tuple[Type[PdObject], ...], Callable[[Any], PdObject]]]) -> None:
        self.coercions = coercions
    def accepts(self, arg: PdObject) -> bool:
        for typs, coercion in self.coercions:
            if isinstance(arg, typs): return True
        return False
    def maybe_process(self, arg: PdObject) -> Optional[PdObject]:
        for typs, coercion in self.coercions:
            if isinstance(arg, typs):
                return coercion(arg)
        return None

    @staticmethod
    def just_type(*typs: Type[PdObject]) -> 'ArgType':
        return ArgType([(tuple(typs), lambda obj: obj)])

just_int       = ArgType.just_type(int)
just_char      = ArgType.just_type(Char)
just_number    = ArgType.just_type(Char, int, float, complex)
just_str       = ArgType.just_type(str)
just_list      = ArgType.just_type(list, range, Hoard)
just_seq       = ArgType.just_type(str, list, range, Hoard)
just_block     = ArgType.just_type(Block)
just_hoard     = ArgType.just_type(Hoard)
just_immutable = ArgType.just_type(Char, int, float, complex, str, list, range)
just_value     = ArgType.just_type(Char, int, float, complex, str, list, range, Hoard)
just_any       = ArgType.just_type(Char, int, float, complex, str, list, range, Hoard, Block)

# Accepts a list, coercing Chars or numbers to single-element lists
list_singleton = ArgType([
        ((Char, int, float, complex), lambda x: [x]),
        ((list, range, Hoard),        lambda x: x),
        ])

# Accepts a seq, dereferencing hoards
seq_deref = ArgType([
        ((str, list, range), lambda x: x),
        ((Hoard,),           lambda x: x.to_list()),
        ])

# Accepts a sequence, coercing Chars or numbers to single-element strings or
# lists
seq_singleton = ArgType([
        ((Char,),                   lambda x: x.chr),
        ((int, float, complex),     lambda x: [x]),
        ((str, list, range, Hoard), lambda x: x),
        ])
# Accepts a sequence, coercing Chars or numbers to ranges
seq_range = ArgType([
        ((Char,),                   lambda x: range(x.ord)),
        ((int,),                    lambda x: range(x)),
        ((float,),                  lambda x: range(int(x))),
        ((complex,),                lambda x: range(int(x.real))),
        ((str, list, range, Hoard), lambda x: x),
        ])
seq_range_deref = ArgType([
        ((Char,),            lambda x: range(x.ord)),
        ((int,),             lambda x: range(x)),
        ((float,),           lambda x: range(int(x))),
        ((complex,),         lambda x: range(int(x.real))),
        ((str, list, range), lambda x: x),
        ((Hoard,),           lambda x: x.to_list()),
        ])

# Accepts a list, coercing strings to lists of integers and Chars or numbers to ranges
list_int_range = ArgType([
        ((Char,),       lambda x: range(x.ord)),
        ((int,),        lambda x: range(x)),
        ((float,),      lambda x: range(int(x))),
        ((complex,),    lambda x: range(int(x.real))),
        ((str,),        lambda x: [ord(c) for c in x]),
        ((list, range), lambda x: x),
        ])

# Accepts an int, coercing Chars, floats, and strings to integers
int_coerce = ArgType([
        ((Char,),       lambda x: x.ord),
        ((int,),        lambda x: x),
        ((float,),      lambda x: int(x)),
        ((complex,),    lambda x: int(x.real)),
        ((str,),        lambda x: int(x)),
        ])

# Accepts an int, coercing Chars and floats to integers and taking the
# lengths of sequences
int_len = ArgType([
        ((Char,),          lambda x: x.ord),
        ((int,),           lambda x: x),
        ((float,),         lambda x: int(x)),
        ((complex,),       lambda x: int(abs(x))),
        ((str,list,range), lambda x: len(x)),
        ])

# Accepts an int or a float, coercing Chars to integers and taking the lengths
# of sequences
number_len = ArgType([
        ((Char,),             lambda x: x.ord),
        ((int,float,complex), lambda x: x),
        ((str,list,range),    lambda x: len(x)),
        ])

# A case in a function definition, which specifies a list of types of
# arguments the function might accept and what the function would do with
# them.

# Example: + would have a case like (str, str, lambda a, b: [a + b]), which
# says that + could accept two strings, and if it did it would push one
# object onto the stack, namely the strings concatenated.

# Typechecking this is implausible, but we can write a lot of wrapper functions
# around it that are typechecked.
class Case:
    def __init__(self,
            arity: int,
            arg_types: List[ArgType],
            func: Callable[..., List[PdObject]],
            commutative: bool = False) -> None:
        self.arity = arity
        self.arg_types = arg_types
        self.func = func
        self.commutative = commutative

    def maybe_run_noncommutatively(self, env: Environment, args: List[PdObject]) -> Optional[List[PdObject]]:
        assert self.arity == len(args)
        processed_args = []
        for arg, arg_type in zip(args, self.arg_types):
            p_arg = arg_type.maybe_process(arg)
            if p_arg is None: return None
            processed_args.append(p_arg)
        res = self.func(env, *processed_args)
        return res

    def maybe_run(self, env: Environment, args: List[PdObject]) -> Optional[List[PdObject]]:
        res = self.maybe_run_noncommutatively(env, args)
        if res is None and self.commutative:
            res = self.maybe_run_noncommutatively(env,
                    [args[1], args[0]] + args[2:])
        return res

    @staticmethod
    def void(func: Callable[[Environment], List[PdObject]]) -> 'Case':
        return Case(0, [], func)
    @staticmethod
    def any(func: Callable[[Environment, PdObject], List[PdObject]]) -> 'Case':
        return Case(1, [just_any], func)
    @staticmethod
    def int_(func: Callable[[Environment, int], List[PdObject]]) -> 'Case':
        return Case(1, [just_int], func)
    @staticmethod
    def int_len(func: Callable[[Environment, int], List[PdObject]]) -> 'Case':
        return Case(1, [int_len], func)
    @staticmethod
    def str_(func: Callable[[Environment, str], List[PdObject]]) -> 'Case':
        return Case(1, [just_str], func)
    @staticmethod
    def list_(func: Callable[[Environment, Union[list, range, Hoard]], List[PdObject]]) -> 'Case':
        return Case(1, [just_list], func)
    @staticmethod
    def seq(func: Callable[[Environment, PdSeq], List[PdObject]]) -> 'Case':
        return Case(1, [just_seq], func)
    @staticmethod
    def seq_deref(func: Callable[[Environment, PdImmutableSeq], List[PdObject]]) -> 'Case':
        return Case(1, [seq_deref], func)
    @staticmethod
    def seq_range(func: Callable[[Environment, PdSeq], List[PdObject]]) -> 'Case':
        return Case(1, [seq_range], func)
    @staticmethod
    def seq_range_deref(func: Callable[[Environment, PdImmutableSeq], List[PdObject]]) -> 'Case':
        return Case(1, [seq_range_deref], func)
    @staticmethod
    def number(func: Callable[[Environment, Union[int, float, complex]], List[PdObject]]) -> 'Case':
        return Case(1, [just_number], func)
    @staticmethod
    def value(func: Callable[[Environment, PdValue], List[PdObject]]) -> 'Case':
        return Case(1, [just_value], func)
    @staticmethod
    def value_n2v(func: Callable[[Union[int, float, complex]], PdValue]) -> 'Case':
        return Case(1, [just_value], lambda env, a: [pd_deepmap_n2v(func, a)])
    @staticmethod
    def value_r2v(func: Callable[[Union[int, float]], PdValue]) -> 'Case':
        return Case(1, [just_value], lambda env, a: [pd_deepmap_r2v(func, a)])
    @staticmethod
    def value_rc2v(
            rfunc: Callable[[Union[int, float]], PdValue],
            cfunc: Callable[[complex], PdValue]) -> 'Case':
        return Case(1, [just_value], lambda env, a: [pd_deepmap_rc2v(rfunc, cfunc, a)])
    @staticmethod
    def block(func: Callable[[Environment, Block], List[PdObject]]) -> 'Case':
        return Case(1, [just_block], func)
    @staticmethod
    def list_int_range(func: Callable[[Environment, Union[list, range]], List[PdObject]]) -> 'Case':
        return Case(1, [list_int_range], func)

    @staticmethod
    def any2(func: Callable[[Environment, PdObject, PdObject], List[PdObject]]) -> 'Case':
        return Case(2, [just_any, just_any], func)
    @staticmethod
    def number2(func: Callable[[Environment, PdNum, PdNum], List[PdObject]]) -> 'Case':
        return Case(2, [just_number, just_number], func)
    @staticmethod
    def int2_coerce(func: Callable[[Environment, int, int], List[PdObject]]) -> 'Case':
        return Case(2, [int_coerce, int_coerce], func)
    @staticmethod
    def number2_len(func: Callable[[Environment, Union[int, float], Union[int, float]], List[PdObject]]) -> 'Case':
        return Case(2, [number_len, number_len], func)
    @staticmethod
    def str2(func: Callable[[Environment, str, str], List[PdObject]]) -> 'Case':
        return Case(2, [just_str, just_str], func)
    @staticmethod
    def list2(func: Callable[[Environment, Union[list, range, Hoard], Union[list, range, Hoard]], List[PdObject]]) -> 'Case':
        return Case(2, [just_list, just_list], func)
    @staticmethod
    def list_list_singleton(func: Callable[[Environment, Union[list, range, Hoard], Union[list, range, Hoard]], List[PdObject]]) -> 'Case':
        return Case(2, [just_list, list_singleton], func)
    @staticmethod
    def list2_singleton(func: Callable[[Environment, Union[list, range, Hoard], Union[list, range, Hoard]], List[PdObject]]) -> 'Case':
        return Case(2, [list_singleton, list_singleton], func)
    @staticmethod
    def list_number(func: Callable[[Environment, Union[list, range, Hoard], PdNum], List[PdObject]], commutative: bool = True) -> 'Case':
        return Case(2, [just_list, just_number], func,
                commutative=commutative)
    @staticmethod
    def list_range_number(func: Callable[[Environment, Union[list, range, Hoard], PdNum], List[PdObject]], commutative: bool = True) -> 'Case':
        return Case(2, [list_int_range, just_number], func,
                commutative=commutative)
    @staticmethod
    def str_number(func: Callable[[Environment, str, PdNum], List[PdObject]], commutative: bool = True) -> 'Case':
        return Case(2, [just_str, just_number], func,
                commutative=commutative)
    @staticmethod
    def seq2(func: Callable[[Environment, PdSeq, PdSeq], List[PdObject]]) -> 'Case':
        return Case(2, [just_seq, just_seq], func)
    @staticmethod
    def seq_seq_singleton(func: Callable[[Environment, PdSeq, PdSeq], List[PdObject]]) -> 'Case':
        return Case(2, [just_seq, seq_singleton], func)
    @staticmethod
    def seq2_singleton(func: Callable[[Environment, PdSeq, PdSeq], List[PdObject]]) -> 'Case':
        return Case(2, [seq_singleton, seq_singleton], func)
    @staticmethod
    def seq2_range(func: Callable[[Environment, PdSeq, PdSeq], List[PdObject]]) -> 'Case':
        return Case(2, [seq_range, seq_range], func)
    @staticmethod
    def number_seq(func: Callable[[Environment, PdNum, PdSeq], List[PdObject]], commutative: bool = True) -> 'Case':
        return Case(2, [just_number, just_seq], func, commutative=commutative)
    @staticmethod
    def value_seq(func: Callable[[Environment, PdValue, PdSeq], List[PdObject]], commutative: bool = True) -> 'Case':
        return Case(2, [just_value, just_seq], func, commutative=commutative)
    @staticmethod
    def seq_value(func: Callable[[Environment, PdSeq, PdValue], List[PdObject]], commutative: bool = True) -> 'Case':
        return Case(2, [just_seq, just_value], func, commutative=commutative)
    @staticmethod
    def hoard_immutable(func: Callable[[Environment, Hoard, PdValue], List[PdObject]], commutative: bool = True) -> 'Case':
        return Case(2, [just_hoard, just_immutable], func, commutative=commutative)
    @staticmethod
    def char_number(func: Callable[[Environment, Char, PdNum], List[PdObject]], commutative: bool = True) -> 'Case':
        return Case(2, [just_char, just_number], func, commutative=commutative)
    @staticmethod
    def value_number(func: Callable[[Environment, PdValue, PdNum], List[PdObject]], commutative: bool = True) -> 'Case':
        return Case(2, [just_value, just_number], func, commutative=commutative)
    @staticmethod
    def value2(func: Callable[[Environment, PdValue, PdValue], List[PdObject]]) -> 'Case':
        return Case(2, [just_value, just_value], func)
    @staticmethod
    def any_number(func: Callable[[Environment, PdObject, PdNum], List[PdObject]], commutative: bool = True) -> 'Case':
        return Case(2, [just_any, just_number], func, commutative=commutative)
    @staticmethod
    def block_seq_range(func: Callable[[Environment, Block, PdSeq], List[PdObject]], commutative: bool = True) -> 'Case':
        return Case(2, [just_block, seq_range], func, commutative=commutative)
    @staticmethod
    def condition_block(func: Callable[[Environment, PdObject, Block], List[PdObject]], commutative: bool = True) -> 'Case':
        return Case(2, [just_any, just_block], func, commutative=commutative)
    @staticmethod
    def block_value(func: Callable[[Environment, Block, PdValue], List[PdObject]], commutative: bool = True) -> 'Case':
        return Case(2, [just_block, just_value], func, commutative=commutative)
    @staticmethod
    def block2(func: Callable[[Environment, Block, Block], List[PdObject]]) -> 'Case':
        return Case(2, [just_block, just_block], func)

    @staticmethod
    def any3(func: Callable[[Environment, PdObject, PdObject, PdObject], List[PdObject]]) -> 'Case':
        return Case(3, [just_any, just_any, just_any], func)
    @staticmethod
    def value3(func: Callable[[Environment, PdValue, PdValue, PdValue], List[PdObject]]) -> 'Case':
        return Case(3, [just_value, just_value, just_value], func)
    @staticmethod
    def seq3_singleton(func: Callable[[Environment, PdSeq, PdSeq, PdSeq], List[PdObject]]) -> 'Case':
        return Case(3, [seq_singleton, seq_singleton, seq_singleton], func)
    @staticmethod
    def any_any_number(func: Callable[[Environment, PdObject, PdObject, PdNum], List[PdObject]], commutative: bool = True) -> 'Case':
        return Case(3, [just_any, just_any, just_number], func, commutative=commutative)
    @staticmethod
    def list_list_singleton_value(func: Callable[[Environment, Union[list, range, Hoard], Union[list, range, Hoard], PdValue], List[PdObject]]) -> 'Case':
        return Case(3, [just_list, list_singleton, just_value], func)
    @staticmethod
    def list_list_block(func: Callable[[Environment, Union[list, range, Hoard], Union[list, range, Hoard], Block], List[PdObject]]) -> 'Case':
        return Case(3, [just_list, just_list, just_block], func)
    @staticmethod
    def seq2_range_block(func: Callable[[Environment, PdSeq, PdSeq, Block], List[PdObject]], commutative: bool = True) -> 'Case':
        return Case(3, [seq_range, seq_range, just_block], func, commutative=commutative)
    @staticmethod
    def value2_block(func: Callable[[Environment, PdValue, PdValue, Block], List[PdObject]]) -> 'Case':
        return Case(3, [just_value, just_value, just_block], func)
    @staticmethod
    def list_range_number_any(func: Callable[[Environment, PdSeq, PdNum, PdObject], List[PdObject]], commutative: bool = True) -> 'Case':
        return Case(3, [seq_range, just_number, just_any], func, commutative=commutative)

    @staticmethod
    def value3_block(func: Callable[[Environment, PdValue, PdValue, PdValue, Block], List[PdObject]]) -> 'Case':
        return Case(4, [just_value, just_value, just_value, just_block], func)

class CasedBuiltIn(Block):
    def __init__(self,
            name: str,
            cases: List[Case],
            aliases: Optional[List[str]] = None,
            docs: Optional[str] = None,
            stability: str = "unknown",
            golf_aliases: Optional[List[str]] = None) -> None:

        for c1, c2 in zip(cases, cases[1:]):
            assert c1.arity <= c2.arity

        self.name = name
        self.aliases: List[str] = aliases or [name]
        self.golf_aliases: List[str] = golf_aliases or []
        self.cases = cases
        self.docs = docs
        self.stability = stability

    def __call__(self, env: 'Environment') -> None:
        collected_args: List[PdObject] = []
        for case in self.cases:
            assert len(collected_args) <= case.arity
            try:
                for _ in range(case.arity - len(collected_args)):
                    collected_args.insert(0, env.pop())
            except PdEmptyStackException as ex:
                raise AssertionError('Not enough arguments on stack: wanted {}, got only {}: {}'.format(case.arity, len(collected_args), repr(collected_args))) from ex
            res = case.maybe_run(env, collected_args)
            if res is not None:
                env.push(*res)
                return
        raise NotImplementedError('No cases match for built-in ' + self.name + ' with args ' + repr(collected_args))
    def code_repr(self) -> str:
        return self.name
    def __repr__(self) -> str:
        return '<CasedBuiltIn {}>'.format(self.name)

# vim:set tabstop=4 shiftwidth=4 expandtab fdm=marker:
