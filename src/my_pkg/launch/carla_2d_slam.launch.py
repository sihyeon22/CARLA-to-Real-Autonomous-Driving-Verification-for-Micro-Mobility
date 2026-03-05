from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.conditions import IfCondition
from launch.substitutions import EnvironmentVariable, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    bag_path = LaunchConfiguration('bag_path')
    bag_rate = LaunchConfiguration('bag_rate')
    use_rviz = LaunchConfiguration('use_rviz')
    rviz_config = LaunchConfiguration('rviz_config')

    return LaunchDescription([
        DeclareLaunchArgument(
            'bag_path',
            default_value=PathJoinSubstitution([EnvironmentVariable('HOME'), 'my_ws', 'bag']),
            description='Path to rosbag2 directory',
        ),
        DeclareLaunchArgument(
            'bag_rate',
            default_value='0.1',
            description='Rosbag playback rate',
        ),
        DeclareLaunchArgument(
            'use_rviz',
            default_value='true',
            description='Launch RViz2',
        ),
        DeclareLaunchArgument(
            'rviz_config',
            default_value=PathJoinSubstitution([FindPackageShare('my_pkg'), 'rviz', 'carla_slam.rviz']),
            description='RViz2 config file',
        ),

        # Replay bag-recorded /clock only (do not use --clock) to avoid duplicate publishers.
        ExecuteProcess(
            cmd=[
                'ros2', 'bag', 'play', bag_path, '-r', bag_rate,
                '--topics',
                '/clock',
                '/carla/hero/lidar',
                '/carla/hero/odometry',
                '/tf',
                '/tf_static',
            ],
            output='screen',
        ),

        # Build odom frame from map so slam_toolbox can resolve odom -> hero
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='map_to_odom_static_tf',
            arguments=[
                '--x', '0', '--y', '0', '--z', '0',ㄱ
                '--roll', '0', '--pitch', '0', '--yaw', '0',
                '--frame-id', 'map', '--child-frame-id', 'odom',
            ],
            output='screen',
        ),

        Node(
            package='pointcloud_to_laserscan',
            executable='pointcloud_to_laserscan_node',
            name='pointcloud_to_laserscan',
            output='screen',
            parameters=[{
                'use_sim_time': True,
                'target_frame': 'hero',
                'transform_tolerance': 0.2,
                'min_height': -0.5,
                'max_height': 0.8,
                'angle_min': -3.14159,
                'angle_max': 3.14159,
                'angle_increment': 0.0174,
                'range_min': 0.5,
                'range_max': 30.0,
                'use_inf': True,
            }],
            remappings=[
                ('cloud_in', '/carla/hero/lidar'),
                ('scan', '/scan'),
            ],
        ),

        Node(
            package='slam_toolbox',
            executable='async_slam_toolbox_node',
            name='slam_toolbox',
            output='screen',
            parameters=[{
                'use_sim_time': True,
                'map_frame': 'map',
                'odom_frame': 'odom',
                'base_frame': 'hero',
                'scan_topic': '/scan',
                'publish_map_to_odom_transform': False,
                'transform_timeout': 0.2,
                'tf_buffer_duration': 30.0,
            }],
        ),

        Node(
            condition=IfCondition(use_rviz),
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            arguments=['-d', rviz_config],
            parameters=[{'use_sim_time': True}],
            output='screen',
        ),
    ])
