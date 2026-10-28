import json
import pickle

import numpy as np


def save_split(
    output_dir,
    name,
    X,
    y,
    filenames,
):
    """
    Save one dataset partition.
    """

    np.save(
        output_dir / f"X_{name}.npy",
        X,
    )

    np.save(
        output_dir / f"y_{name}.npy",
        y,
    )

    with open(
        output_dir / f"{name}_files.json",
        "w",
    ) as f:

        json.dump(
            filenames,
            f,
            indent=2,
        )


def save_encoder(output_dir, encoder):

    with open(
        output_dir / "label_encoder.pkl",
        "wb",
    ) as f:

        pickle.dump(
            encoder,
            f,
        )


def save_metadata(
    output_dir,
    train_groups,
    val_groups,
    test_groups,
):
    """
    Save exactly which recording groups went
    into each partition.
    """

    metadata = {
        "train_groups": [
            list(group)
            for group in train_groups
        ],
        "validation_groups": [
            list(group)
            for group in val_groups
        ],
        "test_groups": [
            list(group)
            for group in test_groups
        ],
    }

    with open(
        output_dir / "split_metadata.json",
        "w",
    ) as f:

        json.dump(
            metadata,
            f,
            indent=2,
        )