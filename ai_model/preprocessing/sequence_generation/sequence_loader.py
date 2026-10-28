import numpy as np

from .sequence_config import (
    EXPECTED_SHAPE,
    NUM_FRAMES,
    TARGET_FEATURES,
)


def load_sequence(filepath):
    """
    Load one normalized NPZ and flatten landmarks.

    Input:
        (20, 75, 4)

    Output:
        (20, 300)
    """

    data = np.load(filepath)

    if "arr_0" not in data:
        raise KeyError(
            f"'arr_0' not found in {filepath}"
        )

    sequence = data["arr_0"]

    if sequence.shape != EXPECTED_SHAPE:
        raise ValueError(
            f"{filepath}\n"
            f"Expected: {EXPECTED_SHAPE}\n"
            f"Found: {sequence.shape}"
        )

    sequence = sequence.astype(np.float32)

    if not np.isfinite(sequence).all():
        raise ValueError(
            f"NaN/Inf detected in {filepath}"
        )

    return sequence.reshape(
        NUM_FRAMES,
        TARGET_FEATURES,
    )


def load_dataset(files):
    """
    Load a list of normalized files.

    Returns:
        X       -> numpy array
        labels  -> class names
        names   -> relative filenames
    """

    X = []
    labels = []
    names = []

    for sample in files:

        X.append(
            load_sequence(
                sample["filepath"]
            )
        )

        labels.append(
            sample["class_name"]
        )

        names.append(
            f'{sample["class_name"]}/'
            f'{sample["filename"]}'
        )

    X = np.stack(X).astype(np.float32)

    return X, labels, names