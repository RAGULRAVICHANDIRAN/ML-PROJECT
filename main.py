"""
main.py – CLI entry-point for the Credit Card Fraud Detection project.

Usage:
    python main.py preprocess          Preprocess the dataset
    python main.py train --existing    Train paper-replication models (NB, RF, XGB)
    python main.py train --proposed    Train proposed models (Stacking + tuning)
    python main.py evaluate            Evaluate all saved models and generate metrics
    python main.py explain             Run SHAP & LIME explainability
    python main.py dashboard           Launch Streamlit dashboard
    python main.py all                 Run full pipeline end-to-end
"""

import argparse
import sys
import warnings
import numpy as np
import pandas as pd
import joblib
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.config import (
    RANDOM_SEED, MODELS_DIR, FIGURES_DIR, DATASET_NAME,
    MODEL_NB, MODEL_RF, MODEL_XGB, MODEL_LGBM,
    MODEL_CNN_BIGRU, MODEL_BERT, MODEL_STACKING,
)
from src.utils.metrics import evaluate_model, results_to_dataframe
from src.data.download_data import download_dataset
from src.data.preprocessing import preprocess, load_processed
from src.data.balancing_strategies import get_balanced_datasets, describe_balance
from src.models.baseline_models import get_naive_bayes
from src.models.ensemble_models import (
    get_random_forest, get_xgboost, get_lightgbm, get_stacking_ensemble,
    tune_random_forest, tune_xgboost,
)


# ──────────────────────────────────────────────
# Reproducibility
# ──────────────────────────────────────────────
np.random.seed(RANDOM_SEED)
warnings.filterwarnings("ignore")


# ══════════════════════════════════════════════
# Preprocessing
# ══════════════════════════════════════════════

def cmd_preprocess(args):
    """Run preprocessing for the European dataset."""
    print("\n" + "=" * 60)
    print("  STEP 1 — PREPROCESSING")
    print("=" * 60)
    download_dataset()

    try:
        data = preprocess()
        print("[✓] Dataset preprocessed.\n")
    except FileNotFoundError as e:
        print(f"[✗] {e}\n")
        data = None

    return data


# ══════════════════════════════════════════════
# Training – existing work
# ══════════════════════════════════════════════

def _get_model(model_name):
    if model_name == MODEL_NB:
        return get_naive_bayes()
    elif model_name == MODEL_RF:
        return get_random_forest(paper_params=True)
    elif model_name == MODEL_XGB:
        return get_xgboost(paper_params=True)
    elif model_name == MODEL_LGBM:
        return get_lightgbm(paper_params=True)
    else:
        raise ValueError(f"Unknown model: {model_name}")


def _train_and_eval(model, model_name, X_train, y_train, X_test, y_test):
    """Train a sklearn-compatible model, evaluate, and return metrics dict."""
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    y_prob = (model.predict_proba(X_test)[:, 1]
              if hasattr(model, "predict_proba") else None)
    metrics = evaluate_model(y_test, y_pred, y_prob)
    print(f"  {model_name:15s}  F1={metrics['f1']:.4f}  "
          f"AUC={metrics['roc_auc']:.4f}")
    return model, metrics


def cmd_train_existing(args):
    """Train NB, RF, XGBoost on all strategy combinations."""
    print("\n" + "=" * 60)
    print("  STEP 2a — TRAINING EXISTING MODELS")
    print("=" * 60)

    try:
        data = load_processed()
    except FileNotFoundError:
        print("[!] Processed data not found. Run 'preprocess' first.")
        return {}

    balanced = get_balanced_datasets(data["X_train"], data["y_train"])
    all_results = {DATASET_NAME: {}}

    for strat_name, (X_bal, y_bal) in balanced.items():
        print(f"\n--- {strat_name} ---")
        describe_balance(y_bal, strat_name)
        all_results[DATASET_NAME][strat_name] = {}

        for model_name in [MODEL_NB, MODEL_RF, MODEL_XGB, MODEL_LGBM]:
            model = _get_model(model_name)
            trained, metrics = _train_and_eval(
                model, model_name,
                X_bal, y_bal,
                data["X_test"], data["y_test"],
            )
            all_results[DATASET_NAME][strat_name][model_name] = metrics

            # Save model
            out_path = MODELS_DIR / f"{DATASET_NAME}_{strat_name}_{model_name}.joblib"
            joblib.dump(trained, out_path)

    # Save results
    df = results_to_dataframe(all_results)
    df.to_csv(MODELS_DIR / "existing_results.csv", index=False)
    print(f"\n[✓] Results saved to {MODELS_DIR / 'existing_results.csv'}")
    return all_results


# ══════════════════════════════════════════════
# Training – proposed work
# ══════════════════════════════════════════════

