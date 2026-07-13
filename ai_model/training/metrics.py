import logging
from typing import List, Optional, Union

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    classification_report as sk_classification_report,
    confusion_matrix as sk_confusion_matrix,
    f1_score as sk_f1_score,
    precision_score,
    recall_score,
)

logger = logging.getLogger(__name__)


def accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    Compute the accuracy score for multiclass sign language recognition.

    Args:
        y_true: Ground truth (correct) labels.
        y_pred: Predicted labels as returned by a classifier.

    Returns:
        The fraction of correctly classified samples as a float.
    """
    logger.debug("Computing accuracy score.")
    score = accuracy_score(y_true, y_pred)
    logger.debug("Accuracy computed: %.4f", score)
    return float(score)


def precision(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    average: str = "weighted",
    zero_division: Union[str, int] = 0,
) -> Union[float, np.ndarray]:
    """
    Compute the precision score for multiclass sign language recognition.

    Args:
        y_true: Ground truth (correct) labels.
        y_pred: Predicted labels as returned by a classifier.
        average: Averaging strategy for multiclass data (e.g., 'micro', 'macro', 'weighted').
                 Defaults to 'weighted' to account for potential class imbalances in gesture data.
        zero_division: Sets the value to return when there is a zero division.

    Returns:
        Precision score. If `average` is None, returns per-class scores as a numpy array.
    """
    logger.debug("Computing precision score with average='%s'.", average)
    score = precision_score(y_true, y_pred, average=average, zero_division=zero_division)
    logger.debug("Precision computed successfully.")
    return score


def recall(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    average: str = "weighted",
    zero_division: Union[str, int] = 0,
) -> Union[float, np.ndarray]:
    """
    Compute the recall score for multiclass sign language recognition.

    Args:
        y_true: Ground truth (correct) labels.
        y_pred: Predicted labels as returned by a classifier.
        average: Averaging strategy for multiclass data (e.g., 'micro', 'macro', 'weighted').
                 Defaults to 'weighted' to account for potential class imbalances in gesture data.
        zero_division: Sets the value to return when there is a zero division.

    Returns:
        Recall score. If `average` is None, returns per-class scores as a numpy array.
    """
    logger.debug("Computing recall score with average='%s'.", average)
    score = recall_score(y_true, y_pred, average=average, zero_division=zero_division)
    logger.debug("Recall computed successfully.")
    return score


def f1_score(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    average: str = "weighted",
    zero_division: Union[str, int] = 0,
) -> Union[float, np.ndarray]:
    """
    Compute the F1 score for multiclass sign language recognition.

    Args:
        y_true: Ground truth (correct) labels.
        y_pred: Predicted labels as returned by a classifier.
        average: Averaging strategy for multiclass data (e.g., 'micro', 'macro', 'weighted').
                 Defaults to 'weighted' to account for potential class imbalances in gesture data.
        zero_division: Sets the value to return when there is a zero division.

    Returns:
        F1 score. If `average` is None, returns per-class scores as a numpy array.
    """
    logger.debug("Computing F1 score with average='%s'.", average)
    score = sk_f1_score(y_true, y_pred, average=average, zero_division=zero_division)
    logger.debug("F1 score computed successfully.")
    return score


def confusion_matrix(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    labels: Optional[List] = None,
) -> np.ndarray:
    """
    Compute the confusion matrix to evaluate the accuracy of a classification
    for multiclass sign language recognition.

    Args:
        y_true: Ground truth (correct) labels.
        y_pred: Predicted labels as returned by a classifier.
        labels: Optional list of labels to index the matrix. This can be used to
                reorder or select a subset of sign language gestures.

    Returns:
        A 2D numpy array representing the confusion matrix.
    """
    logger.debug("Computing confusion matrix.")
    cm = sk_confusion_matrix(y_true, y_pred, labels=labels)
    logger.debug("Confusion matrix computed with shape: %s", cm.shape)
    return cm


def classification_report(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    target_names: Optional[List[str]] = None,
    zero_division: Union[str, int] = 0,
) -> str:
    """
    Build a text report showing the main classification metrics for multiclass
    sign language recognition.

    Args:
        y_true: Ground truth (correct) labels.
        y_pred: Predicted labels as returned by a classifier.
        target_names: Optional list of sign language gesture names corresponding
                      to the class labels.
        zero_division: Sets the value to return when there is a zero division.

    Returns:
        A string containing the full classification report.
    """
    logger.debug("Generating classification report.")
    report = sk_classification_report(
        y_true,
        y_pred,
        target_names=target_names,
        zero_division=zero_division,
    )
    logger.debug("Classification report generated successfully.")
    return report