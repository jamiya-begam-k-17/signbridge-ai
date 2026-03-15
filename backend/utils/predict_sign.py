"""
backend/utils/predict_sign.py
------------------------------
GRU sequence model inference for SignBridge.

Works with 10 signs:
    hello, allthebest, yes, no, water,
    thankyou, sorry, book, excuseme, seeyoulater

The 40-frame sliding window lives here (server-side).
Call reset_session() whenever a new detection session starts.
"""

import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

import sys
import cv2
import numpy as np
import joblib
from collections import deque

import tensorflow as tf

# ── Path setup: import feature_extraction and attention_layer from ai_model ───
_AI_MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "ai_model")
_AI_MODEL_DIR = os.path.abspath(_AI_MODEL_DIR)
if _AI_MODEL_DIR not in sys.path:
    sys.path.insert(0, _AI_MODEL_DIR)

from feature_extraction import extract_features, FEATURE_SIZE   # noqa: E402
from attention_layer    import TemporalAttention                 # noqa: E402

# ── Model paths ───────────────────────────────────────────────────────────────
MODEL_PATH   = os.path.join(_AI_MODEL_DIR, "gesture_model.h5")
ENCODER_PATH = os.path.join(_AI_MODEL_DIR, "label_encoder.pkl")

SEQ_LEN     = 40
CONF_THRESH = 0.70   # ignore predictions below this confidence
SMOOTH_WIN  = 7      # majority-vote window

# ── Load model & encoder once at import time ──────────────────────────────────
print("[SignBridge] Loading GRU model…")
model   = tf.keras.models.load_model(
    MODEL_PATH,
    custom_objects={"TemporalAttention": TemporalAttention},
)
encoder = joblib.load(ENCODER_PATH)
print(f"[SignBridge] Ready. Classes: {encoder.classes_.tolist()}")

# ── MediaPipe (Solutions API — same API used during training) ─────────────────
import mediapipe as mp

_mp_hands = mp.solutions.hands
_mp_pose  = mp.solutions.pose
_mp_face  = mp.solutions.face_mesh

_hands = _mp_hands.Hands(
    static_image_mode=False, max_num_hands=2,
    min_detection_confidence=0.5, min_tracking_confidence=0.5,
)
_pose = _mp_pose.Pose(
    static_image_mode=False,
    min_detection_confidence=0.5, min_tracking_confidence=0.5,
)
_face = _mp_face.FaceMesh(
    static_image_mode=False, max_num_faces=1, refine_landmarks=False,
    min_detection_confidence=0.5, min_tracking_confidence=0.5,
)

# ── Per-session state ─────────────────────────────────────────────────────────
_frame_buffer  = deque(maxlen=SEQ_LEN)
_smooth_buffer = deque(maxlen=SMOOTH_WIN)
_prev_wrist    = None


def _get_hands(hand_res):
    right_hand = left_hand = None
    if hand_res.multi_hand_landmarks and hand_res.multi_handedness:
        for lm, hd in zip(hand_res.multi_hand_landmarks,
                          hand_res.multi_handedness):
            label = hd.classification[0].label
            if label == "Right":
                right_hand = lm
            else:
                left_hand = lm
    return right_hand, left_hand


def _majority_vote(buf):
    if not buf:
        return None
    counts: dict = {}
    for x in buf:
        counts[x] = counts.get(x, 0) + 1
    return max(counts, key=counts.get)


# ── Public functions ───────────────────────────────────────────────────────────

def reset_session():
    """Clear the sliding window. Call this when user clicks 'Start Detection'."""
    global _prev_wrist
    _frame_buffer.clear()
    _smooth_buffer.clear()
    _prev_wrist = None


def predict_sign(frame: np.ndarray) -> dict:
    """
    Accept one BGR frame, update the sliding window, return prediction.

    Returns
    -------
    {
        "prediction": str,   # sign label or "" if not yet confident
        "confidence": float, # 0.0 – 1.0
        "buffered":   int,   # frames collected so far (max 40)
    }
    """
    global _prev_wrist

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    rgb.flags.writeable = False

    hand_res = _hands.process(rgb)
    pose_res = _pose.process(rgb)
    face_res = _face.process(rgb)

    right_hand, left_hand = _get_hands(hand_res)

    pose_lm = pose_res.pose_landmarks if pose_res else None
    face_lm = (face_res.multi_face_landmarks[0]
               if face_res and face_res.multi_face_landmarks else None)

    features, _prev_wrist = extract_features(
        right_hand, left_hand, pose_lm, face_lm,
        prev_right_wrist=_prev_wrist,
    )
    _frame_buffer.append(features)

    if len(_frame_buffer) < SEQ_LEN:
        return {"prediction": "", "confidence": 0.0, "buffered": len(_frame_buffer)}

    seq   = np.expand_dims(np.array(_frame_buffer, dtype=np.float32), 0)  # (1, 40, 158)
    probs = model.predict(seq, verbose=0)[0]
    idx   = int(np.argmax(probs))
    conf  = float(probs[idx])

    _smooth_buffer.append(idx if conf >= CONF_THRESH else None)

    voted = _majority_vote(_smooth_buffer)
    if voted is not None:
        label = encoder.inverse_transform([voted])[0]
        return {"prediction": label, "confidence": conf, "buffered": SEQ_LEN}

    return {"prediction": "", "confidence": conf, "buffered": SEQ_LEN}


