import os

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

import json
import logging
import time
from pathlib import Path
from typing import Any, Tuple

import joblib
import numpy as np
import tensorflow as tf

from models.tcn import build_tcn_model
from training.callbacks import get_callbacks
from training.evaluate import (
    accuracy,
    classification_report,
    confusion_matrix,
    f1_score,
    precision,
    recall,
)
from training.utils import (
    count_model_parameters,
    create_directory,
    plot_training_history,
    save_json,
    save_training_history,
    seed_everything,
)

SEED = 42
BATCH_SIZE = 16
EPOCHS = 100
LEARNING_RATE = 3e-4

DATASET_DIR = Path("datasets/sequences_leakage_free_original")
SAVE_DIR = Path("saved_model_original")

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def setup_hardware() -> None:
    gpus = tf.config.list_physical_devices("GPU")
    for gpu in gpus:
        try:
            tf.config.experimental.set_memory_growth(gpu, True)
        except RuntimeError as exc:
            logger.warning("GPU setup failed: %s", exc)

    logger.info("GPU(s) detected: %d", len(gpus))


def load_data(
    dataset_dir: Path,
) -> Tuple[
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    Any,
]:
    files = {
        "X_train": "X_train.npy",
        "y_train": "y_train.npy",
        "X_val": "X_val.npy",
        "y_val": "y_val.npy",
        "X_test": "X_test.npy",
        "y_test": "y_test.npy",
    }

    data = {
        name: np.load(dataset_dir / filename)
        for name, filename in files.items()
    }
    label_encoder = joblib.load(dataset_dir / "label_encoder.pkl")

    return (
        data["X_train"],
        data["y_train"],
        data["X_val"],
        data["y_val"],
        data["X_test"],
        data["y_test"],
        label_encoder,
    )


def validate_data(
    X_train: np.ndarray,
    X_val: np.ndarray,
    X_test: np.ndarray,
    y_train: np.ndarray,
    y_val: np.ndarray,
    y_test: np.ndarray,
    num_classes: int,
) -> None:
    for name, X in (
        ("train", X_train),
        ("validation", X_val),
        ("test", X_test),
    ):
        if X.ndim != 3 or X.shape[1:] != (20, 300):
            raise ValueError(
                f"{name} data must have shape (N, 20, 300), got {X.shape}"
            )

    for name, X, y in (
        ("train", X_train, y_train),
        ("validation", X_val, y_val),
        ("test", X_test, y_test),
    ):
        if len(X) != len(y):
            raise ValueError(
                f"{name} features and labels have different lengths: "
                f"{len(X)} vs {len(y)}"
            )

    if num_classes != 6:
        raise ValueError(f"Expected 6 classes, found {num_classes}")


def class_distribution(y: np.ndarray, classes: np.ndarray) -> dict[str, int]:
    counts = np.bincount(y, minlength=len(classes))
    return {
        str(class_name): int(count)
        for class_name, count in zip(classes, counts)
    }


def save_experiment_config(
    input_shape: tuple[int, int],
    classes: np.ndarray,
    train_counts: dict[str, int],
    val_counts: dict[str, int],
    test_counts: dict[str, int],
    total_params: int,
    trainable_params: int,
) -> None:
    config = {
        "seed": SEED,
        "dataset_directory": str(DATASET_DIR),
        "input_shape": list(input_shape),
        "classes": classes.tolist(),
        "batch_size": BATCH_SIZE,
        "max_epochs": EPOCHS,
        "optimizer": "Adam",
        "learning_rate": LEARNING_RATE,
        "loss": "SparseCategoricalCrossentropy",
        "class_weighting": None,
        "model": {
            "architecture": "Residual TCN",
            "filters": 64,
            "kernel_size": 3,
            "dilation_rates": [1, 2, 4],
            "dropout_rate": 0.3,
            "l2_regularization": 1e-4,
            "dense_units": 64,
            "padding": "same",
            "global_pooling": "GlobalAveragePooling1D",
        },
        "callbacks": {
            "early_stopping_patience": 10,
            "reduce_lr_factor": 0.5,
            "reduce_lr_patience": 5,
            "minimum_learning_rate": 1e-6,
            "restore_best_weights": True,
        },
        "parameters": {
            "total": total_params,
            "trainable": trainable_params,
        },
        "class_distribution": {
            "train": train_counts,
            "validation": val_counts,
            "test": test_counts,
        },
    }
    save_json(config, SAVE_DIR / "experiment_config.json")


