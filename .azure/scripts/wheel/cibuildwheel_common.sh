#!/bin/bash
set -e -x

WHEEL_SH_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
export REPO_HOME="$WHEEL_SH_DIR/../../.."
export COMMON_CMAKE_OPTS="-DBUILD_IDLC=0 -DBUILD_SCHEMA=0 -DENABLE_SHM=0 -DENABLE_SSL=0 -DENABLE_SECURITY=0 -DENABLE_TOPIC_DISCOVERY=1 -DENABLE_TYPE_DISCOVERY=1"

export CIBW_SKIP="pp*"  # No PyPy builds

# Run testing with pytest after each wheel build
export CIBW_TEST_REQUIRES="pytest pytest-cov pytest-mock"
export CIBW_TEST_COMMAND="pytest {package}/tests"

# We can crosscompile for Apple Silicon ARM-based macs
# But they are not actually available to run on
# So these wheels cannot be tested in CI
export CIBW_TEST_SKIP="*-macosx_arm64 *-macosx_universal2:arm64"