def _subsample(X, y, max_n=50000):
    """Subsample to at most max_n rows to keep training fast."""
    if len(X) <= max_n:
        return X, y
    idx = np.random.choice(len(X), max_n, replace=False)
    X_sub = X.iloc[idx] if hasattr(X, "iloc") else X[idx]
    y_sub = y.iloc[idx] if hasattr(y, "iloc") else y[idx]
    print(f"  [subsample] {len(X):,} → {max_n:,} samples for speed")
    return X_sub, y_sub


def cmd_train_proposed(args):
    """Train Stacking, CNN-BiGRU, BERT (on SMOTE-balanced data)."""
    print("\n" + "=" * 60)
    print("  STEP 2b — TRAINING PROPOSED MODELS")
    print("=" * 60)

    try:
        data = load_processed()
    except FileNotFoundError:
        print("[!] Processed data not found.")
        return {}

    balanced = get_balanced_datasets(data["X_train"], data["y_train"])
    X_smote, y_smote = balanced["smote"]
    X_test, y_test = data["X_test"], data["y_test"]
    X_val, y_val = data["X_val"], data["y_val"]
    results = {}

    # Cap training size for speed
    X_fast, y_fast = _subsample(X_smote, y_smote, max_n=50000)

    # ── Stacking ──
    print("\n--- Stacking Ensemble ---")
    try:
        stacking = get_stacking_ensemble()
        stacking.fit(X_fast, y_fast)
        y_pred = stacking.predict(X_test)
        y_prob = stacking.predict_proba(X_test)[:, 1]
        metrics = evaluate_model(y_test, y_pred, y_prob)
        results[MODEL_STACKING] = metrics
        print(f"  Stacking  F1={metrics['f1']:.4f}  AUC={metrics['roc_auc']:.4f}")
        joblib.dump(stacking, MODELS_DIR / f"{DATASET_NAME}_smote_stacking.joblib")
    except Exception as e:
        print(f"  [!] Stacking failed: {e}")

    # ── CNN-BiGRU ──
    print("\n--- CNN-BiGRU ---")
    try:
        from src.models.deep_learning_models import (
            build_cnn_bigru, compile_cnn_bigru, train_cnn_bigru, reshape_for_cnn,
        )
        X_tr_3d = reshape_for_cnn(X_fast)
        X_val_3d = reshape_for_cnn(X_val)
        X_te_3d = reshape_for_cnn(X_test)

        cnn_model = build_cnn_bigru(input_shape=(X_tr_3d.shape[1], 1))
        cnn_model = compile_cnn_bigru(cnn_model)
        _history = train_cnn_bigru(cnn_model, X_tr_3d, y_fast, X_val_3d, y_val)

        y_prob_cnn = cnn_model.predict(X_te_3d).flatten()
        y_pred_cnn = (y_prob_cnn >= 0.5).astype(int)
        metrics = evaluate_model(y_test, y_pred_cnn, y_prob_cnn)
        results[MODEL_CNN_BIGRU] = metrics
        print(f"  CNN-BiGRU  F1={metrics['f1']:.4f}  AUC={metrics['roc_auc']:.4f}")
        cnn_model.save(str(MODELS_DIR / f"{DATASET_NAME}_smote_cnn_bigru.h5"))
    except Exception as e:
        print(f"  [!] CNN-BiGRU failed: {e}")

    # ── BERT ──
    print("\n--- BERT ---")
    try:
        from src.models.deep_learning_models import BertFraudClassifier

        n_bert = min(5000, len(X_fast))
        idx = np.random.choice(len(X_fast), n_bert, replace=False)
        X_bert_train = X_fast.iloc[idx] if hasattr(X_fast, "iloc") else X_fast[idx]
        y_bert_train = y_fast.iloc[idx] if hasattr(y_fast, "iloc") else y_fast[idx]

        n_test = min(2000, len(X_test))
        X_bert_test = X_test.iloc[:n_test] if hasattr(X_test, "iloc") else X_test[:n_test]
        y_bert_test = y_test.iloc[:n_test] if hasattr(y_test, "iloc") else y_test[:n_test]

        bert_clf = BertFraudClassifier()
        bert_clf.prepare_data(X_bert_train, y_bert_train)
        bert_clf.train()
        y_prob_bert = bert_clf.predict_proba(X_bert_test)
        y_pred_bert = (y_prob_bert >= 0.5).astype(int)
        metrics = evaluate_model(y_bert_test, y_pred_bert, y_prob_bert)
        results[MODEL_BERT] = metrics
        print(f"  BERT  F1={metrics['f1']:.4f}  AUC={metrics['roc_auc']:.4f}")
    except Exception as e:
        print(f"  [!] BERT failed: {e}")

    # Hyperparameter tuning
    print("\n--- Hyperparameter Tuning (RF & XGB on SMOTE) ---")
    try:
        X_sm, y_sm = _subsample(X_smote, y_smote, max_n=50000)

        best_rf, _ = tune_random_forest(X_sm, y_sm, n_iter=15)
        joblib.dump(best_rf, MODELS_DIR / "tuned_rf.joblib")

        best_xgb, _ = tune_xgboost(X_sm, y_sm, n_iter=15)
        joblib.dump(best_xgb, MODELS_DIR / "tuned_xgb.joblib")
    except Exception as e:
        print(f"  [!] Tuning failed: {e}")

    return results


