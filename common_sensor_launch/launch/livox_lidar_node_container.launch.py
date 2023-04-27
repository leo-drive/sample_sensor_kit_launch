# Copyright 2023 LeoDrive Teknoloji A.Ş., Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os

import launch
from launch.actions import DeclareLaunchArgument
from launch.actions import OpaqueFunction
from launch.actions import SetLaunchConfiguration
from launch.conditions import IfCondition
from launch.conditions import UnlessCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import ComposableNodeContainer
from launch_ros.actions import LoadComposableNodes
from launch_ros.descriptions import ComposableNode
from launch_ros.substitutions import FindPackageShare

def get_config_path(path):
    return os.path.join(
        FindPackageShare("livox_ros2_driver").perform(launch.LaunchContext()),
        path
    )

def launch_setup(context, *args, **kwargs):
    def create_parameter_dict(*args):
        result = {}
        for x in args:
            result[x] = LaunchConfiguration(x)
        return result

    nodes = []

    # livox tag filter component
    nodes.append(
        ComposableNode(
            package="livox_tag_filter",
            plugin="livox_tag_filter::LivoxTagFilterNode",
            name="livox_tag_filter",
            remappings=[
                ("input", "livox_points"),
                ("output", "livox_points_filtered/pointcloud"),
            ],
            extra_arguments=[{"use_intra_process_comms": LaunchConfiguration("use_intra_process")}],
        )
    )

    container = ComposableNodeContainer(
        name=LaunchConfiguration("container_name"),
        namespace="pointcloud_preprocessor",
        package="rclcpp_components",
        executable=LaunchConfiguration("container_executable"),
        composable_node_descriptions=nodes,
        condition=UnlessCondition(LaunchConfiguration("use_pointcloud_container")),
        output="screen",
    )

    component_loader = LoadComposableNodes(
        composable_node_descriptions=nodes,
        target_container=LaunchConfiguration("container_name"),
        condition=IfCondition(LaunchConfiguration("use_pointcloud_container")),
    )

    driver_component = ComposableNode(
        package='livox_ros2_driver',
        plugin='livox_ros::LivoxDriver',
        name='livox_lidar_publisher',
        parameters=[
            {
                **create_parameter_dict(
                    "xfer_format",
                    "multi_topic",
                    "data_src",
                    "publish_freq",
                    "output_data_type",
                    "frame_id",
                    "lvx_file_path",
                    "user_config_path",
                    "cmdline_input_bd_code",
                ),
            }
        ],
    )

    target_container = (
        container
        if UnlessCondition(LaunchConfiguration("use_pointcloud_container")).evaluate(context)
        else LaunchConfiguration("container_name")
    )

    driver_component_loader = LoadComposableNodes(
        composable_node_descriptions=[driver_component],
        target_container=target_container,
        condition=IfCondition(LaunchConfiguration("launch_driver")),
    )

    return [container, component_loader, driver_component_loader]


def generate_launch_description():
    launch_arguments = []

    def add_launch_arg(name: str, default_value=None, description=None):
        # a default_value of None is equivalent to not passing that kwarg at all
        launch_arguments.append(
            DeclareLaunchArgument(name, default_value=default_value, description=description)
        )

    add_launch_arg("launch_driver", "True", "do launch driver")
    add_launch_arg("container_name", "lidar_composable_node_container", "container name")
    add_launch_arg("xfer_format", "0")
    add_launch_arg("multi_topic", "0")
    add_launch_arg("data_src", "0")
    add_launch_arg("publish_freq", "10.0")
    add_launch_arg("output_data_type", "0")
    add_launch_arg("frame_id", "livox_frame")
    add_launch_arg("lvx_file_path", "/home/livox/livox_test.lvx")
    add_launch_arg("user_config_path", get_config_path("config/livox_lidar_config.json"))
    add_launch_arg("cmdline_input_bd_code", "livox0000000001")
    add_launch_arg("use_multithread", "False", "use multithread")
    add_launch_arg("use_intra_process", "False", "use ROS2 component container communication")

    set_container_executable = SetLaunchConfiguration(
        "container_executable",
        "component_container",
        condition=UnlessCondition(LaunchConfiguration("use_multithread")),
    )

    set_container_mt_executable = SetLaunchConfiguration(
        "container_executable",
        "component_container_mt",
        condition=IfCondition(LaunchConfiguration("use_multithread")),
    )

    return launch.LaunchDescription(
        launch_arguments
        + [set_container_executable, set_container_mt_executable]
        + [OpaqueFunction(function=launch_setup)]
    )
