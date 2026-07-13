import logging
from typing import Sequence, Tuple

import tensorflow as tf
from tensorflow.keras import layers, models, regularizers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def residual_block(
    x: tf.Tensor,
    dilation_rate: int,
    num_filters: int,
    kernel_size: int,
    dropout_rate: float,
    l2_reg: float,
    block_name: str = "res_block"
) -> tf.Tensor:
    """
    Creates a single Temporal Convolutional Network (TCN) residual block.

    Args:
        x: Input tensor.
        dilation_rate: Dilation rate for the dilated convolutions.
        num_filters: Number of filters in the convolutional layers.
        kernel_size: Size of the convolutional kernels.
        dropout_rate: Dropout rate for SpatialDropout1D.
        l2_reg: L2 regularization factor.
        block_name: Name prefix for the layers in this block.

    Returns:
        Output tensor after applying the residual connection and final ReLU.
    """
    reg = regularizers.l2(l2_reg)

    # First Convolutional Block
    conv = layers.Conv1D(
        filters=num_filters,
        kernel_size=kernel_size,
        dilation_rate=dilation_rate,
        padding="same",
        kernel_initializer="he_normal",
        kernel_regularizer=reg,
        name=f"{block_name}_conv1"
    )(x)
    conv = layers.BatchNormalization(name=f"{block_name}_bn1")(conv)
    conv = layers.ReLU(name=f"{block_name}_relu1")(conv)
    conv = layers.SpatialDropout1D(dropout_rate, name=f"{block_name}_spatial_dropout1")(conv)

    # Second Convolutional Block
    conv = layers.Conv1D(
        filters=num_filters,
        kernel_size=kernel_size,
        dilation_rate=dilation_rate,
        padding="same",
        kernel_initializer="he_normal",
        kernel_regularizer=reg,
        name=f"{block_name}_conv2"
    )(conv)
    conv = layers.BatchNormalization(name=f"{block_name}_bn2")(conv)
    conv = layers.ReLU(name=f"{block_name}_relu2")(conv)
    conv = layers.SpatialDropout1D(dropout_rate, name=f"{block_name}_spatial_dropout2")(conv)

    # Residual Path
    if x.shape[-1] != num_filters:
        residual = layers.Conv1D(
            filters=num_filters,
            kernel_size=1,
            padding="same",
            kernel_initializer="he_normal",
            kernel_regularizer=reg,
            name=f"{block_name}_residual_conv1d"
        )(x)
    else:
        residual = x

    # Residual Connection and Final ReLU
    x = layers.Add(name=f"{block_name}_add")([conv, residual])
    return layers.ReLU(name=f"{block_name}_final_relu")(x)


def build_tcn_model(
    input_shape: Tuple[int, int] = (20, 300),
    num_classes: int = 5,
    filters: int = 64,
    kernel_size: int = 3,
    dropout_rate: float = 0.3,
    l2_regularization: float = 1e-4,
    dilation_rates: Sequence[int] = (1, 2, 4)
) -> models.Model:
    """
    Builds the Temporal Convolutional Network (TCN) model for sequence classification.

    Args:
        input_shape: Shape of the input sequence (sequence_length, features).
        num_classes: Number of output classes for classification.
        filters: Number of filters to use in each TCN block.
        kernel_size: Size of the convolutional kernels.
        dropout_rate: Dropout rate applied after activations.
        l2_regularization: L2 regularization weight.
        dilation_rates: Sequence of dilation rates for the sequential TCN blocks.

    Returns:
        An uncompiled TensorFlow/Keras Model instance.
    """
    logger.info("Building TCN model architecture...")
    logger.info(f"Input Shape: {input_shape} | Classes: {num_classes}")
    logger.info(f"Filters: {filters} | Kernel: {kernel_size} | Dilations: {dilation_rates}")

    inputs = layers.Input(shape=input_shape, name="input_layer")
    x = inputs

    # Stack TCN Blocks with increasing dilation
    for i, dilation in enumerate(dilation_rates):
        x = residual_block(
            x,
            dilation_rate=dilation,
            num_filters=filters,
            kernel_size=kernel_size,
            dropout_rate=dropout_rate,
            l2_reg=l2_regularization,
            block_name=f"tcn_block_{i + 1}"
        )

    # Classification Head
    x = layers.GlobalAveragePooling1D(name="global_avg_pool")(x)

    x = layers.Dense(
        256,
        activation="relu",
        kernel_initializer="he_normal",
        kernel_regularizer=regularizers.l2(l2_regularization),
        name="dense_256"
    )(x)
    x = layers.Dropout(dropout_rate, name="dense_dropout")(x)

    outputs = layers.Dense(
        num_classes,
        activation="softmax",
        dtype="float32",
        name="output_layer"
    )(x)

    model = models.Model(inputs=inputs, outputs=outputs, name="SignBridge_TCN")

    logger.info(f"Output Shape: {model.output_shape}")
    logger.info(f"Total Parameters: {model.count_params():,}")

    return model


def print_model_summary(model: models.Model) -> None:
    """
    Logs the summary of the provided Keras model using the logger.

    Args:
        model: The TensorFlow/Keras model to summarize.
    """
    if model is None:
        logger.error("Cannot print summary. Model is None.")
        return
    logger.info("Printing model summary...")
    model.summary(print_fn=lambda x: logger.info(x.strip()))