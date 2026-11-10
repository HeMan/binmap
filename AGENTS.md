# AGENTS.md

Guidance for AI coding agents (and humans) working on **binmap**.

## What this project is

`binmap` is a small, pure-Python, **zero-dependency** library for declaring binary
record layouts as dataclasses. Type hints choose the wire format, `bytes(obj)` packs,
and `Cls(raw_bytes)` / `obj.frombytes(raw)` unpack. Under the hood it uses the stdlib
`struct` module.

```python
from binmap import BinmapDataclass, b_types, calculatedfield

class Reading(BinmapDataclass, byteorder="<"):   # default byteorder is ">" (big-endian)
    temp: b_types.signedchar = 0
    hum: b_types.unsignedchar = 0
    def chk(self) -> b_types.unsignedchar:
        return (self.temp + self.hum) & 0xFF
    checksum: b_types.unsignedchar = calculatedfield(chk)

bytes(Reading(temp=-20, hum=10))   # b'\xec\n\xf6'
Reading(b"\xec\n\xf6").temp        # -20
```

It is published on PyPI as `binmap`, is marked *Production/Stable*, and its docs are on
Read the Docs. **Keep the public API backwards compatible.** That covers the field
factory functions, the type names, the `byteorder=` class keyword, exception types and
messages, and `repr` output.

## Repository layout

| Path | Purpose |
|---|---|
| `binmap/__init__.py` | The entire implementation: descriptors, `_struct_code()`, field factories (`padding`, `constant`, `autolength`, `stringfield`, `enumfield`, `calculatedfield`), and `BinmapDataclass`. `__all__` lists the public API. |
| `binmap/types.py` | One `Annotated[<Python type>, StructCode(<code>)]` alias per `struct` format character (`unsignedchar`, `short`, `double`, `pad`, ...), plus `StructCode`. Re-exported as `binmap.b_types`. |
| `binmap/st.py` | Single-letter aliases named after the `struct` format characters (`st.B`, `st.H`, `st.x`, ...). |
| `binmap/py.typed` | PEP 561 marker: tells type checkers to use binmap's annotations. Shipped via `package_data` in `setup.py`. |
| `tests/test_binmap.py` | Tests for the library. |
| `tests/test_readme.py` | Runs every `>>>` example in `README.rst` as a doctest. |
| `tests/test_packaging.py` | Checks that `setup.py` packages only `binmap` (and its subpackages) and ships `py.typed`. Skipped without setuptools. |
| `tests/typecheck/check_usage.py` | Everyday user code that mypy and pyright must accept without errors (CI checks it). `tests/test_typecheck.py` runs it, so it must also work at runtime. |
| `docs/source/` | Sphinx docs. `index.rst` includes `README.rst`; `binmap.rst` autodocs the package. `conf.py` reads the version from `setup.py`. |
| `.readthedocs.yml` | Read the Docs build: the main docs site for `master` (latest) and release tags (stable). |
| `setup.py` | setuptools packaging. There is no `pyproject.toml`. `find_packages(include=["binmap", "binmap.*"])` keeps `tests/` out of the installed packages. |
| `requirements-dev.txt`, `requirements-doc.txt` | Dev and docs tools. Nothing is pinned, and there is no lockfile. |
| `.python-version` | Pins the local dev environment to Python 3.14 for uv. It's not 3.15 because bump2version doesn't run there. |
| `tox.ini` | Holds the flake8 and isort config as well as a tox env. |
| `.bumpversion.cfg` | bump2version config. The version lives here and in `setup.py`. |
| `.github/workflows/` | `pythonpackage.yml` (CI), `pythondist.yml` (publish to PyPI on tag), `docs.yml` (build docs and publish each branch to GitHub Pages). |
| `.github/scripts/gh-pages.sh` | Publishes or removes one branch's docs on the `gh-pages` branch and regenerates its index page. Used by `docs.yml`. |

## Setup and commands

