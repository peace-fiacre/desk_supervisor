# perception_node.py
# Nœud ROS2 : capture webcam + détection YOLO + publication des résultats

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import cv2
from ultralytics import YOLO
import json

# Classes COCO qui nous intéressent (identique à la Phase 1)
CLASSES_INTERESSANTES = {0: "person", 67: "cell phone"}


class PerceptionNode(Node):
    def __init__(self):
        # Initialise le nœud avec le nom "perception_node"
        super().__init__('perception_node')

        # Charge le modèle YOLO (déjà téléchargé en Phase 1, donc pas de re-téléchargement)
        self.model = YOLO("yolov8n.pt")

        # Ouvre la webcam
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            self.get_logger().error("Impossible d'ouvrir la webcam")
            raise RuntimeError("Webcam inaccessible")

        # Crée le publisher sur le topic /perception/detections
        self.publisher_ = self.create_publisher(String, '/perception/detections', 10)

        # Abonnement à l'état de la FSM (pour affichage)
        self.current_state = "FOCUS"  # valeur par défaut avant le premier message reçu
        self.state_subscription = self.create_subscription(
            String,
            '/decision/state',
            self.state_callback,
            10
        )

        # Timer qui appelle self.timer_callback toutes les 0.1s (~10 Hz)
        self.timer = self.create_timer(0.1, self.timer_callback)
        self.get_logger().info("Perception node démarré")

    def state_callback(self, msg):
        self.current_state = msg.data

    def timer_callback(self):
        ret, frame = self.cap.read()
        if not ret:
            self.get_logger().warn("Frame non lue")
            return

        # Inférence YOLO sur la frame actuelle (seuil de confiance à 0.40)
        results = self.model(frame, conf=0.70, verbose=False)[0]

        # Valeurs par défaut : rien détecté
        person_detected = False
        phone_detected = False
        person_confidence = 0.0
        phone_confidence = 0.0

        for box in results.boxes:
            class_id = int(box.cls[0])

            # Filtre : ignore tout ce qui n'est pas person/cell phone
            if class_id not in CLASSES_INTERESSANTES:
                continue

            confiance = float(box.conf[0])

            if class_id == 0:  # person
                person_detected = True
                person_confidence = max(person_confidence, confiance)
            elif class_id == 67:  # cell phone
                phone_detected = True
                phone_confidence = max(phone_confidence, confiance)

            # Dessine le rectangle et le label sur l'image
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            label = CLASSES_INTERESSANTES[class_id]
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, f"{label} {confiance:.2f}", (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # Construit le message JSON
        data = {
            "person_detected": person_detected,
            "phone_detected": phone_detected,
            "person_confidence": round(person_confidence, 2),
            "phone_confidence": round(phone_confidence, 2),
            "timestamp": self.get_clock().now().to_msg().sec
        }

        # Affichage vidéo avec état FSM
        cv2.putText(frame, f"Etat: {self.current_state}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)
        cv2.imshow("Desk Supervisor - Debug", frame)
        cv2.waitKey(1)

        msg = String()
        msg.data = json.dumps(data)
        self.publisher_.publish(msg)

    def destroy_node(self):
        # Libère la webcam proprement quand le nœud s'arrête
        self.cap.release()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = PerceptionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()