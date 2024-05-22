import inspect


class ChiveLazyFunc:
    def __init__(self, func, *args, **kwargs):
        if inspect.isgeneratorfunction(func):
            raise ValueError("ChiveLazyFunc cannot be used with generator functions")
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.cache_val = None
        self.cache_error = None

    def __call__(self):
        if self.cache_val is not None:
            # print("Returning cached value")
            return self.cache_val
        if self.cache_error is not None:
            raise self.cache_error
        try:
            self.cache_val = self.func(
                *[_resolve(arg) for arg in self.args],
                **{k: _resolve(v) for k, v in self.kwargs.items()}
            )
        except Exception as e:
            self.cache_error = e
            raise
        return self.cache_val


def _resolve(arg):
    if isinstance(arg, ChiveLazyFunc):
        return arg()
    return arg
