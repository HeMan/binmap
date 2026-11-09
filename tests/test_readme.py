import doctest
import pathlib
from dataclasses import asdict, astuple
from enum import IntEnum

import binmap
from binmap import types

README = pathlib.Path(__file__).resolve().parent.parent / "README.rst"


def test_readme_examples():
    # The README examples leave out imports, so provide what they use: binmap's
    # public names, the type names and a few standard library names.
    globs = {
        "IntEnum": IntEnum,
        "asdict": asdict,
        "astuple": astuple,
        **{
            name: getattr(binmap, name)
            for name in dir(binmap)
            if not name.startswith("_")
        },
        **{
            name: getattr(types, name)
            for name in dir(types)
            if not name.startswith("_")
        },
    }
    test = doctest.DocTestParser().get_doctest(
        README.read_text(encoding="utf-8"), globs, "README.rst", str(README), 0
    )
    output = []
    result = doctest.DocTestRunner().run(test, out=output.append)
    assert result.attempted > 0
    assert result.failed == 0, "".join(output)
