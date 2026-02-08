#!/usr/bin/env python3

"""
Launch Gazebo Sim with the x3 warehouse world.
Sets GZ_SIM_RESOURCE_PATH so the local gate model (model://gate) is found.
"""

import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, SetEnvironmentVariable
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.substitutions import FindPackageShare


def get_package_paths():
    """Return (models_path, world_path) for mav_gazebo.
    Prefers source-world path when launch file is in src/ so world edits apply without reinstalling.
    """
    this_file = os.path.abspath(__file__)
    launch_dir = os.path.dirname(this_file)
    source_pkg_root = os.path.dirname(launch_dir)  # .../mav_gazebo
    source_world = os.path.join(source_pkg_root, 'worlds', 'warehouse.world')

    try:
        from ament_index_python.packages import get_package_share_directory
        pkg_share = get_package_share_directory('mav_gazebo')
    except Exception:
        pkg_share = source_pkg_root

    models_path = os.path.join(pkg_share, 'models')
    # Use source world when it exists (e.g. running from src/) so edits show without colcon build
    if os.path.isfile(source_world):
        world_path = source_world
    else:
        world_path = os.path.join(pkg_share, 'worlds', 'x3_warehouse.world')
    return models_path, world_path


def generate_launch_description():
    models_path, world_path = get_package_paths()
    current = os.environ.get('GZ_SIM_RESOURCE_PATH', '')
    new_resource_path = models_path + (':' + current if current else '')

    set_model_path = SetEnvironmentVariable(
        'GZ_SIM_RESOURCE_PATH',
        new_resource_path
    )

    # Use X11 (xcb) instead of EGL to avoid "egl: failed to create dri2 screen" and improve GUI stability
    set_qt_platform = SetEnvironmentVariable(
        'QT_QPA_PLATFORM',
        os.environ.get('QT_QPA_PLATFORM', 'xcb')
    )

    headless_arg = DeclareLaunchArgument(
        'headless',
        default_value='false',
        description='Run gz sim in server-only mode (no GUI). Use to avoid GUI crashes (e.g. GazeboDrawer.qml).'
    )

    headless = LaunchConfiguration('headless', default='false')
    base_args = '-r -v 4 ' + world_path
    gz_args_gui = LaunchConfiguration('gz_args', default=base_args)

    gz_sim_launch_source = PythonLaunchDescriptionSource([
        PathJoinSubstitution([
            FindPackageShare('ros_gz_sim'),
            'launch',
            'gz_sim.launch.py'
        ])
    ])
    launch_args_v8 = [('gz_version', '8')]

    # Headless: server-only (-s) avoids GazeboDrawer.qml GUI crash
    gazebo_headless = IncludeLaunchDescription(
        gz_sim_launch_source,
        launch_arguments=[
            ('gz_args', base_args + ' -s'),
            *launch_args_v8,
        ],
        condition=IfCondition(headless),
    )

    # With GUI (default)
    gazebo_gui = IncludeLaunchDescription(
        gz_sim_launch_source,
        launch_arguments=[
            ('gz_args', gz_args_gui),
            *launch_args_v8,
        ],
        condition=UnlessCondition(headless),
    )

    return LaunchDescription([
        set_model_path,
        set_qt_platform,
        headless_arg,
        gazebo_headless,
        gazebo_gui,
    ])
