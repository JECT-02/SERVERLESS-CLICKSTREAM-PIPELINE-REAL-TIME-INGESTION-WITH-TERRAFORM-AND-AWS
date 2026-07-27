import numpy as np
import pandas as pd

MODEL_FEATURE_COLS = [
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

CATEGORICAL_COLS = ['device']

RETENTION_THRESHOLD = 0.7


def _map_payload_to_row(payload: dict, device_encoded: int) -> dict:
    idle_ms = payload.get('idle_seconds', 0.0) * 1000
    dwell_ms = payload.get('dwell_seconds', 0.0) * 1000
    dwell_count = payload.get('dwell_segments', 0)
    hes_ms = payload.get('payment_hesitation_seconds', 0.0) * 1000
    clicks = payload.get('mouse_click_count', 0)

    return {
        'velocity_avg': payload.get('velocity_avg', 0.0),
        'velocity_max': payload.get('velocity_max', 0.0),
        'velocity_std': payload.get('velocity_std', 0.0),
        'acceleration_avg': payload.get('acceleration_avg', 0.0),
        'acceleration_max': payload.get('acceleration_max', 0.0),
        'total_idle_ms': idle_ms,
        'total_distance_px': payload.get('distance_total', 0.0),
        'exit_intent_count': payload.get('exit_intent_count', 0),
        'total_dwell_ms': dwell_ms,
        'dwell_event_count': dwell_count,
        'session_duration_s': 0.0,
        'click_frequency': payload.get('click_frequency', 0.0),
        'idle_ratio': 0.0,
        'cart_value_max': payload.get('cart_value', 0.0),
        'cart_value_avg': payload.get('cart_value', 0.0),
        'cart_delta_total': payload.get('cart_delta', 0.0),
        'shipping_switches': payload.get('shipping_switches', 0),
        'page_regression_count': payload.get('page_regression_count', 0),
        'heartbeat_count': 1,
        'total_events': 1,
        'product_count_max': payload.get('product_count', 0),
        'add_to_cart_count': 0,
        'remove_from_cart_count': 0,
        'checkout_count': 1 if payload.get('page') == 'checkout' else 0,
        'view_product_count': 0,
        'payment_hesitation_ms': hes_ms,
        'events_per_minute': 0.0,
        'total_clicks': clicks,
        'device': device_encoded,
    }


def preprocess(payload: dict, scaler, encoders: dict, feature_cols: list) -> np.ndarray:
    device_raw = payload.get('device', 'desktop')
    encoder = encoders.get('device')
    if encoder:
        device_encoded = encoder.transform([device_raw])[0]
    else:
        device_encoded = 0

    row = _map_payload_to_row(payload, device_encoded)

    available = [c for c in feature_cols if c in row]
    missing = [c for c in feature_cols if c not in row]
    for col in missing:
        row[col] = 0.0

    df = pd.DataFrame([row])[feature_cols]
    df = df.fillna(0.0).astype(float)
    scaled = scaler.transform(df)
    return scaled


def predict(model, X: np.ndarray) -> float:
    return float(model.predict_proba(X)[0, 1])


def select_retention_type(probability: float, payload: dict) -> dict:
    shipping_cost = payload.get('shipping_cost', 0)
    delivery_mode = payload.get('delivery_mode', 'shipping')
    shipping_type = payload.get('shipping_type', 'standard')

    if delivery_mode == 'shipping' and shipping_cost > 0:
        return {
            'retention_type': 'shipping_discount',
            'coupon_code': None,
        }
    elif shipping_type == 'standard':
        return {
            'retention_type': 'express_upgrade',
            'coupon_code': None,
        }
    else:
        return {
            'retention_type': 'coupon',
            'coupon_code': 'SAVE10',
        }


def run_inference(payload: dict, model, scaler, encoders: dict, feature_cols: list) -> dict:
    X = preprocess(payload, scaler, encoders, feature_cols)
    probability = predict(model, X)
    trigger = probability >= RETENTION_THRESHOLD

    result = {
        'abandon_probability': round(probability, 4),
        'trigger_retention': trigger,
    }

    if trigger:
        retention = select_retention_type(probability, payload)
        result.update(retention)

    return result
