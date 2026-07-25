from datetime import datetime, timezone
from typing import Dict, List, Optional
import math
import statistics


def parse_timestamp(ts):
    if isinstance(ts, str):
        return datetime.fromisoformat(ts.replace('Z', '+00:00'))
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    return datetime.fromtimestamp(float(str(ts)), tz=timezone.utc)


def calculate_velocity(x1: float, y1: float, x2: float, y2: float, dt_s: float) -> float:
    if dt_s <= 0:
        return 0.0
    distance = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    return distance / dt_s


def calculate_distance(x1: float, y1: float, x2: float, y2: float) -> float:
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def calculate_idle_time(velocity: float, dt_ms: int, threshold: float = 5.0) -> int:
    if velocity < threshold:
        return dt_ms
    return 0


def calculate_acceleration(vel1: float, vel2: float, dt_s: float) -> float:
    if dt_s <= 0:
        return 0.0
    return (vel2 - vel1) / dt_s


def detect_exit_intent(mouse_y: float, velocity: float,
                       y_upper_bound: float = 100,
                       velocity_threshold: float = 200) -> bool:
    return mouse_y < y_upper_bound and velocity > velocity_threshold


def calculate_dwell_segments(events: List[Dict]) -> List[Dict]:
    segments = []
    current_dwell_start = None
    dwell_count = 0

    for i, e in enumerate(events):
        mx = e.get('mouse_x', 0)
        my = e.get('mouse_y', 0)

        if i > 0:
            prev = events[i - 1]
            dx = abs(mx - prev.get('mouse_x', 0))
            dy = abs(my - prev.get('mouse_y', 0))
            is_static = dx == 0 and dy == 0

            if is_static:
                if current_dwell_start is None:
                    current_dwell_start = parse_timestamp(e['timestamp'])
                dwell_count += 1
            else:
                if current_dwell_start is not None and dwell_count > 0:
                    segments.append({
                        'start': current_dwell_start,
                        'end': parse_timestamp(prev['timestamp']),
                        'count': dwell_count
                    })
                    current_dwell_start = None
                    dwell_count = 0

    if current_dwell_start is not None and dwell_count > 0:
        segments.append({
            'start': current_dwell_start,
            'end': parse_timestamp(events[-1]['timestamp']),
            'count': dwell_count
        })

    return segments


def calculate_click_frequency(click_count: int, prev_click_count: int, dt_s: float) -> float:
    if dt_s <= 0:
        return 0.0
    delta_clicks = click_count - prev_click_count
    if delta_clicks < 0:
        return 0.0
    return delta_clicks / dt_s


def detect_product_removal(current_qty: Dict, prev_qty: Dict) -> Dict:
    removed = {}
    for prod_id, qty in prev_qty.items():
        current = current_qty.get(prod_id, 0)
        if current < qty:
            removed[prod_id] = qty - current
    return removed


def detect_product_addition(current_qty: Dict, prev_qty: Dict) -> Dict:
    added = {}
    for prod_id, qty in current_qty.items():
        prev = prev_qty.get(prod_id, 0)
        if qty > prev:
            added[prod_id] = qty - prev
    return added


def count_value_changes(values: List) -> int:
    if len(values) < 2:
        return 0
    changes = 0
    for i in range(1, len(values)):
        if values[i] != values[i - 1]:
            changes += 1
    return changes


def aggregate_window(events: List[Dict], window_s: float) -> Dict:
    heartbeats = [e for e in events if e.get('event_type') == 'heartbeat']
    if len(heartbeats) < 2:
        return {}

    sorted_hb = sorted(heartbeats, key=lambda e: parse_timestamp(e['timestamp']))
    now = parse_timestamp(sorted_hb[-1]['timestamp'])
    cutoff = now.timestamp() - window_s

    window_hb = [e for e in sorted_hb if parse_timestamp(e['timestamp']).timestamp() >= cutoff]
    if len(window_hb) < 2:
        return {}

    velocities = []
    total_clicks_window = 0
    static_count = 0

    for i in range(1, len(window_hb)):
        prev = window_hb[i - 1]
        curr = window_hb[i]

        prev_ts = parse_timestamp(prev['timestamp'])
        curr_ts = parse_timestamp(curr['timestamp'])
        dt_s = (curr_ts - prev_ts).total_seconds()
        if dt_s <= 0:
            dt_s = 0.25

        vel = calculate_velocity(
            prev.get('mouse_x', 0), prev.get('mouse_y', 0),
            curr.get('mouse_x', 0), curr.get('mouse_y', 0),
            dt_s
        )
        velocities.append(vel)

        dx = abs(curr.get('mouse_x', 0) - prev.get('mouse_x', 0))
        dy = abs(curr.get('mouse_y', 0) - prev.get('mouse_y', 0))
        if dx == 0 and dy == 0:
            static_count += 1

    v_avg = statistics.mean(velocities) if velocities else 0.0
    v_max = max(velocities) if velocities else 0.0
    v_std = statistics.stdev(velocities) if len(velocities) >= 2 else 0.0

    first_click = window_hb[0].get('mouse_click_count', 0)
    last_click = window_hb[-1].get('mouse_click_count', 0)
    total_clicks_window = max(0, last_click - first_click)

    total_hb = len(window_hb)
    idle_ratio = static_count / total_hb if total_hb > 0 else 0.0

    return {
        'velocity_avg': v_avg,
        'velocity_max': v_max,
        'velocity_std': v_std,
        'total_clicks': total_clicks_window,
        'idle_ratio': idle_ratio,
        'heartbeat_count': total_hb
    }


