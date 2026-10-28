from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
NORMALIZED_DIR = BASE_DIR / "datasets" / "normalized"

# done Experiment A
# EVALUATION_MODE = "original"

EVALUATION_MODE = "augmented"

OUTPUT_ROOT = BASE_DIR / "datasets"
if EVALUATION_MODE == "original":
    OUTPUT_DIR = OUTPUT_ROOT / "sequences_leakage_free_original"
else:
    OUTPUT_DIR = OUTPUT_ROOT / "sequences_leakage_free_augmented"

# Sequence configuration

NUM_FRAMES = 20
NUM_LANDMARKS = 75
NUM_FEATURES = 4

TARGET_FEATURES = NUM_LANDMARKS * NUM_FEATURES

EXPECTED_SHAPE = (
    NUM_FRAMES,
    NUM_LANDMARKS,
    NUM_FEATURES,
)


# Dataset split

TRAIN_RATIO = 0.70
VAL_RATIO = 0.15
TEST_RATIO = 0.15

RANDOM_STATE = 42


# Augmentation naming

AUGMENTATION_SUFFIXES = (
    "_bright",
    "_dark",
    "_rotate",
    "_zoom",
)
