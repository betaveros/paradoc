from typing import Callable, Generic, List, Optional, Tuple, TypeVar
from paradoc.objects import PdObject, Environment

# bool is whether the result is "reluctant"

T = TypeVar('T')
TrailerFunc = Callable[[Environment, T], Tuple[PdObject, bool]]

class Trailer(Generic[T]):
    def __init__(self, name: str, func: TrailerFunc[T],
            aliases: Optional[List[str]] = None,
            docs: Optional[str] = None,
            stability: str = "unknown") -> None:
        self.name = name
        self.func = func
        self.aliases = aliases or [name]
        self.docs = docs
        self.stability = stability

    def __call__(self, env: Environment, obj: T) -> Tuple[PdObject, bool]:
        return self.func(env, obj)

# vim:set tabstop=4 shiftwidth=4 expandtab fdm=marker:
