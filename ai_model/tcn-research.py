import json
import logging
import time
from pathlib import Path

import joblib
import numpy as np
import tensorflow as tf
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

# -------------------------------------------------------
# Paths
# -------------------------------------------------------

DATASET_DIR = Path("datasets/sequences")
MODEL_PATH = Path("saved_model/saved_model/best_model.keras")

OUTPUT_FILE = Path("saved_model/evaluation_report.json")


# -------------------------------------------------------
# Load Dataset
# -------------------------------------------------------

logger.info("Loading test dataset...")

X_test = np.load(DATASET_DIR / "X_test.npy")
y_test = np.load(DATASET_DIR / "y_test.npy")

label_encoder = joblib.load(DATASET_DIR / "label_encoder.pkl")

logger.info(f"Test samples : {len(X_test)}")

# -------------------------------------------------------
# Load Model
# -------------------------------------------------------

logger.info("Loading trained model...")

model = tf.keras.models.load_model(MODEL_PATH)

# -------------------------------------------------------
# Prediction
# -------------------------------------------------------

start = time.perf_counter()

probabilities = model.predict(X_test, verbose=0)

end = time.perf_counter()

prediction_time = ((end - start) / len(X_test)) * 1000

predictions = np.argmax(probabilities, axis=1)

# -------------------------------------------------------
# Metrics
# -------------------------------------------------------

accuracy = accuracy_score(y_test, predictions)

precision = precision_score(
    y_test,
    predictions,
    average="macro",
    zero_division=0
)

recall = recall_score(
    y_test,
    predictions,
    average="macro",
    zero_division=0
)

f1 = f1_score(
    y_test,
    predictions,
    average="macro",
    zero_division=0
)

report = classification_report(
    y_test,
    predictions,
    target_names=label_encoder.classes_,
    output_dict=True,
    zero_division=0
)

cm = confusion_matrix(y_test, predictions)

import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import ConfusionMatrixDisplay

disp = ConfusionMatrixDisplay(
    confusion_matrix=cm,
    display_labels=label_encoder.classes_
)

fig, ax = plt.subplots(figsize=(6,6))
disp.plot(ax=ax, cmap="Blues", colorbar=False)

plt.tight_layout()
plt.savefig("confusion_matrix.png", dpi=300)

# -------------------------------------------------------
# Save Report
# -------------------------------------------------------

results = {

    "model": "Temporal Convolutional Network",

    "dataset": {

        "test_samples": int(len(X_test)),
        "sequence_length": int(X_test.shape[1]),
        "feature_size": int(X_test.shape[2]),
        "num_classes": int(len(label_encoder.classes_)),
        "classes": label_encoder.classes_.tolist()

    },

    "performance": {

        "accuracy": float(accuracy),
        "precision_macro": float(precision),
        "recall_macro": float(recall),
        "f1_macro": float(f1)

    },

    "classification_report": report,

    "confusion_matrix": cm.tolist(),

    "prediction": {

        "prediction_time_per_sample_ms": float(prediction_time)

    }

}

with open(OUTPUT_FILE, "w") as f:
    json.dump(results, f, indent=4)

logger.info("=" * 60)
logger.info("Evaluation Complete")
logger.info("=" * 60)

logger.info(f"Accuracy : {accuracy:.4f}")
logger.info(f"Precision: {precision:.4f}")
logger.info(f"Recall   : {recall:.4f}")
logger.info(f"F1 Score : {f1:.4f}")
logger.info(f"Prediction Time : {prediction_time:.4f} ms/sample")

logger.info(f"\nSaved to {OUTPUT_FILE}")