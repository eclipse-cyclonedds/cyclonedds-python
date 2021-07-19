cmake_minimum_required(VERSION 3.18)
# CMAKE_PREFIX_PATH environment variable is available in CMake >= 3.18
project(_clayer LANGUAGES C)
find_package(PythonExtensions REQUIRED)
find_package(CycloneDDS REQUIRED)

add_library(_clayer MODULE clayer/src/cdrkeyvm.c clayer/src/pysertype.c)
target_link_libraries(_clayer CycloneDDS::ddsc)
python_extension_module(_clayer)
install(
  TARGETS _clayer
  LIBRARY DESTINATION cyclonedds
  RUNTIME DESTINATION cyclonedds)
