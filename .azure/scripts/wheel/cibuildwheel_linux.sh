#!/bin/bash
set -e -x

WHEEL_SH_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
source "$WHEEL_SH_DIR/cibuildwheel_common.sh"

export CIBW_MANYLINUX_X86_64_IMAGE=manylinux2014
export CIBW_MANYLINUX_I686_IMAGE=manylinux2014
export CIBW_REPAIR_WHEEL_COMMAND="auditwheel repair -w {dest_dir} {wheel}"

CIBW_BEFORE_ALL="git clone https://github.com/eclipse-cyclonedds/cyclonedds.git main && "
CIBW_BEFORE_ALL+="mkdir -p build /project/install && cd build && "
CIBW_BEFORE_ALL+="cmake ../main -DCMAKE_INSTALL_PREFIX=/project/install $COMMON_CMAKE_OPTS && "
CIBW_BEFORE_ALL+="cmake --build . --target install"

CIBW_ENVIRONMENT="CYCLONEDDS_HOME=/project/install "
CIBW_ENVIRONMENT+="LIBRARY_PATH=/project/install/lib:/project/install/lib64 "
CIBW_ENVIRONMENT+="LD_LIBRARY_PATH=/project/install/lib:/project/install/lib64"

export CIBW_BEFORE_ALL
export CIBW_ENVIRONMENT

export CIBW_BEFORE_TEST="pip install /host/$REPO_HOME/src/pycdr"
