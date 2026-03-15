"""
feature_extraction.py
---------------------
Converts raw MediaPipe landmark results into a fixed-size, normalized feature
vector that the GRU model will consume.

Feature layout (per frame):
  - Right hand  : 21 landmarks x 3 = 63 values
  - Left hand   : 21 landmarks x 3 = 63 values
  - Pose subset : 7 keypoints  x 3 = 21 values  (nose, l/r shoulder, l/r elbow, l/r wrist)
  - Face subset :  2 keypoints x 3 =  6 values  (nose-tip, mouth-center)
  - Derived     : 5 scalar features
                  (right-wrist->nose dist, right-wrist->L-shoulder dist,
                   right-wrist->R-shoulder dist, right-wrist velocity,
                   hand-movement-direction in radians)
  Total per frame: 63 + 63 + 21 + 6 + 5 = 158
"""

import numpy as np

# ── Pose landmark indices we actually use ──────────────────────────────────────
POSE_NOSE        = 0
POSE_L_SHOULDER  = 11
POSE_R_SHOULDER  = 12
POSE_L_ELBOW     = 13
POSE_R_ELBOW     = 14
POSE_L_WRIST     = 15
POSE_R_WRIST     = 16

POSE_INDICES = [
    POSE_NOSE,
    POSE_L_SHOULDER, POSE_R_SHOULDER,
    POSE_L_ELBOW,    POSE_R_ELBOW,
    POSE_L_WRIST,    POSE_R_WRIST,
]

# Face mesh landmark indices for nose-tip and mouth-centre (MediaPipe 468-point)
FACE_NOSE_TIP    = 4
FACE_MOUTH_CTR   = 13   # upper-lip centre

FEATURE_SIZE = 63 + 63 + 21 + 6 + 5   # = 158


# ── Helpers ────────────────────────────────────────────────────────────────────

def _lm_to_array(lm_list, indices=None):
    arr = np.array([[lm.x, lm.y, lm.z] for lm in lm_list], dtype=np.float32)
    if indices is not None:
        arr = arr[indices]
    return arr


def _hand_array(hand_landmarks):
    if hand_landmarks is None:
        return np.zeros((21, 3), dtype=np.float32)
    return _lm_to_array(hand_landmarks.landmark)


def _pose_array(pose_landmarks):
    if pose_landmarks is None:
        return np.zeros((len(POSE_INDICES), 3), dtype=np.float32)
    return _lm_to_array(pose_landmarks.landmark, POSE_INDICES)


def _face_array(face_landmarks):
    if face_landmarks is None:
        return np.zeros((2, 3), dtype=np.float32)
    lms = face_landmarks.landmark
    return np.array([
        [lms[FACE_NOSE_TIP].x,  lms[FACE_NOSE_TIP].y,  lms[FACE_NOSE_TIP].z],
        [lms[FACE_MOUTH_CTR].x, lms[FACE_MOUTH_CTR].y, lms[FACE_MOUTH_CTR].z],
    ], dtype=np.float32)


def _shoulder_center(pose_arr):
    return (pose_arr[1] + pose_arr[2]) / 2.0


def _normalize_to_shoulder(coords, origin, scale=1.0):
    return (coords - origin) / (scale + 1e-8)


# ── Public API ─────────────────────────────────────────────────────────────────

def extract_features(right_hand, left_hand, pose, face, prev_right_wrist=None):
    """
    Build a single-frame feature vector.

    Parameters
    ----------
    right_hand       : mediapipe hand landmark result or None
    left_hand        : mediapipe hand landmark result or None
    pose             : mediapipe pose landmark result or None
    face             : mediapipe face landmark result or None
    prev_right_wrist : (3,) ndarray from the previous frame (for velocity)

    Returns
    -------
    features     : (FEATURE_SIZE,) = (158,) float32 ndarray
    right_wrist  : (3,) ndarray — pass as prev_right_wrist on next call
    """
    rh_arr   = _hand_array(right_hand)
    lh_arr   = _hand_array(left_hand)
    pose_arr = _pose_array(pose)
    face_arr = _face_array(face)

    origin          = _shoulder_center(pose_arr)
    shoulder_width  = np.linalg.norm(pose_arr[1] - pose_arr[2]) + 1e-8

    rh_norm   = _normalize_to_shoulder(rh_arr,   origin, shoulder_width).flatten()
    lh_norm   = _normalize_to_shoulder(lh_arr,   origin, shoulder_width).flatten()
    pose_norm = _normalize_to_shoulder(pose_arr, origin, shoulder_width).flatten()
    face_norm = _normalize_to_shoulder(face_arr, origin, shoulder_width).flatten()

    r_wrist = pose_arr[6]   # index 6 in POSE_INDICES = POSE_R_WRIST
    nose    = pose_arr[0]

    dist_nose       = np.linalg.norm(r_wrist - nose)        / (shoulder_width + 1e-8)
    dist_l_shoulder = np.linalg.norm(r_wrist - pose_arr[1]) / (shoulder_width + 1e-8)
    dist_r_shoulder = np.linalg.norm(r_wrist - pose_arr[2]) / (shoulder_width + 1e-8)

    if prev_right_wrist is not None:
        delta     = r_wrist - prev_right_wrist
        velocity  = np.linalg.norm(delta)          / (shoulder_width + 1e-8)
        direction = float(np.arctan2(delta[1], delta[0]))
    else:
        velocity  = 0.0
        direction = 0.0

    derived = np.array([dist_nose, dist_l_shoulder, dist_r_shoulder,
                        velocity, direction], dtype=np.float32)

    features = np.concatenate([rh_norm, lh_norm, pose_norm, face_norm, derived])

    assert features.shape == (FEATURE_SIZE,), \
        f"Feature size mismatch: {features.shape} vs expected ({FEATURE_SIZE},)"

    return features.astype(np.float32), r_wrist