# ══════════════════════════════════════════════
# Evaluate & generate visualizations
# ══════════════════════════════════════════════

def cmd_evaluate(args):
    """Load results CSV and create all plots."""
    print("\n" + "=" * 60)
    print("  STEP 3 — EVALUATION & VISUALIZATION")
    print("=" * 60)

    from src.visualization.plot_utils import (
        plot_methodology_flowchart,
        plot_performance_by_dataset,
        plot_f1_density,
        plot_average_performance,
    )

    csv_path = MODELS_DIR / "existing_results.csv"
    if not csv_path.exists():
        print("[!] No results CSV found. Run 'train --existing' first.")
        return

    df = pd.read_csv(csv_path)

    plot_methodology_flowchart()
    plot_performance_by_dataset(df)
    plot_f1_density(df)
    plot_average_performance(df)

    print(f"\n[✓] All figures saved to {FIGURES_DIR}")


# ══════════════════════════════════════════════
# Explainability
# ══════════════════════════════════════════════

def cmd_explain(args):
    """Run SHAP and LIME on the best tree-based model."""
    print("\n" + "=" * 60)
    print("  STEP 4 — EXPLAINABILITY")
    print("=" * 60)

    from src.models.explainability import (
        shap_analysis, shap_force_plot, lime_analysis, feature_importance_report,
    )

    model_path = MODELS_DIR / f"{DATASET_NAME}_smote_xgboost.joblib"
    if not model_path.exists():
        print(f"[!] Model {model_path} not found. Run training first.")
        return

    model = joblib.load(model_path)
    data = load_processed()
    save_dir = FIGURES_DIR / DATASET_NAME

    print(f"\n--- Explainability Analysis ---")
    shap_analysis(model, data["X_test"], model_type="tree", save_dir=save_dir)
    shap_force_plot(model, data["X_test"], instance_idx=0, save_dir=save_dir)
    lime_analysis(model, data["X_train"], data["X_test"],
                  instance_idx=0, save_dir=save_dir)
    feature_importance_report(model, data["X_test"], data["y_test"],
                              save_dir=save_dir)

    print(f"\n[✓] Explainability reports saved to {FIGURES_DIR}")


# ══════════════════════════════════════════════
# Dashboard
# ══════════════════════════════════════════════

def cmd_dashboard(args):
    """Launch the Streamlit admin dashboard."""
    import subprocess
    dashboard_path = PROJECT_ROOT / "dashboard" / "app.py"
    print(f"Launching admin dashboard: {dashboard_path}")
    subprocess.run(["streamlit", "run", str(dashboard_path)], check=True)


def cmd_atm(args):
    """Launch the standalone ATM Streamlit app on port 8502."""
    import subprocess
    atm_path = PROJECT_ROOT / "dashboard" / "atm_app.py"
    print(f"Launching ATM app: {atm_path}")
    print("  ATM URL:   http://localhost:8502")
    print("  Admin URL: http://localhost:8501  (run 'python main.py dashboard' separately)")
    subprocess.run(["streamlit", "run", str(atm_path), "--server.port", "8502"], check=True)


# ══════════════════════════════════════════════
# Full pipeline
# ══════════════════════════════════════════════

def cmd_all(args):
    """Run entire pipeline end-to-end."""
    cmd_preprocess(args)
    cmd_train_existing(args)
    cmd_train_proposed(args)
    cmd_evaluate(args)
    cmd_explain(args)


# ══════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Credit Card Fraud Detection – CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("preprocess", help="Preprocess the dataset")

    train_p = sub.add_parser("train", help="Train models")
    train_group = train_p.add_mutually_exclusive_group(required=True)
    train_group.add_argument("--existing", action="store_true",
                             help="Train paper-replication models")
    train_group.add_argument("--proposed", action="store_true",
                             help="Train proposed deep-learning models")

    sub.add_parser("evaluate", help="Generate metrics & plots")
    sub.add_parser("explain", help="Run SHAP & LIME explainability")
    sub.add_parser("dashboard", help="Launch Streamlit admin dashboard")
    sub.add_parser("atm", help="Launch standalone ATM app (port 8502)")
    sub.add_parser("all", help="Run full pipeline")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    commands = {
        "preprocess": cmd_preprocess,
        "train": lambda a: cmd_train_existing(a) if a.existing else cmd_train_proposed(a),
        "evaluate": cmd_evaluate,
        "explain": cmd_explain,
        "dashboard": cmd_dashboard,
        "atm": cmd_atm,
        "all": cmd_all,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
