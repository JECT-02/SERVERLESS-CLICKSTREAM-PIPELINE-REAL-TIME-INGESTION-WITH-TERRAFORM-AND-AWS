import pytest
import numpy as np
from sklearn.preprocessing import StandardScaler, LabelEncoder
from app.inference import preprocess, run_inference, select_retention_type, _map_payload_to_row


@pytest.fixture
def sample_model():
    from xgboost import XGBClassifier
    model = XGBClassifier(n_estimators=10, random_state=42)
    rng = np.random.RandomState(42)
    X = rng.rand(100, 29)
    y = (X[:, 0] + X[:, 1] > 1).astype(int)
    model.fit(X, y)
    return model


@pytest.fixture
def sample_scaler():
    scaler = StandardScaler()
    scaler.fit(np.random.RandomState(42).rand(100, 29))
    return scaler


@pytest.fixture
def sample_encoders():
    le = LabelEncoder()
    le.fit(['desktop', 'mobile', 'tablet'])
    return {'device': le}


@pytest.fixture
def sample_feature_cols():
    return [
        'velocity_avg', 'velocity_max', 'velocity_std',
        'acceleration_avg', 'acceleration_max',
        'total_idle_ms', 'total_distance_px', 'exit_intent_count',
        'total_dwell_ms', 'dwell_event_count', 'session_duration_s',
        'click_frequency', 'idle_ratio', 'cart_value_max', 'cart_value_avg',
        'cart_delta_total', 'shipping_switches', 'page_regression_count',
        'heartbeat_count', 'total_events', 'product_count_max',
        'add_to_cart_count', 'remove_from_cart_count', 'checkout_count',
        'view_product_count', 'payment_hesitation_ms', 'events_per_minute',
        'total_clicks', 'device',
    ]


@pytest.fixture
def sample_payload():
    return {
        'session_id': 'test-session',
        'user_id': 'test-user',
        'cart_value': 150.0,
        'product_count': 3,
        'shipping_option_selected': 'express',
        'delivery_mode': 'shipping',
        'shipping_type': 'standard',
        'shipping_cost': 8.0,
        'page': 'cart',
        'velocity_avg': 120.5,
        'velocity_max': 350.0,
        'velocity_std': 45.2,
        'acceleration_avg': 30.1,
        'acceleration_max': 150.0,
        'idle_seconds': 2.5,
        'distance_total': 800.0,
        'exit_intent_count': 1,
        'dwell_seconds': 1.2,
        'dwell_segments': 3,
        'click_frequency': 0.5,
        'cart_delta': -20.0,
        'shipping_switches': 2,
        'page_regression_count': 1,
        'payment_hesitation_seconds': 0.0,
        'payment_method_switches': 0,
    }


def test_preprocess_returns_expected_shape(sample_payload, sample_scaler, sample_encoders, sample_feature_cols):
    X = preprocess(sample_payload, sample_scaler, sample_encoders, sample_feature_cols)
    assert X.shape == (1, len(sample_feature_cols))


def test_preprocess_fills_missing_features(sample_payload, sample_scaler, sample_encoders, sample_feature_cols):
    minimal = {'device': 'mobile', 'cart_value': 100.0, 'page': 'checkout'}
    X = preprocess(minimal, sample_scaler, sample_encoders, sample_feature_cols)
    assert X.shape == (1, len(sample_feature_cols))
    assert not np.any(np.isnan(X))


def test_preprocess_encodes_device(sample_payload, sample_scaler, sample_encoders, sample_feature_cols):
    X = preprocess(sample_payload, sample_scaler, sample_encoders, sample_feature_cols)
    assert X.shape[1] == len(sample_feature_cols)


def test_map_payload_to_row_converts_units():
    payload = {
        'idle_seconds': 3.0,
        'dwell_seconds': 1.5,
        'dwell_segments': 2,
        'payment_hesitation_seconds': 0.5,
        'mouse_click_count': 10,
        'cart_value': 200.0,
        'page': 'checkout',
    }
    row = _map_payload_to_row(payload, device_encoded=1)
    assert row['total_idle_ms'] == 3000.0
    assert row['total_dwell_ms'] == 1500.0
    assert row['dwell_event_count'] == 2
    assert row['payment_hesitation_ms'] == 500.0
    assert row['total_clicks'] == 10


def test_map_payload_to_row_defaults():
    row = _map_payload_to_row({}, device_encoded=0)
    assert row['total_idle_ms'] == 0.0
    assert row['heartbeat_count'] == 1
    assert row['checkout_count'] == 0


def test_select_retention_type_free_shipping():
    result = select_retention_type(0.85, {'shipping_type': 'standard'})
    assert result['retention_type'] == 'free_shipping'


def test_select_retention_type_express_discount():
    result = select_retention_type(0.85, {'shipping_type': 'express'})
    assert result['retention_type'] == 'express_discount'


def test_run_inference_returns_structure(sample_payload, sample_model, sample_scaler, sample_encoders, sample_feature_cols):
    result = run_inference(sample_payload, sample_model, sample_scaler, sample_encoders, sample_feature_cols)
    assert 'abandon_probability' in result
    assert 'trigger_retention' in result
    assert isinstance(result['abandon_probability'], float)
    assert isinstance(result['trigger_retention'], bool)
