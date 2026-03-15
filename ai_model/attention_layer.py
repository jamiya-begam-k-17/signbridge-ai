"""
attention_layer.py
------------------
Custom Keras layer implementing Temporal Self-Attention.

How it works
------------
Given a sequence of GRU hidden states  H in R^(T x d):

  1. Score each time-step with a learned weight vector:
       e_t = tanh(H_t . W + b)        (W in R^d,  b in R)

  2. Normalise scores across time with softmax to get attention weights alpha:
       alpha = softmax(e)              alpha in R^T,  sum(alpha_t) = 1

  3. Compute the context vector as a weighted sum of hidden states:
       c = sum_t alpha_t . H_t        c in R^d

This lets the model focus on the most informative frames in the gesture
(e.g. the peak of a hand wave) rather than only using the final hidden state.

NOTE ON PYLANCE WARNING
-----------------------
"Import tensorflow.keras.layers could not be resolved" is a Pylance/VS Code
type-checker issue only — it does NOT affect runtime. We use the `keras`
package directly below which also silences the warning on most setups.
"""

import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

# Use keras directly — works with TF 2.13+ and silences the Pylance warning.
# If this import fails on your machine, replace with:
#   from tensorflow.keras.layers import Layer
#   import tensorflow as tf
try:
    import keras
    from keras.layers import Layer
    import keras.backend as K
    _BACKEND = "keras"
except ImportError:
    from tensorflow.keras.layers import Layer   # type: ignore[no-redef]
    import tensorflow as tf
    K = tf.keras.backend
    _BACKEND = "tf.keras"

import tensorflow as tf   # always needed for tf.nn.softmax, tf.matmul etc.


class TemporalAttention(Layer):
    """
    Additive (Bahdanau-style) temporal attention over a GRU sequence output.

    Input shape  : (batch, time_steps, gru_units)
    Output shape : (batch, gru_units)   <- weighted sum collapsed over time
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def build(self, input_shape):
        # input_shape = (batch, T, d)
        d = input_shape[-1]

        # Learned projection: each hidden state -> scalar score
        self.W = self.add_weight(
            name="attn_W",
            shape=(d, 1),
            initializer="glorot_uniform",
            trainable=True,
        )
        self.b = self.add_weight(
            name="attn_b",
            shape=(1,),
            initializer="zeros",
            trainable=True,
        )
        super().build(input_shape)

    def call(self, hidden_states):
        """
        Parameters
        ----------
        hidden_states : Tensor  (batch, T, d)

        Returns
        -------
        context : Tensor  (batch, d)
        """
        # Score each time step: (batch, T, d) @ (d, 1) -> (batch, T, 1) -> (batch, T)
        e = tf.squeeze(
            tf.tanh(tf.matmul(hidden_states, self.W) + self.b),
            axis=-1,
        )

        # Softmax across time axis -> attention weights (batch, T)
        alpha = tf.nn.softmax(e, axis=1)

        # Weighted sum -> context vector (batch, d)
        context = tf.reduce_sum(tf.expand_dims(alpha, axis=-1) * hidden_states, axis=1)

        return context

    def get_config(self):
        return super().get_config()
    
    



    
    # -----------------------------------------------------------------------------------





    
    # """
# attention_layer.py
# ------------------
# Custom Keras layer implementing Temporal Self-Attention.

# How it works
# ------------
# Given a sequence of GRU hidden states  H in R^(T x d):

#     1. Score each time-step with a learned weight vector:
#         e_t = tanh(H_t . W + b)        (W in R^d,  b in R)

#     2. Normalise scores across time with softmax to get attention weights alpha:
#         alpha = softmax(e)              alpha in R^T,  sum(alpha_t) = 1

#     3. Compute the context vector as a weighted sum of hidden states:
#         c = sum_t alpha_t . H_t        c in R^d

# This lets the model focus on the most informative frames in the gesture
# (e.g. the peak of a hand wave) rather than only using the final hidden state.
# """

# import os
# os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

# # Use keras directly — works with TF 2.13+ and silences the Pylance warning.
# # If this import fails on your machine, replace with:
# #   from tensorflow.keras.layers import Layer
# #   import tensorflow as tf
# try:
#     import keras
#     from keras.layers import Layer
#     import keras.backend as K
#     _BACKEND = "keras"
# except ImportError:
#     from tensorflow.keras.layers import Layer   # type: ignore[no-redef]
#     import tensorflow as tf
#     K = tf.keras.backend
#     _BACKEND = "tf.keras"

# import tensorflow as tf   # always needed for tf.nn.softmax, tf.matmul etc.


# class TemporalAttention(Layer):
#     """
#     Additive (Bahdanau-style) temporal attention over a GRU sequence output.

