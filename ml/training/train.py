import argparse
import json
import joblib
from pathlib import Path
# elegi xgboost por la poca cantidad de variables para este ejemplo
import xgboost as xgb
import numpy as np

from data_prep import get_training_data
from evaluate import evaluate_model

MODEL_DIR = Path('data/models')
MODEL_PATH = MODEL_DIR / 'modelo_propension.pkl'
REPORT_PATH = MODEL_DIR / 'training_report.json'

RANDOM_STATE = 42


def train_xgboost(X_train, y_train, scale_pos_weight=None):
    if scale_pos_weight is None:
        neg_count = np.sum(y_train == 0)
        pos_count = np.sum(y_train == 1)
        scale_pos_weight = neg_count / max(pos_count, 1)

    model = xgb.XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=scale_pos_weight,
        eval_metric='logloss',
        use_label_encoder=False,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )

    model.fit(
        X_train, y_train,
        eval_set=[(X_train, y_train)],
        verbose=False,
    )

    return model


def save_model(model, feature_cols, scaler, encoders):
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    artifact = {
        'model': model,
        'feature_cols': feature_cols,
        'scaler': scaler,
        'encoders': encoders,
    }
    joblib.dump(artifact, MODEL_PATH)


def save_report(metrics):
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PATH, 'w') as f:
        json.dump(metrics, f, indent=2)


def main(local_only=False):
    X_train, X_test, y_train, y_test, feature_cols, scaler, encoders = get_training_data()

    model = train_xgboost(X_train, y_train)

    metrics = evaluate_model(model, X_test, y_test, X_train, y_train)

    metrics['feature_cols'] = feature_cols
    metrics['n_train'] = int(len(y_train))
    metrics['n_test'] = int(len(y_test))
    metrics['class_distribution'] = {
        'train_neg': int(np.sum(y_train == 0)),
        'train_pos': int(np.sum(y_train == 1)),
        'test_neg': int(np.sum(y_test == 0)),
        'test_pos': int(np.sum(y_test == 1)),
    }

    save_model(model, feature_cols, scaler, encoders)
    save_report(metrics)

    return metrics


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--local', action='store_true')
    args = parser.parse_args()
    main(local_only=args.local)
