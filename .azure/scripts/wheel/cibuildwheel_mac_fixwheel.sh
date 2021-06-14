#!/bin/bash
set -e -x

DESTINATION=$1
WHEEL=$2
DELOCATE_ARCHS=$3

# Unpack the wheel
wheel unpack -d temp $WHEEL

# Get the wheel directory
files=(temp/*)
UNWHEEL="${files[0]}"
files=($UNWHEEL/cyclonedds/_clayer*)
DYLIB="${files[0]}"

# Strip out the rpath
install_name_tool -change @rpath/libddsc.0.dylib $CYCLONEDDS_HOME/lib/libddsc.dylib $DYLIB

# Remove old wheel and repackage
rm $WHEEL
wheel pack -d $(dirname $WHEEL) $UNWHEEL
rm -rf temp

# Run delocate to pull in ddsc
delocate-listdeps $WHEEL
delocate-wheel -v --require-archs $DELOCATE_ARCHS -w $DESTINATION $WHEEL
