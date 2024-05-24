from collections import defaultdict
import decorator
import importlib
from pathlib import Path
import pytest
from typing import *  # type: ignore
import yaml

from .lazy import ChiveLazyFunc, _resolve
from .io import get_save_path, ChiveIO
from .nodes import default_scope, param
from .utils import ChiveInternalError

# Need to import fixtures located in here:
from .mpl import *


def pytest_plugin_registered(plugin, plugin_name, manager):
    if plugin_name == "chive":
        if not manager.hasplugin("chive_sub"):
            manager.register(ChivePlugin(), name="chive_sub")


class ChivePlugin:
    def __init__(self, force_recompute=False):
        self.params = {}
        self.force_recompute = force_recompute
        self.IO = ChiveIO()
        self.main_workflows: List[str] = []
        self.sub_workflows: List[str] = []

        self.checkpoint_parameter_overrides = defaultdict(dict)

        self.manager = None

    def pytest_plugin_registered(self, plugin, plugin_name, manager):
        for name, obj in plugin.__dict__.items():
            if isinstance(obj, param):
                self._load_param(name, obj, overwrite=False)

        if plugin_name == "chive_sub":
            self.manager = manager

    def pytest_addoption(self, parser, pluginmanager):
        parser.addoption(
            "--chive_config",
            default=[],
            action="extend",
            help="Chive config YAML file(s)",
            nargs="*",
        )
        parser.addoption(
            "--savefig",
            action="store_true",
            default=False,
            help="save figures from tests",
        )
        parser.addini("workflows", help="Main workflow(s)", default=[], type="args")
        parser.addini(
            "chive_config", help="Chive Configuration File(s)", default=[], type="args"
        )

    def pytest_configure(self, config):
        config.addinivalue_line("markers", "chive_output: Chive output node")

        self.main_workflows = config.getini("workflows")
        # Note: passing file(s) into the command line options will overwrite the ini settings
        chive_configs = config.getoption("--chive_config") or config.getini(
            "chive_config"
        )
        for chive_config in chive_configs:
            with open(chive_config) as f:
                cfg = yaml.safe_load(f)
            if "workflows" in cfg:
                self.sub_workflows.extend(cfg["workflows"])
            if "parameters" in cfg:
                for name, vals in cfg["parameters"].items():
                    self._load_param(name, param(vals), overwrite=True)
            if "checkpoints" in cfg:
                for name, vals in cfg["checkpoints"].items():
                    self.checkpoint_parameter_overrides[name].update(vals)
            if "recompute" in cfg:
                self.force_recompute = cfg["recompute"]

        self._load_workflows()

    def pytest_collect_file(self, file_path, parent):
        pass

    def pytest_pycollect_makeitem(self, collector, name, obj):
        if hasattr(obj, "pytestmark") and "chive_output" in [
            mark.name for mark in obj.pytestmark
        ]:
            # return pytest.Function.from_parent(parent=collector, name=name)
            return list(collector._genfunctions(name, obj))

    def pytest_generate_tests(self, metafunc):
        for name, vals in self.params.items():
            if name in metafunc.fixturenames:
                metafunc.parametrize(
                    name,
                    vals,
                    scope=default_scope,
                )


    def pytest_fixture_setup(self, fixturedef, request):
        if hasattr(fixturedef.func, "_chive_checkpoint"):
            save_path = get_save_path(request)
            save_name = f"{save_path}/{fixturedef.argname}.pkl"
            ckpt_data = fixturedef.func._chive_checkpoint
            if not (ckpt_data["recompute"] == True or self.force_recompute):

                try:
                    val = self.IO.load(save_name)
                    print(f"Loaded {fixturedef.argname} from checkpoint")

                    def cache_func(*args, **kwargs):
                        return val

                    # we're going to need to put the original function back after the test
                    fixturedef._chive_old_func = fixturedef.func
                    fixturedef.func = cache_func
                except Exception:
                    if ckpt_data["recompute"] == "error":
                        raise

            # Add a wrapper to save the value when it's computed
            # Have to be careful not to save multiple times because we're outside the lazy function that caches
            def wrapper(func, *args, **kwargs):
                lazy_func = func(*args, **kwargs)
                if not isinstance(lazy_func, ChiveLazyFunc):
                    raise ChiveInternalError("why?")
                lazy_func.save_callback = lambda val: self.IO.save(val, save_name)
                return lazy_func

            fixturedef._chive_old_func = fixturedef.func
            fixturedef.func = decorator.decorator(wrapper, fixturedef.func)

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_setup(self, item):
        yield
        # Resolve any lazy functions that will actually get used
        for name, val in item.funcargs.items():
            if name in item._fixtureinfo.argnames and isinstance(val, ChiveLazyFunc):
                v = val()
                item.funcargs[name] = v

    def pytest_fixture_post_finalizer(self, fixturedef, request):
        if hasattr(fixturedef, "_chive_old_func"):
            fixturedef.func = fixturedef._chive_old_func
            del fixturedef._chive_old_func
        if 0:
            if (
                hasattr(fixturedef.func, "_chive_checkpoint")
                and fixturedef.cached_result
                and not isinstance(fixturedef.cached_result, ChiveLazyFunc)
            ):
                save_path = get_save_path(request)
                save_name = f"{save_path}/{fixturedef.argname}.pkl"
                cached_val = request.getfixturevalue(fixturedef.argname)
                self.IO.save(cached_val, save_name)

    # Internal functions
    def _load_workflows(self):
        if self.manager is None:
            raise ChiveInternalError("Manager not loaded")
        for workflow in [*self.main_workflows, *self.sub_workflows]:
            mod = importlib.import_module(workflow)
            self.manager.register(mod, name=workflow)

    def _load_param(self, name, param, overwrite):
        if overwrite or name not in self.params and not overwrite:
            self.params[name] = param.vals
