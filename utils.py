import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
from imblearn.over_sampling import RandomOverSampler, SMOTE
from imblearn.under_sampling import RandomUnderSampler
import joblib
import shap
from src.config import DATA_PATH, MODELS_DIR, RANDOM_STATE, RESAMPLING_METHOD

def load_and_preprocess_data():
    """Load EU dataset, scale Amount & Time, return features/target."""
    df = pd.read_csv(DATA_PATH)
    # Scale 'Amount' and 'Time'
    scaler = StandardScaler()
    df['Amount_scaled'] = scaler.fit_transform(df['Amount'].values.reshape(-1, 1))
    df['Time_scaled'] = scaler.fit_transform(df['Time'].values.reshape(-1, 1))
    # Drop original columns
    df.drop(['Time', 'Amount'], axis=1, inplace=True)
    # Rename scaled columns
    df.rename(columns={'Amount_scaled': 'Amount', 'Time_scaled': 'Time'}, inplace=True)
    # Features & target
    X = df.drop('Class', axis=1)
    y = df['Class']
    return X, y

def split_data(X, y):
    """Train / validation / test split."""
    X_temp, X_test, y_temp, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_STATE, stratify=y)
    X_train, X_val, y_train, y_val = train_test_split(
        X_temp, y_temp, test_size=0.15, random_state=RANDOM_STATE, stratify=y_temp)  # 0.15*0.8=0.12 of total
    return X_train, X_val, X_test, y_train, y_val, y_test

def apply_resampling(X_train, y_train, method=RESAMPLING_METHOD):
    """Handle class imbalance using specified method."""
    if method == 'oversample':
        resampler = RandomOverSampler(random_state=RANDOM_STATE)
    elif method == 'undersample':
        resampler = RandomUnderSampler(random_state=RANDOM_STATE)
    elif method == 'smote':
        resampler = SMOTE(random_state=RANDOM_STATE)
    else:
        return X_train, y_train
    X_res, y_res = resampler.fit_resample(X_train, y_train)
    return X_res, y_res

def evaluate_model(model, X_val, y_val):
    """Return dictionary of metrics."""
    y_pred = model.predict(X_val)
    y_proba = model.predict_proba(X_val)[:, 1] if hasattr(model, 'predict_proba') else None
    metrics = {
        'accuracy': accuracy_score(y_val, y_pred),
        'precision': precision_score(y_val, y_pred, zero_division=0),
        'recall': recall_score(y_val, y_pred, zero_division=0),
        'f1': f1_score(y_val, y_pred, zero_division=0)
    }
    if y_proba is not None:
        metrics['roc_auc'] = roc_auc_score(y_val, y_proba)
    return metrics

def save_model(model, name):
    """Save model to MODELS_DIR."""
    joblib.dump(model, MODELS_DIR / f'{name}.pkl')

def load_model(name):
    """Load model from MODELS_DIR."""
    return joblib.load(MODELS_DIR / f'{name}.pkl')

def get_shap_explainer(model, X_background):
    """Create TreeExplainer for tree‑based models."""
    explainer = shap.TreeExplainer(model, X_background)
    return explainer

def generate_fraud_explanation(shap_values, feature_names, instance_idx=0):
    """Return human‑readable explanation string for a fraud prediction."""
    values = shap_values[instance_idx]
    base_value = shap_values.base_values[instance_idx] if hasattr(shap_values, 'base_values') else 0
    contributions = []
    for i, feat in enumerate(feature_names):
        contributions.append({
            'feature': feat,
            'shap_value': values[i],
            'abs_shap': abs(values[i])
        })
    contributions.sort(key=lambda x: x['abs_shap'], reverse=True)
    reasons = []
    for c in contributions[:3]:
        if c['shap_value'] > 0:
            reasons.append(f"- **{c['feature']}**: +{c['shap_value']:.3f} contribution")
    if not reasons:
        reasons = ["- No strong fraud indicators (model uncertain)"]
    explanation = f"**Base fraud probability (log‑odds):** {base_value:.3f}\n\n"
    explanation += "**Top reasons for fraud flag:**\n" + "\n".join(reasons)
    return explanation