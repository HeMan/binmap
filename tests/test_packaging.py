import pathlib
import runpy

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent


def test_only_binmap_is_packaged(monkeypatch):
    # Run setup.py with setuptools.setup() replaced, so its arguments can be
    # inspected without building anything.
    setuptools = pytest.importorskip("setuptools")
    arguments = {}
    monkeypatch.setattr(setuptools, "setup", lambda **kwargs: arguments.update(kwargs))
    monkeypatch.chdir(ROOT)  # find_packages() searches the current directory

    runpy.run_path(str(ROOT / "setup.py"), run_name="__main__")

    assert sorted(arguments["packages"]) == ["binmap"]
    # py.typed (PEP 561) tells type checkers to use binmap's annotations
    assert arguments["package_data"] == {"binmap": ["py.typed"]}
    assert (ROOT / "binmap" / "py.typed").is_file()
