"""
data_collection.py
------------------
Records gesture sequences from the webcam and saves them as .npy files.

Usage
-----
    python data_collection.py

The script will loop through each gesture in SIGNS and collect
NUM_SAMPLES sequences of SEQ_LEN frames each.

Controls during collection:
    SPACE  — start recording a sample (shown in green border)
    Q      — quit early
"""

import cv2
import mediapipe as mp
import numpy as np
import os
import time

from feature_extraction import extract_features, FEATURE_SIZE

# ── Configuration ──────────────────────────────────────────────────────────────

SIGNS = [
    "hello",
    "allthebest",
    "yes",
    "no",
    "water",
    "thankyou",
    "sorry",
    "book",
    "excuseme",
    "seeyoulater",
]

SEQ_LEN    = 40    # frames per sample
NUM_SAMPLES = 100  # samples per sign
DATASET_DIR = "dataset"
CAMERA_IDX  = 0

# ── MediaPipe setup ────────────────────────────────────────────────────────────

mp_hands   = mp.solutions.hands
mp_pose    = mp.solutions.pose
mp_face    = mp.solutions.face_mesh
mp_drawing = mp.solutions.drawing_utils

hands   = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=2,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5,
)
pose    = mp_pose.Pose(
    static_image_mode=False,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5,
)
face    = mp_face.FaceMesh(
    static_image_mode=False,
    max_num_faces=1,
    refine_landmarks=False,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def make_dirs():
    for sign in SIGNS:
        os.makedirs(os.path.join(DATASET_DIR, sign), exist_ok=True)


def detect_landmarks(frame):
    """Run all three MediaPipe models on an BGR frame."""
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    rgb.flags.writeable = False

    hand_res = hands.process(rgb)
    pose_res  = pose.process(rgb)
    face_res  = face.process(rgb)

    rgb.flags.writeable = True
    return hand_res, pose_res, face_res


def get_hands(hand_res):
    """Return (right_hand, left_hand) landmark objects or None."""
    right_hand = left_hand = None
    if hand_res.multi_hand_landmarks and hand_res.multi_handedness:
        for lm, hd in zip(hand_res.multi_hand_landmarks,
                            hand_res.multi_handedness):
            label = hd.classification[0].label  # 'Left' or 'Right'
            if label == "Right":
                right_hand = lm
            else:
                left_hand = lm
    return right_hand, left_hand


def count_existing(sign):
    sign_dir = os.path.join(DATASET_DIR, sign)
    return len([f for f in os.listdir(sign_dir) if f.endswith(".npy")])


def draw_ui(frame, sign, sample_idx, recording, countdown):
    h, w = frame.shape[:2]
    color = (0, 200, 0) if recording else (0, 120, 255)

    # Border
    cv2.rectangle(frame, (0, 0), (w - 1, h - 1), color, 4)

    # Sign name
    cv2.putText(frame, f"Sign: {sign}", (10, 35),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)

    # Sample counter
    cv2.putText(frame, f"Sample: {sample_idx}/{NUM_SAMPLES}", (10, 70),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)

    if recording:
        cv2.putText(frame, "● RECORDING", (10, 110),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    elif countdown > 0:
        cv2.putText(frame, f"Starting in {countdown}...", (10, 110),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 255), 2)
    else:
        cv2.putText(frame, "Press SPACE to record", (10, 110),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (180, 180, 180), 2)

    return frame


# ── Main loop ─────────────────────────────────────────────────────────────────

def collect_sign(cap, sign):
    sign_dir   = os.path.join(DATASET_DIR, sign)
    start_idx  = count_existing(sign)
    sample_idx = start_idx
    print(f"\n[INFO] Collecting '{sign}'  (already have {start_idx} samples)")

    while sample_idx < NUM_SAMPLES:
        # ── Wait for SPACE key ──────────────────────────────────────────────
        waiting = True
        while waiting:
            ret, frame = cap.read()
            if not ret:
                continue
            frame = cv2.flip(frame, 1)
            draw_ui(frame, sign, sample_idx, recording=False, countdown=0)
            cv2.imshow("Data Collection", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord(" "):
                waiting = False
            elif key == ord("q"):
                return False   # quit signal

        # ── Short countdown ─────────────────────────────────────────────────
        for cnt in [3, 2, 1]:
            ret, frame = cap.read()
            if ret:
                frame = cv2.flip(frame, 1)
                draw_ui(frame, sign, sample_idx, recording=False, countdown=cnt)
                cv2.imshow("Data Collection", frame)
            cv2.waitKey(700)

        # ── Record SEQ_LEN frames ────────────────────────────────────────────
        sequence   = []
        prev_wrist = None

        for frame_idx in range(SEQ_LEN):
            ret, frame = cap.read()
            if not ret:
                continue
            frame = cv2.flip(frame, 1)

            hand_res, pose_res, face_res = detect_landmarks(frame)
            right_hand, left_hand = get_hands(hand_res)

            features, prev_wrist = extract_features(
                right_hand, left_hand,
                pose_res.pose_landmarks if pose_res else None,
                face_res.multi_face_landmarks[0]
                    if face_res and face_res.multi_face_landmarks else None,
                prev_right_wrist=prev_wrist,
            )
            sequence.append(features)

            draw_ui(frame, sign, sample_idx, recording=True, countdown=0)
            cv2.putText(frame, f"Frame {frame_idx+1}/{SEQ_LEN}", (10, 145),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 255, 200), 1)
            cv2.imshow("Data Collection", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                return False

        # ── Save ────────────────────────────────────────────────────────────
        arr = np.array(sequence, dtype=np.float32)   # (SEQ_LEN, FEATURE_SIZE)
        save_path = os.path.join(sign_dir, f"sample_{sample_idx}.npy")
        np.save(save_path, arr)
        print(f"  Saved sample {sample_idx}  shape={arr.shape}  → {save_path}")
        sample_idx += 1

    return True   # completed normally


def main():
    make_dirs()
    cap = cv2.VideoCapture(CAMERA_IDX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    print("=" * 60)
    print("  Sign Language Data Collection")
    print(f"  Signs     : {SIGNS}")
    print(f"  Seq len   : {SEQ_LEN} frames")
    print(f"  Samples   : {NUM_SAMPLES} per sign")
    print(f"  Feature Ø : {FEATURE_SIZE}")
    print("=" * 60)
    print("Press SPACE to begin each sample.  Q to quit.")

    for sign in SIGNS:
        ok = collect_sign(cap, sign)
        if not ok:
            print("[INFO] Quit by user.")
            break
        print(f"[INFO] '{sign}' complete!")

    cap.release()
    cv2.destroyAllWindows()
    hands.close()
    pose.close()
    face.close()
    print("\n[INFO] Data collection finished.")


if __name__ == "__main__":
    main()