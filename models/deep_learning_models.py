"""
Deep-learning models for credit card fraud detection:
  1. Hybrid CNN-BiGRU (TensorFlow / Keras)
  2. BERT-based classifier (HuggingFace Transformers + PyTorch)
"""

import numpy as np

from src.utils.config import RANDOM_SEED, CNN_BIGRU_CONFIG, BERT_CONFIG

# ══════════════════════════════════════════════
# 1.  CNN-BiGRU  (Keras)
# ══════════════════════════════════════════════

def build_cnn_bigru(input_shape, config=None):
    """
    Build a hybrid Conv1D → BiGRU model for fraud detection.

    Architecture
    ------------
    Input → Conv1D (64, kernel=3, relu) → MaxPool1D → Bidirectional GRU (64) →
    Dropout (0.5) → Dense (32, relu) → Dense (1, sigmoid)

    Parameters
    ----------
    input_shape : tuple  – (timesteps, features). For tabular data we reshape
                           each sample to (n_features, 1).
    config : dict, optional – override CNN_BIGRU_CONFIG values.

    Returns
    -------
    keras.Model (uncompiled)
    """
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras import layers

    tf.random.set_seed(RANDOM_SEED)
    cfg = {**CNN_BIGRU_CONFIG, **(config or {})}

    model = keras.Sequential([
        layers.Input(shape=input_shape),
        layers.Conv1D(
            filters=cfg["conv_filters"],
            kernel_size=cfg["kernel_size"],
            activation="relu",
            padding="same",
        ),
        layers.MaxPooling1D(pool_size=2),
        layers.Bidirectional(
            layers.GRU(cfg["gru_units"], return_sequences=False)
        ),
        layers.Dropout(cfg["dropout_rate"]),
        layers.Dense(cfg["dense_units"], activation="relu"),
        layers.Dense(1, activation="sigmoid"),
    ])
    return model


def compile_cnn_bigru(model, learning_rate=None):
    """Compile the CNN-BiGRU model with Adam and binary cross-entropy."""
    import tensorflow as tf

    lr = learning_rate or CNN_BIGRU_CONFIG["learning_rate"]
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=lr),
        loss="binary_crossentropy",
        metrics=["accuracy",
                 tf.keras.metrics.Precision(name="precision"),
                 tf.keras.metrics.Recall(name="recall"),
                 tf.keras.metrics.AUC(name="auc")],
    )
    return model


def train_cnn_bigru(model, X_train, y_train, X_val=None, y_val=None,
                    config=None):
    """
    Train the CNN-BiGRU model with early stopping.

    Parameters
    ----------
    model      : compiled Keras model.
    X_train    : np.ndarray – shape (n, features, 1).
    y_train    : np.ndarray – binary labels.
    X_val      : optional validation features.
    y_val      : optional validation labels.

    Returns
    -------
    history : keras.callbacks.History
    """
    from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau

    cfg = {**CNN_BIGRU_CONFIG, **(config or {})}

    callbacks = [
        EarlyStopping(monitor="val_loss" if X_val is not None else "loss",
                      patience=5, restore_best_weights=True),
        ReduceLROnPlateau(factor=0.5, patience=3, min_lr=1e-6),
    ]

    validation_data = (X_val, y_val) if X_val is not None else None

    history = model.fit(
        X_train, y_train,
        epochs=cfg["epochs"],
        batch_size=cfg["batch_size"],
        validation_data=validation_data,
        callbacks=callbacks,
        verbose=1,
    )
    return history


def reshape_for_cnn(X):
    """Reshape 2-D tabular data (n, d) → (n, d, 1) for Conv1D input."""
    arr = np.asarray(X)
    if arr.ndim == 2:
        return arr.reshape(arr.shape[0], arr.shape[1], 1)
    return arr


# ══════════════════════════════════════════════
# 2.  BERT-based classifier  (PyTorch + HuggingFace)
# ══════════════════════════════════════════════

def _features_to_text(row):
    """
    Convert a single row of numeric features into a human-readable text
    string suitable for a language-model input.

    Example output:
      "Transaction: amount 125.50 | feature_V1 -1.35 | feature_V2 1.19 | …"
    """
    parts = ["Transaction:"]
    for col, val in row.items():
        parts.append(f"{col} {val:.4f}")
    return " | ".join(parts)


