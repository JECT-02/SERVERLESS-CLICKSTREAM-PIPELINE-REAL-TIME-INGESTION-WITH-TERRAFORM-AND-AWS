import polars as pl
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from pathlib import Path

GOLD_PATH = Path('data/processed/gold.parquet')

CATEGORICAL_COLS = ['device']
NUMERIC_COLS = [
    'velocity_avg', 'velocity_max', 'velocity_std',
    'acceleration_avg', 'acceleration_max',
    'total_idle_ms', 'total_distance_px', 'exit_intent_count',
    'total_dwell_ms', 'dwell_event_count', 'session_duration_s',
    'click_frequency', 'idle_ratio', 'cart_value_max', 'cart_value_avg',
    'cart_delta_total', 'shipping_switches', 'page_regression_count',
    'heartbeat_count', 'total_events', 'product_count_max',
    'add_to_cart_count', 'remove_from_cart_count', 'checkout_count',
    'view_product_count', 'payment_hesitation_ms', 'events_per_minute',
    'total_clicks',
]

TARGET_COL = 'abandoned'
RANDOM_STATE = 42


def load_gold_data():
    df = pl.read_parquet(GOLD_PATH)
    return df.to_pandas()


def prepare_features(df):
    df = df.copy()

    cat_encoders = {}
    for col in CATEGORICAL_COLS:
        if col in df.columns:
            le = LabelEncoder()
            df[col] = le.fit_transform(df[col].astype(str).fillna('unknown'))
            cat_encoders[col] = le

    available_numeric = [c for c in NUMERIC_COLS if c in df.columns]
    for col in available_numeric:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    feature_cols = available_numeric + CATEGORICAL_COLS
    feature_cols = [c for c in feature_cols if c in df.columns]

    X = df[feature_cols].values
    y = df[TARGET_COL].values if TARGET_COL in df.columns else None

    scaler = StandardScaler()
    X = scaler.fit_transform(X)

    return X, y, feature_cols, scaler, cat_encoders


def split_data(X, y, test_size=0.2):
    return train_test_split(
        X, y, test_size=test_size,
        stratify=y, random_state=RANDOM_STATE
    )


def get_training_data():
    df = load_gold_data()
    X, y, feature_cols, scaler, encoders = prepare_features(df)
    X_train, X_test, y_train, y_test = split_data(X, y)
    return X_train, X_test, y_train, y_test, feature_cols, scaler, encoders


if __name__ == '__main__':
    get_training_data()
