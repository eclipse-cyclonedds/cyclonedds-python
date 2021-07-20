cmake_minimum_required(VERSION 3.18)
# CMAKE_PREFIX_PATH environment variable is available in CMake >= 3.18
project(_clayer LANGUAGES C)
find_package(PythonExtensions REQUIRED)
find_package(CycloneDDS REQUIRED)

# Set reasonably strict warning options for Clang, GCC and Visual Studio
if(CMAKE_C_COMPILER_ID STREQUAL "Clang" OR
   CMAKE_C_COMPILER_ID STREQUAL "AppleClang")
  add_compile_options(-Wall -Wextra -Wconversion -Wmissing-prototypes -Wunused
                      -Winfinite-recursion -Wassign-enum -Wcomma -Wshadow
                      -Wstrict-prototypes -Wconditional-uninitialized)
elseif(CMAKE_C_COMPILER_ID STREQUAL "GNU")
  add_compile_options(-Wall -Wextra -Wconversion -Wmissing-prototypes)
elseif(CMAKE_C_COMPILER_ID STREQUAL "MSVC")
  add_compile_options(/W3)
endif()

add_library(_clayer MODULE clayer/src/cdrkeyvm.c clayer/src/pysertype.c)
target_link_libraries(_clayer CycloneDDS::ddsc)
python_extension_module(_clayer)
install(
  TARGETS _clayer
  LIBRARY DESTINATION cyclonedds
  RUNTIME DESTINATION cyclonedds)
