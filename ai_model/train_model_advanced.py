import pandas as pd
import numpy as np
import joblib
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.pipeline import Pipeline

# ==============================
# LOAD DATASET
# ==============================
DATA_PATH = "sign_landmarks.csv"

df = pd.read_csv(DATA_PATH)

print("\nDataset Loaded:", df.shape)

# clean + shuffle
df.drop_duplicates(inplace=True)
df = df.sample(frac=1, random_state=42).reset_index(drop=True)

print("\nClass Distribution:")
print(df["label"].value_counts())

# ==============================
# FEATURES & LABELS
# ==============================
X = df.drop("label", axis=1)
y = df["label"]

encoder = LabelEncoder()
y_encoded = encoder.fit_transform(y)

print("\nClasses:")
for i, c in enumerate(encoder.classes_):
    print(i, "->", c)

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

# ==============================
# MODEL (TUNED)
# ==============================
model = RandomForestClassifier(
    n_estimators=300,
    max_depth=20,
    min_samples_split=2,
    min_samples_leaf=1,
    class_weight="balanced",
    random_state=42,
    n_jobs=-1
)

pipeline = Pipeline([
    ("model", model)
])

# ==============================
# CROSS VALIDATION
# ==============================
print("\nRunning Cross Validation...")
scores = cross_val_score(pipeline, X, y_encoded, cv=5)

print("Cross-validation scores:", scores)
print("Mean CV accuracy:", scores.mean())

# ==============================
# TRAIN MODEL
# ==============================
print("\nTraining model...")
pipeline.fit(X_train, y_train)

# ==============================
# EVALUATION
# ==============================
y_pred = pipeline.predict(X_test)

accuracy = accuracy_score(y_test, y_pred)
print("\nTest Accuracy:", accuracy)

print("\nClassification Report:\n")
print(classification_report(y_test, y_pred))

# ==============================
# CONFUSION MATRIX
# ==============================
cm = confusion_matrix(y_test, y_pred)

plt.figure(figsize=(6,6))
sns.heatmap(
    cm,
    annot=True,
    fmt="d",
    xticklabels=encoder.classes_,
    yticklabels=encoder.classes_
)
plt.xlabel("Predicted")
plt.ylabel("Actual")
plt.title("Confusion Matrix")
plt.show()

# ==============================
# FEATURE IMPORTANCE
# ==============================
importances = pipeline.named_steps["model"].feature_importances_

plt.figure(figsize=(10,4))
plt.plot(importances)
plt.title("Feature Importance")
plt.xlabel("Feature Index")
plt.ylabel("Importance")
plt.show()

# ==============================
# SAVE MODEL
# ==============================
joblib.dump(pipeline, "sign_pipeline.pkl")
joblib.dump(encoder, "label_encoder.pkl")

print("\nModel saved → sign_pipeline.pkl")
print("Encoder saved → label_encoder.pkl")