def augment_sequence(seq, noise_std=0.01, scale_range=(0.95, 1.05)):
    """
    CPU-friendly data augmentation on a (T, F) sequence.
    Applied only during training — never during inference.
    """
    seq = seq.copy()
    seq += np.random.normal(0, noise_std, seq.shape).astype(np.float32)
    seq *= np.random.uniform(*scale_range)
    return seq


# --------------------------------------------------


# """
# feature_extraction.py
# ---------------------
# Converts raw MediaPipe landmark results into a fixed-size, normalized feature
# vector that the GRU model will consume.

# Feature layout (per frame):
#     - Right hand  : 21 landmarks × 3 = 63 values
#     - Left hand   : 21 landmarks × 3 = 63 values
#     - Pose subset : 7 keypoints × 3  = 21 values  (nose, l/r shoulder, l/r elbow, l/r wrist)
#     - Face subset :  2 keypoints × 3 =  6 values  (nose-tip, mouth-center)
#     - Derived     : 5 scalar features
#                     (right-wrist→nose dist, right-wrist→L-shoulder dist,
#                     right-wrist→R-shoulder dist, right-wrist velocity,
#                     hand-movement-direction in radians)
#     Total per frame: 63 + 63 + 21 + 6 + 5 = 158
#     """

# import numpy as np

# # ── Pose landmark indices we actually use ──────────────────────────────────────
# POSE_NOSE        = 0
# POSE_L_SHOULDER  = 11
# POSE_R_SHOULDER  = 12
# POSE_L_ELBOW     = 13
# POSE_R_ELBOW     = 14
# POSE_L_WRIST     = 15
# POSE_R_WRIST     = 16

# POSE_INDICES = [
#     POSE_NOSE,
#     POSE_L_SHOULDER, POSE_R_SHOULDER,
#     POSE_L_ELBOW,    POSE_R_ELBOW,
#     POSE_L_WRIST,    POSE_R_WRIST,
# ]

# # Face mesh landmark indices for nose-tip and mouth-centre (MediaPipe 468-point)
# FACE_NOSE_TIP    = 4
# FACE_MOUTH_CTR   = 13   # upper-lip centre — stable, not tracking mouth opening

# FEATURE_SIZE = 63 + 63 + 21 + 6 + 5   # = 158


# # ── Helpers ────────────────────────────────────────────────────────────────────

# def _lm_to_array(lm_list, indices=None):
#     """Convert a list of landmark objects to (N, 3) numpy array.
#     Optionally select only *indices*."""
#     arr = np.array([[lm.x, lm.y, lm.z] for lm in lm_list], dtype=np.float32)
#     if indices is not None:
#         arr = arr[indices]
#     return arr


# def _hand_array(hand_landmarks):
#     """Return (21, 3) array or zeros if hand not detected."""
#     if hand_landmarks is None:
#         return np.zeros((21, 3), dtype=np.float32)
#     return _lm_to_array(hand_landmarks.landmark)


# def _pose_array(pose_landmarks):
#     """Return (7, 3) array for our chosen pose keypoints, or zeros."""
#     if pose_landmarks is None:
#         return np.zeros((len(POSE_INDICES), 3), dtype=np.float32)
#     return _lm_to_array(pose_landmarks.landmark, POSE_INDICES)


