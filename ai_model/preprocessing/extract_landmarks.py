import os
import json
import logging
from pathlib import Path
from typing import Tuple, Dict, List, Any

import cv2
import numpy as np

import mediapipe as mp

from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import (
    HandLandmarker,
    HandLandmarkerOptions,
    PoseLandmarker,
    PoseLandmarkerOptions,
    RunningMode,
)

from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Constants
NUM_FRAMES = 20
IMG_SIZE = (224, 224)
LANDMARK_SHAPE = (75, 4)  # 75 landmarks, 4 values (x, y, z, visibility)
SEQUENCE_LENGTH = NUM_FRAMES
LANDMARK_COUNT = LANDMARK_SHAPE[0]
FEATURE_COUNT = LANDMARK_SHAPE[1]
DTYPE = np.float32
SUPPORTED_EXTENSIONS = {".mp4", ".mov"}
MODEL_DIR = Path(__file__).resolve().parent.parent / "assets" / "models"
POSE_MODEL_PATH = MODEL_DIR / "pose_landmarker_full.task"
HAND_MODEL_PATH = MODEL_DIR / "hand_landmarker.task"

# Landmark indices mapping
POSE_START = 0
POSE_END = 33
LEFT_HAND_START = 33
LEFT_HAND_END = 54
RIGHT_HAND_START = 54
RIGHT_HAND_END = 75


def get_project_dirs() -> Tuple[Path, Path, Path]:
    """Resolve project directories relative to this script's location."""
    base_dir = Path(__file__).resolve().parent.parent
    raw_dir = base_dir / "datasets" / "augmented"
    landmarks_dir = base_dir / "datasets" / "landmarks"
    metadata_dir = base_dir / "datasets" / "metadata"
    
    # Ensure output directories exist
    landmarks_dir.mkdir(parents=True, exist_ok=True)
    metadata_dir.mkdir(parents=True, exist_ok=True)
    
    return raw_dir, landmarks_dir, metadata_dir


def create_landmarkers() -> Tuple[Any, Any]:
    """Create MediaPipe Tasks API pose and hand landmarkers."""
    if not POSE_MODEL_PATH.exists():
        raise FileNotFoundError(f"Pose model not found: {POSE_MODEL_PATH}")
    if not HAND_MODEL_PATH.exists():
        raise FileNotFoundError(f"Hand model not found: {HAND_MODEL_PATH}")

    pose_options = PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(POSE_MODEL_PATH)),
        running_mode=RunningMode.IMAGE,
        min_pose_detection_confidence=0.5,
        min_pose_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    hand_options = HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(HAND_MODEL_PATH)),
        running_mode=RunningMode.IMAGE,
        num_hands=2,
        min_hand_detection_confidence=0.5,
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )

    pose_landmarker = PoseLandmarker.create_from_options(pose_options)
    hand_landmarker = HandLandmarker.create_from_options(hand_options)
    return pose_landmarker, hand_landmarker


def extract_landmarks_from_results(
    pose_result: Any,
    hand_result: Any,
) -> np.ndarray:
    """
    Extracts Pose, Left Hand, and Right Hand landmarks from MediaPipe Tasks API results.
    Missing landmarks are filled with zeros. Hand visibility is hardcoded to 1.0.
    """
    landmarks = np.zeros(LANDMARK_SHAPE, dtype=DTYPE)

    if pose_result.pose_landmarks:
        pose_landmarks = pose_result.pose_landmarks[0]
        for i, lm in enumerate(pose_landmarks):
            visibility = getattr(lm, "visibility", 1.0)
            landmarks[POSE_START + i] = [lm.x, lm.y, lm.z, visibility]

    hand_landmarks_by_side = {"left": None, "right": None}
    if hand_result.hand_landmarks:
        for idx, hand_landmarks in enumerate(hand_result.hand_landmarks):
            handedness = "unknown"
            if hand_result.handedness and len(hand_result.handedness) > idx:
                handedness = hand_result.handedness[idx][0].category_name.lower()

            if handedness == "left":
                hand_landmarks_by_side["left"] = hand_landmarks
            elif handedness == "right":
                hand_landmarks_by_side["right"] = hand_landmarks
            elif hand_landmarks_by_side["left"] is None:
                hand_landmarks_by_side["left"] = hand_landmarks
            elif hand_landmarks_by_side["right"] is None:
                hand_landmarks_by_side["right"] = hand_landmarks

    if hand_landmarks_by_side["left"] is not None:
        for i, lm in enumerate(hand_landmarks_by_side["left"]):
            landmarks[LEFT_HAND_START + i] = [lm.x, lm.y, lm.z, 1.0]

    if hand_landmarks_by_side["right"] is not None:
        for i, lm in enumerate(hand_landmarks_by_side["right"]):
            landmarks[RIGHT_HAND_START + i] = [lm.x, lm.y, lm.z, 1.0]

    return landmarks


