"""
The binmap skill (skills/binmap/SKILL.md) teaches AI assistants how to use binmap.
Its examples must run, it must cover the whole API, and its frontmatter must follow
the Agent Skills specification: https://agentskills.io/specification
"""

import pathlib
import re
from typing import Annotated, Dict, List, Tuple, get_origin

import pytest

import binmap
from binmap import types

SKILL = (
    pathlib.Path(__file__).resolve().parent.parent / "skills" / "binmap" / "SKILL.md"
)


def _split(text: str) -> Tuple[Dict[str, str], str]:
    """The frontmatter's top-level ``key: value`` pairs, and the body."""
    match = re.match(r"---\n(.*?)\n---\n(.*)", text, re.S)
    assert match, "SKILL.md must start with YAML frontmatter between --- lines"
    frontmatter = dict(
        line.split(": ", 1) for line in match.group(1).splitlines() if line.strip()
    )
    return frontmatter, match.group(2)


TEXT = SKILL.read_text(encoding="utf-8")
FRONTMATTER, BODY = _split(TEXT)


def _examples() -> List[Tuple[int, str]]:
    """Every ```python block, with the line it starts on in SKILL.md."""
    return [
        (TEXT.count("\n", 0, match.start(1)), match.group(1))
        for match in re.finditer(r"^```python\n(.*?)^```$", TEXT, re.S | re.M)
    ]


EXAMPLES = _examples()


class TestFrontmatter:
    def test_name_matches_the_directory(self):
        assert FRONTMATTER["name"] == SKILL.parent.name

    def test_name_format(self):
        assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", FRONTMATTER["name"])
        assert len(FRONTMATTER["name"]) <= 64

    def test_description_length(self):
        assert 0 < len(FRONTMATTER["description"]) <= 1024

    def test_compatibility_length(self):
        assert 0 < len(FRONTMATTER["compatibility"]) <= 500

    def test_only_known_fields(self):
        known = {"name", "description", "license", "compatibility", "metadata"}
        assert set(FRONTMATTER) <= known


class TestExamples:
    def test_there_are_examples(self):
        assert len(EXAMPLES) >= 5

    @pytest.mark.parametrize(
        "line, code", EXAMPLES, ids=[f"line {line}" for line, _ in EXAMPLES]
    )
    def test_example_runs_on_its_own(self, line, code):
        # Each block gets a fresh namespace, so it must include its own imports.
        # The leading newlines make tracebacks show SKILL.md's line numbers.
        compiled = compile("\n" * line + code, str(SKILL), "exec")
        exec(compiled, {"__name__": "skill_example"})


class TestCoverage:
    """A new type, field function or exception must be added to the skill."""

    @pytest.mark.parametrize(
        "name",
        [name for name, value in vars(types).items() if get_origin(value) is Annotated]
        + ["StructCode"],
    )
    def test_every_type_is_documented(self, name):
        assert f"`{name}`" in BODY

    @pytest.mark.parametrize(
        "name",
        # The public functions: padding(), constant(), stringfield()...
        [
            name
            for name in binmap.__all__
            if name.islower() and callable(getattr(binmap, name))
        ],
    )
    def test_every_field_function_is_documented(self, name):
        assert f"`{name}(" in BODY

    @pytest.mark.parametrize(
        "name",
        [
            name
            for name in binmap.__all__
            if name.startswith("Binmap") and name.endswith("Error")
        ],
    )
    def test_every_exception_is_documented(self, name):
        assert f"`{name}`" in BODY
