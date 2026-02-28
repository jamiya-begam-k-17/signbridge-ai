import pandas as pd
import numpy as np
import joblib

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report


# ==============================
# LOAD DATASET
# ==============================
DATA_PATH = "sign_landmarks.csv"

df = pd.read_csv(DATA_PATH)

print("\nDataset Loaded")
print(df.shape)


# ==============================
# SPLIT FEATURES & LABELS
# ==============================
X = df.drop("label", axis=1)
y = df["label"]

# encode text labels → numbers
encoder = LabelEncoder()
y_encoded = encoder.fit_transform(y)

print("\nClasses:")
for i, cls in enumerate(encoder.classes_):
    print(i, "->", cls)


# ==============================
# TRAIN TEST SPLIT
# ==============================
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y_encoded,
    test_size=0.2,
    random_state=42,
    stratify=y_encoded
)

print("\nTraining samples:", len(X_train))
print("Testing samples:", len(X_test))


# ==============================
# TRAIN MODEL
# ==============================
model = RandomForestClassifier(
    n_estimators=200,
    max_depth=None,
    random_state=42
)

print("\nTraining model...")
model.fit(X_train, y_train)


# ==============================
# EVALUATION
# ==============================
y_pred = model.predict(X_test)

accuracy = accuracy_score(y_test, y_pred)

print("\nAccuracy:", accuracy)
print("\nClassification Report:\n")
print(classification_report(y_test, y_pred))


# ==============================
# SAVE MODEL
# ==============================
joblib.dump(model, "sign_model.pkl")
joblib.dump(encoder, "label_encoder.pkl")

print("\nModel saved as sign_model.pkl")
print("Label encoder saved as label_encoder.pkl")