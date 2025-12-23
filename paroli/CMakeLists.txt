cmake_minimum_required(VERSION 3.15)
project(paroli LANGUAGES CXX)

option(USE_RKNN "Enable RKNN for accelerated inference" OFF)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_MODULE_PATH ${CMAKE_MODULE_PATH} "${CMAKE_SOURCE_DIR}/cmake/")

set(ORT_ROOT "/home/yash/Documents/Libraries/onnxruntime-linux-x64-gpu-1.14.0" CACHE STRING "Path to ONNX Runtime root directory" FORCE)
if (ORT_ROOT STREQUAL "")
    message(FATAL_ERROR "ORT_ROOT must be set")
endif()

include_directories(${ORT_ROOT}/include)
link_directories(${ORT_ROOT}/lib)

set(PIPER_PHONEMIZE_ROOT "/home/yash/Documents/Libraries/piper_phonemize" CACHE STRING "Path to piper-phonemize root directory" FORCE)
if (PIPER_PHONEMIZE_ROOT STREQUAL "")
    message(FATAL_ERROR "PIPER_PHONEMIZE_ROOT must be set")
endif()

include_directories(${PIPER_PHONEMIZE_ROOT}/include)
link_directories(${PIPER_PHONEMIZE_ROOT}/lib)

find_package(fmt REQUIRED)

add_library(piper
    piper/piper.cpp)

if (USE_RKNN)
    target_compile_definitions(piper PRIVATE USE_RKNN)
    target_sources(piper PRIVATE piper/rknn-inferer.cpp)
    target_link_libraries(piper PRIVATE rknnrt)
endif()
target_precompile_headers(piper PRIVATE piper/pch.hpp)

target_link_libraries(piper
    PRIVATE
    onnxruntime
    espeak-ng
    piper_phonemize
    pthread
    fmt::fmt
    dl)

target_include_directories(piper
    PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/piper)

add_executable(paroli-cli
    paroli-cli/main.cpp)
target_link_libraries(paroli-cli PRIVATE piper)