class BertFraudClassifier:
    """
    Wraps HuggingFace DistilBERT for binary sequence classification on
    tabular data that has been converted to text.

    Usage
    -----
    >>> clf = BertFraudClassifier()
    >>> clf.prepare_data(X_train, y_train, X_val, y_val)
    >>> clf.train()
    >>> preds = clf.predict(X_test)
    """

    def __init__(self, config=None):
        self.cfg = {**BERT_CONFIG, **(config or {})}
        self._model = None
        self._tokenizer = None
        self._device = None

    # ── data prep ──

    def prepare_data(self, X_train, y_train, X_val=None, y_val=None):
        """Tokenise tabular features converted to text."""
        import pandas as pd
        import torch
        from torch.utils.data import TensorDataset, DataLoader
        from transformers import AutoTokenizer

        self._device = torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )
        self._tokenizer = AutoTokenizer.from_pretrained(self.cfg["model_name"])

        def _encode(X, y=None):
            if isinstance(X, pd.DataFrame):
                texts = X.apply(_features_to_text, axis=1).tolist()
            else:
                texts = [_features_to_text(pd.Series(row)) for row in X]
            enc = self._tokenizer(
                texts, padding="max_length", truncation=True,
                max_length=self.cfg["max_length"], return_tensors="pt",
            )
            ids = enc["input_ids"]
            mask = enc["attention_mask"]
            if y is not None:
                labels = torch.tensor(np.asarray(y), dtype=torch.long)
                return TensorDataset(ids, mask, labels)
            return TensorDataset(ids, mask)

        self._train_ds = _encode(X_train, y_train)
        self._val_ds = _encode(X_val, y_val) if X_val is not None else None

        self._train_loader = DataLoader(
            self._train_ds, batch_size=self.cfg["batch_size"], shuffle=True
        )
        self._val_loader = (
            DataLoader(self._val_ds, batch_size=self.cfg["batch_size"])
            if self._val_ds else None
        )

    # ── training ──

    def train(self):
        """Fine-tune DistilBERT for binary classification."""
        import torch
        from transformers import AutoModelForSequenceClassification

        self._model = AutoModelForSequenceClassification.from_pretrained(
            self.cfg["model_name"], num_labels=2
        ).to(self._device)

        optimizer = torch.optim.AdamW(
            self._model.parameters(), lr=self.cfg["learning_rate"]
        )

        self._model.train()
        for epoch in range(self.cfg["epochs"]):
            total_loss = 0
            for batch in self._train_loader:
                ids, mask, labels = [b.to(self._device) for b in batch]
                outputs = self._model(
                    input_ids=ids, attention_mask=mask, labels=labels
                )
                loss = outputs.loss
                loss.backward()
                optimizer.step()
                optimizer.zero_grad()
                total_loss += loss.item()
            avg_loss = total_loss / len(self._train_loader)
            print(f"[BERT] Epoch {epoch+1}/{self.cfg['epochs']}  "
                  f"loss={avg_loss:.4f}")

    # ── inference ──

    def predict(self, X):
        """Return predicted class labels (0/1)."""
        probs = self.predict_proba(X)
        return (probs >= 0.5).astype(int)

    def predict_proba(self, X):
        """Return fraud probability for each sample."""
        import pandas as pd
        import torch
        from torch.utils.data import DataLoader, TensorDataset

        if isinstance(X, pd.DataFrame):
            texts = X.apply(_features_to_text, axis=1).tolist()
        else:
            texts = [_features_to_text(pd.Series(row)) for row in X]

        enc = self._tokenizer(
            texts, padding="max_length", truncation=True,
            max_length=self.cfg["max_length"], return_tensors="pt",
        )
        ds = TensorDataset(enc["input_ids"], enc["attention_mask"])
        loader = DataLoader(ds, batch_size=self.cfg["batch_size"])

        self._model.eval()
        all_probs = []
        with torch.no_grad():
            for ids, mask in loader:
                ids, mask = ids.to(self._device), mask.to(self._device)
                logits = self._model(input_ids=ids, attention_mask=mask).logits
                probs = torch.softmax(logits, dim=1)[:, 1].cpu().numpy()
                all_probs.append(probs)
        return np.concatenate(all_probs)
