from os import path

from setuptools import find_packages, setup

this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, "README.rst")) as f:
    long_description = f.read()

setup(
    name="binmap",
    version="1.2.1",
    author="Jimmy Hedman",
    author_email="jimmy.hedman@gmail.com",
    description="A base class for creating binary parsing and packing classes",
    long_description=long_description,
    long_description_content_type="text/x-rst",
    url="https://github.com/HeMan/binmap",
    packages=find_packages(include=["binmap", "binmap.*"]),
    package_data={"binmap": ["py.typed"]},
    python_requires=">=3.11",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: 3.14",
        "Programming Language :: Python :: 3.15",
    ],
)
