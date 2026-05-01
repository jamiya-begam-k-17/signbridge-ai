import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

import cv2
import numpy as np
import pandas as pd
import mediapipe as mp

from mediapipe.tasks import python
from mediapipe.tasks.python import vision


# =====================================================
# PATH CONFIG
# =====================================================
DATASET_PATH = "../datasets/images"
OUTPUT_CSV = "sign_landmarks.csv"

SIGNS = ["hello", "help", "no", "water", "yes"]


# =====================================================
# MEDIAPIPE TASKS SETUP (NEW API)
# =====================================================
base_options = python.BaseOptions(
    model_asset_path="../backend/models/hand_landmarker.task"
)

options = vision.HandLandmarkerOptions(
    base_options=base_options,
    num_hands=2
)

detector = vision.HandLandmarker.create_from_options(options)


# =====================================================
# NORMALIZE LANDMARKS (WRIST RELATIVE)
# =====================================================
def normalize_landmarks(landmarks):

    for hand in range(2):
        base = hand * 63

        wrist_x = landmarks[base]
        wrist_y = landmarks[base + 1]
        wrist_z = landmarks[base + 2]

        # skip if hand missing
        if wrist_x == 0 and wrist_y == 0:
            continue

        for i in range(21):
            idx = base + i * 3
            landmarks[idx] -= wrist_x
            landmarks[idx + 1] -= wrist_y
            landmarks[idx + 2] -= wrist_z

    return landmarks


# =====================================================
# LANDMARK EXTRACTION
# =====================================================
def extract_landmarks(image):

    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    mp_image = mp.Image(
        image_format=mp.ImageFormat.SRGB,
        data=rgb
    )

    result = detector.detect(mp_image)

    # 126 coords + 2 handedness flags
    landmarks = np.zeros(128)

    if result.hand_landmarks:

        for hand_index, hand_landmarks in enumerate(result.hand_landmarks[:2]):

            handedness = result.handedness[hand_index][0].category_name

            # Right = 1, Left = 0
            landmarks[126 + hand_index] = 1 if handedness == "Right" else 0

            for i, lm in enumerate(hand_landmarks):
                base = hand_index * 63 + i * 3
                landmarks[base] = lm.x
                landmarks[base + 1] = lm.y
                landmarks[base + 2] = lm.z

    landmarks = normalize_landmarks(landmarks)

    return landmarks


# =====================================================
# DATASET CREATION
# =====================================================
data = []
labels = []

for label in SIGNS:

    folder_path = os.path.join(DATASET_PATH, label)

    if not os.path.exists(folder_path):
        print(f"Skipping missing folder: {label}")
        continue

    print(f"\nProcessing: {label}")

    for img_name in os.listdir(folder_path):

        img_path = os.path.join(folder_path, img_name)

        image = cv2.imread(img_path)
        if image is None:
            continue

        landmarks = extract_landmarks(image)

        # skip failed detections
        if np.all(landmarks[:126] == 0):
            continue

        data.append(landmarks)
        labels.append(label)


print("\nLandmark extraction finished.")


# =====================================================
# COLUMN NAMES
# =====================================================
columns = []

for hand in range(2):
    for i in range(21):
        columns += [
            f"h{hand}_lm{i}_x",
            f"h{hand}_lm{i}_y",
            f"h{hand}_lm{i}_z"
        ]

columns += ["hand0_type", "hand1_type"]


# =====================================================
# SAVE DATASET
# =====================================================
df = pd.DataFrame(data, columns=columns)
df["label"] = labels

df.drop_duplicates(inplace=True)

print("\nClass distribution:")
print(df["label"].value_counts())

df.to_csv(OUTPUT_CSV, index=False)

print(f"\nDataset saved → {OUTPUT_CSV}")
print(f"Total samples: {len(df)}")