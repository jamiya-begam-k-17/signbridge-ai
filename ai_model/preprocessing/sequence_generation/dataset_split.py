from sklearn.model_selection import train_test_split

from .sequence_config import (
    TRAIN_RATIO,
    VAL_RATIO,
    TEST_RATIO,
    RANDOM_STATE,
)
from .dataset_groups import get_original

from .sequence_config import EVALUATION_MODE


def split_groups(groups):
    """
    Split original recording GROUPS.

    Never split individual augmented files.
    """

    group_keys = list(groups.keys())

    labels = [
        key[0]
        for key in group_keys
    ]

    # 70% train / 30% temporary
    train_groups, temp_groups = train_test_split(
        group_keys,
        test_size=1.0 - TRAIN_RATIO,
        stratify=labels,
        random_state=RANDOM_STATE,
    )

    temp_labels = [
        key[0]
        for key in temp_groups
    ]

    # Split remaining 30% equally:
    # 15% validation / 15% test
    test_fraction = (
        TEST_RATIO /
        (VAL_RATIO + TEST_RATIO)
    )

    val_groups, test_groups = train_test_split(
        temp_groups,
        test_size=test_fraction,
        stratify=temp_labels,
        random_state=RANDOM_STATE,
    )

    return (
        sorted(train_groups),
        sorted(val_groups),
        sorted(test_groups),
    )

def build_file_lists(
    groups,
    train_groups,
    val_groups,
    test_groups,
):
    """
    Training always contains all variants.

    Evaluation mode:
        original  -> validation/test use originals only
        augmented -> validation/test use all variants
    """

    train_files = []
    val_files = []
    test_files = []

    # -----------------------------------------
    # Training
    # -----------------------------------------

    for key in train_groups:
        train_files.extend(groups[key])

    # -----------------------------------------
    # Validation / Test
    # -----------------------------------------

    if EVALUATION_MODE == "original":

        for key in val_groups:
            val_files.append(
                get_original(groups[key])
            )

        for key in test_groups:
            test_files.append(
                get_original(groups[key])
            )

    elif EVALUATION_MODE == "augmented":

        for key in val_groups:
            val_files.extend(groups[key])

        for key in test_groups:
            test_files.extend(groups[key])

    else:
        raise ValueError(
            f"Unknown EVALUATION_MODE: "
            f"{EVALUATION_MODE}"
        )

    return (
        train_files,
        val_files,
        test_files,
    )

def check_leakage(
    train_files,
    val_files,
    test_files,
):
    """
    Verify that no original recording appears
    in more than one partition.
    """

    def groups(files):
        return {
            (
                item["class_name"],
                item["base_recording"],
            )
            for item in files
        }

    train = groups(train_files)
    val = groups(val_files)
    test = groups(test_files)

    if train & val:
        raise RuntimeError(
            "Leakage detected between train and validation."
        )

    if train & test:
        raise RuntimeError(
            "Leakage detected between train and test."
        )

    if val & test:
        raise RuntimeError(
            "Leakage detected between validation and test."
        )

    print("✓ No recording-level leakage detected.")