import cv2 # OpenCV library
import mediapipe as mp # Google’s ML vision framework.
from mediapipe.tasks.python import vision
from mediapipe.tasks import python

# load model
base_options = python.BaseOptions(
    model_asset_path="models/hand_landmarker.task"
)

options = vision.HandLandmarkerOptions(
    base_options=base_options,
    num_hands=1,
    running_mode=vision.RunningMode.IMAGE
)

detector = vision.HandLandmarker.create_from_options(options)

cap = cv2.VideoCapture(0)

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    result = detector.detect(mp_image)

    if result.hand_landmarks:
        for hand_landmarks in result.hand_landmarks:
            for lm in hand_landmarks:
                h, w, _ = frame.shape
                cx, cy = int(lm.x * w), int(lm.y * h)   # Convert normalized coordinates to real pixel values.
                cv2.circle(frame, (cx, cy), 6, (0, 255, 0), -1)    # Draw green dot at each landmark.

    cv2.imshow("SignBridge Hand Detection", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()