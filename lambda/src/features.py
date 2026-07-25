from datetime import datetime, timezone
from typing import Dict, List, Optional
import math


def parse_timestamp(ts):
    if isinstance(ts, str):
        return datetime.fromisoformat(ts.replace('Z', '+00:00'))
    return ts


def calculate_velocity(x1: float, y1: float, x2: float, y2: float, dt: int) -> float:
    if dt <= 0:
        return 0.0
    distance = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    return distance / dt


def calculate_distance(x1: float, y1: float, x2: float, y2: float) -> float:
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def calculate_idle_time(velocity: float, dt: int, threshold: float = 0.01) -> int:
    if velocity < threshold:
        return dt
    return 0


def extract_session_features(events: List[Dict]) -> Optional[Dict]:
    if len(events) < 2:
        return None

    sorted_events = sorted(events, key=lambda e: parse_timestamp(e['timestamp']))

    velocities = []
    distances = []
    idle_total = 0
    prev_velocity = None
    velocity_trends = []

    for i in range(1, len(sorted_events)):
        prev = sorted_events[i - 1]
        curr = sorted_events[i]

        prev_ts = parse_timestamp(prev['timestamp'])
        curr_ts = parse_timestamp(curr['timestamp'])
        dt = int((curr_ts - prev_ts).total_seconds() * 1000)
        if dt <= 0:
            dt = 1000

        dist = calculate_distance(
            prev.get('mouse_x', 0), prev.get('mouse_y', 0),
            curr.get('mouse_x', 0), curr.get('mouse_y', 0)
        )
        distances.append(dist)

        vel = calculate_velocity(
            prev.get('mouse_x', 0), prev.get('mouse_y', 0),
            curr.get('mouse_x', 0), curr.get('mouse_y', 0),
            dt
        )
        velocities.append(vel)

        idle_total += calculate_idle_time(vel, dt)

        if prev_velocity is not None:
            if vel < prev_velocity * 0.8:
                velocity_trends.append('decreasing')
            elif vel > prev_velocity * 1.2:
                velocity_trends.append('increasing')
            else:
                velocity_trends.append('stable')
        prev_velocity = vel

    velocity_avg = sum(velocities) / len(velocities) if velocities else 0.0
    distance_total = sum(distances)

    if velocity_trends:
        decreasing_count = velocity_trends.count('decreasing')
        increasing_count = velocity_trends.count('increasing')
        if decreasing_count > increasing_count:
            velocity_trend = 'decreasing'
        elif increasing_count > decreasing_count:
            velocity_trend = 'increasing'
        else:
            velocity_trend = 'stable'
    else:
        velocity_trend = 'stable'

    return {
        'velocity_avg': velocity_avg,
        'idle_total_ms': idle_total,
        'distance_total': distance_total,
        'velocity_trend': velocity_trend
    }


def calculate_mouse_features(session_data: Dict) -> Optional[Dict]:
    heartbeats = session_data.get('heartbeats', [])
    if not heartbeats or len(heartbeats) < 2:
        return None

    features = extract_session_features(heartbeats)
    return features


def prepare_inference_payload(session_data: Dict, features: Dict) -> Dict:
    payload = {
        'session_id': session_data.get('session_id'),
        'user_id': session_data.get('user_id'),
        'cart_value': session_data.get('cart_value', 0.0),
        'product_count': session_data.get('product_count', 0),
        'product_quantities': session_data.get('product_quantities', {}),
        'shipping_option_selected': session_data.get('shipping_option_selected', 'standard'),
        'delivery_mode': session_data.get('delivery_mode', 'shipping'),
        'shipping_type': session_data.get('shipping_type', 'standard'),
        'shipping_cost': session_data.get('shipping_cost', 0.0),
        'mouse_click_count': session_data.get('mouse_click_count', 0),
        'page': session_data.get('page', 'cart'),
        'velocity_avg': features.get('velocity_avg', 0.0),
        'idle_seconds': features.get('idle_total_ms', 0) / 1000.0,
        'distance_total': features.get('distance_total', 0.0),
        'velocity_trend': features.get('velocity_trend', 'stable')
    }
    return payload