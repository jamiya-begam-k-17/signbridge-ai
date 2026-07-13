import json
import logging
import random
import shutil
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Constants for landmark slicing
POSE_START, POSE_END = 0, 33
L_HAND_START, L_HAND_END = 33, 54
R_HAND_START, R_HAND_END = 54, 75

# MediaPipe Holistic landmark indices
LEFT_SHOULDER_IDX = 11
RIGHT_SHOULDER_IDX = 12

# Dataset processing constants
EXPECTED_SHAPE = (20, 75, 4)
RANDOM_SEED = 42
EPSILON = 1e-8


def get_project_dirs() -> Tuple[Path, Path]:
    """Resolve input and output directories relative to this script's location."""
    base_dir = Path(__file__).resolve().parent.parent
    input_dir = base_dir / "datasets" / "landmarks"
    output_dir = base_dir / "datasets" / "normalized"
    return input_dir, output_dir


def select_landmark_files(class_dir: Path) -> List[Path]:
    """Return all available .npz landmark files in a class directory."""
    return sorted([f for f in class_dir.iterdir() if f.suffix.lower() == ".npz"])


def normalize_pose(pose_landmarks: np.ndarray) -> np.ndarray:
    """
    Normalizes pose landmarks by translating the shoulder midpoint to the origin
    and scaling by the distance between the shoulders.
    """
    coords = pose_landmarks[:, :3].copy()
    vis = pose_landmarks[:, 3:4]

    l_shoulder = coords[LEFT_SHOULDER_IDX]
    r_shoulder = coords[RIGHT_SHOULDER_IDX]

    # If shoulders are missing (zeros), skip scaling for this frame
    if np.all(l_shoulder == 0) or np.all(r_shoulder == 0):
        return pose_landmarks.copy()

    # Translate so shoulder midpoint is (0, 0, 0)
    midpoint = (l_shoulder + r_shoulder) / 2.0
    coords -= midpoint

    # Scale by shoulder distance
    shoulder_dist = np.linalg.norm(l_shoulder - r_shoulder)
    if shoulder_dist > EPSILON:
        coords /= shoulder_dist

    return np.hstack((coords, vis)).astype(np.float32)


def normalize_hand(hand_landmarks: np.ndarray) -> np.ndarray:
    """
    Normalizes hand landmarks by translating the wrist to the origin
    and scaling by the maximum distance from the wrist to any visible landmark.
    """
    wrist_coord = hand_landmarks[0, :3]

    # If wrist is missing, leave that hand as zeros
    if np.all(wrist_coord == 0):
        return hand_landmarks.copy()

    coords = hand_landmarks[:, :3].copy()
    vis = hand_landmarks[:, 3:4]

    # Translate relative to the wrist
    coords -= wrist_coord

    # Determine max distance to visible landmarks
    vis_mask = hand_landmarks[:, 3] > 0
    if np.any(vis_mask):
        visible_coords = coords[vis_mask]
        max_dist = np.max(np.linalg.norm(visible_coords, axis=1))
    else:
        # Fallback if no visibility info, but wrist was present
        max_dist = np.max(np.linalg.norm(coords, axis=1))

    # Scale if a valid distance is found (prevents divide by zero)
    if max_dist > EPSILON:
        coords /= max_dist

    return np.hstack((coords, vis)).astype(np.float32)


def normalize_sequence(sequence: np.ndarray) -> np.ndarray:
    """
    Applies normalization to the pose, left hand, and right hand 
    for every frame in the sequence.
    """
    normalized_seq = sequence.copy()
    
    for i in range(normalized_seq.shape[0]):
        frame = normalized_seq[i]
        
        # Normalize Pose (indices 0-32)
        frame[POSE_START:POSE_END] = normalize_pose(frame[POSE_START:POSE_END])
        
        # Normalize Left Hand (indices 33-53)
        frame[L_HAND_START:L_HAND_END] = normalize_hand(frame[L_HAND_START:L_HAND_END])
        
        # Normalize Right Hand (indices 54-74)
        frame[R_HAND_START:R_HAND_END] = normalize_hand(frame[R_HAND_START:R_HAND_END])
        
    return normalized_seq