def evaluate_for_research(
    model: tf.keras.Model,
    X_test: np.ndarray,
    y_test: np.ndarray,
    classes: np.ndarray,
) -> None:
    start = time.perf_counter()
    probabilities = model.predict(X_test, batch_size=BATCH_SIZE, verbose=0)
    inference_seconds = time.perf_counter() - start

    predictions = np.argmax(probabilities, axis=1)
    labels = list(range(len(classes)))

    per_class_precision = precision(
        y_test, predictions, average=None
    )
    per_class_recall = recall(
        y_test, predictions, average=None
    )
    per_class_f1 = f1_score(
        y_test, predictions, average=None
    )

    results = {
        "accuracy": accuracy(y_test, predictions),
        "macro_precision": precision(
            y_test, predictions, average="macro"
        ),
        "macro_recall": recall(
            y_test, predictions, average="macro"
        ),
        "macro_f1": f1_score(
            y_test, predictions, average="macro"
        ),
        "weighted_precision": precision(
            y_test, predictions, average="weighted"
        ),
        "weighted_recall": recall(
            y_test, predictions, average="weighted"
        ),
        "weighted_f1": f1_score(
            y_test, predictions, average="weighted"
        ),
        "per_class": {
            str(class_name): {
                "precision": float(p),
                "recall": float(r),
                "f1": float(f),
            }
            for class_name, p, r, f in zip(
                classes,
                per_class_precision,
                per_class_recall,
                per_class_f1,
            )
        },
        "inference": {
            "test_samples": int(len(X_test)),
            "total_seconds": float(inference_seconds),
            "average_ms_per_sample": float(
                inference_seconds / len(X_test) * 1000
            ),
        },
        "classes": classes.tolist(),
        "confusion_matrix": confusion_matrix(
            y_test, predictions, labels=labels
        ).tolist(),
        "classification_report": classification_report(
            y_test,
            predictions,
            labels=labels,
            target_names=classes.tolist(),
        ),
    }

    save_json(results, SAVE_DIR / "research_metrics.json")
    np.save(SAVE_DIR / "test_predictions.npy", predictions)
    np.save(SAVE_DIR / "test_probabilities.npy", probabilities)
    np.save(SAVE_DIR / "test_true_labels.npy", y_test)

    logger.info("Test accuracy: %.4f", results["accuracy"])
    logger.info("Macro F1: %.4f", results["macro_f1"])
    logger.info(
        "Average inference: %.3f ms/sample",
        results["inference"]["average_ms_per_sample"],
    )
    logger.info("\n%s", results["classification_report"])
    logger.info("Confusion matrix:\n%s", np.array(results["confusion_matrix"]))


