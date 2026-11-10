import pathlib
import runpy

USAGE = pathlib.Path(__file__).resolve().parent / "typecheck" / "check_usage.py"


def test_typecheck_usage_runs():
    # CI type-checks this file with mypy and pyright; make sure the code in it
    # also works at runtime.
    runpy.run_path(str(USAGE))