# def _face_array(face_landmarks):
#     """Return (2, 3) array for nose-tip and mouth-centre, or zeros."""
#     if face_landmarks is None:
#         return np.zeros((2, 3), dtype=np.float32)
#     lms = face_landmarks.landmark
#     return np.array([
#         [lms[FACE_NOSE_TIP].x,  lms[FACE_NOSE_TIP].y,  lms[FACE_NOSE_TIP].z],
#         [lms[FACE_MOUTH_CTR].x, lms[FACE_MOUTH_CTR].y, lms[FACE_MOUTH_CTR].z],
#     ], dtype=np.float32)


# def _shoulder_center(pose_arr):
#     """Mid-point of left and right shoulder (indices 1, 2 in POSE_INDICES)."""
#     return (pose_arr[1] + pose_arr[2]) / 2.0


# def _normalize_to_shoulder(coords, origin, scale=1.0):
#     """Translate *coords* so that *origin* is zero, then scale."""
#     return (coords - origin) / (scale + 1e-8)


# # ── Public API ─────────────────────────────────────────────────────────────────

# def extract_features(right_hand, left_hand, pose, face, prev_right_wrist=None):
#     """
#     Build a single-frame feature vector.

#     Parameters
#     ----------
#     right_hand : mediapipe hand landmark result or None
#     left_hand  : mediapipe hand landmark result or None
#     pose       : mediapipe pose landmark result or None
#     face       : mediapipe face landmark result or None
#     prev_right_wrist : (3,) ndarray from the previous frame (for velocity)

#     Returns
#     -------
#     features : (FEATURE_SIZE,) float32 ndarray
#     right_wrist : (3,) ndarray — to be passed as prev_right_wrist next call
#     """
#     # ── Raw arrays ─────────────────────────────────────────────────────────────
#     rh_arr   = _hand_array(right_hand)   # (21, 3)
#     lh_arr   = _hand_array(left_hand)    # (21, 3)
#     pose_arr = _pose_array(pose)         # ( 7, 3)
#     face_arr = _face_array(face)         # ( 2, 3)

#     # ── Normalization origin: shoulder midpoint ────────────────────────────────
#     origin = _shoulder_center(pose_arr)  # (3,)

#     # Estimate scale: shoulder width (L-shoulder to R-shoulder distance)
#     shoulder_width = np.linalg.norm(pose_arr[1] - pose_arr[2]) + 1e-8

#     # ── Normalize all coords ──────────────────────────────────────────────────
#     rh_norm   = _normalize_to_shoulder(rh_arr,   origin, shoulder_width).flatten()
#     lh_norm   = _normalize_to_shoulder(lh_arr,   origin, shoulder_width).flatten()
#     pose_norm = _normalize_to_shoulder(pose_arr, origin, shoulder_width).flatten()
#     face_norm = _normalize_to_shoulder(face_arr, origin, shoulder_width).flatten()

#     # ── Derived features ──────────────────────────────────────────────────────
#     # Right wrist position (index 15 in full pose, index 6 in our POSE_INDICES)
#     r_wrist = pose_arr[6]  # raw, unnormalized

#     # Nose position (index 0 in POSE_INDICES)
#     nose = pose_arr[0]

#     dist_nose      = np.linalg.norm(r_wrist - nose)             / (shoulder_width + 1e-8)
#     dist_l_shoulder= np.linalg.norm(r_wrist - pose_arr[1])      / (shoulder_width + 1e-8)
#     dist_r_shoulder= np.linalg.norm(r_wrist - pose_arr[2])      / (shoulder_width + 1e-8)

#     if prev_right_wrist is not None:
#         delta = r_wrist - prev_right_wrist
#         velocity  = np.linalg.norm(delta)  / (shoulder_width + 1e-8)
#         direction = float(np.arctan2(delta[1], delta[0]))          # radians
#     else:
#         velocity  = 0.0
#         direction = 0.0

#     derived = np.array([dist_nose, dist_l_shoulder, dist_r_shoulder,
#                         velocity, direction], dtype=np.float32)

#     # ── Concatenate ──────────────────────────────────────────────────────────
#     features = np.concatenate([rh_norm, lh_norm, pose_norm, face_norm, derived])

#     assert features.shape == (FEATURE_SIZE,), \
#         f"Feature size mismatch: {features.shape} vs {FEATURE_SIZE}"

#     return features.astype(np.float32), r_wrist


# def augment_sequence(seq, noise_std=0.01, scale_range=(0.95, 1.05)):
#     """
#     Lightweight CPU-friendly data augmentation on a (T, F) sequence.

#     1. Additive Gaussian noise — simulates landmark jitter.
#     2. Uniform random scale — simulates slightly different distances from camera.
#     """
#     seq = seq.copy()
#     # Noise
#     seq += np.random.normal(0, noise_std, seq.shape).astype(np.float32)
#     # Scale
#     scale = np.random.uniform(*scale_range)
#     seq *= scale
#     return seq