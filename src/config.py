import os
from pathlib import Path

# Project root directory (two levels up from this config file)
BASE_DIR = Path(__file__).resolve().parent.parent

# Paths
DATA_PATH = BASE_DIR / 'data' / 'creditcard.csv'
MODELS_DIR = BASE_DIR / 'models'

# Create directories if they don't exist
os.makedirs(MODELS_DIR, exist_ok=True)

# Training settings
RANDOM_STATE = 42
TEST_SIZE = 0.2
VAL_SIZE = 0.15          # from the remaining 80% (0.15*0.8 = 0.12 of total)

# Resampling method (choose 'smote', 'oversample', 'undersample', or None)
RESAMPLING_METHOD = 'smote'

# Model hyperparameters
RF_PARAMS = {
    'n_estimators': 100,
    'max_depth': 10,
    'min_samples_split': 5,
    'random_state': RANDOM_STATE,
    'n_jobs': -1
}

XGB_PARAMS = {
    'n_estimators': 100,
    'max_depth': 6,
    'learning_rate': 0.1,
    'random_state': RANDOM_STATE,
    'eval_metric': 'logloss',
    'use_label_encoder': False
}

LGBM_PARAMS = {
    'n_estimators': 100,
    'max_depth': 6,
    'learning_rate': 0.1,
    'random_state': RANDOM_STATE,
    'verbose': -1
}