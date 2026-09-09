#include <Eigen/Core>
#include <ceres/ceres.h>
#include <opencv2/core.hpp>
#include <pcl/point_cloud.h>
#include <pcl/point_types.h>
#include <yaml-cpp/yaml.h>

int main() {
    const cv::Mat matrix = cv::Mat::eye(3, 3, CV_64F);
    pcl::PointCloud<pcl::PointXYZ> cloud;
    cloud.push_back(pcl::PointXYZ(1, 2, 3));
    ceres::Problem problem;
    const auto config = YAML::Load("ready: true");
    return config["ready"].as<bool>() && cloud.size() == 1 &&
                   matrix.at<double>(0, 0) == 1.0 && problem.NumResidualBlocks() == 0
               ? 0 : 1;
}