The dev environment is managed with [uv](https://docs.astral.sh/uv/), used as a
venv/pip front end. There is no `uv sync` and no `uv.lock`. `uv venv` creates `.venv`
with Python 3.14 from `.python-version`, and uv downloads that Python if it isn't
installed. Tests import `binmap` from the repo root, so no editable install is needed.
When the pin changes, an existing `.venv` stays on the old Python. `uv run` then *skips*
it and silently runs the newly pinned interpreter from elsewhere, without the dev tools
(e.g. `Failed to spawn: black`). Recreate it with `uv venv --clear` and reinstall the
requirements.

**Deactivate any other virtualenv first.** Outside a uv project, `uv run` picks the first
interpreter that matches `.python-version`:
1. an activated `VIRTUAL_ENV`,
2. then `.venv`,
3. then any other Python of the pinned version.

`uv pip` always installs into the activated `VIRTUAL_ENV`. So an activated virtualenv can
silently replace `.venv`, or, when its Python doesn't match the pin, you install into one
environment and run from another.

```sh
uv venv
uv pip install -r requirements-dev.txt

# Tests
uv run pytest -v
uv run pytest -v tests/test_binmap.py::TestAutolength         # one class
uv run pytest -v -k calculated                                # by keyword
uv run --isolated --python 3.11 --with pytest pytest -v       # another Python, without touching .venv

# Type check the package and the user-code sample, as CI does. pyright is the
# engine behind VS Code's Pylance; keep its version in sync with the workflow.
uv run mypy --strict --disallow-any-explicit binmap tests/typecheck
uvx pyright@1.1.414 binmap tests/typecheck

# Lint: CI only *fails* on syntax errors / undefined names:
uv run flake8 binmap tests --count --select=E9,F63,F7,F82 --show-source --statistics
# Full lint with all plugins (black, isort, builtins) using tox.ini config:
uv run flake8 binmap tests

# Format
uv run black binmap tests
uv run isort binmap tests

# Docs (output goes to docs/build/html). Warnings are errors, as in CI and on
# Read the Docs.
uv pip install -r requirements-doc.txt
uv run make -C docs html SPHINXOPTS="-W --keep-going"
```

- Before calling a change done, run `uv run pytest -v` and both type checkers, and run
  `black` and `isort` on the files you touched.
- `uv run tox` runs flake8, mypy and pytest in a single env. It currently stops at its
  strict flake8 step because of the existing lint findings listed under *Code style*.
- **Packaging still uses `setup.py` and the requirements files.** Don't migrate to
  `pyproject.toml`, `uv sync` or `uv.lock`, and don't add new setup.py-era config
  (`setup.cfg`, `MANIFEST.in`), unless asked. Add dev or docs tools to the matching
  requirements file.

### Python versions

- CI tests **3.11 through 3.15**, every CPython version that isn't end-of-life.
  `python_requires=">=3.11"` in `setup.py` matches, so code must work on 3.11.
  - When a version reaches end-of-life (see endoflife.date), remove it from the matrix in
    `.github/workflows/pythonpackage.yml` and from the `setup.py` classifiers, and raise
    `python_requires`.
  - Add new releases to the matrix and the classifiers.
- **Resolve type hints on the class, never on an instance.** Python 3.14+ (PEP 649/749)
  rejects `get_type_hints(instance)`, which is what used to break 3.14.
  - `__init_subclass__` resolves `get_type_hints(cls, include_extras=True)` once and
    stores each field's struct code on the class (`__codes`).
  - `BinField.__set__` reads it from there, so validation and the struct format always use
    the same code. Reading it is also fast; resolving hints on every assignment made
    assignments about 50x slower.
  - The bounds tests in `TestInheritance` guard this. A change that silently skips
    validation for inherited fields would otherwise pass every other test.

## How it works

Read this before touching `binmap/__init__.py`.

- **Subclassing is the decorator.** `BinmapDataclass.__init_subclass__` calls
  `dataclasses.dataclass(cls)` on every subclass, so users never write `@dataclass`. The
  byte order is passed as a class keyword (`byteorder="<"`) and becomes the first
  character of the struct format string.
- **Building the format string.** `__init_subclass__` walks `dataclasses.fields(cls)`.
  For each field it finds the struct code with `_struct_code()`, picks a descriptor based
  on the code and the field's metadata, installs that descriptor as a class attribute,
  and appends the code to a per-class format string.
  - `_struct_code()` takes the code from the `StructCode` in an `Annotated` hint (the
    `binmap.types` aliases, or users' own). Otherwise it maps plain `int`, `float`,
    `bool`, `bytes` and `str` (`_PLAIN_CODES`); an `Annotated` hint without a
    `StructCode` counts as its Python type. Anything else raises `KeyError`, which
    `_field_code()` turns into a `BinmapTypeError` naming the field.
  - That's why `get_type_hints()` is always called with `include_extras=True`: without
    it, `Annotated` metadata is dropped and every alias looks like a plain `int`.
  - **Declaration order is wire order**, and parent-class fields come first.
  - With multiple inheritance, dataclasses collect fields in reverse MRO order. So
    `class C(A, B)` puts B's fields first, then A's, then C's. A field declared in several
    bases gets its *position* from the last of those bases in the MRO, but its *type*
    from the first.
  - The one exception is `calculatedfield(..., last=True)`, which is moved to the end.
    Only one `last` field is allowed per class hierarchy.
- **Per-class bookkeeping is built once, in `__init_subclass__`, and instances never
  change it.** The same loop that builds the format string records:
  - `__datafields`: the names of the fields with a value in the struct, i.e. everything
    except padding, in wire order (the `last` field at the end). It's a tuple.
  - `__datafieldsmap`: field name → `dataclasses.Field`.

  `frombytes` pairs the unpacked values with `__datafields` using
  `zip(..., strict=True)`. Keep anything derived from the class definition out of
  `__post_init__`. `TestClassBookkeeping::test_instantiation_does_not_change_class_state`
  checks this.
- **Field kinds come from metadata keys**, which the factory functions set:

  | Factory | Metadata key | Descriptor |
  |---|---|---|
  | `padding` | `"padding"` | `PaddingField` |
  | `constant` | `"constant"` | `ConstField` |
  | `autolength` | `"autolength"` | `AutolengthField` (a `ConstField`) |
  | `calculatedfield` | `"function"`, `"last"` | `CalculatedField` |
  | `enumfield` | `"enum"` | `EnumField` |
  | `stringfield` | `"length"`, `"autodefault"` | `StringField` |

  A new field kind follows the same pattern. Write a factory that returns
  `dataclasses.field(..., metadata={...})`, then handle it in `__init_subclass__`,
  `__post_init__`, `__bytes__` and `frombytes`.
- **Values live in the instance `__dict__`, and its order matters.** `__bytes__` packs
  `self.__dict__` values in insertion order. `__post_init__` deliberately deletes and
  re-inserts each key so that this order matches field order (the "kludgy hack" comment).
  Anything that adds instance attributes, or changes when keys are inserted, can silently
  corrupt the packed output.
- **Only fields can be assigned.** `BinmapDataclass.__setattr__` raises
  `BinmapAttributeError` (with `name` and `obj` set, so Python suggests similar fields)
  for any name that isn't a field.
  - Class attributes that handle assignment themselves, such as properties, are still
    allowed.
  - The set of field names is computed once per class in `__init_subclass__`; padding is
    included, so assigning to it stays a silent no-op.
  - Internal code that writes `obj.__dict__` directly bypasses the guard, so it must only
    ever add field names. So do `copy` and `pickle`.
- **Calculated fields** store the function itself in `__dict__`. `__bytes__` calls any
  callable value it finds, and the descriptor's `__get__` calls the function.
- **Validation happens on assignment.** `BinField.__set__` calls
  `BinmapDataclass._check_value`. It looks up the field's struct code stored on the
  class, and checks the value in two steps, so a bad value fails as soon as it's
  assigned, including through the constructor and `frombytes`.
  1. `_check_type()` checks the value's type for its code and raises `BinmapTypeError`:
     integers need `__index__` (so NumPy ints work), floats need `__float__` or
     `__index__`, `?` needs a bool or 0/1, and `c`/`s`/`p` need `bytes`.
  2. A trial `struct.pack` raises `BinmapValueError` for anything that doesn't fit; the
     message keeps struct's text, e.g. `temp: 'B' format requires 0 <= number <= 255`.
  - The trial pack uses the class's byte-order prefix (stored by `__init_subclass__`)
    plus the field's code, just as `bytes()` does. So assignment accepts exactly the
    values `bytes()` can pack, and sizes follow the byte order: standard sizes for `>`
    and `<`, native for `@`.
  - Never validate with a bare code: that uses native sizes (`l` is 8 bytes on 64-bit
    Linux, 4 with `>`). `TestIntegerBounds` checks every integer type's bounds in both
    byte orders.
  - Subclasses that add checks (`StringField`, `EnumField`) must end in
    `super().__set__()`, so the struct check still runs.
- **Enum fields** (`EnumField`) accept a member, a member's name or a number.
  - A name is looked up (unknown: `BinmapValueError`) and stores the *member*.
  - An `int` must be one of the enum's values (`BinmapValueError`) and is stored as
    given; `IntFlag` accepts any combination of bits.
  - Anything else raises `BinmapTypeError`, even a float the enum itself would accept,
    such as `2.0` for a member worth 2.
  - Then the value must fit the field, like any other.
  - The enum class is bound to the descriptor when the class is created.
- **The raw-bytes argument** is the `InitVar` `__binarydata`, name-mangled to
  `_BinmapDataclass__binarydata`. It is the first positional parameter, which is why
  `Cls(b"...")` parses data. Code that iterates fields skips names that start with
  `_BinmapDataclass__`.
- **`frombytes` checks data against the class.**
  - Data that isn't bytes raises `BinmapTypeError`.
  - Data of the wrong size raises `BinmapValueError` ("Record needs 12 bytes of data,
    got 11").
  - Constant, autolength and calculated fields are compared with what the class
    expects, and a mismatch raises `BinmapValueError` naming the field and both values
    ("kind: the data has 22, but the constant is 21").
  - Constants and autolength are checked as they come.
  - Calculated fields are checked only after every other field is assigned, because their
    function may read fields that come later in the struct.
  - It's all-or-nothing: on any error, including an invalid enum value, the instance's
    `__dict__` is restored and the exception re-raised. Keep it that way.
- **Strings are `bytes`.** `string` and `pascalstring` (aliases of `bytes`) and plain
  `bytes`/`str` annotations (codes `s` and `p`) take their size from `stringfield(length)`.
  - They use `StringField`, which rejects values longer than the field holds with
    `BinmapValueError`; `struct` itself would cut them silently. A `string` holds `length`
    bytes, a `pascalstring` `length - 1`, never more than 255.
  - A default that doesn't fit raises `BinmapValueError` when the class is defined.
  - `stringfield()` can't tell the two types apart, so it marks an unspecified default
    (`"autodefault"` metadata) as `length` zero bytes. `__init_subclass__` switches it to
    `b""` for a `pascalstring` *before* calling `dataclasses.dataclass()`, which is when
    defaults are captured.
- **Padding.** The field's default is its byte count. Reading it raises
  `BinmapAttributeError` and writing it is a no-op.
  - It's `repr=False` and `compare=False`, so the generated `__repr__` and `__eq__` never
    read it. Two instances that differ only in the padding bytes they were parsed from
    compare equal, because those bytes aren't kept.
  - Every subclass's `__dataclass_fields__` is replaced by
    `_FieldsWithoutPaddingOnInstances`. Through an instance it returns the fields
    *without* padding, so `dataclasses.asdict()`, `astuple()`, `replace()` and
    `copy.replace()` work and leave padding out. Through the class it returns all fields,
    which subclassing and the struct format need.
  - Inside binmap, use `dataclasses.fields(cls)` or `fields(type(self))` whenever
    padding matters. `fields(self)` skips it.

- **Exceptions.** Everything binmap raises derives from `BinmapError`, and also from
  the matching built-in, so ordinary `except` clauses keep working:

  | Class | Also a | Raised for |
  |---|---|---|
  | `BinmapValueError` | `ValueError`, `struct.error` | a value that doesn't fit, bad data, a bad byteorder or default |
  | `BinmapTypeError` | `TypeError`, `struct.error` | a value of the wrong type, an unsupported field type, two `last` fields |
  | `BinmapAttributeError` | `AttributeError` | an unknown attribute, setting a constant/autolength/calculated field, reading padding |

  - `struct.error` is kept in the hierarchy because binmap raised it before 2.0.
  - Don't let a bare `struct.error`, `KeyError` or `ValueError` from binmap's own code
    escape; wrap it, as `_check_value` and `EnumField` do.
  - Only Python's own errors pass through: the dataclass constructor's `TypeError` for
    unknown keywords, and `NameError` for undefined annotations.
  - Messages name the field and the values involved; tests assert them.

### Adding a new datatype

1. Add an alias in `binmap/types.py`:
   `name: TypeAlias = Annotated[<Python type>, StructCode("<code>")]`. Use the Python
   type that `struct` packs and unpacks for that code, since that's what type checkers
   will show.
2. Add the single-letter alias in `binmap/st.py`.
3. Add a field to `AllDatatypes` in the tests, then update the expected bytes and the
   expected `str()`. For an integer type, add it to `INTEGER_TYPES` as well.

### Types for type checkers and editors

Users' editors (VS Code's Pylance is pyright; PyCharm; mypy) only see the static types,
not what `__init_subclass__` does at runtime. Keep these in place:

- **`@dataclass_transform`** on `BinmapDataclass` tells type checkers that subclasses
  are dataclasses, so they know each constructor.
- **The type aliases are `Annotated`**, so type checkers see `int`, `float`, `bool` or
  `bytes`, and `temp: unsignedchar = 0` type-checks. Don't go back to `NewType`, which
  rejects plain values.
- **The field factories are typed as returning the value the field holds**, like
  `dataclasses.field()` in the standard type stubs, although they return a `Field` at
  runtime.
  - `padding()`/`autolength()` → `int`, `stringfield()` → `bytes`, `enumfield()` →
    `int`, `constant(value: T)` → `T`, and `calculatedfield(function: Callable[[S], T])`
    → `T`.
  - A call then reads as the field's default, and a factory used on a field of the wrong
    type is reported.
  - `constant()` and `autolength()` are also the transform's field specifiers. Their
    `init: Literal[False]` parameter tells type checkers they aren't `__init__`
    arguments, matching runtime.
  - Don't make the other factories field specifiers. Type checkers treat a specifier
    call without `default=` as a required field, which isn't allowed after the inherited
    `__binarydata` (it has a default). As a result, type checkers can't flag a missing
    value for an `enumfield()` without a default, which fails at runtime.
- **`__setattr__` is defined under `if not TYPE_CHECKING:`.** A `__setattr__` that type
  checkers can see tells them any attribute name with any value may be assigned, so
  they'd accept typos like `t.humidty = 5`. Hidden, they check assignments against the
  declared fields; the runtime guard is unchanged. The typing sample keeps a typo in
  `_not_allowed()` to hold this.
- **`py.typed` and `__all__`.** Add new public names to `__all__`: with `py.typed`,
  pyright treats a name that's only imported into the module (like `b_types`) as
  private, and Sphinx autodoc documents only what `__all__` lists.
- **`tests/typecheck/check_usage.py` must stay error-free in both checkers.** Extend it
  when you add public API.
  - Its `assert_type()` calls pin what editors show.
  - The lines in `_not_allowed()` must stay errors. The file enables unused-ignore
    warnings, so an ignore that's no longer needed fails the check.

## Tests

- Use pytest with plain `assert`. The sample classes are defined at module level, or
  inside the test for inheritance cases, and grouped into `Test*` classes per feature.
- Tests check exact packed bytes, exact `str()` output, `dataclasses.asdict` and `astuple`
  results, and **substrings of exception messages**. So exception types and messages count
  as behaviour. If you change one, update the tests and treat it as an API change.
- For every behaviour change, test both directions: packing with `bytes(obj)` and parsing
  with `Cls(b"...")`. Add an inheritance case when the change touches field collection,
  ordering or type lookup. Include negative cases (invalid values must still raise),
  because a validation regression is invisible to tests that only use valid input.
  Existing examples are `TestTempClass::test_value_bounds*`/`test_wrong_*`, the
  inheritance tests in `TestInheritance`, and `TestInvalidClassDefinition`.
- Record known bugs as `@pytest.mark.xfail(raises=..., strict=True, reason=...)` tests
  instead of leaving them untested. With `strict=True`, the fix shows up as a failing
  "XPASS", so whoever fixes the bug has to remove the marker deliberately.
- Error messages from `struct` differ between Python versions (for example, 3.10 and
  older spelled out the `ushort` bound differently). Assert only substrings that are
  stable across the CI matrix, such as `"format requires 0 <= number <="`.
- **README examples are tests.** `tests/test_readme.py` runs every `>>>` example in
  `README.rst` with doctest, so an example's output must match exactly.
  - Exceptions need the doctest form: a `Traceback (most recent call last):` line, a
    `...` line, then the exception line.
  - The examples leave out imports. The test supplies binmap's public names, the type
    names, `IntEnum`, `asdict` and `astuple`; add others there if an example needs them.
  - The README is also the PyPI long description and the docs landing page.

## Code style

- Formatting: **black** (default 88 columns) and **isort** (black-compatible settings in
  `tox.ini`). flake8 runs with `max-line-length = 160` and the `flake8-black`,
  `flake8-isort` and `flake8-builtins` plugins.
- Format the files you change, but don't reformat unrelated code in a feature change.
- Some lint findings are already present. Don't "fix" them as a drive-by:
  - flake8 `A005`: `binmap/types.py` shadows the stdlib `types` module. The module name is
    public API, so don't rename it.
  - flake8 `E721` in `tests/test_binmap.py`.
- Docstrings use reST/Sphinx field lists (`:param x:`, `:return:`, `:raises X:`), because
  autodoc renders them into the published docs.
- **No `Any`.**
  - binmap is checked with `mypy --strict --disallow-any-explicit` and with pyright in
    strict mode (`# pyright: strict` at the top of its modules). The user-code sample
    runs in pyright's default mode, as editors do.
  - Annotate everything, as precisely as the checkers can verify.
  - `object` is the honest type where a value really can be anything. Unlike `Any`, the
    checker then makes you narrow it before use. binmap uses it for:
    - inputs that are being validated (descriptors' `__set__`, `_check_value`);
    - type hints (the precise `typing.TypeForm` needs Python 3.15);
    - field values read back from the instance `__dict__`, which Python types as
      `dict[str, Any]`.
  - Don't narrow those with `cast()` just to look precise. A cast is an unchecked
    promise, and nothing proves what's in `__dict__`: internal code, `copy` and
    `pickle` write it directly, bypassing validation.
  - Use `cast()` (with a comment) only where binmap guarantees the type itself, e.g.
    `Field.default` for padding (`int`) and strings (`bytes`).
  - The two `pyright: ignore`s in `binmap/__init__.py` are intentional:
    - The name-mangled `__binarydata` can't clash with subclass fields and is
      positional-only for type checkers.
    - `BinField.__set__` calls `_check_value`, which sits on the class because only
      there do the mangled `__codes`/`__byteorder` resolve for type checkers.
- **No runtime dependencies.** Keep the package stdlib-only.

## Known issues

These are current bugs or debt, not intended behaviour. Fix them only when asked.

- `dataclasses.fields(SomeClass)` still lists padding, while `fields(instance)`,
  `asdict()` and `astuple()` leave it out. So zipping `fields(SomeClass)` with
  `astuple(obj)` silently misaligns the values, and code that walks the class's fields and
  reads each one from an instance still raises.

## Git, CI and releases

- The default branch is `master`. Work on a branch and open a PR against `master`. History
  uses squash merges (`Subject (#NN)`).
- CI (`pythonpackage.yml`) runs on every push and PR, once for each Python in the matrix.
  It sets up uv and the matrix Python with `astral-sh/setup-uv`
  (`activate-environment: true`), runs `uv pip install -r requirements-dev.txt`, then the
  flake8 hard-fail subset, `mypy binmap` and `python -m pytest -v`. The matrix version
  overrides `.python-version`.
- **Documentation** is published in two places:
  - **Read the Docs** (`.readthedocs.yml`) is the main site, for `master` (latest) and
    release tags (stable): https://binmap.readthedocs.io/.
  - **GitHub Pages:** `docs.yml` builds the docs with `sphinx-build -W` on every push to
    any branch except `dependabot/*` and `gh-pages`. It publishes them to
    https://heman.github.io/binmap/<branch>/, using `.github/scripts/gh-pages.sh` to
    update the `gh-pages` branch, and removes a branch's folder when the branch is
    deleted. Branch builds show the branch name next to the version (`DOCS_BRANCH`).
  - Never edit `gh-pages` by hand; the workflow regenerates its index page.
- Dependabot opens weekly PRs that bump GitHub Actions versions.
- **Releases are maintainer-only.** Agents must not bump versions, create tags or push
  tags.
  - The version lives in `setup.py` and `.bumpversion.cfg`. There is no `__version__`.
  - `uv run bump2version patch|minor|major` updates both files, commits
    `Bump version: X → Y` and tags `vX.Y.Z`. It works on the pinned 3.14, with a
    `DeprecationWarning`. bump2version is unmaintained and does not run on Python 3.15+,
    which is why the pin isn't 3.15.
  - **Pushing any tag** triggers `pythondist.yml`, which builds an sdist only
    (`python setup.py sdist`, with setup-python rather than uv) and uploads it to PyPI
    using the `pypi` repo secret.
