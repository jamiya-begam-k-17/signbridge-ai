import json
import logging
import shutil
from pathlib import Path
from typing import List, Tuple, Optional

import joblib
import numpy as np
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Constants derived from base dimensions for future scalability
NUM_FRAMES = 20
NUM_LANDMARKS = 75
NUM_FEATURES = 4

EXPECTED_SHAPE = (NUM_FRAMES, NUM_LANDMARKS, NUM_FEATURES)
TARGET_FEATURES = NUM_LANDMARKS * NUM_FEATURES
RANDOM_STATE = 42


def get_project_dirs() -> Tuple[Path, Path]:
    """Resolve input and output directories relative to this script's location."""
    base_dir = Path(__file__).resolve().parent.parent
    input_dir = base_dir / "datasets" / "normalized"
    output_dir = base_dir / "datasets" / "sequences"
    return input_dir, output_dir


def load_and_flatten_sequence(file_path: Path) -> Optional[np.ndarray]:
    """
    Loads a single .npz file, extracts the sequence, validates it,
    and dynamically flattens each frame from (landmarks, features) to N features.
    """
    try:
        with np.load(file_path) as data:
            sequence = data["arr_0"]
            
        # Validate shape
        if sequence.shape != EXPECTED_SHAPE:
            logger.error(f"Shape mismatch in {file_path.name}. Expected {EXPECTED_SHAPE}, got {sequence.shape}.")
            return None
            
        # Validate dtype
        if sequence.dtype != np.float32:
            logger.error(f"Dtype mismatch in {file_path.name}. Expected float32, got {sequence.dtype}.")
            return None

        # Validate for NaN or Inf
        if not np.all(np.isfinite(sequence)):
            logger.error(f"NaN/Inf detected in {file_path.name}.")
            return None

        # Dynamically flatten each frame: (frames, landmarks, features) -> (frames, -1)
        frames = sequence.shape[0]
        flattened_sequence = sequence.reshape(frames, -1)
        
        # Verify the flattened shape matches expectations
        if flattened_sequence.shape != (frames, TARGET_FEATURES):
            logger.error(f"Flatten failed for {file_path.name}. Expected {(frames, TARGET_FEATURES)}, got {flattened_sequence.shape}.")
            return None
        
        return flattened_sequence

    except Exception as e:
        logger.exception(f"Failed to load {file_path.name}: {e}")
        return None


def build_dataset(input_dir: Path) -> Tuple[List[np.ndarray], List[str], List[str], int]:
    """
    Iterates over all class directories and .npz files to build the dataset.
    Returns lists of sequences, string labels, filenames, plus a failure count.
    """
    sequences: List[np.ndarray] = []
    labels: List[str] = []
    filenames: List[str] = []
    failed_count = 0

    class_dirs = sorted([d for d in input_dir.iterdir() if d.is_dir()])
    
    if not class_dirs:
        logger.error("No class directories found in the input folder.")
        return sequences, labels, filenames, failed_count

    # Calculate total files for progress bar
    total_files = sum(len(list(cls_dir.glob("*.npz"))) for cls_dir in class_dirs)

    with tqdm(total=total_files, desc="Loading Sequences", unit="file") as pbar:
        for class_dir in class_dirs:
            class_name = class_dir.name
            npz_files = sorted(class_dir.glob("*.npz"))
            
            for npz_file in npz_files:
                seq = load_and_flatten_sequence(npz_file)
                
                if seq is not None:
                    sequences.append(seq)
                    labels.append(class_name)
                    filenames.append(npz_file.name)
                else:
                    failed_count += 1
                    
                pbar.set_postfix(Class=class_name, Failed=failed_count)
                pbar.update(1)

    return sequences, labels, filenames, failed_count