def process_video(
    video_path: Path,
    pose_landmarker: Any,
    hand_landmarker: Any,
    label: str
) -> Tuple[np.ndarray, Dict[str, Any], bool]:
    """
    Reads a video, samples 20 frames, extracts landmarks, and returns the array and metadata.
    Returns a tuple of (landmark_array, metadata_dict, success_flag).
    """
    cap = cv2.VideoCapture(str(video_path))
    
    if not cap.isOpened():
        logger.error(f"Failed to open video: {video_path.name}")
        return np.zeros((NUM_FRAMES, *LANDMARK_SHAPE), dtype=DTYPE), {}, False

    # Extract metadata before processing
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    metadata = {
        "video_name": video_path.name,
        "label": label,
        "frames": NUM_FRAMES,
        "sequence_length": SEQUENCE_LENGTH,
        "landmarks": LANDMARK_COUNT,
        "features": FEATURE_COUNT,
        "fps": fps,
        "width": width,
        "height": height,
        "output_file": f"{video_path.stem}.npz",
        "mediapipe_version": getattr(mp, "__version__", "unknown")
    }

    # Handle corrupted or empty video headers
    if total_frames <= 0:
        logger.warning(f"Video has 0 frames reported in header: {video_path.name}")
        cap.release()
        return np.zeros((NUM_FRAMES, *LANDMARK_SHAPE), dtype=DTYPE), metadata, False

    # Calculate frame indices to sample
    # If total_frames < NUM_FRAMES, linspace naturally duplicates the last frame indices
    frame_indices = np.linspace(0, total_frames - 1, NUM_FRAMES, dtype=int)
    
    video_landmarks = []
    success = True

    for idx in frame_indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()

        if not ret:
            # Missing or corrupted frame at this index
            logger.warning(f"Missing frame at index {idx} in {video_path.name}. Filling with zeros.")
            video_landmarks.append(np.zeros(LANDMARK_SHAPE, dtype=DTYPE))
            success = False
            continue

        try:
            # Resize frame to 224x224
            frame = cv2.resize(frame, IMG_SIZE, interpolation=cv2.INTER_AREA)
            
            # Convert BGR to RGB for MediaPipe Tasks API
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = mp.Image(
                image_format=mp.ImageFormat.SRGB,
                data=frame_rgb
            )
            
            pose_result = pose_landmarker.detect(image)
            hand_result = hand_landmarker.detect(image)
            
            # Extract the 75 required landmarks
            frame_landmarks = extract_landmarks_from_results(pose_result, hand_result)
            video_landmarks.append(frame_landmarks)

        except Exception as e:
            logger.error(f"MediaPipe processing failed for frame {idx} in {video_path.name}: {e}")
            video_landmarks.append(np.zeros(LANDMARK_SHAPE, dtype=DTYPE))
            success = False

    cap.release()

    # Stack frames into (20, 75, 4)
    final_landmarks = np.stack(video_landmarks, axis=0).astype(DTYPE)
    return final_landmarks, metadata, success


