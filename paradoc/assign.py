from typing import Callable, Generic, List, Optional, Tuple, TypeVar
from paradoc.objects import Block, BuiltIn, PdObject, Environment
from paradoc.num import Char
import paradoc.objects as objects
import paradoc.num as num

AssignVariantFunc = Callable[[Environment, str], None]

class AssignVariant:
    def __init__(self, name: str, func: AssignVariantFunc,
            aliases: Optional[List[str]] = None,
            docs: Optional[str] = None,
            stability: str = "unknown") -> None:
        self.name = name
        self.func = func
        self.aliases = aliases or [name]
        self.docs = docs
        self.stability = stability

    def block(self, name: str) -> Block:
        def inner(env: Environment) -> None: self.func(env, name)
        return BuiltIn(self.name + name, inner)

def append_func(env: Environment, name: str) -> None:
    # TODO: This will be linear per operation; that's pretty bad.
    obj = env.get(name)
    e = env.pop()
    if isinstance(obj, str):
        env.put(name, obj + env.pd_str(e))
    elif isinstance(obj, list):
        env.put(name, obj + [e])
    elif isinstance(obj, range):
        env.put(name, list(obj) + [e]) # type: ignore
    elif isinstance(obj, (Char, int, float, Block)):
        # Blow away the old value.
        env.put(name, [e])
    else:
        raise AssertionError("Type unaccounted for in appending assignment")

def pop_func(env: Environment, name: str) -> None:
    obj = env.get(name)
    assert isinstance(obj, (str, list, range))
    assert obj
    # TODO: Popping probably shouldn't take linear time...
    env.put(name, obj[:-1])
    env.push(objects.pd_index(obj, -1))

def retrieve_func(env: Environment, name: str) -> None:
    obj = env.get(name)
    env.put(name, 0)
    env.push(obj)

def add_func(env: Environment, name: str) -> None:
    env.put(name, objects.pd_deepvectorize_nn2v(
        num.pd_add, env.get(name), env.pop()))

def sub_func(env: Environment, name: str) -> None:
    env.put(name, objects.pd_deepvectorize_nn2v(
        num.pd_sub, env.get(name), env.pop()))

normal = AssignVariant('.', lambda env, name: env.put(name, env.peek()))
destructive = AssignVariant('._destructive', lambda env, name: env.put(name, env.pop()))
append = AssignVariant('._append', append_func)
pop = AssignVariant('._pop', pop_func)
retrieve = AssignVariant('._retrieve', retrieve_func)
add = AssignVariant('._add', add_func)
sub = AssignVariant('._sub', sub_func)

variant_dict = {
        '.': normal,
        '._destructive': destructive,
        '—': destructive,
        '.a': append,
        '._append': append,
        '.p': pop,
        '._pop': pop,
        '.r': retrieve,
        '._retrieve': retrieve,
        '._add': add,
        '._sub': sub,
}
