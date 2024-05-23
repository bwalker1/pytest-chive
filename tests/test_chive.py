import pytest
import subprocess
import time


def test_import_chive():
    """
    Test if the chive package can be imported in less than 0.2 seconds
    """
    start = time.time()
    assert (
        subprocess.run(["python", "-c", "import chive"], capture_output=True).returncode
        == 0
    )
    elapsed = time.time() - start
    assert elapsed < 0.2


if __name__ == "__main__":
    import pytest

    args = [
        # "-p no:chive",
        "--capture=no",
        "/workspaces/pytest-chive/tests/test_chive.py",
    ]
    pytest.main(args)
