[![License](https://img.shields.io/badge/License-EPL%202.0-blue)](https://choosealicense.com/licenses/epl-2.0/)
[![License](https://img.shields.io/badge/License-EDL%201.0-blue)](https://choosealicense.com/licenses/edl-1.0/)

# Python binding for Eclipse Cyclone DDS

A **work in progress** Python binding for [Eclipse Cyclone DDS][1].

[1]: https://github.com/eclipse-cyclonedds/cyclonedds/

# Getting Started

First, get a python and pip installation of a sufficiently high version (3.6+). Next, you'll need to have CycloneDDS installed on your system. Set a CYCLONEDDS_HOME environment variable to your installation directory. You can then install PyCDR and CDDS as contained in this repo:

```bash
$ cd src
$ pip install ./pycdr
$ pip install ./cyclonedds
```

If you get permission errors you are using your system python. This is not recommended, please use a [virtualenv](https://docs.python.org/3/tutorial/venv.html) or use something like pipenv/pyenv/poetry.

You can now run examples or work in an interactive notebook with jupyter:

```bash
$ pip install jupyterlab
$ jupyter-lab
```
