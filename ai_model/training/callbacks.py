import logging
from pathlib import Path
from typing import List, Union

import tensorflow as tf
from tensorflow.keras.callbacks import (
    Callback,
    CSVLogger,
    EarlyStopping,
    ModelCheckpoint,
    ReduceLROnPlateau,
    TensorBoard,
    TerminateOnNaN,
)

logger = logging.getLogger(__name__)


def get_callbacks(save_dir: Union[str, Path]) -> List[Callback]:
    """
    Configures and returns a list of standard TensorFlow Keras callbacks for training.

    This function automatically handles directory creation for model checkpoints,
    TensorBoard logs, and CSV training logs using `pathlib`.

    Args:
        save_dir: The root directory where all training artifacts (models, logs)
                    will be stored. Can be a string or a `pathlib.Path` object.

    Returns:
        A list of configured `tf.keras.callbacks.Callback` instances.

    Directory Structure Created:
        {save_dir}/
        ├── saved_model/
        │   └── best_model.keras
        ├── logs/
        └── training_log.csv
    """
    # Convert to Path object for robust cross-platform path manipulation
    save_dir = Path(save_dir)

    # Define and create necessary directories
    model_dir = save_dir / "saved_model"
    logs_dir = save_dir / "logs"

    try:
        model_dir.mkdir(parents=True, exist_ok=True)
        logs_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Successfully created/verified directories: %s, %s", model_dir, logs_dir)
    except OSError as e:
        logger.error("Failed to create directories: %s", e)
        raise

    # Define file paths
    best_model_path = model_dir / "best_model.keras"
    csv_log_path = save_dir / "training_log.csv"

    # Initialize callbacks list
    callbacks: List[Callback] = []

    # 1. Early Stopping
    early_stopping = EarlyStopping(
        monitor="val_loss",
        patience=10,
        restore_best_weights=True,
        mode="min",
        verbose=1,
    )
    callbacks.append(early_stopping)

    # 2. Reduce Learning Rate on Plateau
    reduce_lr = ReduceLROnPlateau(
        monitor="val_loss",
        factor=0.5,
        patience=5,
        min_lr=1e-6,
        verbose=1,
        mode="min",
    )
    callbacks.append(reduce_lr)

    # 3. Model Checkpoint
    # Note: Keras expects a string path for the filepath argument in some environments
    model_checkpoint = ModelCheckpoint(
        filepath=str(best_model_path),
        monitor="val_loss",
        save_best_only=True,
        save_weights_only=False,
        verbose=1,
        mode="min",
    )
    callbacks.append(model_checkpoint)
    logger.info("ModelCheckpoint configured to save best model to: %s", best_model_path)

    # 4. CSV Logger
    csv_logger = CSVLogger(
        filename=str(csv_log_path),
        separator=",",
        append=False,
    )
    callbacks.append(csv_logger)

    # 5. TensorBoard
    tensorboard = TensorBoard(
        log_dir=str(logs_dir),
        histogram_freq=1,
        write_graph=True,
        write_images=False,
        update_freq="epoch",
        profile_batch=0,
    )
    callbacks.append(tensorboard)
    logger.info("TensorBoard logs configured at: %s", logs_dir)

    # 6. Terminate on NaN
    terminate_on_nan = TerminateOnNaN()
    callbacks.append(terminate_on_nan)

    return callbacks