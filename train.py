import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.config import *
from src.utils import *
import xgboost as xgb
import lightgbm as lgb
from sklearn.ensemble import RandomForestClassifier
from sklearn.naive_bayes import GaussianNB
import warnings
warnings.filterwarnings('ignore')

def train_all_models():
    print("Loading data...")
    X, y = load_and_preprocess_data()
    X_train, X_val, X_test, y_train, y_val, y_test = split_data(X, y)

    # Apply resampling to training set
    X_train_res, y_train_res = apply_resampling(X_train, y_train)
    print(f"Training set size after resampling: {X_train_res.shape}")

    # Define models
    models = {
        'xgboost': xgb.XGBClassifier(**XGB_PARAMS),
        'lightgbm': lgb.LGBMClassifier(**LGBM_PARAMS),
        'randomforest': RandomForestClassifier(**RF_PARAMS),
        'naivebayes': GaussianNB()
    }

    results = {}
    for name, model in models.items():
        print(f"Training {name}...")
        model.fit(X_train_res, y_train_res)
        save_model(model, name)
        metrics = evaluate_model(model, X_val, y_val)
        results[name] = metrics
        print(f"{name} - F1: {metrics['f1']:.4f}, ROC AUC: {metrics.get('roc_auc', 0):.4f}")

    # Save split data and full data for dashboard
    joblib.dump((X_train, X_val, X_test, y_train, y_val, y_test), MODELS_DIR / 'split_data.pkl')
    joblib.dump((X, y), MODELS_DIR / 'full_data.pkl')

    # Create SHAP explainer for XGBoost (best model)
    print("Creating SHAP explainer...")
    xgb_model = load_model('xgboost')
    X_background = X_train.sample(n=min(100, len(X_train)), random_state=RANDOM_STATE)
    explainer = shap.TreeExplainer(xgb_model, X_background)
    joblib.dump(explainer, MODELS_DIR / 'shap_explainer.pkl')

    print("Training complete. All models saved.")
    return results

if __name__ == '__main__':
    results = train_all_models()
    print("\n=== Validation Performance ===")
    for model, metrics in results.items():
        print(f"{model.upper()}: F1={metrics['f1']:.4f}, Precision={metrics['precision']:.4f}, "
              f"Recall={metrics['recall']:.4f}, Accuracy={metrics['accuracy']:.4f}")