def extract_session_features(events: List[Dict]) -> Optional[Dict]:
    if len(events) < 2:
        return None

    sorted_events = sorted(events, key=lambda e: parse_timestamp(e['timestamp']))

    velocities = []
    accelerations = []
    distances = []
    idle_total = 0
    prev_velocity = None
    prev_prev_velocity = None
    velocity_trends = []
    exit_intent_count = 0
    seg_dts_s = []

    for i in range(1, len(sorted_events)):
        prev = sorted_events[i - 1]
        curr = sorted_events[i]

        prev_ts = parse_timestamp(prev['timestamp'])
        curr_ts = parse_timestamp(curr['timestamp'])
        dt_s = (curr_ts - prev_ts).total_seconds()
        dt_ms = int(dt_s * 1000)
        if dt_s <= 0:
            dt_s = 0.25
            dt_ms = 250

        dist = calculate_distance(
            prev.get('mouse_x', 0), prev.get('mouse_y', 0),
            curr.get('mouse_x', 0), curr.get('mouse_y', 0)
        )
        distances.append(dist)

        vel = calculate_velocity(
            prev.get('mouse_x', 0), prev.get('mouse_y', 0),
            curr.get('mouse_x', 0), curr.get('mouse_y', 0),
            dt_s
        )
        velocities.append(vel)
        seg_dts_s.append(dt_s)

        idle_total += calculate_idle_time(vel, dt_ms)

        if prev_velocity is not None:
            accel = calculate_acceleration(prev_velocity, vel, dt_s)
            accelerations.append(accel)

            if vel < prev_velocity * 0.8:
                velocity_trends.append('decreasing')
            elif vel > prev_velocity * 1.2:
                velocity_trends.append('increasing')
            else:
                velocity_trends.append('stable')

            prev_prev_velocity = prev_velocity
        prev_velocity = vel

        curr_y = curr.get('mouse_y', 0)
        if detect_exit_intent(curr_y, vel):
            exit_intent_count += 1

    velocity_avg = sum(velocities) / len(velocities) if velocities else 0.0
    velocity_max = max(velocities) if velocities else 0.0
    velocity_std = statistics.stdev(velocities) if len(velocities) >= 2 else 0.0
    acceleration_avg = sum(accelerations) / len(accelerations) if accelerations else 0.0
    acceleration_max = max(accelerations) if accelerations else 0.0
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

    dwell_segments = calculate_dwell_segments(sorted_events)
    total_dwell_ms = sum(
        int((s['end'] - s['start']).total_seconds() * 1000) for s in dwell_segments
    )
    dwell_count = sum(s['count'] for s in dwell_segments)

    first_click = sorted_events[0].get('mouse_click_count', 0)
    last_click = sorted_events[-1].get('mouse_click_count', 0)
    total_session_s = (parse_timestamp(sorted_events[-1]['timestamp']) - parse_timestamp(sorted_events[0]['timestamp'])).total_seconds()
    click_frequency = calculate_click_frequency(
        last_click, first_click, total_session_s
    )

    return {
        'velocity_avg': velocity_avg,
        'velocity_max': velocity_max,
        'velocity_std': velocity_std,
        'acceleration_avg': acceleration_avg,
        'acceleration_max': acceleration_max,
        'idle_total_ms': idle_total,
        'distance_total': distance_total,
        'velocity_trend': velocity_trend,
        'exit_intent_count': exit_intent_count,
        'dwell_total_ms': total_dwell_ms,
        'dwell_segments': dwell_count,
        'click_frequency': click_frequency,
        'heartbeat_count': len(sorted_events)
    }


