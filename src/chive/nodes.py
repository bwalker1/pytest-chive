import decorator
from pathlib import Path
import pytest
import types
from typing import Final

from .lazy import ChiveLazyFunc
from .io import get_save_path

default_scope: Final[str] = "session"


def node(func):
    def wrapper(func, *args, **kwargs):
        return ChiveLazyFunc(func, *args, **kwargs)

    return pytest.fixture(decorator.decorator(wrapper, func), scope=default_scope)  # type: ignore


def checkpoint(save_path=None, recompute: bool | str = False, replicate=None):
    if isinstance(save_path, types.FunctionType):
        # Handle case where decorator is called without arguments
        return checkpoint(None)(save_path)  # type: ignore

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
