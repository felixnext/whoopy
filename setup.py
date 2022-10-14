import os
from setuptools import setup
from setuptools import find_packages
from whoopy import __version__
import pathlib


__status__ = "Package"
__copyright__ = "Copyright 2022"
__license__ = "MIT License"
__author__ = "Felix Geilert"


this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, "readme.md"), encoding="utf-8") as f:
    long_description = f.read()


def versions_in_requirements(file):
    lines = file.read().splitlines()
    versions = [line for line in lines if not line.isspace() and "--" not in line]
    return list(versions)


HERE = pathlib.Path(__file__).parent
with open(HERE / "requirements.txt") as f:
    required_list = versions_in_requirements(f)

setup(
    name="whoopy",
    version=__version__,
    description="Unofficial Client for the Whoop API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    keywords="whoop api",
    url="https://github.com/felixnext/whoopy",
    download_url=f"https://github.com/felixnext/whoopy/releases/tag/v{__version__}",
    author="Felix Geilert",
    license="MIT License",
    packages=find_packages(include=["whoopy", "whoopy.*"]),
    install_requires=required_list,
    setup_requires=["pytest-runner", "flake8"],
    tests_require=["pytest"],
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        "Development Status :: 4 - Beta",  # Chose either "3 - Alpha", "4 - Beta" or "5 - Production/Stable" as the current state of your package
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
)