def main() -> None:
    """Main execution pipeline for sequence creation and dataset splitting."""
    input_dir, output_dir = get_project_dirs()

    if not input_dir.exists():
        logger.error(f"Input directory not found: {input_dir}")
        return

    # Clean output directory to prevent stale files from previous runs
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Build dataset
    X_list, y_list, filenames, failed_count = build_dataset(input_dir)

    if not X_list:
        logger.error("No valid sequences were loaded. Aborting.")
        return

    # Stack into final numpy arrays
    X = np.stack(X_list, axis=0).astype(np.float32)
    
    # Encode labels
    encoder = LabelEncoder()
    y = encoder.fit_transform(y_list)

    logger.info(f"Successfully loaded {len(X_list)} sequences. Failed: {failed_count}")

    # Validate final aggregated arrays
    if not np.all(np.isfinite(X)):
        logger.error("NaN/Inf detected in final X array.")
        return

    if not np.all(np.isfinite(y)):
        logger.error("NaN/Inf detected in final y array.")
        return

    # Save the full combined dataset
    np.save(output_dir / "X.npy", X)
    np.save(output_dir / "y.npy", y)

    # Save label mapping
    label_mapping = {str(i): label for i, label in enumerate(encoder.classes_)}
    mapping_path = output_dir / "label_mapping.json"
    with open(mapping_path, "w", encoding="utf-8") as f:
        json.dump(label_mapping, f, indent=4)
    logger.info(f"Label mapping saved to {mapping_path}")

    # Save the LabelEncoder object for future inference scalability
    joblib.dump(encoder, output_dir / "label_encoder.pkl")

    # Train (70%) / Validation (15%) / Test (15%) Split
    indices = np.arange(len(y))

    # First split: Train (70%) and Temp (30%)
    train_idx, temp_idx, y_train_temp, y_temp = train_test_split(
        indices,
        y,
        test_size=0.30,
        stratify=y,
        random_state=RANDOM_STATE
    )

    # Second split: Temp -> Validation (15%) + Test (15%)
    val_idx, test_idx, _, _ = train_test_split(
        temp_idx,
        y_temp,
        test_size=0.50,
        stratify=y_temp,
        random_state=RANDOM_STATE
    )

    X_train = X[train_idx]
    y_train = y[train_idx]

    X_val = X[val_idx]
    y_val = y[val_idx]

    X_test = X[test_idx]
    y_test = y[test_idx]

    # Save splits
    np.save(output_dir / "X_train.npy", X_train)
    np.save(output_dir / "y_train.npy", y_train)

    np.save(output_dir / "X_val.npy", X_val)
    np.save(output_dir / "y_val.npy", y_val)

    np.save(output_dir / "X_test.npy", X_test)
    np.save(output_dir / "y_test.npy", y_test)

    # Save train/test split information and corresponding filenames
    split_info = {
        "random_state": RANDOM_STATE,
        "train_size": len(X_train),
        "validation_size": len(X_val),
        "test_size": len(X_test),

        "train_files": [filenames[i] for i in train_idx],
        "validation_files": [filenames[i] for i in val_idx],
        "test_files": [filenames[i] for i in test_idx]
    }
    split_info_path = output_dir / "split_info.json"
    with open(split_info_path, "w", encoding="utf-8") as f:
        json.dump(split_info, f, indent=4)

    # Generate dataset summary
    summary = {
        "classes": len(encoder.classes_),
        "samples": len(X),
        "train": len(X_train),
        "validation": len(X_val),
        "test": len(X_test),
        "sequence_length": NUM_FRAMES,
        "features": TARGET_FEATURES
    }

    summary_path = output_dir / "dataset_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=4)

    logger.info("=" * 50)
    logger.info("Sequence Creation Complete.")
    logger.info(f"Total Samples: {summary['samples']}")
    logger.info(f"Train Samples: {summary['train']}")
    logger.info(f"Validation Samples: {summary['validation']}")
    logger.info(f"Test Samples: {summary['test']}")
    logger.info(f"X shape: {X.shape} | dtype: {X.dtype}")
    logger.info(f"Summary saved to: {summary_path}")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()