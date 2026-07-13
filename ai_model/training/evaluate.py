import logging
from typing import Union

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    classification_report as sklearn_classification_report,
    confusion_matrix as sklearn_confusion_matrix,
    f1_score as sklearn_f1_score,
    precision_score,
    recall_score,
)

logger = logging.getLogger(__name__)


def accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    Compute the accuracy for multiclass sign language recognition.

    Args:
        y_true: Ground truth (correct) target values.
        y_pred: Estimated targets as returned by a classifier.

    Returns:
        The fraction of correctly classified samples (float).
    """
    logger.debug("Computing accuracy.")
    score = accuracy_score(y_true, y_pred)
    logger.debug("Accuracy computed: %.4f", score)
    return float(score)


def precision(
    y_true: np.ndarray, 
    y_pred: np.ndarray, 
    average: str = "weighted"
) -> Union[float, np.ndarray]:
    """
    Compute the precision for multiclass sign language recognition.

    Args:
        y_true: Ground truth (correct) target values.
        y_pred: Estimated targets as returned by a classifier.
        average: Defines the averaging method ('micro', 'macro', 'weighted'). 
                Defaults to 'weighted' to account for potential class imbalances 
                in sign language datasets.

    Returns:
        Precision score (float if average is not None, otherwise np.ndarray).
    """
    logger.debug("Computing precision with average='%s'.", average)
    score = precision_score(y_true, y_pred, average=average, zero_division=0)
    if isinstance(score, np.ndarray):
        logger.debug("Precision computed per class.")
    else:
        logger.debug("Precision computed: %.4f", score)
    return score


def recall(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    average: str = "weighted"
) -> Union[float, np.ndarray]:
    """
    Compute the recall for multiclass sign language recognition.

    Args:
        y_true: Ground truth (correct) target values.
        y_pred: Estimated targets as returned by a classifier.
        average: Defines the averaging method ('micro', 'macro', 'weighted'). 
                 Defaults to 'weighted' to account for potential class imbalances 
                 in sign language datasets.

    Returns:
        Recall score (float if average is not None, otherwise np.ndarray).
    """
    logger.debug("Computing recall with average='%s'.", average)
    score = recall_score(y_true, y_pred, average=average, zero_division=0)
    if isinstance(score, np.ndarray):
        logger.debug("Recall computed per class.")
    else:
        logger.debug("Recall computed: %.4f", score)
    return score


def f1_score(
    y_true: np.ndarray, 
    y_pred: np.ndarray, 
    average: str = "weighted"
) -> Union[float, np.ndarray]:
    """
    Compute the F1 score for multiclass sign language recognition.

    Args:
        y_true: Ground truth (correct) target values.
        y_pred: Estimated targets as returned by a classifier.
        average: Defines the averaging method ('micro', 'macro', 'weighted'). 
                 Defaults to 'weighted' to account for potential class imbalances 
                 in sign language datasets.

    Returns:
        F1 score (float if average is not None, otherwise np.ndarray).
    """
    logger.debug("Computing F1 score with average='%s'.", average)
    score = sklearn_f1_score(y_true, y_pred, average=average, zero_division=0)
    if isinstance(score, np.ndarray):
        logger.debug("F1 score computed per class.")
    else:
        logger.debug("F1 score computed: %.4f", score)
    return score


def confusion_matrix(y_true: np.ndarray, y_pred: np.ndarray) -> np.ndarray:
    """
    Compute the confusion matrix to evaluate the accuracy of a classification
    for multiclass sign language recognition.

    Args:
        y_true: Ground truth (correct) target values.
        y_pred: Estimated targets as returned by a classifier.

    Returns:
        A 2D numpy array representing the confusion matrix.
    """
    logger.debug("Computing confusion matrix.")
    cm = sklearn_confusion_matrix(y_true, y_pred)
    logger.debug("Confusion matrix computed with shape: %s", cm.shape)
    return cm


def classification_report(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    target_names: list[str] | None = None
) -> str:
    """
    Build a text report showing the main classification metrics for 
    multiclass sign language recognition.

    Args:
        y_true: Ground truth (correct) target values.
        y_pred: Estimated targets as returned by a classifier.
        target_names: Optional list of sign language gesture names corresponding 
                to the class labels.

    Returns:
        A string containing the classification report.
    """
    logger.debug("Generating text classification report.")
    report = sklearn_classification_report(
        y_true, 
        y_pred, 
        target_names=target_names, 
        zero_division=0
    )
    logger.debug("Classification report generated successfully.")
    return report