from setuptools import find_packages, setup

setup(
    name="binmap",
    version="1.0.0",
    author="Jimmy Hedman",
    author_email="jimmy.hedman@gmail.com",
    description="A base class for creating binary parsing and packing classes",
    url="https://github.com/HeMan/binmap",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
)
