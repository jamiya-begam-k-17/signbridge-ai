from pathlib import Path

from .sequence_config import (
    NORMALIZED_DIR,
    AUGMENTATION_SUFFIXES,
)


def get_base_recording(filename: str) -> str:
    """
    Remove augmentation suffix from filename.

    Example:
        how_are_you_001_zoom.npz
        -> how_are_you_001
    """

    stem = Path(filename).stem

    for suffix in AUGMENTATION_SUFFIXES:
        if stem.endswith(suffix):
            return stem[:-len(suffix)]

    return stem


def is_original(filename: str) -> bool:
    """
    Return True if the file has no augmentation suffix.
    """

    return get_base_recording(filename) == Path(filename).stem


def discover_samples():
    """
    Discover all normalized NPZ files.

    Returns:
        [
            {
                "class_name": ...,
                "filename": ...,
                "filepath": ...,
                "base_recording": ...,
                "is_original": ...
            }
        ]
    """

    samples = []

    for class_dir in sorted(NORMALIZED_DIR.iterdir()):

        if not class_dir.is_dir():
            continue

        for filepath in sorted(class_dir.glob("*.npz")):

            filename = filepath.name

            samples.append({
                "class_name": class_dir.name,
                "filename": filename,
                "filepath": filepath,
                "base_recording": get_base_recording(filename),
                "is_original": is_original(filename),
            })

    return samples


def group_recordings(samples):
    """
    Group original recordings with their augmented variants.

    Group key:
        (class_name, base_recording)
    """

    groups = {}

    for sample in samples:

        key = (
            sample["class_name"],
            sample["base_recording"],
        )

        groups.setdefault(key, []).append(sample)

    return groups


def get_original(group):
    """
    Return the single original NPZ from a group.
    """

    originals = [
        sample
        for sample in group
        if sample["is_original"]
    ]

    if len(originals) != 1:

        filenames = [
            sample["filename"]
            for sample in group
        ]

        raise ValueError(
            f"Expected exactly one original file.\n"
            f"Files: {filenames}"
        )

    return originals[0]