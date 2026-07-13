import os

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

import logging
import sys
from collections import deque
from pathlib import Path
from typing import Any, Deque, Dict, Optional, Tuple

import cv2
import joblib
import mediapipe as mp
import numpy as np
import tensorflow as tf
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import (
    HandLandmarker,
    HandLandmarkerOptions,
    PoseLandmarker,
    PoseLandmarkerOptions,
    RunningMode,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT_DIR / "backend"
AI_MODEL_DIR = ROOT_DIR / "ai_model"
PREPROCESSING_DIR = AI_MODEL_DIR / "preprocessing"
MODEL_DIR = BACKEND_DIR / "models"

if str(PREPROCESSING_DIR) not in sys.path:
    sys.path.append(str(PREPROCESSING_DIR))

from extract_landmarks import extract_landmarks_from_results  # noqa: E402
from normalize_landmarks import normalize_sequence  # noqa: E402

SEQUENCE_LENGTH = 20
LANDMARK_SHAPE = (75, 4)
MODEL_PATHS = [
    AI_MODEL_DIR / "saved_model" / "last_model.keras",
    AI_MODEL_DIR / "saved_model" / "saved_model" / "best_model.keras",
]
ENCODER_PATH = AI_MODEL_DIR / "datasets" / "sequences" / "label_encoder.pkl"
POSE_MODEL_PATH = MODEL_DIR / "pose_landmarker_full.task"
HAND_MODEL_PATH = MODEL_DIR / "hand_landmarker.task"

sequence_buffer: Deque[np.ndarray] = deque(maxlen=SEQUENCE_LENGTH)
model: Optional[tf.keras.Model] = None
label_encoder: Optional[Any] = None
pose_landmarker: Optional[Any] = None
hand_landmarker: Optional[Any] = None


def _resolve_model_paths() -> Tuple[Path, Path]:
    """Resolve the MediaPipe model assets used for live inference."""
    hand_path = HAND_MODEL_PATH if HAND_MODEL_PATH.exists() else AI_MODEL_DIR / "assets" / "models" / "hand_landmarker.task"
    pose_path = POSE_MODEL_PATH if POSE_MODEL_PATH.exists() else AI_MODEL_DIR / "assets" / "models" / "pose_landmarker_full.task"
    return pose_path, hand_path


def load_model_artifacts() -> Tuple[Optional[tf.keras.Model], Optional[Any]]:
    """Load the trained Keras model and label encoder for inference."""
    global model, label_encoder

    model_path = next((path for path in MODEL_PATHS if path.exists()), None)
    if model_path is None:
        logger.warning("No trained model found. Prediction will be unavailable.")
        return None, None

    if not ENCODER_PATH.exists():
        logger.warning("Label encoder not found. Prediction will be unavailable.")
        return None, None

    try:
        model = tf.keras.models.load_model(str(model_path), compile=False)
        label_encoder = joblib.load(ENCODER_PATH)
        logger.info("Loaded model from %s", model_path)
    except Exception as exc:
        logger.exception("Failed to load model artifacts: %s", exc)
        return None, None

    return model, label_encoder


def create_landmarkers() -> Tuple[Any, Any]:
    """Create MediaPipe pose and hand landmarkers for live camera inference."""
    global pose_landmarker, hand_landmarker

    pose_path, hand_path = _resolve_model_paths()
    if not pose_path.exists():
        raise FileNotFoundError(f"Pose model not found: {pose_path}")
    if not hand_path.exists():
        raise FileNotFoundError(f"Hand model not found: {hand_path}")

    pose_options = PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(pose_path)),
        running_mode=RunningMode.IMAGE,
        min_pose_detection_confidence=0.5,
        min_pose_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    hand_options = HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(hand_path)),
        running_mode=RunningMode.IMAGE,
        num_hands=2,
        min_hand_detection_confidence=0.5,
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )

    pose_landmarker = PoseLandmarker.create_from_options(pose_options)
    hand_landmarker = HandLandmarker.create_from_options(hand_options)
    return pose_landmarker, hand_landmarker


def extract_frame_landmarks(frame: np.ndarray) -> Optional[np.ndarray]:
    """Extract and normalize a single frame into the same landmark format used in preprocessing."""
    global pose_landmarker, hand_landmarker

    if pose_landmarker is None or hand_landmarker is None:
        create_landmarkers()

    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

    pose_result = pose_landmarker.detect(image)
    hand_result = hand_landmarker.detect(image)
    raw_landmarks = extract_landmarks_from_results(pose_result, hand_result)

    if np.all(raw_landmarks == 0):
        return None

    normalized_frame = normalize_sequence(np.expand_dims(raw_landmarks.astype(np.float32), axis=0))[0]
    return normalized_frame.astype(np.float32)


def predict_sign(frame: np.ndarray) -> Dict[str, Any]:
    """Predict a sign from a single camera frame and return the label with confidence."""
    global model, label_encoder, sequence_buffer

    if model is None or label_encoder is None:
        load_model_artifacts()

    if model is None or label_encoder is None:
        return {"sign": "model_unavailable", "probability": 0.0}

    landmarks = extract_frame_landmarks(frame)
    if landmarks is None:
        return {"sign": "no_landmarks_detected", "probability": 0.0}

    sequence_buffer.append(landmarks)

    if len(sequence_buffer) < SEQUENCE_LENGTH:
        return {"sign": "collecting_frames", "probability": 0.0}

    sequence = np.stack(list(sequence_buffer), axis=0).astype(np.float32)
    flattened = sequence.reshape(1, SEQUENCE_LENGTH, -1)

    probabilities = model.predict(flattened, verbose=0)[0]
    predicted_index = int(np.argmax(probabilities))
    predicted_label = label_encoder.inverse_transform([predicted_index])[0]
    confidence = float(probabilities[predicted_index])

    return {
        "sign": str(predicted_label),
        "probability": round(confidence, 4),
    }


def run_camera() -> None:
    """Open a webcam and display the live predicted sign with confidence."""
    if model is None or label_encoder is None:
        load_model_artifacts()

    if pose_landmarker is None or hand_landmarker is None:
        create_landmarkers()

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Unable to open camera")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        result = predict_sign(frame)

        text = f"{result['sign']} ({result['probability']:.3f})"
        cv2.putText(
            frame,
            text,
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2,
        )
        cv2.imshow("SignBridge Live Prediction", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    run_camera()
