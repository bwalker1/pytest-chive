from collections import defaultdict
import importlib.util
import logging
import pytest
import sys
from typing import *  # type: ignore
import warnings
import yaml

import chive
from .lazy import ChiveLazyFunc, _resolve
from .io import get_save_path


def pytest_addoption(parser, pluginmanager):
    parser.addoption(
        "--param_files", action="append", default=[], help="parameter yaml files"
    )
    parser.addoption(
        "--params", action="store", default={}, help="parameter dictionary"
    )
    parser.addoption(
        "--pipeline", action="store_true", default=False, help="run pipeline code"
    )
    parser.addoption(
        "--savefig", action="store_true", default=False, help="save figures from tests"
    )


def pytest_pycollect_makeitem(collector, name, obj):
    try:
        for mark in obj.pytestmark:  # @IgnoreException
            if mark.name == "chive_output":
                return list(collector._genfunctions(name, obj))
    except AttributeError:
        pass


def pytest_plugin_registered(plugin, plugin_name, manager):
    if not manager.hasplugin("chive_sub"):
        manager.register(ChivePlugin(), name="chive_sub")


class ChivePlugin:
    def __init__(self, force_recompute=False):
        self.params = {}
        self.force_recompute = force_recompute

    def pytest_configure(self, config):
        config.addinivalue_line("markers", "chive_output: Chive output node")
        config.addinivalue_line("markers", "chive_replicate: Chive replicate marker")

        for param in config.getoption("--param_files"):
            with open(param) as f:
                params = yaml.safe_load(f)
            for name, vals in params.items():
                self.load_param(name, chive.param(vals), overwrite=True)

    def pytest_collect_file(self, file_path, parent):
        if file_path.suffix == ".py" and not file_path.name.startswith("_"):
            # first check for the text "chive" to avoid loading unnecessary files
            with open(file_path) as f:
                if "chive" not in f.read():
                    return
            mod = _load_from_path(file_path)
            for name, obj in mod.__dict__.items():
                if isinstance(obj, chive.param):
                    self.load_param(name, obj, overwrite=False)

                if (
                    hasattr(obj, "_chive_checkpoint")
                    and "replicate" in obj._chive_checkpoint  # type: ignore
                ):
                    self.replicate[obj.__name__] = obj._chive_checkpoint["replicate"]  # type: ignore

    def load_param(self, name, param, overwrite):
        if overwrite or name not in self.params and not overwrite:
            self.params[name] = param.vals

    def pytest_generate_tests(self, metafunc):
        for name, vals in self.params.items():
            if name in metafunc.fixturenames:
                metafunc.parametrize(
                    name,
                    vals,
                    scope=chive.default_scope,
                )

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_setup(self, item):
        yield
        # Resolve any lazy functions that will actually get used
        if hasattr(item, "callspec"):
            for name, val in item.callspec.params.items():
                if isinstance(val, ChiveLazyFunc):
                    raise NotImplementedError("Does this happen?")
                    item.callspec.params[name] = val()
        for name, val in item.funcargs.items():
            if name in item._fixtureinfo.argnames and isinstance(val, ChiveLazyFunc):
                v = val()
                item.funcargs[name] = v

    def pytest_fixture_setup(self, fixturedef, request):
        if hasattr(fixturedef.func, "_chive_checkpoint"):
            savename = get_save_path(request)
            ckpt_data = fixturedef.func._chive_checkpoint
            ret_type = ckpt_data["ret_type"]
            if not (ckpt_data["recompute"] or self.force_recompute):
                try:
                    val = chive.IO.load(ret_type, savename)
                    print(f"Loaded {fixturedef.argname} from checkpoint")

                    def cache_func(*args, **kwargs):
                        return val

                    # we're going to need to put the original function back after the test
                    fixturedef._chive_old_func = fixturedef.func
                    fixturedef.func = cache_func
                except Exception:
                    pass

    def pytest_fixture_post_finalizer(self, fixturedef, request):
        if hasattr(fixturedef, "_chive_old_func"):
            fixturedef.func = fixturedef._chive_old_func
            del fixturedef._chive_old_func
        if fixturedef.cached_result and hasattr(fixturedef.func, "_chive_checkpoint"):
            save_path = get_save_path(request)
            save_name = f"{save_path}/{fixturedef.argname}.pkl"
            ckpt_data = fixturedef.func._chive_checkpoint
            cached_val = _resolve(request.getfixturevalue(fixturedef.argname))
            assert isinstance(cached_val, ckpt_data["ret_type"])
            chive.IO.save(cached_val, save_name)


def _load_from_path(path):
    spec = importlib.util.spec_from_file_location(path.name, path)
    module = importlib.util.module_from_spec(spec)  # type:ignore
    spec.loader.exec_module(module)  # type: ignore
    return module
