"""
train_model.py
--------------
Loads the dataset, trains GRU + Attention model, evaluates, saves weights.

Run from inside ai_model/:
    python train_model.py

Outputs (both saved in ai_model/):
    gesture_model.h5    — trained Keras model
    label_encoder.pkl   — fitted sklearn LabelEncoder
"""

import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

import time
import numpy as np
import joblib

from sklearn.preprocessing   import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics         import classification_report, confusion_matrix

import tensorflow as tf

# Use keras directly to avoid Pylance import warning
try:
    import keras
    from keras import layers, Model
    from keras.callbacks import EarlyStopping, ReduceLROnPlateau
except ImportError:
    from tensorflow import keras                             # type: ignore
    from tensorflow.keras import layers, Model              # type: ignore
    from tensorflow.keras.callbacks import (               # type: ignore
        EarlyStopping, ReduceLROnPlateau
    )

from feature_extraction import FEATURE_SIZE, augment_sequence
from attention_layer    import TemporalAttention

# ── Config ─────────────────────────────────────────────────────────────────────
DATASET_DIR    = "dataset"
SEQ_LEN        = 40
MODEL_PATH     = "gesture_model.h5"
ENCODER_PATH   = "label_encoder.pkl"

AUGMENT_COPIES = 2       # extra noise copies per training sample
BATCH_SIZE     = 32
MAX_EPOCHS     = 80
PATIENCE       = 12

CPU_TIME_WARN_MIN = 30


# ── Dataset loading ────────────────────────────────────────────────────────────

def load_dataset():
    X, y = [], []
    signs = sorted(os.listdir(DATASET_DIR))
    print(f"[INFO] Signs found: {signs}")

    for sign in signs:
        sign_dir = os.path.join(DATASET_DIR, sign)
        if not os.path.isdir(sign_dir):
            continue
        files = sorted([f for f in os.listdir(sign_dir) if f.endswith(".npy")])
        loaded = 0
        for fn in files:
            seq = np.load(os.path.join(sign_dir, fn))
            if seq.shape != (SEQ_LEN, FEATURE_SIZE):
                print(f"  [SKIP] {fn}: shape {seq.shape} expected ({SEQ_LEN},{FEATURE_SIZE})")
                continue
            X.append(seq)
            y.append(sign)
            loaded += 1
        print(f"  {sign}: {loaded} samples")

    if len(X) == 0:
        raise RuntimeError(
            "No valid .npy files found. "
            "Run data_collection.py first, then re-run train_model.py."
        )

    X = np.array(X, dtype=np.float32)
    y = np.array(y)
    print(f"\n[INFO] Total: {len(X)} samples  |  {len(set(y))} classes")
    return X, y


def augment_training_data(X_train, y_train, copies=AUGMENT_COPIES):
    aug_X, aug_y = [X_train], [y_train]
    for _ in range(copies):
        aug   = np.array([augment_sequence(s) for s in X_train], dtype=np.float32)
        aug_X.append(aug)
        aug_y.append(y_train)
    X_out = np.concatenate(aug_X)
    y_out = np.concatenate(aug_y)
    # Shuffle
    idx = np.random.permutation(len(X_out))
    return X_out[idx], y_out[idx]


# ── Model ──────────────────────────────────────────────────────────────────────

def build_model(seq_len, feature_size, num_classes):
    """
    Input (40, 158)
    -> GRU(64, return_sequences=True)
    -> Dropout(0.3)
    -> GRU(64, return_sequences=True)
    -> TemporalAttention  -> context (64,)
    -> Dense(64, relu)
    -> Dropout(0.3)
    -> Dense(num_classes, softmax)
    """
    inp = layers.Input(shape=(seq_len, feature_size), name="sequence_input")

    x = layers.GRU(64, return_sequences=True, name="gru_1")(inp)
    x = layers.Dropout(0.3, name="drop_1")(x)
    x = layers.GRU(64, return_sequences=True, name="gru_2")(x)

    x = TemporalAttention(name="temporal_attention")(x)

    x = layers.Dense(64, activation="relu", name="dense_1")(x)
    x = layers.Dropout(0.3, name="drop_2")(x)

    out = layers.Dense(num_classes, activation="softmax", name="output")(x)

    model = Model(inp, out, name="GRU_Attention_10class")
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


