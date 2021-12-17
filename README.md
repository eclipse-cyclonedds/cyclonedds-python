[![License](https://img.shields.io/badge/License-EPL%202.0-blue)](https://choosealicense.com/licenses/epl-2.0/)
[![License](https://img.shields.io/badge/License-EDL%201.0-blue)](https://choosealicense.com/licenses/edl-1.0/)

# Python binding for Eclipse Cyclone DDS

A **work in progress** Python binding for [Eclipse Cyclone DDS][1].

# Getting Started

Eclipse CycloneDDS Python requires Python version 3.7 or higher. You can install it directly from the git repo with pip or clone the git repo first and then install locally. When it is released it will be installable [with included Cyclone DDS binaries](#installing-with-pre-built-binaries) or leveraging an existing Cyclone DDS installation by [installing from source](#installing-from-source) via PyPi.


## Installing from source via git

To install CycloneDDS Python you will have to install [Cyclone DDS][1] first. Then set appropriate environment variables and install with pip. A full example installation of the quickest way to get started is shown below:

```bash
$ git clone https://github.com/eclipse-cyclonedds/cyclonedds
$ cd cyclonedds && mkdir build install && cd build
$ cmake .. -DCMAKE_INSTALL_PREFIX=../install
$ cmake --build . --target install
$ cd ..
$ export CYCLONEDDS_HOME="$(pwd)/install"
$ pip3 install --user git+https://github.com/eclipse-cyclonedds/cyclonedds-python
```

If you want to install with development tools add the `[dev]` component to your installation like so:

```bash
$ pip3 install --user "cyclonedds[dev] @ git+https://github.com/eclipse-cyclonedds/cyclonedds-python"
```

Installation from a local git clone:

```bash
$ cd /path/to/git/clone
$ pip3 install --user .
# or for development:
$ pip3 install --user .[dev]
# or for documentation generation
$ pip3 install --user .[docs]
```

While the quickest way to get going is the `--user` flag it is not the recommended, we recommend using [a virtual environment][2], [poetry][3], [pipenv][4] or [pyenv][5]. After the installation is complete `import cyclonedds` should now work. The `CYCLONEDDS_HOME` variable is essential for the Python backend to locate the CycloneDDS binaries so this always needs to be set when running Python code with Cyclone DDS. Have a look at the [examples](examples/) to learn about how to use the Python API.

You can also run the idl compiler in Python mode if it the Python package is installed. Simply run `idlc -l py file.idl` and a Python module with your types will be generated in the current working directory. If you wish to nest the resulting Python module inside an existing package you can specify the path from the intended root. So if you have a package 'wubble' with a submodule 'fruzzy' and want the generated modules and types under there you can do `idlc -l py -p py-root-prefix=wubble.fruzzy file.idl`.

## When released: Installing with pre-built Cyclone DDS binaries

⚠️ As long as this is unreleased this method is not yet available, please refer to the installation from source via git. ⚠️

This is the most straightforward method to install Cyclone DDS Python, but there are a couple of caveats. The pre-built package:
 * has no support for DDS Security,
 * has no support for shared memory via Iceoryx,
 * comes with generic Cyclone DDS binaries that are not optimized per-platform.

If these are of concern, proceed with an [installation from source](#installing-from-source). If not, running this installation is as simple as:

    $ pip install cyclonedds


If you get permission errors you are using your system python. This is not recommended, we recommend using [a virtual environment][2], [poetry][3], [pipenv][4] or [pyenv][5]. If you _just_ want to get going, you can add `--user` to your pip command to install for the current user. See the [Installing Python Modules][6] Python documentation.


## When released: Installing from source via PyPi

⚠️ As long as this is unreleased this method is not yet available, please refer to the installation from source via git. ⚠️

When installing from source you can make use of the full list of features offered by [Cyclone DDS][1]. First install [Cyclone DDS][1] as normal. Then continue by setting the `CYCLONEDDS_HOME` environment variable to the installation location of [Cyclone DDS][1], which is the same as what was used for `CMAKE_INSTALL_PREFIX`. You will have to have this variable active any time you run Python code that depends on `cyclonedds` so adding it to `.bashrc` on Linux, `~/bash_profile` on MacOS or the System Variables in Windows can be helpful. This also allows you to switch, move or update [Cyclone DDS][1] without recompiling the Python package.

You can either install the source from the latest release from pypi (not yet available):

    $ CMAKE_PREFIX_PATH="/path/to/cyclone" pip install cyclonedds --no-binary cyclonedds

or you can download the code from this repository to get the bleeding edge and directly install from your local filesystem:

    $ CMAKE_PREFIX_PATH="/path/to/cyclone" pip install git+https://github.com/eclipse-cyclonedds/cyclonedds-python

If you get permission errors you are using your system python. This is not recommended, we recommend using [a virtual environment][2], [poetry][3], [pipenv][4] or [pyenv][5]. If you _just_ want to get going, you can add `--user` to your pip command to install for the current user. See the [Installing Python Modules][6] Python documentation.

[1]: https://github.com/eclipse-cyclonedds/cyclonedds/
[2]: https://docs.python.org/3/tutorial/venv.html
[3]: https://python-poetry.org/
[4]: https://pipenv.pypa.io/en/latest/
[5]: https://github.com/pyenv/pyenv
[6]: https://docs.python.org/3/installing/index.html
