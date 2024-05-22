import pytest

import chive


@chive.node
def node_1():
    return 1


dataset = chive.param(["test_dataset", "another_dataset"])


@chive.checkpoint(save_path="helloworld")  # , recompute=True)
def node_2(node_1, dataset) -> str:
    print(f"Hello World from {dataset}")
    return dataset


@chive.output
def other_function(dataset, node_2):
    assert True or node_2 == dataset


if __name__ == "__main__":
    import pytest

    args = [
        "-p no:chive",
        "--capture=no",
        # "--param_files=test/params/params.yaml",
        "/workspaces/chive/chive/pytest_plugin/test_chive.py",
    ]
    pytest.main(args)
