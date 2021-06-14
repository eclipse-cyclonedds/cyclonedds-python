#!/bin/bash
set -e -x

WHEEL_SH_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
source "$WHEEL_SH_DIR/cibuildwheel_common.sh"

WINPATH_REPO_HOME="$BUILD_REPOSITORY_LOCALPATH"
export CYCLONEDDS_HOME="$WINPATH_REPO_HOME\install"

export CIBW_ARCHS_WINDOWS=auto32
export CIBW_BEFORE_BUILD="pip install delvewheel==0.0.12"
export CIBW_REPAIR_WHEEL_COMMAND="delvewheel repair -w {dest_dir} --no-mangle-all {wheel}"

CIBW_BEFORE_ALL="git clone https://github.com/eclipse-cyclonedds/cyclonedds.git main && "
CIBW_BEFORE_ALL+="mkdir -p build $CYCLONEDDS_HOME && cd build && "
CIBW_BEFORE_ALL+="cmake ../main -DCMAKE_INSTALL_PREFIX=$CYCLONEDDS_HOME $COMMON_CMAKE_OPTS -A \"Win32\" && "
CIBW_BEFORE_ALL+="cmake --build . --target install"

CIBW_ENVIRONMENT="PATH=\"\$PATH;${CYCLONEDDS_HOME//$'\\'/'\\'}\\\\lib;${CYCLONEDDS_HOME//$'\\'/'\\'}\\\\bin\" "
CIBW_ENVIRONMENT+="CYCLONEDDS_HOME=\"${CYCLONEDDS_HOME//$'\\'/'\\'}\""

export CIBW_BEFORE_ALL
export CIBW_ENVIRONMENT

export CIBW_BEFORE_TEST="pip install $WINPATH_REPO_HOME\\src\\pycdr"
