# test_yolo_standalone.py
# Script de test : détection YOLO en direct depuis la webcam, hors ROS2

import cv2
from ultralytics import YOLO
import time

# Charge le modèle YOLOv8n (nano = le plus léger, adapté au CPU)
# Au premier lancement, ultralytics télécharge automatiquement le fichier
# de poids "yolov8n.pt" (~6 Mo) depuis les serveurs officiels
model = YOLO("yolov8n.pt")

# Classes COCO qui nous intéressent (les autres seront ignorées)
# Dans le dataset COCO, "person" = classe 0, "cell phone" = classe 67
CLASSES_INTERESSANTES = {0: "person", 67: "cell phone"}

# Ouvre la webcam (index 0 = webcam par défaut)
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Erreur : impossible d'ouvrir la webcam")
    exit()

# Variables pour calculer le FPS réel
prev_time = time.time()

while True:
    ret, frame = cap.read()
    if not ret:
        print("Erreur : frame non lue")
        break

    # Lance l'inférence YOLO sur la frame actuelle
    # verbose=False évite d'inonder le terminal de logs à chaque frame
    results = model(frame, conf=0.40, verbose=False)[0]

    # Parcourt toutes les détections trouvées dans cette frame
    for box in results.boxes:
        class_id = int(box.cls[0])

        # On ignore tout ce qui n'est pas dans notre liste (voiture, chat, etc.)
        if class_id not in CLASSES_INTERESSANTES:
            continue

        # Coordonnées du rectangle de détection
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        confiance = float(box.conf[0])
        label = CLASSES_INTERESSANTES[class_id]

        # Dessine le rectangle et le texte sur l'image
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(frame, f"{label} {confiance:.2f}", (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    # Calcul du FPS réel (temps entre deux frames)
    curr_time = time.time()
    fps = 1 / (curr_time - prev_time)
    prev_time = curr_time
    cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

    # Affiche l'image dans une fenêtre
    cv2.imshow("Test YOLO - Desk Supervisor", frame)

    # Quitte si on appuie sur 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