def write_output_files(metadata_dir: Path, metadata_records: List[Dict[str, Any]], total_processed: int, total_failed: int) -> None:
    """Persist metadata records and a compact processing summary."""
    metadata_path = metadata_dir / "metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata_records, f, indent=4)

    summary = {
        "classes": len({record["label"] for record in metadata_records if "label" in record}),
        "videos": len(metadata_records),
        "sequence_length": SEQUENCE_LENGTH,
        "landmarks": LANDMARK_COUNT,
        "processed": total_processed,
        "failed": total_failed,
    }

    summary_path = metadata_dir / "summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=4)


def main() -> None:
    """Main execution pipeline for SignBridge AI landmark extraction."""
    raw_dir, landmarks_dir, metadata_dir = get_project_dirs()

    if not raw_dir.exists():
        logger.error(f"Raw dataset directory not found: {raw_dir}")
        write_output_files(metadata_dir, [], 0, 0)
        return

    pose_landmarker, hand_landmarker = create_landmarkers()

    try:
        # Collect all valid video paths
        video_tasks: List[Tuple[Path, str]] = []
        for class_dir in sorted(raw_dir.iterdir()):
            if class_dir.is_dir():
                label = class_dir.name
                for vid_path in sorted(class_dir.iterdir()):
                    if vid_path.suffix.lower() in SUPPORTED_EXTENSIONS:
                        video_tasks.append((vid_path, label))

        if not video_tasks:
            logger.warning("No videos found in the raw dataset directory.")
            write_output_files(metadata_dir, [], 0, 0)
            return

        total_processed = 0
        total_failed = 0
        metadata_records: List[Dict[str, Any]] = []

        # Process all videos with a single progress bar
        with tqdm(total=len(video_tasks), desc="Extracting Landmarks", unit="video") as pbar:
            for video_path, label in video_tasks:
                tqdm.write(f"Processing class '{label}' | Video: {video_path.name}")
                
                try:
                    landmarks_array, metadata, success = process_video(video_path, pose_landmarker, hand_landmarker, label)
                    
                    # Create label-specific output directory
                    out_dir = landmarks_dir / label
                    out_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Save the numpy array
                    out_path = out_dir / metadata["output_file"]
                    np.savez_compressed(out_path, landmarks_array)
                    
                    # Append metadata
                    metadata_records.append(metadata)
                    
                    if success:
                        total_processed += 1
                    else:
                        total_failed += 1
                        logger.warning(f"Processed with errors (saved zeros for missing parts): {video_path.name}")

                except Exception as e:
                    total_failed += 1
                    logger.error(f"Completely failed to process video {video_path.name}: {e}", exc_info=True)
                    
                    # Still append metadata to track the failure if possible
                    metadata_records.append({
                        "video_name": video_path.name,
                        "label": label,
                        "frames": 0,
                        "sequence_length": SEQUENCE_LENGTH,
                        "landmarks": LANDMARK_COUNT,
                        "features": FEATURE_COUNT,
                        "fps": 0.0,
                        "width": 0,
                        "height": 0,
                        "output_file": f"{video_path.stem}.npz",
                        "mediapipe_version": getattr(mp, "__version__", "unknown"),
                        "error": str(e)
                    })

                # Update progress bar
                pbar.set_postfix(
                    Class=label, 
                    Processed=total_processed, 
                    Failed=total_failed
                )
                pbar.update(1)
    finally:
        pose_landmarker.close()
        hand_landmarker.close()

    write_output_files(metadata_dir, metadata_records, total_processed, total_failed)

    metadata_path = metadata_dir / "metadata.json"
    summary_path = metadata_dir / "summary.json"

    logger.info("="*50)
    logger.info("Extraction Complete.")
    logger.info(f"Total Videos Processed Successfully: {total_processed}")
    logger.info(f"Total Videos Failed/Partial: {total_failed}")
    logger.info(f"Metadata saved to: {metadata_path}")
    logger.info(f"Summary saved to: {summary_path}")
    logger.info("="*50)


if __name__ == "__main__":
    main()
