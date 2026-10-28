import json
import time
import joblib
import numpy as np
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report,
)

# =====================================================
# PATHS
# =====================================================

DATASET = "sign_landmarks.csv"
MODEL = "sign_pipeline.pkl"
ENCODER = "label_encoder.pkl"

OUTPUT_JSON = "summary-rf.json"

# =====================================================
# LOAD DATA
# =====================================================

print("Loading dataset...")

df = pd.read_csv(DATASET)

X = df.drop("label", axis=1)
y = df["label"]

print(f"Dataset shape : {df.shape}")
print(f"Features      : {X.shape[1]}")
print(f"Classes       : {sorted(y.unique())}")

# =====================================================
# LOAD MODEL
# =====================================================

print("\nLoading trained model...")

model = joblib.load(MODEL)
encoder = joblib.load(ENCODER)

# Encode labels exactly like training
y_encoded = encoder.transform(y)

# =====================================================
# RECREATE TRAIN/TEST SPLIT
# =====================================================

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y_encoded,
    test_size=0.20,
    random_state=42,
    stratify=y_encoded
)

print(f"\nTraining Samples : {len(X_train)}")
print(f"Testing Samples  : {len(X_test)}")

# =====================================================
# PREDICTION
# =====================================================

start = time.perf_counter()

y_pred = model.predict(X_test)

prediction_time = (time.perf_counter() - start) / len(X_test)

# =====================================================
# METRICS
# =====================================================

accuracy = accuracy_score(y_test, y_pred)

precision = precision_score(
    y_test,
    y_pred,
    average="macro",
    zero_division=0
)

recall = recall_score(
    y_test,
    y_pred,
    average="macro",
    zero_division=0
)

f1 = f1_score(
    y_test,
    y_pred,
    average="macro",
    zero_division=0
)

cm = confusion_matrix(y_test, y_pred)

report = classification_report(
    y_test,
    y_pred,
    target_names=encoder.classes_,
    output_dict=True,
    zero_division=0
)

# =====================================================
# MODEL INFORMATION
# =====================================================

summary = {

    "model": "Random Forest",

    "dataset": {
        "total_samples": int(len(df)),
        "train_samples": int(len(X_train)),
        "test_samples": int(len(X_test)),
        "num_features": int(X.shape[1]),
        "num_classes": int(len(encoder.classes_)),
        "classes": encoder.classes_.tolist()
    },

    "hyperparameters": model.get_params(),

    "performance": {
        "accuracy": float(accuracy),
        "precision_macro": float(precision),
        "recall_macro": float(recall),
        "f1_macro": float(f1)
    },

    "classification_report": report,

    "confusion_matrix": cm.tolist(),

    "feature_information": {
        "total_features": int(model.n_features_in_),
        "landmark_features": 126,
        "handedness_features": 2
    },

    "model_information": {
        "number_of_trees": model.n_estimators,
        "max_depth": model.max_depth,
        "criterion": model.criterion,
        "random_state": model.random_state
    },

    "prediction": {
        "prediction_time_per_sample_ms": round(
            prediction_time * 1000,
            6
        )
    }
}

# =====================================================
# SAVE JSON
# =====================================================

with open(OUTPUT_JSON, "w") as f:
    json.dump(summary, f, indent=4)

# =====================================================
# PRINT RESULTS
# =====================================================

print("\n===================================")
print("MODEL EVALUATION")
print("===================================")

print(f"Accuracy : {accuracy:.4f}")
print(f"Precision: {precision:.4f}")
print(f"Recall   : {recall:.4f}")
print(f"F1 Score : {f1:.4f}")

print("\nConfusion Matrix:")
print(cm)

print("\nClassification Report:")
print(
    classification_report(
        y_test,
        y_pred,
        target_names=encoder.classes_,
        zero_division=0
    )
)

print(f"\nsummary-rf.json saved successfully.")