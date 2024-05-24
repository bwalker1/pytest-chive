import decorator
from pathlib import Path
import pytest
import types
from typing import *

from .lazy import ChiveLazyFunc
from .io import get_save_path

default_scope: Final[str] = "session"


def node(lazy: bool | Callable = True):
    if not isinstance(lazy, bool):
        # Handle case where decorator is called without arguments
        return node()(lazy)

    def deco(func):
        def wrapper(func, *args, **kwargs):
            return ChiveLazyFunc(func, *args, **kwargs)

        maybe_wrapped_func = decorator.decorator(wrapper, func) if lazy else func

        return pytest.fixture(maybe_wrapped_func, scope=default_scope)  # type: ignore

    return deco


def checkpoint(recompute: bool | Literal["error"] | Callable = False, replicate=None):
    if not isinstance(recompute, bool) and recompute != "error":
        # Handle case where decorator is called without arguments
        return checkpoint()(recompute)  # type: ignore

    def deco(func):
        func._chive_checkpoint = {
            "recompute": recompute,
        }
        if replicate is not None:
            func._chive_checkpoint["replicate"] = replicate

        return node(func)

    return deco


def input(*args, **kwargs):
    return pytest.fixture(scope=default_scope, *args, **kwargs)  # type: ignore


def output(func):
    mark = pytest.mark.chive_output
    return mark(func)


class param:
    def __init__(self, *vals):
        self.vals = vals


@node
def save_path(request):
    save_path = get_save_path(request, filter_dependencies=False)
    return save_path