# ── Quick standalone camera test ───────────────────────────────────────────────
def run_camera():
    reset_session()
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    print("Running camera test. Press Q to quit.")
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        frame  = cv2.flip(frame, 1)
        result = predict_sign(frame)

        sign     = result["prediction"] or "…"
        conf     = result["confidence"]
        buffered = result["buffered"]

        cv2.putText(frame, f"{sign}  ({conf*100:.0f}%)", (20, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 120), 2)
        cv2.putText(frame, f"Buffer {buffered}/{SEQ_LEN}", (20, 85),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 180, 180), 1)
        cv2.imshow("SignBridge", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    run_camera()







# import os
# os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

# import cv2
# import numpy as np
# import joblib
# import mediapipe as mp

# from mediapipe.tasks import python
# from mediapipe.tasks.python import vision

# from collections import deque

# prediction_buffer = deque(maxlen=15)

# # =========================================
# # LOAD TRAINED MODEL
# # =========================================
# MODEL_PATH = "../ai_model/sign_pipeline.pkl"
# ENCODER_PATH = "../ai_model/label_encoder.pkl"
# TASK_MODEL = "models/hand_landmarker.task"

# pipeline = joblib.load(MODEL_PATH)
# encoder = joblib.load(ENCODER_PATH)


# # =========================================
# # MEDIAPIPE HAND LANDMARKER SETUP
# # =========================================
# base_options = python.BaseOptions(model_asset_path=TASK_MODEL)

# options = vision.HandLandmarkerOptions(
#     base_options=base_options,
#     num_hands=2,
#     min_hand_detection_confidence=0.7,
#     min_hand_presence_confidence=0.7
# )

# detector = vision.HandLandmarker.create_from_options(options)


# # =========================================
# # NORMALIZE LANDMARKS (same as training)
# # =========================================
# def normalize_landmarks(landmarks):

#     for hand in range(2):
#         base = hand * 63

#         wrist_x = landmarks[base]
#         wrist_y = landmarks[base + 1]
#         wrist_z = landmarks[base + 2]

#         if wrist_x == 0 and wrist_y == 0:
#             continue

#         for i in range(21):
#             idx = base + i * 3
#             landmarks[idx] -= wrist_x
#             landmarks[idx + 1] -= wrist_y
#             landmarks[idx + 2] -= wrist_z

#     return landmarks


# # =========================================
# # EXTRACT LANDMARK FEATURES
# # =========================================
# def extract_landmarks(frame):

#     rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

#     mp_image = mp.Image(
#         image_format=mp.ImageFormat.SRGB,
#         data=rgb
#     )

#     result = detector.detect(mp_image)

#     landmarks = np.zeros(128)

#     if result.hand_landmarks:

#         for hand_index, hand_landmarks in enumerate(result.hand_landmarks[:2]):

#             handedness = result.handedness[hand_index][0].category_name
#             landmarks[126 + hand_index] = 1 if handedness == "Right" else 0

#             for i, lm in enumerate(hand_landmarks):
#                 base = hand_index * 63 + i * 3
#                 landmarks[base] = lm.x
#                 landmarks[base + 1] = lm.y
#                 landmarks[base + 2] = lm.z

#     landmarks = normalize_landmarks(landmarks)

#     return landmarks


# # =========================================
# # PREDICT SIGN
# # =========================================
# def predict_sign(frame):

#     features = extract_landmarks(frame)

#     # no hand detected
#     if np.all(features[:126] == 0):
#         return "No hand detected"

#     prediction = pipeline.predict([features])[0]
#     label = encoder.inverse_transform([prediction])[0]

#     # prediction_buffer.append(label)

#     # # majority voting
#     # final_prediction = max(set(prediction_buffer),
#     #                     key=prediction_buffer.count)

#     return label


# # =========================================
# # REAL-TIME CAMERA TEST
# # =========================================
# def run_camera():

#     cap = cv2.VideoCapture(0)

#     while cap.isOpened():

#         ret, frame = cap.read()
#         if not ret:
#             break

#         frame = cv2.flip(frame, 1)

#         sign = predict_sign(frame)

#         # display prediction
#         cv2.putText(
#             frame,
#             f"Prediction: {sign}",
#             (20, 50),
#             cv2.FONT_HERSHEY_SIMPLEX,
#             1,
#             (0, 255, 0),
#             2
#         )

#         cv2.imshow("SignBridge Detection", frame)

#         if cv2.waitKey(1) & 0xFF == ord("q"):
#             break

#     cap.release()
#     cv2.destroyAllWindows()


# # =========================================
# # RUN DIRECTLY
# # =========================================
# if __name__ == "__main__":
#     run_camera()