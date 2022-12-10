"""
This type stub file was generated by pyright.
"""

import enum
import sys
from dataclasses import dataclass
from typing import Any, Dict, Generic, Literal, Set, TypeVar, Union, overload
from weakref import WeakKeyDictionary
from ._core._eventloop import get_asynclib

if sys.version_info >= (3, 8):
    ...
else:
    ...
T = TypeVar("T")
D = TypeVar("D")
async def checkpoint() -> None:
    """
    Check for cancellation and allow the scheduler to switch to another task.

    Equivalent to (but more efficient than)::

        await checkpoint_if_cancelled()
        await cancel_shielded_checkpoint()

    .. versionadded:: 3.0

    """
    ...

async def checkpoint_if_cancelled() -> None:
    """
    Enter a checkpoint if the enclosing cancel scope has been cancelled.

    This does not allow the scheduler to switch to a different task.

    .. versionadded:: 3.0

    """
    ...

async def cancel_shielded_checkpoint() -> None:
    """
    Allow the scheduler to switch to another task but without checking for cancellation.

    Equivalent to (but potentially more efficient than)::

        with CancelScope(shield=True):
            await checkpoint()

    .. versionadded:: 3.0

    """
    ...

def current_token() -> object:
    """Return a backend specific token object that can be used to get back to the event loop."""
    ...

_run_vars: WeakKeyDictionary[Any, Dict[str, Any]] = ...
_token_wrappers: Dict[Any, _TokenWrapper] = ...
@dataclass(frozen=True)
class _TokenWrapper:
    __slots__ = ...
    _token: object


class _NoValueSet(enum.Enum):
    NO_VALUE_SET = ...


class RunvarToken(Generic[T]):
    __slots__ = ...
    def __init__(self, var: RunVar[T], value: Union[T, Literal[_NoValueSet.NO_VALUE_SET]]) -> None:
        ...
    


class RunVar(Generic[T]):
    """Like a :class:`~contextvars.ContextVar`, expect scoped to the running event loop."""
    __slots__ = ...
    NO_VALUE_SET: Literal[_NoValueSet.NO_VALUE_SET] = ...
    _token_wrappers: Set[_TokenWrapper] = ...
    def __init__(self, name: str, default: Union[T, Literal[_NoValueSet.NO_VALUE_SET]] = ...) -> None:
        ...
    
    @overload
    def get(self, default: D) -> Union[T, D]:
        ...
    
    @overload
    def get(self) -> T:
        ...
    
    def get(self, default: Union[D, Literal[_NoValueSet.NO_VALUE_SET]] = ...) -> Union[T, D]:
        ...
    
    def set(self, value: T) -> RunvarToken[T]:
        ...
    
    def reset(self, token: RunvarToken[T]) -> None:
        ...
    
    def __repr__(self) -> str:
        ...
    


