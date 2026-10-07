include(FindPython)
find_package(Python REQUIRED COMPONENTS Interpreter)

add_subdirectory(hello)
add_subdirectory(dump)
