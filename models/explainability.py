"""
Explainability module: SHAP, LIME, and feature-importance analysis.
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

from src.utils.config import FIGURES_DIR, RANDOM_SEED


# ══════════════════════════════════════════════
# SHAP
# ══════════════════════════════════════════════

def shap_analysis(model, X, model_type="tree", max_samples=500,
                  save_dir=None):
    """
    Compute SHAP values and produce summary + bar plots.

    Parameters
    ----------
    model      : trained model (sklearn / xgboost).
    X          : pd.DataFrame or np.ndarray – test features.
    model_type : 'tree' for tree-based models, 'kernel' for any model.
    max_samples: int – subsample X for performance.
    save_dir   : Path – where to save figures; defaults to FIGURES_DIR.

    Returns
    -------
    shap_values : np.ndarray
    """
    import shap

    save_dir = Path(save_dir or FIGURES_DIR)
    save_dir.mkdir(parents=True, exist_ok=True)

    if isinstance(X, pd.DataFrame):
        X_sample = X.sample(min(max_samples, len(X)), random_state=RANDOM_SEED)
    else:
        idx = np.random.RandomState(RANDOM_SEED).choice(
            len(X), min(max_samples, len(X)), replace=False
        )
        X_sample = X[idx]

    if model_type == "tree":
        explainer = shap.TreeExplainer(model)
    else:
        explainer = shap.KernelExplainer(
            model.predict_proba if hasattr(model, "predict_proba") else model.predict,
            shap.sample(X_sample, 100),
        )

    shap_values = explainer.shap_values(X_sample)

    # Handle list output (binary classification)
    if isinstance(shap_values, list):
        shap_values = shap_values[1]  # positive class

    # Summary plot
    plt.figure()
    shap.summary_plot(shap_values, X_sample, show=False)
    plt.tight_layout()
    plt.savefig(save_dir / "shap_summary.png", dpi=150)
    plt.close()

    # Bar plot
    plt.figure()
    shap.summary_plot(shap_values, X_sample, plot_type="bar", show=False)
    plt.tight_layout()
    plt.savefig(save_dir / "shap_bar.png", dpi=150)
    plt.close()

    print(f"[SHAP] Saved summary & bar plots to {save_dir}")
    return shap_values


def shap_force_plot(model, X, instance_idx=0, model_type="tree",
                    save_dir=None):
    """
    Generate a SHAP force plot for a single prediction.
    """
    import shap

    save_dir = Path(save_dir or FIGURES_DIR)
    save_dir.mkdir(parents=True, exist_ok=True)

    if model_type == "tree":
        explainer = shap.TreeExplainer(model)
    else:
        explainer = shap.KernelExplainer(
            model.predict_proba if hasattr(model, "predict_proba") else model.predict,
            shap.sample(X, 100),
        )

    row = X.iloc[[instance_idx]] if isinstance(X, pd.DataFrame) else X[[instance_idx]]
    sv = explainer.shap_values(row)
    if isinstance(sv, list):
        sv = sv[1]

    force = shap.force_plot(
        explainer.expected_value if not isinstance(explainer.expected_value, list)
        else explainer.expected_value[1],
        sv, row, matplotlib=True, show=False,
    )
    plt.savefig(save_dir / f"shap_force_{instance_idx}.png",
                dpi=150, bbox_inches="tight")
    plt.close()
    print(f"[SHAP] Saved force plot for instance {instance_idx}")


# ══════════════════════════════════════════════
# LIME
# ══════════════════════════════════════════════

def lime_analysis(model, X_train, X_explain, instance_idx=0,
                  feature_names=None, save_dir=None):
    """
    Generate a LIME explanation for a single instance.

    Parameters
    ----------
    model        : trained model with predict_proba.
    X_train      : training data (used to fit the explainer).
    X_explain    : dataset containing the instance to explain.
    instance_idx : index of the instance in X_explain.
    feature_names: list of feature names.
    save_dir     : output directory.

    Returns
    -------
    lime.explanation.Explanation
    """
    import lime.lime_tabular

    save_dir = Path(save_dir or FIGURES_DIR)
    save_dir.mkdir(parents=True, exist_ok=True)

    X_tr = np.asarray(X_train)
    X_ex = np.asarray(X_explain)

    if feature_names is None:
        if isinstance(X_train, pd.DataFrame):
            feature_names = list(X_train.columns)
        else:
            feature_names = [f"feature_{i}" for i in range(X_tr.shape[1])]

    explainer = lime.lime_tabular.LimeTabularExplainer(
        X_tr,
        feature_names=feature_names,
        class_names=["Legitimate", "Fraud"],
        mode="classification",
        random_state=RANDOM_SEED,
    )

    exp = explainer.explain_instance(
        X_ex[instance_idx],
        model.predict_proba,
        num_features=min(10, X_tr.shape[1]),
    )

    fig = exp.as_pyplot_figure()
    fig.tight_layout()
    fig.savefig(save_dir / f"lime_instance_{instance_idx}.png", dpi=150)
    plt.close(fig)

    # Save HTML
    exp.save_to_file(str(save_dir / f"lime_instance_{instance_idx}.html"))
    print(f"[LIME] Saved explanation for instance {instance_idx}")
    return exp


# ══════════════════════════════════════════════
# Feature importance
# ══════════════════════════════════════════════

def feature_importance_report(model, X, y, feature_names=None,
                              save_dir=None, n_repeats=10):
    """
    Build a feature-importance report using:
      1. Built-in importance (if available, e.g. tree models)
      2. Permutation importance

    Returns
    -------
    pd.DataFrame with columns: feature, builtin_importance, perm_importance_mean
    """
    from sklearn.inspection import permutation_importance

    save_dir = Path(save_dir or FIGURES_DIR)
    save_dir.mkdir(parents=True, exist_ok=True)

    if feature_names is None:
        if isinstance(X, pd.DataFrame):
            feature_names = list(X.columns)
        else:
            feature_names = [f"feature_{i}" for i in range(X.shape[1])]

    report = pd.DataFrame({"feature": feature_names})

    # Built-in
    if hasattr(model, "feature_importances_"):
        report["builtin_importance"] = model.feature_importances_
    else:
        report["builtin_importance"] = np.nan

    # Permutation
    perm = permutation_importance(
        model, X, y, n_repeats=n_repeats, random_state=RANDOM_SEED, n_jobs=-1
    )
    report["perm_importance_mean"] = perm.importances_mean
    report["perm_importance_std"] = perm.importances_std
    report = report.sort_values("perm_importance_mean", ascending=False)

    # Plot
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))

    top_n = min(15, len(report))
    top = report.head(top_n)

    if not top["builtin_importance"].isna().all():
        axes[0].barh(top["feature"], top["builtin_importance"])
        axes[0].set_title("Built-in Feature Importance")
        axes[0].invert_yaxis()

    axes[1].barh(top["feature"], top["perm_importance_mean"],
                 xerr=top["perm_importance_std"])
    axes[1].set_title("Permutation Feature Importance")
    axes[1].invert_yaxis()

    plt.tight_layout()
    plt.savefig(save_dir / "feature_importance.png", dpi=150)
    plt.close()

    print(f"[Importance] Saved feature-importance report to {save_dir}")
    return report
