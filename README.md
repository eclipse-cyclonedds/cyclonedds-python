[![License](https://img.shields.io/badge/License-EPL%202.0-blue)](https://choosealicense.com/licenses/epl-2.0/)
[![License](https://img.shields.io/badge/License-EDL%201.0-blue)](https://choosealicense.com/licenses/edl-1.0/)

# Python binding for Eclipse Cyclone DDS

A **work in progress** Python binding for [Eclipse Cyclone DDS][1].

# Getting Started

Eclipse CycloneDDS Python requires Python version 3.6 or higher. It can be installed [with included Cyclone DDS binaries](#installing-with-pre-built-binaries) or leveraging an existing Cyclone DDS installation by [installing from source](#installing-from-source).

## Installing with pre-built Cyclone DDS binaries

This is the most straightforward method to install Cyclone DDS Python, but there are a couple of caveats. The pre-built package:
 * does not include the Cyclone DDS IDL compiler,
 * has no support for DDS Security,
 * has no support for shared memory via Iceoryx,
 * comes with generic Cyclone DDS binaries that are not optimized per-platform.

If these are of concern, proceed with an [installation from source](#installing-from-source). If not, running this installation is as simple as:

    $ pip install cyclonedds


If you get permission errors you are using your system python. This is not recommended, we recommend using [a virtual environment][2], [poetry][3], [pipenv][4] or [pyenv][5]. If you _just_ want to get going, you can add `--user` to your pip command to install for the current user. See the [Installing Python Modules][6] Python documentation.

## Installing from source

When installing from source you can make use of the full list of features offered by [Cyclone DDS][1]. First install [Cyclone DDS][1] as normal. Then continue by setting the `CYCLONEDDS_HOME` environment variable to the installation location of [Cyclone DDS][1], which is the same as what was used for `CMAKE_INSTALL_PREFIX`. You will have to have this variable active any time you run Python code that depends on `cyclonedds` so adding it to `.bashrc` on Linux, `~/bash_profile` on MacOS or the System Variables in Windows can be helpful. This also allows you to switch, move or update [Cyclone DDS][1] without recompiling the Python package.

You can either install the source from the latest release from pypi:

    $ export CYCLONEDDS_HOME="/path/to/cyclone"
    $ pip install cyclonedds --no-binary :all:

or you can download the code from this repository to get the bleeding edge and directly install from your local filesystem:

    $ git clone https://github.com/eclipse-cyclonedds/cyclonedds-python
    $ cd cyclonedds-python
    $ export CYCLONEDDS_HOME="/path/to/cyclone"
    $ pip install ./src/pycdr
    $ pip install ./src/cyclonedds

If you get permission errors you are using your system python. This is not recommended, we recommend using [a virtual environment][2], [poetry][3], [pipenv][4] or [pyenv][5]. If you _just_ want to get going, you can add `--user` to your pip command to install for the current user. See the [Installing Python Modules][6] Python documentation.

[1]: https://github.com/eclipse-cyclonedds/cyclonedds/
[2]: https://docs.python.org/3/tutorial/venv.html
[3]: https://python-poetry.org/
[4]: https://pipenv.pypa.io/en/latest/
[5]: https://github.com/pyenv/pyenv
[6]: https://docs.python.org/3/installing/index.html


# Installing the Python backend for the IDL compiler

The code for the Python backend for the IDL compiler is contained in `src/idlpy` and builds like any other cmake project:

    $ git clone https://github.com/eclipse-cyclonedds/cyclonedds-python
    $ cd cyclonedds-python/src/idlpy
    $ mkdir build
    $ cmake -DCMAKE_INSTALL_PREFIX=<install-location> \
            -DCMAKE_PREFIX_PATH="<cyclonedds-install-location>" \
            ..
    $ cmake --build .
    $ cmake --build . --target install

For more details on this process take a look at the [Eclipse Cyclone DDS C++ repository][7] which explains the cmake process in depth.

[7]: https://github.com/eclipse-cyclonedds/cyclonedds-cxx/
