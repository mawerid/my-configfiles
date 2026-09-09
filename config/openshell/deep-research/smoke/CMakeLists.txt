cmake_minimum_required(VERSION 3.22)
project(deep_research_smoke LANGUAGES C CXX)
set(CMAKE_CXX_STANDARD 17)
find_package(Eigen3 REQUIRED)
find_package(PCL REQUIRED COMPONENTS common)
find_package(OpenCV REQUIRED COMPONENTS core)
find_package(Ceres REQUIRED)
find_package(yaml-cpp REQUIRED)
add_executable(deep_research_smoke main.cpp)
target_include_directories(deep_research_smoke PRIVATE ${PCL_INCLUDE_DIRS} ${OpenCV_INCLUDE_DIRS})
target_link_libraries(deep_research_smoke PRIVATE
    Eigen3::Eigen ${PCL_LIBRARIES} ${OpenCV_LIBS}
    Ceres::ceres yaml-cpp)
