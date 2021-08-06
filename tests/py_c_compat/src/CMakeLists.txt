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

cmake_policy(SET CMP0060 NEW)

idlc_generate(TARGET pyccompat_lib FILES py_c_compat.idl $ENV{FUZZY_LOCATION})

add_custom_command(
    OUTPUT   "${CMAKE_CURRENT_BINARY_DIR}/fuzzymod"
    COMMAND  CycloneDDS::idlc "-l" $ENV{IDLPY} $ENV{FUZZY_LOCATION}
    DEPENDS  $ENV{FUZZY_LOCATION} CycloneDDS::idlc)
add_custom_target(pyccompat_fuzzy DEPENDS "${CMAKE_CURRENT_BINARY_DIR}/fuzzymod")

get_filename_component(_fuzzy $ENV{FUZZY_LOCATION} NAME_WE)
file(WRITE ${CMAKE_CURRENT_BINARY_DIR}/fuzzy_type_support.h "#ifndef FUZZY_TYPE_SUPPORT_H\n")
file(APPEND ${CMAKE_CURRENT_BINARY_DIR}/fuzzy_type_support.h "#define FUZZY_TYPE_SUPPORT_H\n\n")
file(APPEND ${CMAKE_CURRENT_BINARY_DIR}/fuzzy_type_support.h "#include \"${_fuzzy}.h\"\n")
file(APPEND ${CMAKE_CURRENT_BINARY_DIR}/fuzzy_type_support.h "#include \"dds/dds.h\"\n\n")
file(APPEND ${CMAKE_CURRENT_BINARY_DIR}/fuzzy_type_support.h "static const struct { const char* name; const dds_topic_descriptor_t* descriptor} fuzzy_descriptors[] = {\n")

set(COUNTER 0)
foreach(_type $ENV{FUZZY_TYPES})
    MATH(EXPR COUNTER "${COUNTER}+1")
    file(APPEND ${CMAKE_CURRENT_BINARY_DIR}/fuzzy_type_support.h "\t{\"${_type}\", &fuzzymod_${_type}_desc},\n")
endforeach()

file(APPEND ${CMAKE_CURRENT_BINARY_DIR}/fuzzy_type_support.h "};\n\nstatic const unsigned long long fuzzy_descriptors_size = ${COUNTER};\n\n")
file(APPEND ${CMAKE_CURRENT_BINARY_DIR}/fuzzy_type_support.h "#endif\n")

add_executable(republisher republisher.c)
add_dependencies(republisher pyccompat_fuzzy)
target_link_libraries(republisher pyccompat_lib CycloneDDS::ddsc)

install(TARGETS republisher DESTINATION bin)
install(DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/fuzzymod" DESTINATION lib/site-packages/)