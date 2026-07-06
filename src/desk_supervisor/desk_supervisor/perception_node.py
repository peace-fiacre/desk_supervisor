# decision_node.py
# Nœud ROS2 : Machine à États (FSM) - reçoit les détections, décide des actions

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from collections import deque
import json
import time

# Seuils de temporisation (en secondes)
SEUIL_NOTIF_TELEPHONE = 3.0   # Mode Focus
SEUIL_ABSENCE_VEILLE = 5.0    # Mode Éco (durée d'absence confirmée avant veille)

# Paramètres du lissage par fenêtre glissante
TAILLE_FENETRE = 10        # nombre de messages récents pris en compte (~1s à 10Hz)
SEUIL_RATIO = 0.30         # en dessous de 30% de détections positives -> considéré absent/pas de téléphone


class DecisionNode(Node):
    def __init__(self):
        super().__init__('decision_node')

        self.subscription = self.create_subscription(
            String,
            '/perception/detections',
            self.detection_callback,
            10
        )

        self.command_publisher = self.create_publisher(String, '/system/commands', 10)
        self.state_publisher = self.create_publisher(String, '/decision/state', 10)

        # État courant de la FSM
        self.state = "FOCUS"

        # Fenêtres glissantes : historique des dernières détections (True/False)
        self.person_history = deque(maxlen=TAILLE_FENETRE)
        self.phone_history = deque(maxlen=TAILLE_FENETRE)

        # Timestamp du début de l'absence courante (utilisé pour le délai de 5s avant veille)
        self.absence_start_time = None

        # Timestamp du début du téléphone en main courant (utilisé pour le délai de 3s)
        self.phone_start_time = None

        # Flags pour ne déclencher chaque action qu'une seule fois par épisode
        self.notif_envoyee = False
        self.veille_envoyee = False

        self.get_logger().info("Decision node démarré, état initial : FOCUS")

    def detection_callback(self, msg):
        try:
            data = json.loads(msg.data)
        except json.JSONDecodeError:
            self.get_logger().warn("JSON invalide reçu, message ignoré")
            return

        now = time.time()
        person_detected = data.get("person_detected", False)
        phone_detected = data.get("phone_detected", False)

        # Ajoute la détection courante à l'historique glissant
        self.person_history.append(person_detected)
        self.phone_history.append(phone_detected)

        # Calcule les ratios sur la fenêtre actuelle
        # Note : tant que la fenêtre n'est pas pleine (au démarrage), le ratio
        # est calculé sur moins de 10 échantillons - donc moins fiable les
        # premières secondes après le lancement du nœud.
        ratio_person = sum(self.person_history) / len(self.person_history)
        ratio_phone = sum(self.phone_history) / len(self.phone_history)

        person_present_smoothed = ratio_person >= SEUIL_RATIO
        phone_present_smoothed = ratio_phone >= SEUIL_RATIO

        # --- Logique de la FSM ---

        if self.state == "FOCUS":
            if not person_present_smoothed:
                # Début d'un épisode d'absence
                self.state = "ABSENT_PENDING"
                self.absence_start_time = now
                self.get_logger().info(
                    f"Transition FOCUS -> ABSENT_PENDING (ratio_person={ratio_person:.2f})"
                )
                self.publish_state()
                return

            # Gestion du téléphone (avec lissage)
            if phone_present_smoothed:
                if self.phone_start_time is None:
                    self.phone_start_time = now
                duree_telephone = now - self.phone_start_time
                if duree_telephone >= SEUIL_NOTIF_TELEPHONE and not self.notif_envoyee:
                    self.publish_command("NOTIFY")
                    self.notif_envoyee = True
                    self.get_logger().info("Notification envoyée (téléphone détecté)")
            else:
                self.phone_start_time = None
                self.notif_envoyee = False

        elif self.state == "ABSENT_PENDING":
            if person_present_smoothed:
                self.state = "FOCUS"
                self.absence_start_time = None
                self.get_logger().info(
                    f"Transition ABSENT_PENDING -> FOCUS (ratio_person={ratio_person:.2f})"
                )
                self.publish_state()
                return

            duree_absence = now - self.absence_start_time
            if duree_absence >= SEUIL_ABSENCE_VEILLE and not self.veille_envoyee:
                self.publish_command("SCREEN_OFF")
                self.veille_envoyee = True
                self.state = "SLEEP"
                self.get_logger().info("Transition ABSENT_PENDING -> SLEEP")

        elif self.state == "SLEEP":
            if person_present_smoothed:
                self.publish_command("SCREEN_ON")
                self.veille_envoyee = False
                self.absence_start_time = None
                self.state = "FOCUS"
                self.get_logger().info("Transition SLEEP -> FOCUS (réveil)")

        self.publish_state()

    def publish_command(self, command):
        msg = String()
        msg.data = command
        self.command_publisher.publish(msg)

    def publish_state(self):
        msg = String()
        msg.data = self.state
        self.state_publisher.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = DecisionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
    
    
