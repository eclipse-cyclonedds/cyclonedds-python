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

Documentation can be found on the [cyclonedds.io](https://cyclonedds.io/docs/) website: [Python API docs][3]

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

You can also use the nightly build stream instead, which is built from the `master` branches of `cyclonedds` and `cyclonedds-python`. This will always get you the latest and greatest, but less stable version that might contain API breaks.

```bash
    $ pip install cyclonedds-nightly
```

<!----><a name="installing-from-source"></a>
## Installing from source

When installing from source you can make use of the full list of features offered by [Cyclone DDS][1]. First install [Cyclone DDS][1] as normal. Then continue by setting the `CYCLONEDDS_HOME` environment variable to the installation location of [Cyclone DDS][1], which is the same as what was used for `CMAKE_INSTALL_PREFIX`. You will have to have this variable active any time you run Python code that depends on `cyclonedds` so adding it to `.bashrc` on Linux, `~/bash_profile` on MacOS or the System Variables in Windows can be helpful. This also allows you to switch, move or update [Cyclone DDS][1] without recompiling the Python package.

You'll need the Python development headers to complete the install. If using `apt`, try `sudo apt install python3-dev`. For other distributions, see [this comment](https://stackoverflow.com/a/21530768).

<!----><a name="installing-from-source-via-pypi"></a>
### via PyPi

You can install the source from the latest release from [Pypi](https://pypi.org/project/cyclonedds/), or use a tag to get a specific version. A full example (for linux) is shown below

```bash
$ git clone https://github.com/eclipse-cyclonedds/cyclonedds
$ cd cyclonedds && mkdir build install && cd build
$ cmake .. -DCMAKE_INSTALL_PREFIX=../install
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
$ cmake .. -DCMAKE_INSTALL_PREFIX=../install
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

## `cyclonedds publish`

![`cyclonedds publish --help`](docs/source/static/images/cyclonedds-publish-help.svg)

The `publish` subcommand dynamically builds a REPL with datatypes and a writer for a topic and shows you the data as it arrives. The type is discovered in a similar manner as `typeof`.

## `cyclonedds performance`

![`cyclonedds performance --help`](docs/source/static/images/cyclonedds-performance-help.svg)

The `performance` subcommand is a nicer frontend to `ddsperf` with four modes: `publish`, `subscribe`, `ping` and `pong`. The below performance run example is the `cyclonedds performance subscribe` mode rendered with `cyclonedds performance publish` running in the background.

![`cyclonedds performance --duration 21s --render-output-once-on-exit --force-color-mode subscribe --triggering-mode waitset`](docs/source/static/images/cyclonedds-performance-subscribe-demo.svg)

# Contributing

We very much welcome all contributions to the project, whether that is questions, examples, bug
fixes, enhancements or improvements to the documentation, or anything else really.
When considering contributing code, it might be good to know that build configurations for Azure pipelines are present in the repository and that there is a test suite using pytest, along with flake8 code linting, and documentation built with sphinx. Be sure to install with the [Extra dependencies](#extra-dependencies) if you're going to run tests, lints or build the docs.

You can run the test suite and linting using the [local-ci.py](local-ci.py) script in this repo.
```bash
$ python local-ci.py
```

Or lint a single file/directory (as the whole repo can be a little noisey) using:
```bash
$ python -m flake8 path/to/some_file.py
```

You can build and serve the documentation (at http://localhost:8000/) using:
```bash
cd docs
python -m sphinx source/ _build/
# Serve the HTML files to view at localhost:8000
python -m http.server -d _build
```

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

[1]: https://github.com/eclipse-cyclonedds/cyclonedds/#eclipse-cyclone-dds
[2]: https://setuptools.pypa.io/en/latest/userguide/dependency_management.html#optional-dependencies
[3]: https://cyclonedds.io/docs/cyclonedds-python/latest/

# PyOxidizer build

You can build a self-contained binary of the `cyclonedds` CLI tool using PyOxidizer. It should be as simple as:

```bash
$ cd /path/to/git/clone
$ pip3 install --user pyoxidizer
$ pyoxidizer build
```
