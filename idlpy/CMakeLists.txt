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

add_library(
  idlpy SHARED
    src/context.c
    src/generator.c
    src/naming.c
    src/types.c
    src/util.c
    src/ssos.c
)

target_include_directories(
  idlpy
  PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/src>
    $<BUILD_INTERFACE:${CMAKE_CURRENT_BINARY_DIR}/include>)

target_link_libraries(idlpy PUBLIC CycloneDDS::idl)

install(
  TARGETS idlpy
  LIBRARY DESTINATION cyclonedds/.libs
)

if (DEFINED CIBUILDWHEEL AND "${CIBUILDWHEEL}")
  # We are building a wheel! Include idl lib and idlc in package
  install(IMPORTED_RUNTIME_ARTIFACTS
    CycloneDDS::idl
    LIBRARY DESTINATION cyclonedds/.libs
    RUNTIME DESTINATION cyclonedds/.bin
  )
  install(IMPORTED_RUNTIME_ARTIFACTS
    CycloneDDS::idlc
    LIBRARY DESTINATION cyclonedds/.libs
    RUNTIME DESTINATION cyclonedds/.bin
  )
endif()