def main() -> None:
    setup_logging()
    start_time = time.perf_counter()
    seed_everything(SEED)
    setup_hardware()
    create_directory(SAVE_DIR)

    (
        X_train,
        y_train,
        X_val,
        y_val,
        X_test,
        y_test,
        label_encoder,
    ) = load_data(DATASET_DIR)

    classes = label_encoder.classes_
    validate_data(
        X_train,
        X_val,
        X_test,
        y_train,
        y_val,
        y_test,
        len(classes),
    )

    train_counts = class_distribution(y_train, classes)
    val_counts = class_distribution(y_val, classes)
    test_counts = class_distribution(y_test, classes)

    logger.info("Train: %s", train_counts)
    logger.info("Validation: %s", val_counts)
    logger.info("Test: %s", test_counts)

    model = build_tcn_model(
        input_shape=X_train.shape[1:],
        num_classes=len(classes),
    )

    total_params = count_model_parameters(model, trainable_only=False)
    trainable_params = count_model_parameters(model, trainable_only=True)

    logger.info("Total parameters: %d", total_params)
    logger.info("Trainable parameters: %d", trainable_params)

    save_experiment_config(
        input_shape=X_train.shape[1:],
        classes=classes,
        train_counts=train_counts,
        val_counts=val_counts,
        test_counts=test_counts,
        total_params=total_params,
        trainable_params=trainable_params,
    )

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=LEARNING_RATE),
        loss=tf.keras.losses.SparseCategoricalCrossentropy(),
        metrics=["accuracy"],
    )

    history = model.fit(
        X_train,
        y_train,
        validation_data=(X_val, y_val),
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        callbacks=get_callbacks(SAVE_DIR),
        verbose=1,
    )

    training_seconds = time.perf_counter() - start_time

    save_training_history(history, SAVE_DIR / "history.json")
    plot_training_history(history, SAVE_DIR / "history.png")

    with open(SAVE_DIR / "model_architecture.json", "w", encoding="utf-8") as file:
        file.write(model.to_json())

    save_json(
        {
            "training_time_seconds": float(training_seconds),
            "epochs_completed": len(history.history["loss"]),
            "batch_size": BATCH_SIZE,
            "total_parameters": total_params,
            "trainable_parameters": trainable_params,
        },
        SAVE_DIR / "training_timing.json",
    )

    keras_results = model.evaluate(
        X_test,
        y_test,
        return_dict=True,
        verbose=0,
    )
    save_json(
        {key: float(value) for key, value in keras_results.items()},
        SAVE_DIR / "keras_test_evaluation.json",
    )

    evaluate_for_research(model, X_test, y_test, classes)

    logger.info("Training pipeline completed in %.2f seconds.", training_seconds)
    logger.info("Results saved to %s", SAVE_DIR)


if __name__ == "__main__":
    main()


# import os

# # Hide TensorFlow INFO and WARNING messages
# os.environ["TF_CPP_MIN_LOG_LEVEL"] = "0"
# os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
# import logging
# import joblib
# import time
# from pathlib import Path
# from typing import Tuple, Any

# import numpy as np
# import tensorflow as tf

# from training.utils import (
#     seed_everything,
#     create_directory,
#     plot_training_history,
#     save_training_history,
#     count_model_parameters,
#     save_json
# )

# from training.callbacks import get_callbacks

# from models.tcn import build_tcn_model

# # Configure logging
# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
#     datefmt="%Y-%m-%d %H:%M:%S",
# )
# logger = logging.getLogger(__name__)

# # Constants
# SEED = 42
# BATCH_SIZE = 16
# EPOCHS = 100
# DATASET_DIR = Path("datasets/sequences_leakage_free_original")
# # DATASET_DIR = Path("datasets/sequences_leakage_free_augmented")
# SAVE_DIR = Path("saved_model_original")


# def setup_hardware() -> None:
#     """Detects GPUs and enables mixed precision if available."""
#     gpus = tf.config.list_physical_devices("GPU")
#     if gpus:
#         try:
#             for gpu in gpus:
#                 tf.config.experimental.set_memory_growth(gpu, True)
#             logger.info(f"Detected {len(gpus)} GPU(s). Enabling mixed precision (float16).")
#             tf.keras.mixed_precision.set_global_policy("mixed_float16")
#         except RuntimeError as e:
#             logger.error(f"GPU configuration failed: {e}")
#     else:
#         logger.warning("No GPUs detected. Running on CPU.")


# def load_data(dataset_dir: Path) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, Any]:
#     """Loads train/validation/test arrays and the label encoder from the dataset directory."""
#     logger.info(f"Loading dataset from {dataset_dir}...")
#     X_train = np.load(dataset_dir / "X_train.npy")
#     y_train = np.load(dataset_dir / "y_train.npy")
#     X_val = np.load(dataset_dir / "X_val.npy")
#     y_val = np.load(dataset_dir / "y_val.npy")
#     X_test = np.load(dataset_dir / "X_test.npy")
#     y_test = np.load(dataset_dir / "y_test.npy")

#     label_encoder = joblib.load(dataset_dir / "label_encoder.pkl")

