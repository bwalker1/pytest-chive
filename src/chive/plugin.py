import importlib
import pytest
from typing import *  # type: ignore
import yaml

from .lazy import ChiveLazyFunc, _resolve
from .io import get_save_path, ChiveIO
from .nodes import default_scope, param
from .mpl import figsaver, fig, ax


def pytest_addoption(parser, pluginmanager):
    parser.addoption("--chive_config", default=None, help="Chive config YAML file")
    parser.addoption(
        "--savefig", action="store_true", default=False, help="save figures from tests"
    )
    parser.addini("workflow", help="Main workflow", default=None)
    parser.addini("chive_config", help="Chive Configuration File", default=None)


def pytest_plugin_registered(plugin, plugin_name, manager):
    if plugin_name == "chive":
        if not manager.hasplugin("chive_sub"):
            manager.register(ChivePlugin(), name="chive_sub")


class ChivePlugin:
    def __init__(self, force_recompute=False):
        self.params = {}
        self.force_recompute = force_recompute
        self.IO = ChiveIO()
        self.main_workflow: str | None = None
        self.sub_workflows: List[str] = []

        self.manager = None

    def pytest_configure(self, config):
        config.addinivalue_line("markers", "chive_output: Chive output node")

        self.main_workflow = config.getini("workflow")
        if chive_config := config.getoption("--chive_config") or config.getini(
            "chive_config"
        ):
            with open(chive_config) as f:
                cfg = yaml.safe_load(f)
            if "workflows" in cfg:
                self.sub_workflows.extend(cfg["workflows"])
            if "parameters" in cfg:
                for name, vals in cfg["parameters"].items():
                    self.load_param(name, param(vals), overwrite=True)

        self.load_workflows()

    def pytest_plugin_registered(self, plugin, plugin_name, manager):
        for name, obj in plugin.__dict__.items():
            if isinstance(obj, param):
                self.load_param(name, obj, overwrite=False)
        asdf = 1
        if plugin_name == "chive_sub":
            self.manager = manager

    def load_workflows(self):
        if self.manager is None:
            return
        if self.main_workflow is not None:
            mod = importlib.import_module(self.main_workflow)
            self.manager.register(mod, name=self.main_workflow)

        for sub_workflow in self.sub_workflows:
            mod = importlib.import_module(sub_workflow)
            self.manager.register(mod, name=sub_workflow)

    def load_param(self, name, param, overwrite):
        if overwrite or name not in self.params and not overwrite:
            self.params[name] = param.vals

    def pytest_generate_tests(self, metafunc):
        for name, vals in self.params.items():
            if name in metafunc.fixturenames:
                metafunc.parametrize(
                    name,
                    vals,
                    scope=default_scope,
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
                    val = self.IO.load(ret_type, savename)
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
            self.IO.save(cached_val, save_name)