# ── CPU time estimate ──────────────────────────────────────────────────────────

def estimate_time_mins(n_train, epochs, batch_size):
    # ~0.5 ms per sample per epoch on modern CPU
    return (n_train * epochs * 0.5e-3) / 60


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  SignBridge — GRU + Temporal Attention Training")
    print(f"  SEQ_LEN={SEQ_LEN}  FEATURE_SIZE={FEATURE_SIZE}")
    print("=" * 60)

    # Load
    X, y = load_dataset()

    # Encode labels
    le      = LabelEncoder()
    y_enc   = le.fit_transform(y)
    n_cls   = len(le.classes_)
    print(f"\n[INFO] Classes ({n_cls}): {le.classes_.tolist()}")

    # Split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y_enc, test_size=0.15, random_state=42, stratify=y_enc
    )
    print(f"[INFO] Train: {len(X_train)}  |  Test: {len(X_test)}")

    # Augment
    X_train, y_train = augment_training_data(X_train, y_train)
    print(f"[INFO] After augmentation — Train: {len(X_train)}")

    # CPU time guard
    est = estimate_time_mins(len(X_train), MAX_EPOCHS, BATCH_SIZE)
    print(f"[INFO] Estimated max training time: ~{est:.1f} min (CPU)")
    if est > CPU_TIME_WARN_MIN:
        print("[WARN] Estimated time > 30 min. Early stopping will kick in sooner.")
        print("       You can also reduce AUGMENT_COPIES or MAX_EPOCHS in this file.")

    # Build
    model = build_model(SEQ_LEN, FEATURE_SIZE, n_cls)
    model.summary()

    # Callbacks
    callbacks = [
        EarlyStopping(
            monitor="val_loss", patience=PATIENCE,
            restore_best_weights=True, verbose=1,
        ),
        ReduceLROnPlateau(
            monitor="val_loss", factor=0.5, patience=5,
            min_lr=1e-5, verbose=1,
        ),
    ]

    # Train
    t0 = time.time()
    model.fit(
        X_train, y_train,
        validation_split=0.15,
        epochs=MAX_EPOCHS,
        batch_size=BATCH_SIZE,
        callbacks=callbacks,
        verbose=1,
    )
    elapsed = (time.time() - t0) / 60
    print(f"\n[INFO] Training finished in {elapsed:.1f} min")

    # Evaluate
    y_pred_prob = model.predict(X_test, verbose=0)
    y_pred      = np.argmax(y_pred_prob, axis=1)

    loss, acc = model.evaluate(X_test, y_test, verbose=0)
    print(f"\n── Test Accuracy: {acc:.4f}  |  Loss: {loss:.4f}")

    print("\n── Per-class Report ─────────────────────────────────────")
    print(classification_report(y_test, y_pred, target_names=le.classes_))

    print("── Confusion Matrix ─────────────────────────────────────")
    cm     = confusion_matrix(y_test, y_pred)
    header = "        " + "  ".join(f"{c[:6]:>6}" for c in le.classes_)
    print(header)
    for i, row in enumerate(cm):
        lbl = f"{le.classes_[i][:6]:>6} |"
        print(lbl + "  ".join(f"{v:>6}" for v in row))

    # Save
    model.save(MODEL_PATH)
    joblib.dump(le, ENCODER_PATH)
    print(f"\n[INFO] Model   saved -> {MODEL_PATH}")
    print(f"[INFO] Encoder saved -> {ENCODER_PATH}")
    print("\nNext step: run the backend then open the frontend.")


if __name__ == "__main__":
    main()
    
    
    
    
    
    
    
    
    # """
# train_model.py
# --------------
# Loads the collected dataset, trains the GRU + Attention model, evaluates it,
# and saves the weights + label encoder.

# Usage
# -----
#     python train_model.py

# Outputs
# -------
#     gesture_model.h5   — trained Keras model
#     label_encoder.pkl  — fitted sklearn LabelEncoder
# """

# import os
# import time
# import numpy as np
# import joblib

