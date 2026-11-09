# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import re
import sys

import sphinx_rtd_theme

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)


# -- Project information -----------------------------------------------------

project = "Binmap"
copyright = "2020, Jimmy Hedman"
author = "Jimmy Hedman"

# The package version, from setup.py, where bump2version keeps it.
with open(os.path.join(ROOT, "setup.py"), encoding="utf-8") as setup_py:
    release = re.search(r'version="([^"]+)"', setup_py.read()).group(1)
version = release
# The GitHub Pages workflow (.github/workflows/docs.yml) builds every branch
# and sets DOCS_BRANCH, so those pages say which branch they document.
if os.environ.get("DOCS_BRANCH"):
    version = release = f"{release} ({os.environ['DOCS_BRANCH']} branch)"


# -- General configuration ---------------------------------------------------
master_doc = "index"

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx_rtd_theme",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_rtd_theme"
