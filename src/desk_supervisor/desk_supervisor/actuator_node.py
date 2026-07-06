# actuator_node.py
# Nœud ROS2 : exécute les commandes système reçues du decision_node

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import subprocess


class ActuatorNode(Node):
    def __init__(self):
        super().__init__('actuator_node')

        self.subscription = self.create_subscription(
            String,
            '/system/commands',
            self.command_callback,
            10
        )

        self.get_logger().info("Actuator node démarré")

    def command_callback(self, msg):
        command = msg.data

        if command == "NOTIFY":
            self.notify("Rappel", "Tu tiens ton téléphone depuis un moment !")

        elif command == "SCREEN_OFF":
            self.lock_screen()

        elif command == "SCREEN_ON":
            self.notify("Bienvenue", "Content de te revoir !")

        else:
            self.get_logger().warn(f"Commande inconnue reçue : {command}")

    def notify(self, titre, message):
        try:
            subprocess.run(["notify-send", titre, message], check=True)
            self.get_logger().info(f"Notification envoyée : {titre} - {message}")
        except subprocess.CalledProcessError as e:
            self.get_logger().error(f"Échec de la notification : {e}")
        except FileNotFoundError:
            self.get_logger().error("notify-send introuvable — installe libnotify-bin")

    def lock_screen(self):
        try:
            subprocess.run([
                "gdbus", "call", "--session",
                "--dest", "org.gnome.ScreenSaver",
                "--object-path", "/org/gnome/ScreenSaver",
                "--method", "org.gnome.ScreenSaver.SetActive", "true"
            ], check=True)
            self.get_logger().info("Écran verrouillé")
        except subprocess.CalledProcessError as e:
            self.get_logger().error(f"Échec du verrouillage : {e}")


def main(args=None):
    rclpy.init(args=args)
    node = ActuatorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()