"""
Ensemble models: Random Forest (bagging), XGBoost & LightGBM (boosting), and Stacking.
Includes both paper-parameter versions and hyperparameter-tuned versions.
"""

from sklearn.ensemble import RandomForestClassifier, StackingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import RandomizedSearchCV
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
import numpy as np

from src.utils.config import (
    RANDOM_SEED,
    PAPER_RF_PARAMS,
    PAPER_XGB_PARAMS,
    PAPER_LGBM_PARAMS,
    TUNE_RF_GRID,
    TUNE_XGB_GRID,
    N_SPLITS,
)


# ──────────────────────────────────────────────
# Paper-parameter models
# ──────────────────────────────────────────────

def get_random_forest(paper_params: bool = True, **overrides):
    """
    Return a Random Forest classifier.

    If paper_params=True, uses the exact parameters from the paper:
      n_estimators=5, max_samples=0.2, max_features=0.3, max_depth=3

    Complexity: θ(t · d · n · log(n))  where t = #trees.
    """
    if paper_params:
        params = {**PAPER_RF_PARAMS, **overrides}
    else:
        params = {
            "n_estimators": 100,
            "random_state": RANDOM_SEED,
            **overrides,
        }
    return RandomForestClassifier(**params)


def get_xgboost(paper_params: bool = True, **overrides):
    """
    Return an XGBoost classifier.

    If paper_params=True, uses the exact parameters from the paper:
      n_estimators=5, max_depth=3

    Complexity: O(t · d · log(n))
    """
    if paper_params:
        params = {**PAPER_XGB_PARAMS, **overrides}
    else:
        params = {
            "n_estimators": 100,
            "random_state": RANDOM_SEED,
            "eval_metric": "logloss",
            **overrides,
        }
    return XGBClassifier(**params)


def get_lightgbm(paper_params: bool = True, **overrides):
    """
    Return a LightGBM classifier.

    If paper_params=True, uses default project parameters.
    Complexity: O(t · d · log(n))
    """
    if paper_params:
        params = {**PAPER_LGBM_PARAMS, **overrides}
    else:
        params = {
            "n_estimators": 100,
            "random_state": RANDOM_SEED,
            "verbose": -1,
            **overrides,
        }
    return LGBMClassifier(**params)


# ──────────────────────────────────────────────
# Hyperparameter tuning
# ──────────────────────────────────────────────

def tune_random_forest(X, y, n_iter=50, cv=None, scoring="f1", verbose=1):
    """
    Run RandomizedSearchCV over the RF hyperparameter grid.

    Returns
    -------
    best_model : fitted RandomForestClassifier
    search    : the full RandomizedSearchCV object
    """
    cv = cv or N_SPLITS
    base = RandomForestClassifier(random_state=RANDOM_SEED)
    search = RandomizedSearchCV(
        base, TUNE_RF_GRID, n_iter=min(n_iter, 15), cv=cv,
        scoring=scoring, random_state=RANDOM_SEED,
        n_jobs=-1, verbose=verbose, refit=True,
    )
    search.fit(X, y)
    print(f"[RF Tuning] Best F1: {search.best_score_:.4f}")
    print(f"[RF Tuning] Best params: {search.best_params_}")
    return search.best_estimator_, search


def tune_xgboost(X, y, n_iter=50, cv=None, scoring="f1", verbose=1):
    """
    Run RandomizedSearchCV over the XGBoost hyperparameter grid.

    Returns
    -------
    best_model : fitted XGBClassifier
    search    : the full RandomizedSearchCV object
    """
    cv = cv or N_SPLITS
    base = XGBClassifier(
        random_state=RANDOM_SEED,
        eval_metric="logloss",
    )
    search = RandomizedSearchCV(
        base, TUNE_XGB_GRID, n_iter=min(n_iter, 15), cv=cv,
        scoring=scoring, random_state=RANDOM_SEED,
        n_jobs=-1, verbose=verbose, refit=True,
    )
    search.fit(X, y)
    print(f"[XGB Tuning] Best F1: {search.best_score_:.4f}")
    print(f"[XGB Tuning] Best params: {search.best_params_}")
    return search.best_estimator_, search


# ──────────────────────────────────────────────
# Stacking ensemble
# ──────────────────────────────────────────────

def get_stacking_ensemble(base_learners=None, meta_learner=None):
    """
    Build a Stacking ensemble.

    Parameters
    ----------
    base_learners : list of (name, estimator) tuples.
        Defaults to [RF, XGB].
    meta_learner : estimator for the final combination.
        Defaults to LogisticRegression.

    Returns
    -------
    StackingClassifier
    """
    if base_learners is None:
        base_learners = [
            ("rf", get_random_forest(paper_params=False)),
            ("xgb", get_xgboost(paper_params=False)),
        ]
    if meta_learner is None:
        meta_learner = LogisticRegression(
            max_iter=1000, random_state=RANDOM_SEED
        )
    return StackingClassifier(
        estimators=base_learners,
        final_estimator=meta_learner,
        cv=3,
        n_jobs=-1,
        passthrough=False,
    )
