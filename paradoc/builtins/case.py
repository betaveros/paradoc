from paradoc.objects import *

# A "type" of an argument, possibly with a coercion. Loaded with stuff for
# introspective usefulness. Note we don't typecheck coercions! Their argument
# needs to be an existential type or something to avoid false alarms.
class ArgType:
    def __init__(self, coercions: List[Tuple[Type[PdObject], Callable[[Any], PdObject]]]) -> None:
        self.coercions = coercions
    def accepts(self, arg: PdObject) -> bool:
        for typ, coercion in self.coercions:
            if isinstance(arg, typ): return True
        return False
    def maybe_process(self, arg: PdObject) -> Optional[PdObject]:
        for typ, coercion in self.coercions:
            if isinstance(arg, typ):
                res = coercion(arg)
                return coercion(arg)
        return None

    @staticmethod
    def just_type(*typs: Type[PdObject]) -> 'ArgType':
        return ArgType([(typ, lambda obj: obj) for typ in typs])

just_int    = ArgType.just_type(int)
just_float  = ArgType.just_type(float)
just_number = ArgType.just_type(Char, int, float)
just_str    = ArgType.just_type(str)
just_list   = ArgType.just_type(list, range)
just_seq    = ArgType.just_type(str, list, range)
just_block  = ArgType.just_type(Block)
just_any    = ArgType.just_type(Char, int, float, str, list, range, Block)

# Accepts a list, coercing Chars or numbers to single-element lists
list_singleton = ArgType([
        (Char,  lambda x: [x]),
        (int,   lambda x: [x]),
        (float, lambda x: [x]),
        (list,  lambda x: x),
        (range, lambda x: x)
        ])

# Accepts a sequence, coercing Chars or numbers to single-element strings or
# lists
seq_singleton = ArgType([
        (Char,  lambda x: chr(x.ord)),
        (int,   lambda x: [x]),
        (float, lambda x: [x]),
        (str,   lambda x: x),
        (list,  lambda x: x),
        (range, lambda x: x)
        ])
# Accepts a sequence, coercing Chars or numbers to ranges
seq_range = ArgType([
        (Char,  lambda x: range(x.ord)),
        (int,   lambda x: range(x)),
        (float, lambda x: range(int(x))),
        (str,   lambda x: x),
        (list,  lambda x: x),
        (range, lambda x: x)
        ])

# Accepts a list, coercing strings to lists of integers and Chars or numbers to ranges
list_int_range = ArgType([
        (Char,  lambda x: range(x.ord)),
        (int,   lambda x: range(x)),
        (float, lambda x: range(int(x))),
        (str,   lambda x: [ord(c) for c in x]),
        (list,  lambda x: x),
        (range, lambda x: x)
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
    def any(func: Callable[[Environment, PdObject], List[PdObject]]) -> 'Case':
        return Case(1, [just_any], func)
    @staticmethod
    def int_(func: Callable[[Environment, int], List[PdObject]]) -> 'Case':
        return Case(1, [just_int], func)
    @staticmethod
    def str_(func: Callable[[Environment, str], List[PdObject]]) -> 'Case':
        return Case(1, [just_str], func)
    @staticmethod
    def list_(func: Callable[[Environment, list], List[PdObject]]) -> 'Case':
        return Case(1, [just_list], func)
    @staticmethod
    def seq(func: Callable[[Environment, PdSeq], List[PdObject]]) -> 'Case':
        return Case(1, [just_seq], func)
    @staticmethod
    def seq_range(func: Callable[[Environment, PdSeq], List[PdObject]]) -> 'Case':
        return Case(1, [seq_range], func)
    @staticmethod
    def number(func: Callable[[Environment, Union[int, float]], List[PdObject]]) -> 'Case':
        return Case(1, [just_number], func)
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
    def str2(func: Callable[[Environment, str, str], List[PdObject]]) -> 'Case':
        return Case(2, [just_str, just_str], func)
    @staticmethod
    def list2(func: Callable[[Environment, Union[list, range], Union[list, range]], List[PdObject]]) -> 'Case':
        return Case(2, [just_list, just_list], func)
    @staticmethod
    def list2_singleton(func: Callable[[Environment, Union[list, range], Union[list, range]], List[PdObject]]) -> 'Case':
        return Case(2, [list_singleton, list_singleton], func)
    @staticmethod
    def seq2(func: Callable[[Environment, PdSeq, PdSeq], List[PdObject]]) -> 'Case':
        return Case(2, [just_seq, just_seq], func)
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
    def block_seq_range(func: Callable[[Environment, Block, PdSeq], List[PdObject]], commutative: bool = True) -> 'Case':
        return Case(2, [just_block, seq_range], func, commutative=commutative)
    @staticmethod
    def condition_block(func: Callable[[Environment, PdObject, Block], List[PdObject]], commutative: bool = True) -> 'Case':
        return Case(2, [just_any, just_block], func, commutative=commutative)

    @staticmethod
    def any3(func: Callable[[Environment, PdObject, PdObject, PdObject], List[PdObject]]) -> 'Case':
        return Case(2, [just_any, just_any], func)

class CasedBuiltIn(Block):
    def __init__(self, name: str, cases: List[Case]) -> None:
        self.name = name
        self.cases = cases
    def __call__(self, env: 'Environment') -> None:
        collected_args = [] # type: List[PdObject]
        for case in self.cases:
            assert len(collected_args) <= case.arity
            for _ in range(case.arity - len(collected_args)):
                collected_args.insert(0, env.pop())
            res = case.maybe_run(env, collected_args)
            if res is not None:
                env.push(*res)
                return
        raise NotImplementedError('No cases match for built-in ' + self.name + ' with args ' + repr(collected_args))
    def code_repr(self) -> str:
        return self.name
