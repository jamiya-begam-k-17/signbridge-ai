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


def get_callbacks(save_dir: Union[str, Path]) -> List[Callback]:
    save_dir = Path(save_dir)
    model_dir = save_dir / "saved_model"
    logs_dir = save_dir / "logs"

    model_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    return [
        EarlyStopping(
            monitor="val_loss",
            patience=10,
            restore_best_weights=True,
            mode="min",
            verbose=1,
        ),
        ReduceLROnPlateau(
            monitor="val_loss",
            factor=0.5,
            patience=5,
            min_lr=1e-6,
            mode="min",
            verbose=1,
        ),
        ModelCheckpoint(
            filepath=str(model_dir / "best_model.keras"),
            monitor="val_loss",
            save_best_only=True,
            save_weights_only=False,
            mode="min",
            verbose=1,
        ),
        ModelCheckpoint(
            filepath=str(save_dir / "saved_model" / "last_model.keras"),
            save_best_only=False,
            verbose=0,
        ),
        CSVLogger(str(save_dir / "training_log.csv"), append=False),
        TensorBoard(
            log_dir=str(logs_dir),
            histogram_freq=1,
            write_graph=True,
            update_freq="epoch",
            profile_batch=0,
        ),
        TerminateOnNaN(),
    ]
