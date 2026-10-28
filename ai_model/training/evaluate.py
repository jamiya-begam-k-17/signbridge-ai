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
    return float(accuracy_score(y_true, y_pred))


def precision(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    average: Optional[str] = "weighted",
    zero_division: Union[str, int] = 0,
) -> Union[float, np.ndarray]:
    return precision_score(
        y_true, y_pred, average=average, zero_division=zero_division
    )


def recall(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    average: Optional[str] = "weighted",
    zero_division: Union[str, int] = 0,
) -> Union[float, np.ndarray]:
    return recall_score(
        y_true, y_pred, average=average, zero_division=zero_division
    )


def f1_score(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    average: Optional[str] = "weighted",
    zero_division: Union[str, int] = 0,
) -> Union[float, np.ndarray]:
    return sk_f1_score(
        y_true, y_pred, average=average, zero_division=zero_division
    )


def confusion_matrix(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    labels: Optional[List[int]] = None,
) -> np.ndarray:
    return sk_confusion_matrix(y_true, y_pred, labels=labels)


def classification_report(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    labels: Optional[List[int]] = None,
    target_names: Optional[List[str]] = None,
    zero_division: Union[str, int] = 0,
) -> str:
    return sk_classification_report(
        y_true,
        y_pred,
        labels=labels,
        target_names=target_names,
        zero_division=zero_division,
    )
