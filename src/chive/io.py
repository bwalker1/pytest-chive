from collections import defaultdict
from pathlib import Path
import pickle
from typing import *


class ChiveIO:
    def __init__(self):
        pass

    def save(self, obj, save_name: str | Path):
        save_name = str(save_name)
        Path(save_name).parent.mkdir(parents=True, exist_ok=True)
        if True or type(obj) not in self.io_types:
            # Try to pickle the object
            try:
                with open(save_name + ".pkl", "wb") as f:
                    pickle.dump(obj, f)
            except Exception as e:
                raise NotImplementedError(f"Saving {type(obj)} is not supported") from e
        else:
            write_fn = self.io_types[type(obj)][1]
            ext = self.io_types[type(obj)][2]
            write_fn(obj, save_name + ext)

    def load(self, type, save_name: str | Path):
        save_name = str(save_name)
        if True or type not in self.io_types:
            with open(save_name + ".pkl", "rb") as f:
                return pickle.load(f)

        read_fn = self.io_types[type][0]
        ext = self.io_types[type][2]
        return read_fn(save_name + ext)


def get_save_path(
    request,
    filter_dependencies: bool = True,
):
    if filter_dependencies and hasattr(request, "_fixturedef"):
        # If this is for a checkpoint, not an output, we only want to save it based on
        # the values of parameters/nodes it actually depends on
        dependencies = set()
        fixturedef = request._fixturedef

        def add_dependencies(argnames):
            for argname in argnames:
                if argname == "request":
                    continue
                dependencies.add(argname)
                add_dependencies(request._fixture_defs[argname].argnames)

        add_dependencies(fixturedef.argnames)
    else:
        dependencies = None
    request_params = {k: v for k, v in request._pyfuncitem.callspec.params.items()}
    params = defaultdict(lambda: "")
    try:
        params.update(
            {
                k: v if isinstance(v, str) else f"{k}={str(v)}"
                for k, v in request_params.items()
                if (dependencies is None or k in dependencies)
            }
        )
    except AttributeError:
        pass

    save_path = ".chive/" + "/".join(params.values())
    return save_path
