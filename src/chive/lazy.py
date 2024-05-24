import inspect
from typing import Callable, Any

from .utils import ChiveInternalError


class ChiveLazyFunc:
    def __init__(self, func, *args, **kwargs):
        if inspect.isgeneratorfunction(func):
            raise ValueError("ChiveLazyFunc cannot be used with generator functions")
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.cache_val = None
        self.cache_error = None

        self.save_callback = None

    def set_save_callback(self, save_callback: Callable[[Any], None]):
        self.save_callback = save_callback

    def __call__(self):
        if self.cache_val is not None:
            # print("Returning cached value")
            return self.cache_val
        if self.cache_error is not None:
            raise self.cache_error
        try:
            self.cache_val = self.func(
                *[_resolve(arg) for arg in self.args],
                **{k: _resolve(v) for k, v in self.kwargs.items()},
            )
        except Exception as e:
            self.cache_error = e
            raise
            
        if self.save_callback is not None:
            try:
                self.save_callback(self.cache_val)
            except Exception as e:
                self.cache_error = e
                raise ChiveInternalError(
                    f"Error saving value inside lazy function"
                ) from e

        return self.cache_val


def _resolve(arg):
    if isinstance(arg, ChiveLazyFunc):
        return arg()
    return arg
