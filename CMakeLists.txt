#
# Copyright(c) 2021 ADLINK Technology Limited and others
#
# This program and the accompanying materials are made available under the
# terms of the Eclipse Public License v. 2.0 which is available at
# http://www.eclipse.org/legal/epl-2.0, or the Eclipse Distribution License
# v. 1.0 which is available at
# http://www.eclipse.org/org/documents/edl-v10.php.
#
# SPDX-License-Identifier: EPL-2.0 OR BSD-3-Clause
#
cmake_minimum_required(VERSION 3.18)
# CMAKE_PREFIX_PATH environment variable is available in CMake >= 3.18
project(clayer LANGUAGES C)
find_package(PythonExtensions REQUIRED)
find_package(CycloneDDS REQUIRED)

# Set reasonably strict warning options for Clang, GCC and Visual Studio
if(CMAKE_C_COMPILER_ID STREQUAL "Clang" OR
   CMAKE_C_COMPILER_ID STREQUAL "AppleClang")
  add_compile_options(-Wall -Wextra -Wconversion -Wmissing-prototypes -Wunused
                      -Winfinite-recursion -Wassign-enum -Wcomma -Wshadow
                      -Wstrict-prototypes -Wconditional-uninitialized)
elseif(CMAKE_C_COMPILER_ID STREQUAL "GNU")
  add_compile_options(-Wall -Wextra -Wconversion -Wmissing-prototypes -Wpedantic --pedantic-errors)
elseif(CMAKE_C_COMPILER_ID STREQUAL "MSVC")
  add_compile_options(/W3)
endif()

# Build python c layer
add_library(_clayer MODULE clayer/cdrkeyvm.c clayer/pysertype.c)
target_link_libraries(_clayer CycloneDDS::ddsc)
python_extension_module(_clayer)
install(
  TARGETS _clayer
  LIBRARY DESTINATION cyclonedds)


# Build idl python backend
if (TARGET CycloneDDS::idl)
  add_subdirectory(idlpy)
endif()
