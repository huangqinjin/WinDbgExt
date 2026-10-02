cmake_minimum_required(VERSION 4.4.1)

project(WinDbgExt)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
set(CMAKE_CXX_SCAN_FOR_MODULES OFF)
set(CMAKE_TEST_BUILD_DEPENDS ON)

enable_testing()
add_subdirectory(test)