# from sklearn.preprocessing    import LabelEncoder
# from sklearn.model_selection  import train_test_split
# from sklearn.metrics          import classification_report, confusion_matrix

# import tensorflow as tf
# from tensorflow.keras          import layers, Model
# from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau

# from feature_extraction import FEATURE_SIZE, augment_sequence
# from attention_layer    import TemporalAttention

# # ── Config ─────────────────────────────────────────────────────────────────────
# DATASET_DIR   = "dataset"
# SEQ_LEN       = 40
# MODEL_PATH    = "gesture_model.h5"
# ENCODER_PATH  = "label_encoder.pkl"

# AUGMENT_COPIES = 2       # extra augmented copies per training sample
# BATCH_SIZE     = 32
# MAX_EPOCHS     = 80
# PATIENCE       = 10      # early stopping patience

# # Warn if estimated CPU training time is unreasonable
# CPU_TIME_WARN_MIN = 30

# # ── Dataset loading ────────────────────────────────────────────────────────────

# def load_dataset():
#     X, y = [], []
#     signs = sorted(os.listdir(DATASET_DIR))
#     print(f"[INFO] Signs found: {signs}")

#     for sign in signs:
#         sign_dir = os.path.join(DATASET_DIR, sign)
#         if not os.path.isdir(sign_dir):
#             continue
#         files = sorted([f for f in os.listdir(sign_dir) if f.endswith(".npy")])
#         for fn in files:
#             seq = np.load(os.path.join(sign_dir, fn))   # (T, F)
#             if seq.shape != (SEQ_LEN, FEATURE_SIZE):
#                 print(f"  [SKIP] {fn}: unexpected shape {seq.shape}")
#                 continue
#             X.append(seq)
#             y.append(sign)

#     X = np.array(X, dtype=np.float32)  # (N, T, F)
#     y = np.array(y)
#     print(f"[INFO] Loaded {len(X)} samples across {len(signs)} classes")
#     return X, y, signs


# def augment_training_data(X_train, y_train, copies=AUGMENT_COPIES):
#     """Add *copies* noise-augmented versions of every training sample."""
#     aug_X, aug_y = [X_train], [y_train]
#     for _ in range(copies):
#         aug = np.array([augment_sequence(s) for s in X_train], dtype=np.float32)
#         aug_X.append(aug)
#         aug_y.append(y_train)
#     return np.concatenate(aug_X), np.concatenate(aug_y)


# # ── Model ──────────────────────────────────────────────────────────────────────

# def build_model(seq_len, feature_size, num_classes):
#     """
#     Architecture
#     ------------
#     Input  (T, F)
#     → GRU 64, return_sequences=True
#     → Dropout 0.3
#     → GRU 64, return_sequences=True
#     → TemporalAttention  → context vector (d,)
#     → Dense 64, ReLU
#     → Dropout 0.3
#     → Dense num_classes, Softmax
#     """
#     inp = layers.Input(shape=(seq_len, feature_size), name="sequence_input")

#     x = layers.GRU(64, return_sequences=True, name="gru_1")(inp)
#     x = layers.Dropout(0.3, name="drop_1")(x)
#     x = layers.GRU(64, return_sequences=True, name="gru_2")(x)

#     # Temporal attention collapses the time dimension
#     x = TemporalAttention(name="temporal_attention")(x)

#     x = layers.Dense(64, activation="relu", name="dense_1")(x)
#     x = layers.Dropout(0.3, name="drop_2")(x)
#     out = layers.Dense(num_classes, activation="softmax", name="output")(x)

#     model = Model(inp, out, name="GRU_Attention")
#     model.compile(
#         optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3),
#         loss="sparse_categorical_crossentropy",
#         metrics=["accuracy"],
#     )
#     return model


# # ── Estimate CPU training time ─────────────────────────────────────────────────

# def estimate_time(n_train, seq_len, feature_size, batch_size, epochs):
#     """
#     Very rough heuristic: assume ~0.5 ms per sample per epoch on a modern CPU.
#     """
#     secs = n_train * epochs * 0.5e-3
#     mins = secs / 60
#     return mins


# # ── Main ───────────────────────────────────────────────────────────────────────

