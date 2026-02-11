#!/usr/bin/env python3

"""
MAV Simulator main launch (aligned with gem_init.launch.py).
Launches Gazebo (a2rl_track world), ros_gz_bridge, and spawns the drone.
"""

import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, SetEnvironmentVariable, TimerAction
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    pkg_share = get_package_share_directory('mav_gazebo')
    mav_desc_share = get_package_share_directory('mav_description')
    # Absolute paths so Gazebo and any subprocess resolve model:// reliably
    mav_gazebo_models = os.path.abspath(os.path.join(pkg_share, 'models'))
    mav_desc_models = os.path.abspath(os.path.join(mav_desc_share, 'models'))
    world_path = os.path.join(pkg_share, 'worlds', 'a2rl_track_ign.world')
    current = os.environ.get('GZ_SIM_RESOURCE_PATH', '')
    # mav_desc_models first so model://X3 in world resolves to mav_description/models/X3
    new_resource_path = mav_desc_models + ':' + mav_gazebo_models + (':' + current if current else '')

    set_gz_resource_path = SetEnvironmentVariable(
        'GZ_SIM_RESOURCE_PATH',
        new_resource_path,
    )
    # Use Fortress (gz-sim 8)
    set_gz_version = SetEnvironmentVariable(
        name='GZ_SIM_VERSION',
        value='8',
    )
    
    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time',
        default_value='true',
        description='Use simulation time',
    )
    use_sim_time = LaunchConfiguration('use_sim_time')

    # Load the SDF file from "description" package
    sdf_file = os.path.join(mav_desc_share, 'models', 'X3', 'model.sdf')
    with open(sdf_file, 'r') as infp:
        robot_desc = infp.read()
    # RViz does not resolve model://; use package:// so meshes load in RViz
    robot_desc = robot_desc.replace('model://X3/', 'package://mav_description/models/X3/')


    # Gazebo with warehouse world
    gz_sim_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('ros_gz_sim'),
                'launch',
                'gz_sim.launch.py',
            ])
        ]),
        launch_arguments=[
            ('gz_args', '-r -v 4 ' + world_path),
        ],
    )

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[
            {'use_sim_time': use_sim_time},
            {'robot_description': robot_desc},
        ],
    )

    # ros_gz_bridge (like gem_init)
    bridge_params = PathJoinSubstitution([
        FindPackageShare('mav_gazebo'),
        'config',
        'gz_bridge.yaml',
    ])
    ros_gz_bridge = Node(
        package='ros_gz_bridge',
        executable='bridge_node',
        name='gz_bridge',
        parameters=[{'config_file': bridge_params}],
        output='screen',
    )

    # Bridge Gazebo camera image to ROS (gz topic -> ROS topic; ref: gem_init.launch.py)
    ros_gz_image_bridge = Node(
        package='ros_gz_image',
        executable='image_bridge',
        name='image_bridge',
        arguments=[
            'X3/camera/image_raw',
        ],
        parameters=[{'use_sim_time': use_sim_time}],
        output='screen',
    )

    # Visualize in RViz
    rviz = Node(
       package='rviz2',
       executable='rviz2',
       arguments=['-d', os.path.join(get_package_share_directory('mav_description'), 'rviz', 'mav.rviz')],
    )

   
    return LaunchDescription([
        set_gz_resource_path,
        set_gz_version,
        use_sim_time_arg,
        gz_sim_launch,
        ros_gz_bridge,
        ros_gz_image_bridge,
        robot_state_publisher,
        # rviz,
    ])
