import json
import os
import sys
import pytest
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from features import calculate_mouse_features, prepare_inference_payload


class TestCalculateMouseFeatures:
    def test_insufficient_data_returns_none(self):
        session_data = {'session_id': 'test', 'user_id': 'user'}
        assert calculate_mouse_features(session_data) is None

    def test_single_heartbeat_returns_none(self):
        session_data = {
            'session_id': 'test',
            'user_id': 'user',
            'heartbeats': [{
                'mouse_x': 100, 'mouse_y': 100, 'timestamp': '2026-07-24T18:30:00.000Z'
            }]
        }
        assert calculate_mouse_features(session_data) is None

    def test_two_heartbeats_calculates_features(self):
        session_data = {
            'session_id': 'test',
            'user_id': 'user',
            'heartbeats': [
                {'mouse_x': 100, 'mouse_y': 100, 'timestamp': '2026-07-24T18:30:00.000Z'},
                {'mouse_x': 150, 'mouse_y': 150, 'timestamp': '2026-07-24T18:30:01.000Z'}
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
            'session_id': 'test',
            'user_id': 'user',
            'heartbeats': [
                {'mouse_x': 0, 'mouse_y': 0, 'timestamp': '2026-07-24T18:30:00.000Z'},
                {'mouse_x': 3, 'mouse_y': 4, 'timestamp': '2026-07-24T18:30:01.000Z'},
                {'mouse_x': 6, 'mouse_y': 8, 'timestamp': '2026-07-24T18:30:02.000Z'}
            ]
        }
        result = calculate_mouse_features(session_data)
        assert result['distance_total'] == pytest.approx(10.0, rel=0.1)
        assert result['velocity_avg'] > 0

    def test_velocity_trend_decreasing(self):
        session_data = {
            'session_id': 'test',
            'user_id': 'user',
            'heartbeats': [
                {'mouse_x': 0, 'mouse_y': 0, 'timestamp': '2026-07-24T18:30:00.000Z'},
                {'mouse_x': 10, 'mouse_y': 0, 'timestamp': '2026-07-24T18:30:01.000Z'},
                {'mouse_x': 15, 'mouse_y': 0, 'timestamp': '2026-07-24T18:30:02.000Z'},
                {'mouse_x': 18, 'mouse_y': 0, 'timestamp': '2026-07-24T18:30:03.000Z'},
                {'mouse_x': 20, 'mouse_y': 0, 'timestamp': '2026-07-24T18:30:04.000Z'},
                {'mouse_x': 21, 'mouse_y': 0, 'timestamp': '2026-07-24T18:30:05.000Z'}
            ]
        }
        result = calculate_mouse_features(session_data)
        assert result['velocity_trend'] == 'decreasing'

    def test_velocity_trend_increasing(self):
        session_data = {
            'session_id': 'test',
            'user_id': 'user',
            'heartbeats': [
                {'mouse_x': 0, 'mouse_y': 0, 'timestamp': '2026-07-24T18:30:00.000Z'},
                {'mouse_x': 1, 'mouse_y': 0, 'timestamp': '2026-07-24T18:30:01.000Z'},
                {'mouse_x': 3, 'mouse_y': 0, 'timestamp': '2026-07-24T18:30:02.000Z'},
                {'mouse_x': 6, 'mouse_y': 0, 'timestamp': '2026-07-24T18:30:03.000Z'},
                {'mouse_x': 10, 'mouse_y': 0, 'timestamp': '2026-07-24T18:30:04.000Z'},
                {'mouse_x': 15, 'mouse_y': 0, 'timestamp': '2026-07-24T18:30:05.000Z'}
            ]
        }
        result = calculate_mouse_features(session_data)
        assert result['velocity_trend'] == 'increasing'

    def test_idle_calculation(self):
        session_data = {
            'session_id': 'test',
            'user_id': 'user',
            'heartbeats': [
                {'mouse_x': 100, 'mouse_y': 100, 'timestamp': '2026-07-24T18:30:00.000Z'},
                {'mouse_x': 100, 'mouse_y': 100, 'timestamp': '2026-07-24T18:30:01.000Z'},
                {'mouse_x': 100, 'mouse_y': 100, 'timestamp': '2026-07-24T18:30:02.000Z'}
            ]
        }
        result = calculate_mouse_features(session_data)
        assert result['idle_total_ms'] == 2000


class TestPrepareInferencePayload:
    def test_prepare_payload_includes_all_fields(self):
        session_data = {
            'session_id': 'test-session',
            'user_id': 'test-user',
            'cart_value': 1500.00,
            'product_count': 3,
            'product_quantities': {'prod_001': 1, 'prod_002': 2},
            'shipping_option_selected': 'express',
            'delivery_mode': 'shipping',
            'shipping_type': 'express',
            'shipping_cost': 24.00,
            'mouse_click_count': 25,
            'page': 'cart'
        }
        features = {
            'velocity_avg': 15.5,
            'idle_total_ms': 5000,
            'distance_total': 500,
            'velocity_trend': 'stable'
        }

        payload = prepare_inference_payload(session_data, features)

        assert payload['session_id'] == 'test-session'
        assert payload['user_id'] == 'test-user'
        assert payload['cart_value'] == 1500.00
        assert payload['product_count'] == 3
        assert payload['product_quantities'] == {'prod_001': 1, 'prod_002': 2}
        assert payload['shipping_option_selected'] == 'express'
        assert payload['delivery_mode'] == 'shipping'
        assert payload['shipping_type'] == 'express'
        assert payload['shipping_cost'] == 24.00
        assert payload['mouse_click_count'] == 25
        assert payload['page'] == 'cart'
        assert payload['velocity_avg'] == 15.5
        assert payload['idle_seconds'] == 5.0
        assert payload['distance_total'] == 500
        assert payload['velocity_trend'] == 'stable'

    def test_prepare_payload_handles_missing_features(self):
        session_data = {
            'session_id': 'test-session',
            'user_id': 'test-user',
            'cart_value': 100.00,
            'product_count': 1
        }
        features = {}

        payload = prepare_inference_payload(session_data, features)

        assert payload['velocity_avg'] == 0
        assert payload['idle_seconds'] == 0.0
        assert payload['distance_total'] == 0
        assert payload['velocity_trend'] == 'stable'