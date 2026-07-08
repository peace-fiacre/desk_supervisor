# desk_supervisor_launch.py
# Lance les 3 nœuds du projet en une seule commande

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='desk_supervisor',
            executable='perception_node',
            name='perception_node',
            output='screen'
        ),
        Node(
            package='desk_supervisor',
            executable='decision_node',
            name='decision_node',
            output='screen'
        ),
        Node(
            package='desk_supervisor',
            executable='actuator_node',
            name='actuator_node',
            output='screen'
        ),
    ])