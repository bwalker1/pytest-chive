from pathlib import Path
import pytest


@pytest.fixture(scope="session")
def plt():
    # this takes a while to import, so we delay it until it's actually needed
    import matplotlib.pyplot as plt

    return plt


@pytest.fixture(scope="function")
def figsaver(request, plt, dataset: str, exp_name: str):
    save = request.config.getoption("--savefig")

    def _savefig(fig, idx=None):
        path = f"dataset_figures/{dataset}/{exp_name}/{request.node.name.replace('test_', '').split('[')[0]}"
        if idx is not None:
            path += f"/{idx}"
        path += ".png"
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(
            path,
            dpi=300,
            bbox_inches="tight",
            transparent=True,
        )

    if save:
        with plt.ioff():
            yield _savefig
    else:
        yield lambda fig, idx=None: None


@pytest.fixture(scope="function")
def fig(figsaver, plt):
    fig = plt.figure()
    try:
        yield fig
    except Exception:
        raise
    else:
        figsaver(fig)
    finally:
        plt.close(fig)


@pytest.fixture(scope="function")
def ax(fig):
    return fig.add_subplot(111)
