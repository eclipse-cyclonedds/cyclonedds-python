[![License](https://img.shields.io/badge/License-EPL%202.0-blue)](https://choosealicense.com/licenses/epl-2.0/)
[![License](https://img.shields.io/badge/License-EDL%201.0-blue)](https://choosealicense.com/licenses/edl-1.0/)
[![Website](https://img.shields.io/badge/web-cyclonedds.io-blue)](https://cyclonedds.io)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/cyclonedds)](https://pypi.org/project/cyclonedds/)
[![PyPI](https://img.shields.io/pypi/v/cyclonedds)](https://pypi.org/project/cyclonedds/)
[![Community](https://img.shields.io/badge/discord-join%20community-5865f2)](https://discord.gg/BkRYQPpZVV)

# Python binding for Eclipse Cyclone DDS

A Python binding for [Eclipse Cyclone DDS][1].

# Getting Started

Eclipse CycloneDDS Python requires Python version 3.7 or higher. You can install [with included Cyclone DDS binaries](#installing-with-pre-built-binaries) or leveraging an existing Cyclone DDS installation by [installing from source](#installing-from-source) via PyPi.

<!----><a name="installing-with-pre-built-binaries"></a>
## Installing with pre-built Cyclone DDS binaries

This is the most straightforward method to install Cyclone DDS Python, but there are a couple of caveats. The pre-built package:
 * has no support for DDS Security,
 * has no support for shared memory via Iceoryx,
 * comes with generic Cyclone DDS binaries that are not optimized per-platform.

If these are of concern, proceed with an [installation from source](#installing-from-source). If not, running this installation is as simple as:

```bash
    $ pip install cyclonedds
```

<!----><a name="installing-from-source"></a>
## Installing from source

When installing from source you can make use of the full list of features offered by [Cyclone DDS][1]. First install [Cyclone DDS][1] as normal. Then continue by setting the `CYCLONEDDS_HOME` environment variable to the installation location of [Cyclone DDS][1], which is the same as what was used for `CMAKE_INSTALL_PREFIX`. You will have to have this variable active any time you run Python code that depends on `cyclonedds` so adding it to `.bashrc` on Linux, `~/bash_profile` on MacOS or the System Variables in Windows can be helpful. This also allows you to switch, move or update [Cyclone DDS][1] without recompiling the Python package.

<!----><a name="installing-from-source-via-pypi"></a>
### via PyPi

You can install the source from the latest release from [Pypi](https://pypi.org/project/cyclonedds/), or use a tag to get a specific version. A full example (for linux) is shown below

```bash
$ git clone https://github.com/eclipse-cyclonedds/cyclonedds
$ cd cyclonedds && mkdir build install && cd build
$ cmake .. -DENABLE_TOPIC_DISCOVERY=YES -DENABLE_TYPE_DISCOVERY=YES -DCMAKE_INSTALL_PREFIX=../install
$ cmake --build . --target install
$ cd ..
$ export CYCLONEDDS_HOME="$(pwd)/install"
$ pip3 install cyclonedds --no-binary cyclonedds
```

<!----><a name="installing-from-source-via-git"></a>
### via git

A full example installation of the quickest way to get started via git is shown below:

```bash
$ git clone https://github.com/eclipse-cyclonedds/cyclonedds
$ cd cyclonedds && mkdir build install && cd build
$ cmake .. -DENABLE_TOPIC_DISCOVERY=YES -DENABLE_TYPE_DISCOVERY=YES -DCMAKE_INSTALL_PREFIX=../install
$ cmake --build . --target install
$ cd ..
$ export CYCLONEDDS_HOME="$(pwd)/install"
$ pip3 install git+https://github.com/eclipse-cyclonedds/cyclonedds-python
```

# Command line tooling

The Python package contains a suite of command line tools, all nested under the main entrypoint `cyclonedds`. The main help screen shows the commands available:

![`cyclonedds --help`](docs/source/static/images/cyclonedds-help.svg)

## `cyclonedds ls`

![`cyclonedds ls --help`](docs/source/static/images/cyclonedds-ls-help.svg)

The `ls` subcommand shows you the entities in your DDS system and their QoS settings. For example, here is the output when running the `Vehicle` example from this repo in the background:

![`cyclonedds ls --suppress-progress-bar --force-color-mode`](docs/source/static/images/cyclonedds-ls-demo.svg)

## `cyclonedds ps`

![`cyclonedds ps --help`](docs/source/static/images/cyclonedds-ps-help.svg)

The `ps` subcommand shows you the applications in your DDS system. Note that this depends on so called 'Participant Properties', tactfully named QoS properties in DDS participants. These were merged into CycloneDDS for version 0.10.0. Here is an example of the output when running the `Vehicle` example from this repo in the background on a single host:

![`cyclonedds ps --suppress-progress-bar --force-color-mode`](docs/source/static/images/cyclonedds-ps-demo.svg)

## `cyclonedds typeof`

![`cyclonedds typeof --help`](docs/source/static/images/cyclonedds-typeof-help.svg)

The `typeof` subcommand shows you the type(s) of a topic in your system. With XTypes it can happen that more than one type for each topic exists and that they are still compatible. The types are represented in IDL. Here is an example of the output when running the `Vehicle` example:

![`cyclonedds typeof Vehicle --suppress-progress-bar --force-color-mode`](docs/source/static/images/cyclonedds-typeof-demo.svg)

## `cyclonedds subscribe`

![`cyclonedds subscribe --help`](docs/source/static/images/cyclonedds-subscribe-help.svg)

The `subscribe` subcommand dynamically subscribes to a topic and shows you the data as it arrives. The type is discovered in a similar manner as `typeof`. Here is an example of the output when running the `Vehicle` example:

![`timeout -s INT 10s cyclonedds subscribe Vehicle --suppress-progress-bar --force-color-mode`](docs/source/static/images/cyclonedds-subscribe-demo.svg)

## `cyclonedds performance`

![`cyclonedds performance --help`](docs/source/static/images/cyclonedds-performance-help.svg)

The `cyclonedds` subcommand is a nicer frontend to `ddsperf` with four modes: `publish`, `subscribe`, `ping` and `pong`. The below performance run example is the `subscribe` mode rendered with `cyclonedds performance publish` running in the background.

![`cyclonedds performance --duration 21s --render-output-once-on-exit --force-color-mode subscribe --triggering-mode waitset`](docs/source/static/images/cyclonedds-performance-subscribe-demo.svg)

# Extra dependencies

The `cyclonedds` package defines two sets of optional dependencies, `dev` and `docs`, used for developing `cyclonedds` and building the documentation, respectively. If you want to install with development tools add the component to your installation, for example:

```bash
$ pip3 install --user "cyclonedds[dev] @ git+https://github.com/eclipse-cyclonedds/cyclonedds-python"
```

Or when installing from a local git clone, which is recommended when developing or building the docs:

```bash
$ cd /path/to/git/clone
# for development:
$ pip3 install --user ".[dev]"
# for documentation generation
$ pip3 install --user ".[docs]"
# or for both
$ pip3 install --user ".[dev,docs]"
```

For more information see [the packaging guide information on optional dependencies][2].

# IDL compiler

You can also run the idl compiler in Python mode if it the Python package is installed. Simply run `idlc -l py file.idl` and a Python module with your types will be generated in the current working directory. If you wish to nest the resulting Python module inside an existing package you can specify the path from the intended root. So if you have a package 'wubble' with a submodule 'fruzzy' and want the generated modules and types under there you can do `idlc -l py -p py-root-prefix=wubble.fruzzy file.idl`.


[1]: https://github.com/eclipse-cyclonedds/cyclonedds/#eclipse-cyclone-dds
[2]: https://setuptools.pypa.io/en/latest/userguide/dependency_management.html#optional-dependencies
