#!/bin/bash
set -e -x

WHEEL_SH_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
source "$WHEEL_SH_DIR/cibuildwheel_common.sh"

chmod +x "$WHEEL_SH_DIR/cibuildwheel_mac_fixwheel.sh"
export CYCLONEDDS_HOME="$REPO_HOME/install"

export CIBW_ARCHS_MACOS=arm64
export CIBW_REPAIR_WHEEL_COMMAND="$WHEEL_SH_DIR/cibuildwheel_mac_fixwheel.sh {dest_dir} {wheel} {delocate_archs}"

CIBW_BEFORE_ALL="git clone https://github.com/eclipse-cyclonedds/cyclonedds.git main && "
CIBW_BEFORE_ALL+="mkdir -p build $CYCLONEDDS_HOME && cd build && "
CIBW_BEFORE_ALL+="cmake ../main -DCMAKE_INSTALL_PREFIX=$CYCLONEDDS_HOME $COMMON_CMAKE_OPTS -DCMAKE_OSX_ARCHITECTURES='x86_64;arm64' && "
CIBW_BEFORE_ALL+="cmake --build . --target install"

CIBW_ENVIRONMENT="CYCLONEDDS_HOME=$CYCLONEDDS_HOME "
CIBW_ENVIRONMENT+="DYLD_FALLBACK_LIBRARY_PATH=$CYCLONEDDS_HOME/lib"

export CIBW_BEFORE_ALL
export CIBW_ENVIRONMENT
