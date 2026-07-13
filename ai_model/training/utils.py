import json
import logging
import random
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

import matplotlib.pyplot as plt
import numpy as np
import tensorflow as tf

logger = logging.getLogger(__name__)

# def load_numpy_array(file_path):
#     return np.load(file_path)

def load_numpy_dataset(
    file_path: Union[str, Path], x_key: str = "X", y_key: str = "y"
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Loads a dataset saved as a compressed NumPy (.npz) file.

    Args:
        file_path: Path to the .npz file.
        x_key: The key for the features array in the .npz file. Defaults to "X".
        y_key: The key for the labels array in the .npz file. Defaults to "y".

    Returns:
        A tuple containing (features, labels) as NumPy arrays.

    Raises:
        FileNotFoundError: If the file does not exist.
        KeyError: If the specified x_key or y_key are not found in the file.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        logger.error("Dataset file not found at %s", file_path)
        raise FileNotFoundError(f"Dataset file not found at {file_path}")

    logger.info("Loading NumPy dataset from %s", file_path)
    data = np.load(file_path)
    
    if x_key not in data or y_key not in data:
        logger.error("Keys '%s' or '%s' not found in %s. Available keys: %s", 
                    x_key, y_key, file_path, list(data.keys()))
        raise KeyError(f"Missing keys in {file_path}")

    return data[x_key], data[y_key]


def save_json(data: Dict[str, Any], file_path: Union[str, Path]) -> None:
    """
    Saves a dictionary to a JSON file.

    Args:
        data: The dictionary to save.
        file_path: The destination path for the JSON file.
    """
    file_path = Path(file_path)
    create_directory(file_path.parent)
    
    logger.info("Saving JSON data to %s", file_path)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def load_json(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Loads a dictionary from a JSON file.

    Args:
        file_path: The path to the JSON file.

    Returns:
        The dictionary loaded from the JSON file.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        logger.error("JSON file not found at %s", file_path)
        raise FileNotFoundError(f"JSON file not found at {file_path}")

    logger.info("Loading JSON data from %s", file_path)
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def seed_everything(seed: int) -> None:
    """
    Sets the random seed for Python, NumPy, and TensorFlow to ensure reproducibility.

    Args:
        seed: The integer seed value.
    """
    logger.info("Setting random seed to %d for reproducibility", seed)
    random.seed(seed)
    np.random.seed(seed)
    tf.random.set_seed(seed)


def create_directory(dir_path: Union[str, Path]) -> Path:
    """
    Creates a directory if it does not already exist.

    Args:
        dir_path: The path to the directory to create.

    Returns:
        The Path object of the created/existing directory.
    """
    dir_path = Path(dir_path)
    if not dir_path.exists():
        logger.info("Creating directory at %s", dir_path)
        dir_path.mkdir(parents=True, exist_ok=True)
    else:
        logger.debug("Directory already exists at %s", dir_path)
    return dir_path


def plot_training_history(
    history: tf.keras.callbacks.History,
    save_path: Optional[Union[str, Path]] = None,
) -> None:
    """
    Plots the training and validation accuracy and loss from a Keras History object.

    Args:
        history: The Keras History object returned by model.fit().
        save_path: Optional path to save the generated plot image. If None,
                    the plot is not saved to disk.
    """
    logger.debug("Plotting training history")
    hist = history.history
    
    # Determine metric keys (TF2 uses 'accuracy', older versions or custom metrics might vary)
    acc_key = "accuracy" if "accuracy" in hist else "acc"
    val_acc_key = f"val_{acc_key}"
    
    plt.figure(figsize=(12, 5))

    # Plot Accuracy
    plt.subplot(1, 2, 1)
    plt.plot(hist[acc_key], label=f"Training {acc_key}")
    if val_acc_key in hist:
        plt.plot(hist[val_acc_key], label=f"Validation {acc_key}")
    plt.title("Model Accuracy")
    plt.ylabel("Accuracy")
    plt.xlabel("Epoch")
    plt.legend(loc="upper left")

    # Plot Loss
    plt.subplot(1, 2, 2)
    plt.plot(hist["loss"], label="Training Loss")
    if "val_loss" in hist:
        plt.plot(hist["val_loss"], label="Validation Loss")
    plt.title("Model Loss")
    plt.ylabel("Loss")
    plt.xlabel("Epoch")
    plt.legend(loc="upper left")

    plt.tight_layout()

    if save_path:
        save_path = Path(save_path)
        create_directory(save_path.parent)
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        logger.info("Training history plot saved to %s", save_path)
    
    plt.close()


def save_training_history(
    history: tf.keras.callbacks.History, 
    file_path: Union[str, Path]
) -> None:
    """
    Saves the training history metrics to a JSON file.
    Converts NumPy arrays to native Python lists for JSON serialization.

    Args:
        history: The Keras History object returned by model.fit().
        file_path: The destination path for the JSON file.
    """
    logger.info("Serializing training history to JSON")
    hist = history.history
    
    # Convert numpy arrays/lists to standard Python floats for JSON compatibility
    serializable_hist = {
        key: [float(val) for val in values] 
        for key, values in hist.items()
    }
    
    save_json(serializable_hist, file_path)


def count_model_parameters(model: tf.keras.Model, trainable_only: bool = True) -> int:
    """
    Counts the number of parameters in a TensorFlow/Keras model.

    Args:
        model: The Keras model instance.
        trainable_only: If True, counts only trainable parameters. 
                        If False, counts all parameters.

    Returns:
        The total number of parameters as an integer.
    """
    if trainable_only:
        param_count = sum(np.prod(w.shape) for w in model.trainable_weights)
        logger.debug("Counted trainable parameters: %d", param_count)
    else:
        param_count = model.count_params()
        logger.debug("Counted total parameters: %d", param_count)
        
    return int(param_count)