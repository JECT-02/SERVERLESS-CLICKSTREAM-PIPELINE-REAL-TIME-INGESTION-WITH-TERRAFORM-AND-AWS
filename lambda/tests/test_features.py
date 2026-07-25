import os
import sys
import pytest
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from features import (
    calculate_mouse_features,
    extract_all_features,
    prepare_inference_payload,
    calculate_velocity,
    calculate_distance,
    calculate_acceleration,
    detect_exit_intent,
    calculate_dwell_segments,
    calculate_click_frequency,
    detect_product_removal,
    detect_product_addition,
    count_value_changes,
    aggregate_window,
    extract_cart_features,
    extract_funnel_features
)


def make_hb(ts, mx=0, my=0, cv=0, pc=0, pq=None, shipping='standard', cc=0, page='cart'):
    return {
        'event_type': 'heartbeat',
        'mouse_x': mx, 'mouse_y': my, 'timestamp': ts,
        'cart_value': cv, 'product_count': pc,
        'product_quantities': pq or {},
        'shipping_option_selected': shipping,
        'mouse_click_count': cc, 'page': page
    }


class TestCoreFunctions:
    def test_calculate_velocity_zero_dt(self):
        assert calculate_velocity(0, 0, 10, 0, 0) == 0.0

    def test_calculate_velocity_normal(self):
        v = calculate_velocity(0, 0, 3, 4, 1.0)
        assert v == pytest.approx(5.0, rel=0.01)

    def test_calculate_distance(self):
        d = calculate_distance(0, 0, 3, 4)
        assert d == pytest.approx(5.0, rel=0.01)

    def test_calculate_acceleration(self):
        a = calculate_acceleration(10, 30, 2.0)
        assert a == pytest.approx(10.0, rel=0.01)

    def test_calculate_acceleration_zero_dt(self):
        assert calculate_acceleration(10, 30, 0) == 0.0

    def test_detect_exit_intent_true(self):
        assert detect_exit_intent(50, 300, y_upper_bound=100, velocity_threshold=200) is True

    def test_detect_exit_intent_false_low_velocity(self):
        assert detect_exit_intent(50, 10, y_upper_bound=100, velocity_threshold=200) is False

    def test_detect_exit_intent_false_low_y(self):
        assert detect_exit_intent(150, 300, y_upper_bound=100, velocity_threshold=200) is False


class TestDwellSegments:
    def test_no_dwell_all_moving(self):
        events = [
            make_hb('2026-07-25T20:00:00.000Z', 0, 0),
            make_hb('2026-07-25T20:00:00.250Z', 10, 10),
            make_hb('2026-07-25T20:00:00.500Z', 20, 20),
        ]
        segs = calculate_dwell_segments(events)
        assert len(segs) == 0

    def test_dwell_two_consecutive_static(self):
        events = [
            make_hb('2026-07-25T20:00:00.000Z', 100, 100),
            make_hb('2026-07-25T20:00:00.250Z', 100, 100),
            make_hb('2026-07-25T20:00:00.500Z', 100, 100),
            make_hb('2026-07-25T20:00:00.750Z', 200, 200),
        ]
        segs = calculate_dwell_segments(events)
        assert len(segs) == 1
        assert segs[0]['count'] >= 2

    def test_dwell_no_events(self):
        assert calculate_dwell_segments([]) == []


class TestClickFrequency:
    def test_click_frequency_normal(self):
        freq = calculate_click_frequency(20, 10, 2.0)
        assert freq == pytest.approx(5.0, rel=0.01)

    def test_click_frequency_zero_dt(self):
        assert calculate_click_frequency(20, 10, 0) == 0.0

    def test_click_frequency_negative_delta(self):
        assert calculate_click_frequency(5, 10, 2.0) == 0.0


class TestProductChanges:
    def test_detect_product_removal(self):
        prev = {'prod_001': 3, 'prod_002': 1}
        curr = {'prod_001': 1, 'prod_002': 1}
        result = detect_product_removal(curr, prev)
        assert result == {'prod_001': 2}

    def test_detect_product_removal_empty(self):
        assert detect_product_removal({'prod_001': 2}, {'prod_001': 2}) == {}

    def test_detect_product_addition(self):
        prev = {'prod_001': 1}
        curr = {'prod_001': 2, 'prod_002': 1}
        result = detect_product_addition(curr, prev)
        assert result == {'prod_001': 1, 'prod_002': 1}


class TestValueChanges:
    def test_no_changes(self):
        assert count_value_changes(['a', 'a', 'a']) == 0

    def test_one_change(self):
        assert count_value_changes(['a', 'b', 'b']) == 1

    def test_multiple_changes(self):
        assert count_value_changes(['a', 'b', 'a', 'c']) == 3

    def test_single_element(self):
        assert count_value_changes(['a']) == 0

    def test_empty(self):
        assert count_value_changes([]) == 0


