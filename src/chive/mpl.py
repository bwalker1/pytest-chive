from pathlib import Path
import pytest


@pytest.fixture(scope="function")  # type: ignore
def figsaver(request, dataset: str, exp_name: str):
    import matplotlib.pyplot as plt

    save = request.config.getoption("--savefig")

    def _savefig(fig, idx=None):
        path = f"chive_output/{dataset}/{exp_name}/{request.node.name.replace('test_', '').split('[')[0]}"
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
def fig(figsaver):
    import matplotlib.pyplot as plt

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
