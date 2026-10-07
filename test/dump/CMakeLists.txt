project(afxcoll)

add_executable(${PROJECT_NAME} afxcoll.cpp)

add_test(
    NAME ${PROJECT_NAME}
    BUILD_DEPENDS ${PROJECT_NAME}
    WORKING_DIRECTORY $<TARGET_FILE_DIR:${PROJECT_NAME}>
    COMMAND Python::Interpreter -m cdb ${CMAKE_CURRENT_LIST_DIR}/${PROJECT_NAME}.yaml
)