class TestAggregateWindow:
    def test_window_returns_empty_insufficient_data(self):
        events = [make_hb('2026-07-25T20:00:00.000Z', 0, 0)]
        assert aggregate_window(events, 5) == {}

    def test_window_returns_velocity_stats(self):
        events = [
            make_hb('2026-07-25T20:00:00.000Z', 0, 0),
            make_hb('2026-07-25T20:00:00.250Z', 10, 0),
            make_hb('2026-07-25T20:00:00.500Z', 20, 0),
        ]
        result = aggregate_window(events, 5)
        assert 'velocity_avg' in result
        assert 'velocity_max' in result
        assert 'velocity_std' in result
        assert 'total_clicks' in result
        assert 'idle_ratio' in result
        assert 'heartbeat_count' in result
        assert result['heartbeat_count'] >= 2


class TestExtractCartFeatures:
    def test_cart_features_insufficient_data(self):
        events = [make_hb('2026-07-25T20:00:00.000Z')]
        result = extract_cart_features(events)
        assert result['cart_delta'] == 0.0
        assert result['shipping_switches'] == 0

    def test_cart_features_delta(self):
        events = [
            make_hb('2026-07-25T20:00:00.000Z', cv=100, pq={'prod_001': 1}),
            make_hb('2026-07-25T20:00:00.250Z', cv=150, pq={'prod_001': 1, 'prod_002': 1}),
        ]
        result = extract_cart_features(events)
        assert result['cart_delta'] == 50.0
        assert 'prod_002' in result['product_additions']

    def test_cart_features_shipping_switch(self):
        events = [
            make_hb('2026-07-25T20:00:00.000Z', shipping='standard'),
            make_hb('2026-07-25T20:00:00.250Z', shipping='express'),
            make_hb('2026-07-25T20:00:00.500Z', shipping='standard'),
        ]
        result = extract_cart_features(events)
        assert result['shipping_switches'] == 2


class TestExtractFunnelFeatures:
    def test_no_funnel_events(self):
        assert extract_funnel_features([]) == {
            'page_regression_count': 0,
            'payment_hesitation_ms': 0,
            'payment_method_switches': 0
        }

    def test_page_regression(self):
        events = [
            {'page': 'checkout', 'timestamp': '2026-07-25T20:00:01Z'},
            {'page': 'cart', 'timestamp': '2026-07-25T20:00:02Z'},
            {'page': 'checkout', 'timestamp': '2026-07-25T20:00:03Z'},
        ]
        result = extract_funnel_features(events)
        assert result['page_regression_count'] == 1

    def test_payment_hesitation(self):
        events = [
            {'page': 'checkout', 'payment_method_selected': None, 'timestamp': '2026-07-25T20:00:00Z'},
            {'page': 'checkout', 'payment_method_selected': None, 'timestamp': '2026-07-25T20:00:03Z'},
            {'page': 'checkout', 'payment_method_selected': 'credit_card', 'timestamp': '2026-07-25T20:00:05Z'},
        ]
        result = extract_funnel_features(events)
        assert result['payment_hesitation_ms'] >= 5000
        assert result['payment_method_switches'] >= 1


class TestExtractAllFeatures:
    def test_all_features_returns_none_insufficient(self):
        session_data = {'heartbeats': [make_hb('2026-07-25T20:00:00.000Z')]}
        assert extract_all_features(session_data) is None

    def test_all_features_contains_all_groups(self):
        session_data = {
            'heartbeats': [
                make_hb('2026-07-25T20:00:00.000Z', 0, 0, cv=100, cc=0, shipping='standard'),
                make_hb('2026-07-25T20:00:00.250Z', 100, 0, cv=150, cc=2, shipping='express'),
                make_hb('2026-07-25T20:00:00.500Z', 200, 0, cv=150, cc=2, shipping='express'),
            ]
        }
        result = extract_all_features(session_data)
        assert result is not None
        assert 'velocity_avg' in result
        assert 'acceleration_avg' in result
        assert 'exit_intent_count' in result
        assert 'dwell_total_ms' in result
        assert 'click_frequency' in result
        assert 'cart_delta' in result
        assert 'shipping_switches' in result
        assert 'page_regression_count' in result
        assert 'payment_hesitation_ms' in result
        assert 'window_5s' in result
        assert 'window_10s' in result
        assert 'window_30s' in result