#     logger.info(f"X_train shape: {X_train.shape}, y_train shape: {y_train.shape}")
#     logger.info(f"X_val shape: {X_val.shape}, y_val shape: {y_val.shape}")
#     logger.info(f"X_test shape: {X_test.shape}, y_test shape: {y_test.shape}")
#     logger.info(f"Number of classes: {len(label_encoder.classes_)}")
    
#     return X_train, y_train, X_val, y_val, X_test, y_test, label_encoder


# def main() -> None:
#     """Main execution pipeline for training the TCN model."""
#     start_time = time.time()
    
#     try:
#         # 1. Setup
#         seed_everything(SEED)
#         setup_hardware()
#         create_directory(SAVE_DIR)

#         # 2. Load Data
#         X_train, y_train, X_val, y_val, X_test, y_test, label_encoder = load_data(DATASET_DIR)
#         input_shape = X_train.shape[1:]
#         num_classes = len(label_encoder.classes_)

#         # 3. Build Model
#         logger.info("Building TCN model...")
#         model = build_tcn_model(input_shape=input_shape, num_classes=num_classes)
        
#         logger.info("Model Summary:")
#         model.summary(print_fn=lambda x: logger.info(x))
        
#         total_params = count_model_parameters(model, trainable_only=False)
#         trainable_params = count_model_parameters(model, trainable_only=True)
#         logger.info(f"Total parameters: {total_params:,} | Trainable parameters: {trainable_params:,}")

#         # 4. Compile Model
#         logger.info("Compiling model with Adam, Sparse Categorical Crossentropy, and Accuracy.")
#         model.compile(
#             optimizer=tf.keras.optimizers.Adam(learning_rate=3e-4),
#             loss=tf.keras.losses.SparseCategoricalCrossentropy(),
#             metrics=["accuracy"],
#         )

#         # 5. Callbacks
#         # get_callbacks expects a root directory and creates a 'saved_model' folder inside it.
#         # We pass '.' so the 'saved_model' folder is created in the current working directory.
#         callbacks_list = get_callbacks(save_dir=SAVE_DIR)

#         # 6. Train Model
#         logger.info(f"Starting training for {EPOCHS} epochs...")
#         history = model.fit(
#             X_train,
#             y_train,
#             validation_data=(X_val, y_val),
#             epochs=EPOCHS,
#             batch_size=BATCH_SIZE,
#             callbacks=callbacks_list,
#             verbose=1,
#         )

#         # 7. Save Artifacts (Last model, History)
#         best_model_path = SAVE_DIR / "best_model.keras"
#         model.save(best_model_path)
#         logger.info(f"Saved best model to {best_model_path}")
#         architecture_json_path = SAVE_DIR / "model_architecture.json"
#         with open(architecture_json_path, "w", encoding="utf-8") as f:
#             f.write(model.to_json())
#         logger.info(f"Saved last model to {last_model_path}")
#         logger.info(f"Saved model architecture to {architecture_json_path}")

#         history_json_path = SAVE_DIR / "history.json"
#         save_training_history(history, history_json_path)
#         logger.info(f"Saved training history to {history_json_path}")

#         history_plot_path = SAVE_DIR / "history.png"
#         plot_training_history(history, save_path=history_plot_path)
#         logger.info(f"Saved training history plot to {history_plot_path}")

#         # 8. Final Evaluation
#         logger.info("Evaluating model on test set...")
#         eval_results = model.evaluate(X_test, y_test, return_dict=True, verbose=0)
#         save_json(eval_results,SAVE_DIR / "evaluation.json")
        
#         logger.info("--- Final Test Evaluation ---")
#         for metric_name, value in eval_results.items():
#             logger.info(f"{metric_name.capitalize():<10}: {value:.4f}")

#         elapsed_time = time.time() - start_time
#         logger.info(f"Training pipeline completed successfully in {elapsed_time:.2f} seconds.")

#     except FileNotFoundError as e:
#         logger.error(f"Dataset or required file not found: {e}")
#     except ImportError as e:
#         logger.error(f"Failed to import required module: {e}")
#     except Exception as e:
#         logger.error(f"An unexpected error occurred during training: {e}", exc_info=True)
#         raise


# if __name__ == "__main__":
#     main()