def process_video(file_path: Path, output_path: Path) -> bool:
    """Loads a single .npz file, normalizes it, and saves it preserving other metadata."""
    try:
        # Load compressed NumPy archive and preserve all existing arrays/metadata
        data = np.load(file_path)
        save_dict = dict(data)
        
        sequence = data["arr_0"].astype(np.float32)
        
        # Validate expected shape
        if sequence.shape != EXPECTED_SHAPE:
            logger.error(f"Unexpected shape {sequence.shape} in {file_path.name}. Expected {EXPECTED_SHAPE}. Skipping.")
            return False

        # Apply normalization pipeline
        normalized_sequence = normalize_sequence(sequence)

        # Safeguard assertions
        assert normalized_sequence.shape == EXPECTED_SHAPE, f"Shape mismatch after normalization: {normalized_sequence.shape}"
        assert normalized_sequence.dtype == np.float32, f"Dtype mismatch after normalization: {normalized_sequence.dtype}"

        # Enforce dtype before saving
        save_dict["arr_0"] = normalized_sequence.astype(np.float32)

        # Save compressed .npz
        np.savez_compressed(output_path, **save_dict)
        return True

    except Exception as e:
        logger.exception(f"Failed to process {file_path.name}: {e}")
        return False


def main() -> None:
    """Main execution pipeline for balanced dataset normalization."""
    # Set random seed for reproducible class balancing
    random.seed(RANDOM_SEED)

    input_dir, output_dir = get_project_dirs()

    if not input_dir.exists():
        logger.error(f"Input directory not found: {input_dir}")
        return

    # Clean output folder to prevent stale files from previous runs
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Gather class directories
    class_dirs = sorted([d for d in input_dir.iterdir() if d.is_dir()])
    if not class_dirs:
        logger.error("No class directories found in the input folder.")
        return

    total_processed = 0
    total_failed = 0
    total_selected = 0
    selected_videos_map: Dict[str, List[str]] = {}
    videos_per_class: Dict[str, int] = {}

    # First pass: Count total selected videos and track selections for a unified progress bar
    all_tasks: List[Tuple[Path, Path, str, int, int]] = []
    
    for class_idx, class_dir in enumerate(class_dirs, start=1):
        class_name = class_dir.name
        selected_files = select_landmark_files(class_dir)
        
        # Record selected videos for reproducibility metadata
        selected_videos_map[class_name] = [f.name for f in selected_files]
        videos_per_class[class_name] = len(selected_files)
        
        out_class_dir = output_dir / class_name
        out_class_dir.mkdir(parents=True, exist_ok=True)
        
        for vid_idx, vid_file in enumerate(selected_files, start=1):
            out_file = out_class_dir / vid_file.name
            all_tasks.append((vid_file, out_file, class_name, class_idx, vid_idx))
            
    total_selected = len(all_tasks)
    total_classes = len(class_dirs)

    # Second pass: Process with a single progress bar
    with tqdm(total=total_selected, desc="Normalizing Landmarks", unit="video") as pbar:
        for vid_path, out_path, class_name, class_idx, vid_idx in all_tasks:
            logger.info(f"[{class_idx}/{total_classes}] {class_name} ({vid_idx}/{len(selected_files)})")
            
            success = process_video(vid_path, out_path)
            
            if success:
                total_processed += 1
            else:
                total_failed += 1

            pbar.set_postfix(
                Processed=total_processed, 
                Failed=total_failed
            )
            pbar.update(1)

    # Generate normalized_summary.json with reproducibility tracking
    summary = {
        "classes": total_classes,
        "videos_selected": total_selected,
        "videos_per_class": videos_per_class,
        "processed": total_processed,
        "failed": total_failed,
        "random_seed": RANDOM_SEED,
        "selected_videos": selected_videos_map
    }

    summary_path = output_dir / "normalized_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=4)

    logger.info("=" * 50)
    logger.info("Normalization Complete.")
    logger.info(f"Total Videos Selected: {total_selected}")
    logger.info(f"Total Processed Successfully: {total_processed}")
    logger.info(f"Total Failed: {total_failed}")
    logger.info(f"Summary saved to: {summary_path}")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()