class TestCalculateMouseFeatures:
    def test_insufficient_data_returns_none(self):
        assert calculate_mouse_features({'session_id': 'test', 'user_id': 'user'}) is None

    def test_single_heartbeat_returns_none(self):
        session_data = {
            'session_id': 'test', 'user_id': 'user',
            'heartbeats': [make_hb('2026-07-24T18:30:00.000Z', 100, 100)]
        }
        assert calculate_mouse_features(session_data) is None

    def test_two_heartbeats_calculates_features(self):
        session_data = {
            'session_id': 'test', 'user_id': 'user',
            'heartbeats': [
                make_hb('2026-07-24T18:30:00.000Z', 100, 100),
                make_hb('2026-07-24T18:30:01.000Z', 150, 150),
            ]
        }
        result = calculate_mouse_features(session_data)
        assert result is not None
        assert 'velocity_avg' in result
        assert 'idle_total_ms' in result
        assert 'distance_total' in result
        assert 'velocity_trend' in result

    def test_multiple_heartbeats_calculates_correct_distance(self):
        session_data = {
            'session_id': 'test', 'user_id': 'user',
            'heartbeats': [
                make_hb('2026-07-24T18:30:00.000Z', 0, 0),
                make_hb('2026-07-24T18:30:01.000Z', 3, 4),
                make_hb('2026-07-24T18:30:02.000Z', 6, 8),
            ]
        }
        result = calculate_mouse_features(session_data)
        assert result['distance_total'] == pytest.approx(10.0, rel=0.1)
        assert result['velocity_avg'] > 0

    def test_velocity_trend_decreasing(self):
        session_data = {
            'session_id': 'test', 'user_id': 'user',
            'heartbeats': [
                make_hb('2026-07-24T18:30:00.000Z', 0, 0),
                make_hb('2026-07-24T18:30:01.000Z', 10, 0),
                make_hb('2026-07-24T18:30:02.000Z', 15, 0),
                make_hb('2026-07-24T18:30:03.000Z', 18, 0),
                make_hb('2026-07-24T18:30:04.000Z', 20, 0),
                make_hb('2026-07-24T18:30:05.000Z', 21, 0),
            ]
        }
        result = calculate_mouse_features(session_data)
        assert result['velocity_trend'] == 'decreasing'

    def test_velocity_trend_increasing(self):
        session_data = {
            'session_id': 'test', 'user_id': 'user',
            'heartbeats': [
                make_hb('2026-07-24T18:30:00.000Z', 0, 0),
                make_hb('2026-07-24T18:30:01.000Z', 1, 0),
                make_hb('2026-07-24T18:30:02.000Z', 3, 0),
                make_hb('2026-07-24T18:30:03.000Z', 6, 0),
                make_hb('2026-07-24T18:30:04.000Z', 10, 0),
                make_hb('2026-07-24T18:30:05.000Z', 15, 0),
            ]
        }
        result = calculate_mouse_features(session_data)
        assert result['velocity_trend'] == 'increasing'

    def test_idle_calculation(self):
        session_data = {
            'session_id': 'test', 'user_id': 'user',
            'heartbeats': [
                make_hb('2026-07-24T18:30:00.000Z', 100, 100),
                make_hb('2026-07-24T18:30:01.000Z', 100, 100),
                make_hb('2026-07-24T18:30:02.000Z', 100, 100),
            ]
        }
        result = calculate_mouse_features(session_data)
        assert result['idle_total_ms'] == 2000


class TestPrepareInferencePayload:
    def test_prepare_payload_includes_all_fields(self):
        session_data = {
            'session_id': 'test-session', 'user_id': 'test-user',
            'cart_value': 1500.00, 'product_count': 3,
            'product_quantities': {'prod_001': 1, 'prod_002': 2},
            'shipping_option_selected': 'express',
            'delivery_mode': 'shipping', 'shipping_type': 'express',
            'shipping_cost': 24.00, 'mouse_click_count': 25, 'page': 'cart'
        }
        features = {
            'velocity_avg': 15.5, 'velocity_max': 30.0, 'velocity_std': 5.0,
            'acceleration_avg': 2.0, 'acceleration_max': 5.0,
            'idle_total_ms': 5000, 'distance_total': 500,
            'velocity_trend': 'stable', 'exit_intent_count': 1,
            'dwell_total_ms': 3000, 'dwell_segments': 2,
            'click_frequency': 0.5, 'cart_delta': 0.0,
            'shipping_switches': 1, 'page_regression_count': 0,
            'payment_hesitation_ms': 2000, 'payment_method_switches': 0,
            'window_5s': {}, 'window_10s': {}, 'window_30s': {}
        }

        payload = prepare_inference_payload(session_data, features)
        assert payload['session_id'] == 'test-session'
        assert payload['velocity_avg'] == 15.5
        assert payload['velocity_max'] == 30.0
        assert payload['acceleration_avg'] == 2.0
        assert payload['exit_intent_count'] == 1
        assert payload['dwell_seconds'] == 3.0
        assert payload['click_frequency'] == 0.5
        assert payload['shipping_switches'] == 1
        assert payload['payment_hesitation_seconds'] == 2.0
        assert 'window_5s' in payload
        assert 'window_10s' in payload
        assert 'window_30s' in payload

    def test_prepare_payload_handles_missing_features(self):
        session_data = {
            'session_id': 'test-session', 'user_id': 'test-user',
            'cart_value': 100.00, 'product_count': 1
        }
        features = {}
        payload = prepare_inference_payload(session_data, features)
        assert payload['velocity_avg'] == 0
        assert payload['idle_seconds'] == 0.0
        assert payload['velocity_trend'] == 'stable'
        assert payload['exit_intent_count'] == 0
        assert payload['dwell_seconds'] == 0.0