#     Input shape  : (batch, time_steps, gru_units)
#     Output shape : (batch, gru_units)   <- weighted sum collapsed over time
#     """

#     def __init__(self, **kwargs):
#         super().__init__(**kwargs)

#     def build(self, input_shape):
#         # input_shape = (batch, T, d)
#         d = input_shape[-1]

#         # Learned projection: each hidden state -> scalar score
#         self.W = self.add_weight(
#             name="attn_W",
#             shape=(d, 1),
#             initializer="glorot_uniform",
#             trainable=True,
#         )
#         self.b = self.add_weight(
#             name="attn_b",
#             shape=(1,),
#             initializer="zeros",
#             trainable=True,
#         )
#         super().build(input_shape)

#     def call(self, hidden_states):
#         """
#         Parameters
#         ----------
#         hidden_states : Tensor  (batch, T, d)

#         Returns
#         -------
#         context : Tensor  (batch, d)
#         """
#         # Score each time step: (batch, T, d) @ (d, 1) -> (batch, T, 1) -> (batch, T)
#         e = tf.squeeze(
#             tf.tanh(tf.matmul(hidden_states, self.W) + self.b),
#             axis=-1,
#         )

#         # Softmax across time axis -> attention weights (batch, T)
#         alpha = tf.nn.softmax(e, axis=1)

#         # Weighted sum -> context vector (batch, d)
#         context = tf.reduce_sum(tf.expand_dims(alpha, axis=-1) * hidden_states, axis=1)

#         return context

#     def get_config(self):
#         return super().get_config()
    

# # """
# # attention_layer.py
# # ------------------
# # Custom Keras layer implementing Temporal Self-Attention.

# # How it works
# # ------------
# # Given a sequence of GRU hidden states  H ∈ ℝ^(T × d):

# #   1. Score each time-step with a learned weight vector:
# #        e_t = tanh(H_t · W + b)        (W ∈ ℝ^d,  b ∈ ℝ)

# #   2. Normalise scores across time with softmax to get attention weights α:
# #        α = softmax(e)                  α ∈ ℝ^T,  Σ α_t = 1

# #   3. Compute the context vector as a weighted sum of hidden states:
# #        c = Σ_t α_t · H_t              c ∈ ℝ^d

# # This lets the model focus on the most informative frames in the gesture
# # (e.g. the peak of a hand wave) rather than only using the final hidden state.
# # Because the attention is additive (Bahdanau-style) it is very cheap — just one
# # Dense-equivalent multiply — and runs comfortably on CPU.
# # """

# # import tensorflow as tf
# # from tensorflow.keras.layers import Layer


# # class TemporalAttention(Layer):
# #     """
# #     Additive (Bahdanau-style) temporal attention over a GRU sequence output.

# #     Input shape  : (batch, time_steps, gru_units)
# #     Output shape : (batch, gru_units)   ← weighted sum collapsed over time
# #     """

# #     def __init__(self, **kwargs):
# #         super().__init__(**kwargs)

# #     def build(self, input_shape):
# #         # input_shape = (batch, T, d)
# #         d = input_shape[-1]

# #         # Learned projection into a scalar score per time-step
# #         self.W = self.add_weight(
# #             name="attn_W",
# #             shape=(d, 1),
# #             initializer="glorot_uniform",
# #             trainable=True,
# #         )
# #         self.b = self.add_weight(
# #             name="attn_b",
# #             shape=(1,),
# #             initializer="zeros",
# #             trainable=True,
# #         )
# #         super().build(input_shape)

# #     def call(self, hidden_states):
# #         """
# #         Parameters
# #         ----------
# #         hidden_states : Tensor  (batch, T, d)

# #         Returns
# #         -------
# #         context : Tensor  (batch, d)
# #         """
# #         # ── Score ────────────────────────────────────────────────────────────
# #         # (batch, T, d) @ (d, 1) → (batch, T, 1) → squeeze → (batch, T)
# #         e = tf.squeeze(
# #             tf.tanh(tf.matmul(hidden_states, self.W) + self.b),
# #             axis=-1,
# #         )

# #         # ── Attention weights ─────────────────────────────────────────────────
# #         alpha = tf.nn.softmax(e, axis=1)                  # (batch, T)

# #         # ── Context vector ───────────────────────────────────────────────────
# #         # Expand alpha for broadcasting: (batch, T, 1)
# #         alpha_expanded = tf.expand_dims(alpha, axis=-1)

# #         # Weighted sum across time → (batch, d)
# #         context = tf.reduce_sum(alpha_expanded * hidden_states, axis=1)

# #         return context

# #     def get_config(self):
# #         return super().get_config()