# def main():
#     print("=" * 60)
#     print("  GRU + Attention Training")
#     print("=" * 60)

#     # ── Load ────────────────────────────────────────────────────────────────────
#     X, y, signs = load_dataset()

#     # ── Encode labels ───────────────────────────────────────────────────────────
#     le = LabelEncoder()
#     y_enc = le.fit_transform(y)
#     num_classes = len(le.classes_)
#     print(f"[INFO] Classes ({num_classes}): {le.classes_.tolist()}")

#     # ── Train / test split ──────────────────────────────────────────────────────
#     X_train, X_test, y_train, y_test = train_test_split(
#         X, y_enc, test_size=0.15, random_state=42, stratify=y_enc
#     )
#     print(f"[INFO] Train: {len(X_train)}  Test: {len(X_test)}")

#     # ── Augment training set ────────────────────────────────────────────────────
#     X_train, y_train = augment_training_data(X_train, y_train)
#     print(f"[INFO] After augmentation — Train: {len(X_train)}")

#     # ── CPU time estimate ────────────────────────────────────────────────────────
#     est_min = estimate_time(len(X_train), SEQ_LEN, FEATURE_SIZE,
#                             BATCH_SIZE, MAX_EPOCHS)
#     print(f"[INFO] Estimated max training time: ~{est_min:.1f} min (CPU)")
#     if est_min > CPU_TIME_WARN_MIN:
#         print("[WARN] Estimated training time exceeds 30 minutes.")
#         print("       Consider reducing NUM_SAMPLES, AUGMENT_COPIES, or MAX_EPOCHS.")
#         print("       Alternatively use a GPU environment for faster training.")
#         print("       Continuing anyway — early stopping will terminate sooner.")

#     # ── Build model ─────────────────────────────────────────────────────────────
#     model = build_model(SEQ_LEN, FEATURE_SIZE, num_classes)
#     model.summary()

#     # ── Callbacks ────────────────────────────────────────────────────────────────
#     callbacks = [
#         EarlyStopping(
#             monitor="val_loss", patience=PATIENCE,
#             restore_best_weights=True, verbose=1,
#         ),
#         ReduceLROnPlateau(
#             monitor="val_loss", factor=0.5, patience=5,
#             min_lr=1e-5, verbose=1,
#         ),
#     ]

#     # ── Train ────────────────────────────────────────────────────────────────────
#     t0 = time.time()
#     history = model.fit(
#         X_train, y_train,
#         validation_split=0.15,
#         epochs=MAX_EPOCHS,
#         batch_size=BATCH_SIZE,
#         callbacks=callbacks,
#         verbose=1,
#     )
#     elapsed = (time.time() - t0) / 60
#     print(f"\n[INFO] Training finished in {elapsed:.1f} minutes.")

#     # ── Evaluate ─────────────────────────────────────────────────────────────────
#     y_pred_prob = model.predict(X_test, verbose=0)
#     y_pred      = np.argmax(y_pred_prob, axis=1)

#     print("\n── Test Accuracy ───────────────────────────────────────────")
#     loss, acc = model.evaluate(X_test, y_test, verbose=0)
#     print(f"   Loss: {loss:.4f}   Accuracy: {acc:.4f}")

#     print("\n── Per-class Report (F1, Precision, Recall) ─────────────────")
#     print(classification_report(y_test, y_pred,
#                                 target_names=le.classes_))

#     print("\n── Confusion Matrix ─────────────────────────────────────────")
#     cm = confusion_matrix(y_test, y_pred)
#     header = "      " + "  ".join(f"{c[:5]:>5}" for c in le.classes_)
#     print(header)
#     for i, row in enumerate(cm):
#         label = f"{le.classes_[i][:5]:>5} |"
#         print(label + "  ".join(f"{v:>5}" for v in row))

#     # ── Save ─────────────────────────────────────────────────────────────────────
#     model.save(MODEL_PATH)
#     joblib.dump(le, ENCODER_PATH)
#     print(f"\n[INFO] Model saved   → {MODEL_PATH}")
#     print(f"[INFO] Encoder saved → {ENCODER_PATH}")


# if __name__ == "__main__":
#     main()