def extract_cart_features(events: List[Dict]) -> Dict:
    heartbeats = [e for e in events if e.get('event_type') == 'heartbeat']
    if len(heartbeats) < 2:
        return {
            'cart_delta': 0.0,
            'product_removals': {},
            'product_additions': {},
            'shipping_switches': 0
        }

    sorted_hb = sorted(heartbeats, key=lambda e: parse_timestamp(e['timestamp']))

    last = sorted_hb[-1]
    prev = sorted_hb[-2]

    cart_delta = last.get('cart_value', 0) - prev.get('cart_value', 0)

    current_qty = last.get('product_quantities', {})
    prev_qty = prev.get('product_quantities', {})

    removals = detect_product_removal(current_qty, prev_qty)
    additions = detect_product_addition(current_qty, prev_qty)

    shipping_values = [e.get('shipping_option_selected', 'standard') for e in sorted_hb]
    shipping_switches = count_value_changes(shipping_values)

    return {
        'cart_delta': cart_delta,
        'product_removals': removals,
        'product_additions': additions,
        'shipping_switches': shipping_switches
    }


def extract_funnel_features(events: List[Dict]) -> Dict:
    pages = [e.get('page') for e in events if e.get('page')]
    page_regression = 0
    for i in range(1, len(pages)):
        if pages[i] == 'cart' and pages[i - 1] == 'checkout':
            page_regression += 1

    checkout_events = [e for e in events if e.get('page') == 'checkout']
    hesitation_ms = 0
    payment_switches = 0

    if checkout_events:
        sorted_ce = sorted(checkout_events, key=lambda e: parse_timestamp(e['timestamp']))
        first_ce = parse_timestamp(sorted_ce[0]['timestamp'])
        last_ce = parse_timestamp(sorted_ce[-1]['timestamp'])
        hesitation_ms = int((last_ce - first_ce).total_seconds() * 1000)

        payment_methods = [e.get('payment_method_selected') for e in sorted_ce]
        payment_switches = count_value_changes(payment_methods)

    return {
        'page_regression_count': page_regression,
        'payment_hesitation_ms': hesitation_ms,
        'payment_method_switches': payment_switches
    }


def calculate_mouse_features(session_data: Dict) -> Optional[Dict]:
    heartbeats = session_data.get('heartbeats', [])
    if not heartbeats or len(heartbeats) < 2:
        return None

    features = extract_session_features(heartbeats)
    return features


def extract_all_features(session_data: Dict) -> Optional[Dict]:
    heartbeats = session_data.get('heartbeats', [])
    if not heartbeats or len(heartbeats) < 2:
        return None

    all_events = [{'event_type': 'heartbeat', **hb} for hb in heartbeats]
    if session_data.get('current_event'):
        all_events.append(session_data['current_event'])

    session_features = extract_session_features(heartbeats)
    if session_features is None:
        return None

    cart_features = extract_cart_features(heartbeats)
    funnel_features = extract_funnel_features(all_events)

    window_5s = aggregate_window(heartbeats, 5)
    window_10s = aggregate_window(heartbeats, 10)
    window_30s = aggregate_window(heartbeats, 30)

    return {
        **session_features,
        'cart_delta': cart_features['cart_delta'],
        'product_removals': cart_features['product_removals'],
        'product_additions': cart_features['product_additions'],
        'shipping_switches': cart_features['shipping_switches'],
        'page_regression_count': funnel_features['page_regression_count'],
        'payment_hesitation_ms': funnel_features['payment_hesitation_ms'],
        'payment_method_switches': funnel_features['payment_method_switches'],
        'window_5s': window_5s,
        'window_10s': window_10s,
        'window_30s': window_30s
    }


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
        'velocity_max': features.get('velocity_max', 0.0),
        'velocity_std': features.get('velocity_std', 0.0),
        'acceleration_avg': features.get('acceleration_avg', 0.0),
        'acceleration_max': features.get('acceleration_max', 0.0),
        'idle_seconds': features.get('idle_total_ms', 0) / 1000.0,
        'distance_total': features.get('distance_total', 0.0),
        'velocity_trend': features.get('velocity_trend', 'stable'),
        'exit_intent_count': features.get('exit_intent_count', 0),
        'dwell_seconds': features.get('dwell_total_ms', 0) / 1000.0,
        'dwell_segments': features.get('dwell_segments', 0),
        'click_frequency': features.get('click_frequency', 0.0),
        'cart_delta': features.get('cart_delta', 0.0),
        'shipping_switches': features.get('shipping_switches', 0),
        'page_regression_count': features.get('page_regression_count', 0),
        'payment_hesitation_seconds': features.get('payment_hesitation_ms', 0) / 1000.0,
        'payment_method_switches': features.get('payment_method_switches', 0),
        'window_5s': features.get('window_5s', {}),
        'window_10s': features.get('window_10s', {}),
        'window_30s': features.get('window_30s', {})
    }
    return payload