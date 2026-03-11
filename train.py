"""
ML Training Pipeline
Trains Naive Bayes, Random Forest, XGBoost, LightGBM with SMOTE.
Evaluates, selects best model, and saves artifacts.
"""

import os
import sys
import json
import warnings
import joblib
import numpy as np
import pandas as pd

from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.naive_bayes import GaussianNB
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
from sklearn.metrics import (accuracy_score, precision_score, recall_score,
                             f1_score, roc_auc_score)
from sklearn.preprocessing import StandardScaler
from imblearn.over_sampling import SMOTE

warnings.filterwarnings('ignore')

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def load_data(dataset_path):
    """Load the credit card dataset."""
    df = pd.read_csv(dataset_path)
    X = df.drop('is_fraud', axis=1)
    y = df['is_fraud']
    return X, y


def train_and_evaluate():
    """Full training pipeline."""
    from config import Config

    dataset_path = Config.DATASET_PATH
    model_dir = Config.MODEL_DIR
    os.makedirs(model_dir, exist_ok=True)

    # Check if dataset exists, if not generate it
    if not os.path.exists(dataset_path):
        print("Dataset not found. Generating synthetic dataset...")
        from dataset.generate_dataset import generate_dataset
        df = generate_dataset()
        os.makedirs(os.path.dirname(dataset_path), exist_ok=True)
        df.to_csv(dataset_path, index=False)
        print(f"Dataset saved to {dataset_path}")

    print("Loading dataset...")
    X, y = load_data(dataset_path)
    print(f"Dataset shape: {X.shape}, Fraud ratio: {y.mean():.2%}")

    # Train-test split (70-30)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=y
    )

    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Apply SMOTE on training set only
    print("Applying SMOTE...")
    smote = SMOTE(random_state=42)
    X_train_resampled, y_train_resampled = smote.fit_resample(X_train_scaled, y_train)
    print(f"After SMOTE: {len(X_train_resampled)} samples, "
          f"Fraud ratio: {y_train_resampled.mean():.2%}")

    # Define models
    models = {
        'Naive Bayes': GaussianNB(),
        'Random Forest': RandomForestClassifier(
            n_estimators=100, random_state=42, n_jobs=-1
        ),
        'XGBoost': XGBClassifier(
            n_estimators=100, random_state=42, use_label_encoder=False,
            eval_metric='logloss', verbosity=0
        ),
        'LightGBM': LGBMClassifier(
            n_estimators=100, random_state=42, verbose=-1
        )
    }

    results = {}
    trained_models = {}

    for name, model in models.items():
        print(f"\nTraining {name}...")

        # Train
        model.fit(X_train_resampled, y_train_resampled)
        trained_models[name] = model

        # Predict
        y_pred = model.predict(X_test_scaled)
        y_prob = model.predict_proba(X_test_scaled)[:, 1]

        # Metrics
        accuracy = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred, zero_division=0)
        recall = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)
        roc_auc = roc_auc_score(y_test, y_prob)

        # Cross-validation (5-fold)
        cv_scores = cross_val_score(model, X_train_resampled, y_train_resampled,
                                    cv=5, scoring='f1')

        results[name] = {
            'accuracy': round(accuracy, 4),
            'precision': round(precision, 4),
            'recall': round(recall, 4),
            'f1_score': round(f1, 4),
            'roc_auc': round(roc_auc, 4),
            'cv_f1_mean': round(cv_scores.mean(), 4),
            'cv_f1_std': round(cv_scores.std(), 4)
        }

        print(f"  Accuracy: {accuracy:.4f} | Precision: {precision:.4f} | "
              f"Recall: {recall:.4f} | F1: {f1:.4f} | ROC-AUC: {roc_auc:.4f}")
        print(f"  CV F1: {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")

    # Select best model (F1 primary, ROC-AUC tiebreak)
    best_name = max(results, key=lambda k: (results[k]['f1_score'], results[k]['roc_auc']))
    best_model = trained_models[best_name]

    print(f"\n{'='*60}")
    print(f"Best Model: {best_name}")
    print(f"F1-Score: {results[best_name]['f1_score']}")
    print(f"ROC-AUC: {results[best_name]['roc_auc']}")
    print(f"{'='*60}")

    # Save artifacts
    joblib.dump(best_model, os.path.join(model_dir, 'best_model.pkl'))
    joblib.dump(scaler, os.path.join(model_dir, 'scaler.pkl'))

    meta = {
        'best_model_name': best_name,
        'feature_names': list(X.columns),
        'results': results
    }
    with open(os.path.join(model_dir, 'metrics.json'), 'w') as f:
        json.dump(meta, f, indent=2)

    # Save all models for comparison
    for name, model in trained_models.items():
        safe_name = name.lower().replace(' ', '_')
        joblib.dump(model, os.path.join(model_dir, f'{safe_name}.pkl'))

    print(f"\nAll models and metrics saved to {model_dir}")
    return best_name, results


if __name__ == '__main__':
    train_and_evaluate()
