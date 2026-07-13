import os

# Hide TensorFlow INFO and WARNING messages
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "0"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
import logging
import joblib
import time
from pathlib import Path
from typing import Tuple, Any

import numpy as np
import tensorflow as tf

from training.utils import (
    seed_everything,
    create_directory,
    plot_training_history,
    save_training_history,
    count_model_parameters,
    save_json
)

from training.callbacks import get_callbacks

from models.tcn import build_tcn_model

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Constants
SEED = 42
BATCH_SIZE = 16
EPOCHS = 100
DATASET_DIR = Path("datasets/sequences")
SAVE_DIR = Path("saved_model")


def setup_hardware() -> None:
    """Detects GPUs and enables mixed precision if available."""
    gpus = tf.config.list_physical_devices("GPU")
    if gpus:
        try:
            for gpu in gpus:
                tf.config.experimental.set_memory_growth(gpu, True)
            logger.info(f"Detected {len(gpus)} GPU(s). Enabling mixed precision (float16).")
            tf.keras.mixed_precision.set_global_policy("mixed_float16")
        except RuntimeError as e:
            logger.error(f"GPU configuration failed: {e}")
    else:
        logger.warning("No GPUs detected. Running on CPU.")


def load_data(dataset_dir: Path) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, Any]:
    """Loads train/validation/test arrays and the label encoder from the dataset directory."""
    logger.info(f"Loading dataset from {dataset_dir}...")
    X_train = np.load(dataset_dir / "X_train.npy")
    y_train = np.load(dataset_dir / "y_train.npy")
    X_val = np.load(dataset_dir / "X_val.npy")
    y_val = np.load(dataset_dir / "y_val.npy")
    X_test = np.load(dataset_dir / "X_test.npy")
    y_test = np.load(dataset_dir / "y_test.npy")

    label_encoder = joblib.load(dataset_dir / "label_encoder.pkl")

    logger.info(f"X_train shape: {X_train.shape}, y_train shape: {y_train.shape}")
    logger.info(f"X_val shape: {X_val.shape}, y_val shape: {y_val.shape}")
    logger.info(f"X_test shape: {X_test.shape}, y_test shape: {y_test.shape}")
    logger.info(f"Number of classes: {len(label_encoder.classes_)}")
    
    return X_train, y_train, X_val, y_val, X_test, y_test, label_encoder


def main() -> None:
    """Main execution pipeline for training the TCN model."""
    start_time = time.time()
    
    try:
        # 1. Setup
        seed_everything(SEED)
        setup_hardware()
        create_directory(SAVE_DIR)

        # 2. Load Data
        X_train, y_train, X_val, y_val, X_test, y_test, label_encoder = load_data(DATASET_DIR)
        input_shape = X_train.shape[1:]
        num_classes = len(label_encoder.classes_)

        # 3. Build Model
        logger.info("Building TCN model...")
        model = build_tcn_model(input_shape=input_shape, num_classes=num_classes)
        
        logger.info("Model Summary:")
        model.summary(print_fn=lambda x: logger.info(x))
        
        total_params = count_model_parameters(model, trainable_only=False)
        trainable_params = count_model_parameters(model, trainable_only=True)
        logger.info(f"Total parameters: {total_params:,} | Trainable parameters: {trainable_params:,}")

        # 4. Compile Model
        logger.info("Compiling model with Adam, Sparse Categorical Crossentropy, and Accuracy.")
        model.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=3e-4),
            loss=tf.keras.losses.SparseCategoricalCrossentropy(),
            metrics=["accuracy"],
        )

        # 5. Callbacks
        # get_callbacks expects a root directory and creates a 'saved_model' folder inside it.
        # We pass '.' so the 'saved_model' folder is created in the current working directory.
        callbacks_list = get_callbacks(save_dir=SAVE_DIR)

        # 6. Train Model
        logger.info(f"Starting training for {EPOCHS} epochs...")
        history = model.fit(
            X_train,
            y_train,
            validation_data=(X_val, y_val),
            epochs=EPOCHS,
            batch_size=BATCH_SIZE,
            callbacks=callbacks_list,
            verbose=1,
        )

        # 7. Save Artifacts (Last model, History)
        last_model_path = SAVE_DIR / "last_model.keras"
        model.save(last_model_path)
        architecture_json_path = SAVE_DIR / "model_architecture.json"
        with open(architecture_json_path, "w", encoding="utf-8") as f:
            f.write(model.to_json())
        logger.info(f"Saved last model to {last_model_path}")
        logger.info(f"Saved model architecture to {architecture_json_path}")

        history_json_path = SAVE_DIR / "history.json"
        save_training_history(history, history_json_path)
        logger.info(f"Saved training history to {history_json_path}")

        history_plot_path = SAVE_DIR / "history.png"
        plot_training_history(history, save_path=history_plot_path)
        logger.info(f"Saved training history plot to {history_plot_path}")

        # 8. Final Evaluation
        logger.info("Evaluating model on test set...")
        eval_results = model.evaluate(X_test, y_test, return_dict=True, verbose=0)
        save_json(eval_results,SAVE_DIR / "evaluation.json")
        
        logger.info("--- Final Test Evaluation ---")
        for metric_name, value in eval_results.items():
            logger.info(f"{metric_name.capitalize():<10}: {value:.4f}")

        elapsed_time = time.time() - start_time
        logger.info(f"Training pipeline completed successfully in {elapsed_time:.2f} seconds.")

    except FileNotFoundError as e:
        logger.error(f"Dataset or required file not found: {e}")
    except ImportError as e:
        logger.error(f"Failed to import required module: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred during training: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()