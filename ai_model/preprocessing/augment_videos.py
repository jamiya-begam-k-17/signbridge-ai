import logging
import json
from pathlib import Path
from typing import Dict, List, Tuple

import cv2
from tqdm import tqdm

import shutil

# ==============================================================================
# Constants
# ==============================================================================
BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "datasets" / "raw"
AUG_DIR = BASE_DIR / "datasets" / "augmented"

SUPPORTED_FORMATS: Tuple[str, ...] = (".mp4", ".mov", ".avi")

BRIGHTNESS_FACTOR: float = 1.15
DARKNESS_FACTOR: float = 0.85
ROTATION_ANGLE: float = 5.0
ZOOM_FACTOR: float = 1.05

AUGMENTATION_TYPES: List[str] = [
    "original_copy",
    "brightness",
    "darkness",
    "rotation",
    "zoom"
]

# ==============================================================================
# Logging Configuration
# ==============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def apply_brightness(frame: cv2.Mat) -> cv2.Mat:
    """Increase frame brightness by a constant factor."""
    return cv2.convertScaleAbs(frame, alpha=BRIGHTNESS_FACTOR, beta=0)


def apply_darkness(frame: cv2.Mat) -> cv2.Mat:
    """Decrease frame brightness by a constant factor."""
    return cv2.convertScaleAbs(frame, alpha=DARKNESS_FACTOR, beta=0)


def apply_rotation(frame: cv2.Mat, matrix: cv2.Mat, dims: Tuple[int, int]) -> cv2.Mat:
    """Apply pre-calculated rotation matrix to a frame."""
    return cv2.warpAffine(frame, matrix, dims, borderMode=cv2.BORDER_REFLECT_101)


def apply_zoom(frame: cv2.Mat, target_dims: Tuple[int, int]) -> cv2.Mat:
    """Center crop and resize to simulate zooming in."""
    h, w = frame.shape[:2]
    target_w, target_h = target_dims
    
    new_h = int(h / ZOOM_FACTOR)
    new_w = int(w / ZOOM_FACTOR)
    
    y1 = (h - new_h) // 2
    x1 = (w - new_w) // 2
    
    cropped = frame[y1 : y1 + new_h, x1 : x1 + new_w]
    return cv2.resize(cropped, (target_w, target_h), interpolation=cv2.INTER_LINEAR)


def process_single_video(
    video_path: Path,
    output_dir: Path,
    class_name: str,
    stats: Dict[str, int]
) -> None:
    """
    Read a single video, apply transformations, and save outputs.
    Updates stats dictionary in place for processed/failed counts.
    """
    cap = cv2.VideoCapture(str(video_path))
    
    if not cap.isOpened():
        logger.error(f"[{class_name}] Failed to open video: {video_path.name}")
        stats["failed"] += 1
        return

    # Extract original video metadata
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    
    dims = (width, height)
    stem = video_path.stem
    suffix = ".mp4"

    # Pre-compute transformation matrices (constant for all frames in this video)
    cx, cy = width / 2, height / 2
    rot_matrix = cv2.getRotationMatrix2D((cx, cy), ROTATION_ANGLE, 1.0)

    # Define output paths
    paths = {
        "original": output_dir / f"{stem}{suffix}",
        "bright": output_dir / f"{stem}_bright{suffix}",
        "dark": output_dir / f"{stem}_dark{suffix}",
        "rot": output_dir / f"{stem}_rotate{suffix}",
        "zoom": output_dir / f"{stem}_zoom{suffix}",
    }

    # Initialize writers
    writers = {
        "original": cv2.VideoWriter(str(paths["original"]), fourcc, fps, dims),
        "bright": cv2.VideoWriter(str(paths["bright"]), fourcc, fps, dims),
        "dark": cv2.VideoWriter(str(paths["dark"]), fourcc, fps, dims),
        "rot": cv2.VideoWriter(str(paths["rot"]), fourcc, fps, dims),
        "zoom": cv2.VideoWriter(str(paths["zoom"]), fourcc, fps, dims),
    }


    try:
        for name, writer in writers.items():
            if not writer.isOpened():
                raise RuntimeError(
                    f"Failed to create VideoWriter for '{name}' augmentation: {paths[name]}"
                )
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            writers["original"].write(frame)
            writers["bright"].write(apply_brightness(frame))
            writers["dark"].write(apply_darkness(frame))
            writers["rot"].write(apply_rotation(frame, rot_matrix, dims))
            writers["zoom"].write(apply_zoom(frame, dims))

        stats["processed"] += 1
        stats["augmented_videos_generated"] += 4  # Excluding the original copy
        tqdm.write(f"[{class_name}] Processed: {video_path.name}")

    except Exception as e:
        logger.error(f"[{class_name}] Error processing {video_path.name}: {e}", exc_info=True)
        stats["failed"] += 1
        stats["processed"] -= 0  # Ensure it wasn't falsely incremented
        
        # Clean up partially written files on failure
        for path in paths.values():
            if path.exists():
                path.unlink()

    finally:
        cap.release()
        for writer in writers.values():
            writer.release()


def process_class(class_dir: Path, output_class_dir: Path, stats: Dict[str, int]) -> None:
    """Find all videos in a class directory and process them."""
    class_name = class_dir.name
    output_class_dir.mkdir(parents=True, exist_ok=True)
    
    videos = [v for v in class_dir.iterdir() if v.is_file() and v.suffix.lower() in SUPPORTED_FORMATS]
    
    for video_path in tqdm(videos, desc=f"Class: {class_name}", leave=False):
        process_single_video(video_path, output_class_dir, class_name, stats)


def save_summary(stats: Dict[str, int], output_path: Path) -> None:
    """Save the augmentation summary statistics to a JSON file."""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=4)
    logger.info(f"Augmentation summary saved to {output_path}")


def main() -> None:
    """Main execution pipeline for video augmentation."""
    if AUG_DIR.exists():
        shutil.rmtree(AUG_DIR)

    if not RAW_DIR.exists():
        logger.error(f"Raw dataset directory not found: {RAW_DIR}")
        return

    AUG_DIR.mkdir(parents=True, exist_ok=True)

    stats: Dict[str, int] = {
        "total_classes": 0,
        "original_videos": 0,
        "augmented_videos_generated": 0,
        "processed": 0,
        "failed": 0,
        "augmentation_types": AUGMENTATION_TYPES
    }

    class_dirs = [d for d in RAW_DIR.iterdir() if d.is_dir()]
    stats["total_classes"] = len(class_dirs)

    logger.info(f"Starting augmentation. Found {stats['total_classes']} classes.")

    for class_dir in tqdm(class_dirs, desc="Overall Progress"):
        output_class_dir = AUG_DIR / class_dir.name
        
        videos = [v for v in class_dir.iterdir() if v.is_file() and v.suffix.lower() in SUPPORTED_FORMATS]
        stats["original_videos"] += len(videos)
        
        process_class(class_dir, output_class_dir, stats)

    summary_path = AUG_DIR / "augmentation_summary.json"
    save_summary(stats, summary_path)
    
    logger.info("="*50)
    logger.info("Augmentation Pipeline Finished.")
    logger.info(f"Total Classes      : {stats['total_classes']}")
    logger.info(f"Original Videos    : {stats['original_videos']}")
    logger.info(f"Augmented Created  : {stats['augmented_videos_generated']}")
    logger.info(f"Successfully Proc. : {stats['processed']}")
    logger.info(f"Failed             : {stats['failed']}")
    logger.info("="*50)


if __name__ == "__main__":
    main()