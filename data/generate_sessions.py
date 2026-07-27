import json
import math
import os
import random
import statistics
import sys
import time
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import polars as pl

SESSION_COUNT = 5000
ABANDON_RATE_TARGET = 0.70
MAX_SESSION_SECONDS = 120
HEARTBEAT_INTERVAL_BASE_MS = 250
HEARTBEAT_JITTER_MS = 150
VIEWPORT_W = 1920
VIEWPORT_H = 1080

CATALOG = [
    {'id': 'prod_001', 'nombre': 'Laptop Gamer X', 'precio': 1200, 'categoria': 'computacion'},
    {'id': 'prod_002', 'nombre': 'Teclado Mecanico RGB', 'precio': 85, 'categoria': 'perifericos'},
    {'id': 'prod_003', 'nombre': 'Monitor 27 4K', 'precio': 450, 'categoria': 'computacion'},
    {'id': 'prod_004', 'nombre': 'Mouse Inalambrico', 'precio': 45, 'categoria': 'perifericos'},
    {'id': 'prod_005', 'nombre': 'Auriculares Bluetooth', 'precio': 95, 'categoria': 'audio'},
    {'id': 'prod_006', 'nombre': 'Webcam HD 1080p', 'precio': 70, 'categoria': 'perifericos'},
    {'id': 'prod_007', 'nombre': 'Tablet 10 Pulgadas', 'precio': 350, 'categoria': 'computacion'},
    {'id': 'prod_008', 'nombre': 'Smartwatch Deportivo', 'precio': 200, 'categoria': 'wearables'},
    {'id': 'prod_009', 'nombre': 'Silla Ergonomicas', 'precio': 320, 'categoria': 'muebles'},
    {'id': 'prod_010', 'nombre': 'Escritorio Electrico', 'precio': 580, 'categoria': 'muebles'},
    {'id': 'prod_011', 'nombre': 'Camara Web 4K', 'precio': 130, 'categoria': 'perifericos'},
    {'id': 'prod_012', 'nombre': 'Hub USB-C 7 puertos', 'precio': 40, 'categoria': 'perifericos'},
    {'id': 'prod_013', 'nombre': 'Microfono Condensador', 'precio': 110, 'categoria': 'audio'},
    {'id': 'prod_014', 'nombre': 'iPad Air', 'precio': 650, 'categoria': 'computacion'},
    {'id': 'prod_015', 'nombre': 'Cargador Portatil', 'precio': 35, 'categoria': 'accesorios'},
]
CATEGORIES = sorted(set(p['categoria'] for p in CATALOG))
PROD_BY_CATEGORY = defaultdict(list)
for p in CATALOG:
    PROD_BY_CATEGORY[p['categoria']].append(p)

DEVICES = ['desktop', 'mobile', 'tablet']
DEVICE_WEIGHTS = [0.65, 0.25, 0.10]
DELIVERY_MODES = ['shipping', 'store']
SHIPPING_TYPES = ['standard', 'express']
SHIPPING_COST_PER_ITEM = {'standard': 4.0, 'express': 12.0}
ABANDON_REASONS = ['extra_costs', 'complex_checkout', 'browsing', 'slow_delivery',
                   'payment_security', 'just_browsing']
ABANDON_REASON_WEIGHTS = [0.32, 0.18, 0.17, 0.15, 0.10, 0.08]
PAYMENT_METHODS = ['credit_card', 'debit_card', 'paypal', 'transfer']
PAYMENT_METHOD_WEIGHTS = [0.40, 0.25, 0.20, 0.15]

RNG = random.Random()
np.random.seed(42)


def weighted_choice(items, weights):
    total = sum(weights)
    r = RNG.random() * total
    upto = 0.0
    for item, w in zip(items, weights):
        upto += w
        if r <= upto:
            return item
    return items[-1]


def pick_items() -> List[Tuple]:
    n = RNG.randint(1, 6)
    chosen = RNG.sample(CATALOG, min(n, len(CATALOG)))
    items = []
    for p in chosen:
        qty = RNG.randint(1, 3)
        items.append((p['id'], p['nombre'], p['precio'], p['categoria'], qty))
    return items


def cart_value_and_qty(items):
    total_value = 0.0
    total_qty = 0
    qty_dict = {}
    for pid, nombre, precio, categoria, qty in items:
        total_value += precio * qty
        total_qty += qty
        qty_dict[pid] = qty
    return total_value, total_qty, qty_dict


def generate_user_id():
    return str(uuid.uuid4())


def generate_session_id():
    return str(uuid.uuid4())


def clamped_gauss(mean, sigma, lo, hi):
    v = RNG.gauss(mean, sigma)
    return max(lo, min(hi, v))


class MousePath:
    CART_CENTER = (500, 350, 200, 900, 100, 650)
    CART_BOTTOM = (550, 780, 200, 900, 700, 900)
    CHECKOUT_CENTER = (600, 400, 250, 1000, 100, 700)
    CHECKOUT_OPTIONS = (600, 300, 250, 1000, 150, 500)
    CHECKOUT_FORM = (550, 500, 250, 1000, 300, 700)
    CHECKOUT_PLACE = (600, 800, 300, 1000, 650, 900)
    PRODUCT_MODAL = (800, 400, 500, 1400, 100, 800)
    EXIT_TOP_RIGHT = (1880, 20, 1820, 1920, 0, 80)
    BACK_TO_CART = (100, 800, 50, 250, 700, 900)
    ERRATIC_CENTER = (700, 450, 300, 1200, 200, 700)
    CART_HEADER = (500, 100, 200, 900, 50, 180)

    ZONES = {
        'cart_center': CART_CENTER,
        'cart_bottom': CART_BOTTOM,
        'checkout_center': CHECKOUT_CENTER,
        'checkout_options': CHECKOUT_OPTIONS,
        'checkout_form': CHECKOUT_FORM,
        'checkout_place': CHECKOUT_PLACE,
        'product_modal': PRODUCT_MODAL,
        'exit_top_right': EXIT_TOP_RIGHT,
        'back_to_cart': BACK_TO_CART,
        'erratic_center': ERRATIC_CENTER,
        'cart_header': CART_HEADER,
    }

    @staticmethod
    def random_point(zone_name: str) -> Tuple[int, int]:
        z = MousePath.ZONES[zone_name]
        cx, cy, xmin, xmax, ymin, ymax = z
        x = int(RNG.uniform(xmin, xmax))
        y = int(RNG.uniform(ymin, ymax))
        return (x, y)

    @staticmethod
    def walk(start: Tuple[int, int], end: Tuple[int, int],
             steps: int, archetype: str, phase: str = 'normal') -> List[Tuple[int, int]]:
        sx, sy = start
        ex, ey = end
        points = []

        if archetype == 'purchaser':
            for i in range(steps):
                t = (i + 1) / steps
                noise = RNG.gauss(0, 6)
                x = sx + (ex - sx) * t + noise
                y = sy + (ey - sy) * t + noise * 0.6
                points.append((int(x), int(y)))
        else:
            if phase == 'browse':
                for i in range(steps):
                    t = (i + 1) / steps
                    noise = RNG.gauss(0, 12)
                    x = sx + (ex - sx) * t + noise
                    y = sy + (ey - sy) * t + noise * 0.8
                    points.append((int(x), int(y)))
            elif phase == 'hesitate':
                for i in range(steps):
                    t = (i + 1) / steps
                    noise = RNG.gauss(0, 8)
                    slowdown = 1.0 - 0.4 * t
                    x = sx + (ex - sx) * t + noise * slowdown
                    y = sy + (ey - sy) * t + noise * 0.5 * slowdown
                    points.append((int(x), int(y)))
            elif phase == 'frustrate':
                for i in range(steps):
                    t = (i + 1) / steps
                    shake = RNG.gauss(0, 20 + t * 15)
                    wobble = math.sin(math.pi * i * 0.3) * 15
                    x = sx + (ex - sx) * t + shake + wobble
                    y = sy + (ey - sy) * t + shake * 0.7
                    x = max(0, min(VIEWPORT_W, x))
                    y = max(0, min(VIEWPORT_H, y))
                    points.append((int(x), int(y)))
            elif phase == 'exit':
                for i in range(steps):
                    t = (i + 1) / steps
                    noise = RNG.gauss(0, 15)
                    x = sx + (ex - sx) * t + noise
                    y = sy + (ey - sy) * t + noise * 0.5
                    points.append((int(x), int(y)))
            else:
                for i in range(steps):
                    t = (i + 1) / steps
                    x = sx + (ex - sx) * t + RNG.gauss(0, 10)
                    y = sy + (ey - sy) * t + RNG.gauss(0, 10)
                    points.append((int(x), int(y)))

        return points

    @staticmethod
    def idle_steps(current: Tuple[int, int], steps: int,
                   archetype: str, phase: str = 'normal') -> List[Tuple[int, int]]:
        points = []
        for i in range(steps):
            if archetype == 'purchaser':
                noise = RNG.gauss(0, 2)
            else:
                if phase == 'hesitate':
                    noise = RNG.gauss(0, 3 + math.sin(i * 0.5) * 2)
                elif phase == 'frustrate':
                    noise = RNG.gauss(0, 5 + math.sin(i * 0.3) * 4)
                else:
                    noise = RNG.gauss(0, 3)
            x = int(current[0] + noise)
            y = int(current[1] + RNG.gauss(0, 2))
            x = max(0, min(VIEWPORT_W, x))
            y = max(0, min(VIEWPORT_H, y))
            points.append((x, y))
        return points


class SessionGenerator:
    def __init__(self):
        self.session_id = generate_session_id()
        self.user_id = generate_user_id()
        self.device = weighted_choice(DEVICES, DEVICE_WEIGHTS)
        self.page = 'cart'
        self.cart_items = pick_items()
        self.cart_value, self.product_count, self.product_quantities = cart_value_and_qty(self.cart_items)
        self.delivery_mode = 'shipping'
        self.shipping_type = 'standard'
        self.shipping_option_selected = 'standard'
        self.shipping_cost = self.product_count * SHIPPING_COST_PER_ITEM['standard']
        self.mouse_click_count = 0
        self.mouse_x = 500
        self.mouse_y = 350
        self.base_timestamp = datetime.now(timezone.utc) - timedelta(
            hours=RNG.randint(1, 72), minutes=RNG.randint(0, 59)
        )
        self.events: List[Dict] = []
        self.clock_offset_ms = 0
        self.shipping_switches = 0
        self.page_regressions = 0
        self.cart_adds = 0
        self.cart_removes = 0
        self.exit_intent_count = 0
        self.last_action_ts = self.base_timestamp
        self.abandon_reason = None
        self.payment_method = None
        self.payment_method_selected = None
        self.time_on_page = 0

    def now(self) -> datetime:
        return self.base_timestamp + timedelta(milliseconds=self.clock_offset_ms)

    def advance(self, delta_ms: int):
        self.clock_offset_ms += delta_ms
        self.time_on_page = self.clock_offset_ms // 1000

    def heartbeat_interval_ms(self) -> int:
        jitter = RNG.randint(-HEARTBEAT_JITTER_MS, HEARTBEAT_JITTER_MS)
        return max(50, HEARTBEAT_INTERVAL_BASE_MS + jitter)

    def timestamp_str(self):
        return self.now().isoformat().replace('+00:00', 'Z')

    def emit(self, event_type: str, extra: dict = None):
        payload = {
            'event_type': event_type,
            'timestamp': self.timestamp_str(),
            'session_id': self.session_id,
            'user_id': self.user_id,
            'mouse_click_count': self.mouse_click_count,
            'device': self.device,
            'time_on_page': self.time_on_page,
        }
        if extra:
            payload.update(extra)
        payload.setdefault('cart_value', self.cart_value)
        payload.setdefault('product_count', self.product_count)
        payload.setdefault('product_quantities', self.product_quantities)
        payload.setdefault('shipping_option_selected', self.shipping_option_selected)
        payload.setdefault('delivery_mode', self.delivery_mode)
        payload.setdefault('shipping_type', self.shipping_type)
        payload.setdefault('shipping_cost', self.shipping_cost)
        self.events.append(payload)

    def heartbeat(self, mx: int = None, my: int = None):
        self.advance(self.heartbeat_interval_ms())
        if mx is not None:
            self.mouse_x = mx
        if my is not None:
            self.mouse_y = my
        extra = {
            'page': self.page,
            'mouse_x': self.mouse_x,
            'mouse_y': self.mouse_y,
        }
        self.emit('heartbeat', extra)

    def add_to_cart(self, product):
        self.advance(RNG.randint(200, 800))
        self.cart_items.append((product['id'], product['nombre'], product['precio'],
                                product['categoria'], 1))
        self.cart_value, self.product_count, self.product_quantities = cart_value_and_qty(self.cart_items)
        self.mouse_click_count += 1
        self.cart_adds += 1
        self.emit('add_to_cart', {
            'product_id': product['id'],
            'category': product['categoria'],
            'price': product['precio'],
            'page': self.page,
            'mouse_x': self.mouse_x,
            'mouse_y': self.mouse_y,
        })

    def remove_from_cart(self, pid, precio, categoria):
        self.advance(RNG.randint(200, 600))
        for item in list(self.cart_items):
            if item[0] == pid and item[4] > 0:
                qty = item[4]
                if qty > 1:
                    idx = self.cart_items.index(item)
                    self.cart_items[idx] = (item[0], item[1], item[2], item[3], qty - 1)
                else:
                    self.cart_items.remove(item)
                break
        self.cart_value, self.product_count, self.product_quantities = cart_value_and_qty(self.cart_items)
        self.mouse_click_count += 1
        self.cart_removes += 1
        self.emit('remove_from_cart', {
            'page': self.page,
            'mouse_x': self.mouse_x,
            'mouse_y': self.mouse_y,
        })

    def start_checkout(self):
        self.advance(RNG.randint(500, 1500))
        self.page = 'checkout'
        self.mouse_click_count += 1
        self.emit('start_checkout', {
            'page': 'checkout',
            'payment_method_selected': None,
            'mouse_x': self.mouse_x,
            'mouse_y': self.mouse_y,
        })

    def back_to_cart(self):
        self.advance(RNG.randint(300, 1000))
        self.page = 'cart'
        self.page_regressions += 1
        self.emit('page_view', {
            'page': 'cart',
            'mouse_x': self.mouse_x,
            'mouse_y': self.mouse_y,
        })

    def toggle_shipping(self):
        self.advance(RNG.randint(300, 800))
        options = [s for s in SHIPPING_TYPES if s != self.shipping_type]
        self.shipping_type = RNG.choice(options) if options else 'standard'
        self.shipping_option_selected = self.shipping_type
        if self.delivery_mode == 'store':
            self.shipping_cost = 0
        else:
            self.shipping_cost = self.product_count * SHIPPING_COST_PER_ITEM[self.shipping_type]
        self.mouse_click_count += 1
        self.shipping_switches += 1

    def toggle_delivery_mode(self):
        self.advance(RNG.randint(300, 800))
        modes = [m for m in DELIVERY_MODES if m != self.delivery_mode]
        self.delivery_mode = RNG.choice(modes) if modes else 'shipping'
        if self.delivery_mode == 'store':
            self.shipping_cost = 0
        else:
            self.shipping_cost = self.product_count * SHIPPING_COST_PER_ITEM[self.shipping_type]
        self.mouse_click_count += 1
        self.shipping_switches += 1

    def abandon(self, reason=None):
        self.advance(RNG.randint(500, 2000))
        if reason is None:
            reason = weighted_choice(ABANDON_REASONS, ABANDON_REASON_WEIGHTS)
        self.abandon_reason = reason
        self.emit('abandon', {
            'abandon_reason': reason,
            'page': self.page,
            'mouse_x': self.mouse_x,
            'mouse_y': self.mouse_y,
        })

    def purchase(self):
        self.advance(RNG.randint(500, 3000))
        pm = weighted_choice(PAYMENT_METHODS, PAYMENT_METHOD_WEIGHTS)
        self.payment_method = pm
        self.payment_method_selected = pm
        self.mouse_click_count += 1
        self.emit('purchase', {
            'payment_method_selected': pm,
            'payment_method': pm,
            'page': 'checkout',
            'mouse_x': self.mouse_x,
            'mouse_y': self.mouse_y,
        })

    def view_product(self, product):
        self.advance(RNG.randint(300, 1000))
        self.emit('view_product', {
            'product_id': product['id'],
            'category': product['categoria'],
            'price': product['precio'],
            'page': self.page,
            'mouse_x': self.mouse_x,
            'mouse_y': self.mouse_y,
        })

    def elapsed_seconds(self) -> float:
        return self.clock_offset_ms / 1000.0


def generate_purchaser_session() -> SessionGenerator:
    gen = SessionGenerator()
    total_duration_s = RNG.randint(80, 120)
    start_ts = gen.now()

    cart_phase_end_s = RNG.randint(15, 40)
    checkout_phase_end_s = total_duration_s - RNG.randint(10, 20)

    while gen.elapsed_seconds() < cart_phase_end_s:
        zone = 'cart_center' if gen.elapsed_seconds() < cart_phase_end_s * 0.6 else 'cart_bottom'
        mx, my = MousePath.random_point(zone)
        gen.heartbeat(mx, my)

        if gen.elapsed_seconds() > 5 and RNG.random() < 0.03:
            cat = RNG.choice(CATEGORIES)
            if PROD_BY_CATEGORY[cat]:
                gen.add_to_cart(RNG.choice(PROD_BY_CATEGORY[cat]))

    gen.start_checkout()

    while gen.elapsed_seconds() < checkout_phase_end_s:
        progress = (gen.elapsed_seconds() - cart_phase_end_s) / (checkout_phase_end_s - cart_phase_end_s)
        if progress < 0.4:
            mx, my = MousePath.random_point('checkout_options')
        elif progress < 0.8:
            mx, my = MousePath.random_point('checkout_form')
        else:
            mx, my = MousePath.random_point('checkout_place')
        gen.heartbeat(mx, my)

        if RNG.random() < 0.06 and gen.shipping_switches < 1:
            gen.toggle_shipping()

    mx, my = MousePath.random_point('checkout_place')
    gen.heartbeat(mx, my)
    gen.purchase()
    return gen


def generate_abandoner_session() -> SessionGenerator:
    gen = SessionGenerator()
    total_duration_s = RNG.randint(60, 120)
    hesitation_level = RNG.uniform(0.25, 0.50)

    phase1_end = int(total_duration_s * hesitation_level)
    phase2_end = int(total_duration_s * (hesitation_level + RNG.uniform(0.15, 0.25)))
    phase3_end = total_duration_s - RNG.randint(3, 8)

    goes_to_checkout = RNG.random() < 0.65

    while gen.elapsed_seconds() < phase1_end:
        mx, my = MousePath.random_point('cart_center')
        gen.heartbeat(mx, my)
        if RNG.random() < 0.06 and gen.cart_adds < 3:
            cat = RNG.choice(CATEGORIES)
            if PROD_BY_CATEGORY[cat]:
                gen.add_to_cart(RNG.choice(PROD_BY_CATEGORY[cat]))
        if gen.cart_items and RNG.random() < 0.04 and gen.cart_removes < 2:
            item = RNG.choice(gen.cart_items)
            gen.remove_from_cart(item[0], item[2], item[3])

    while gen.elapsed_seconds() < phase2_end:
        remaining = phase2_end - gen.elapsed_seconds()
        if remaining < 3:
            for _ in range(RNG.randint(3, 8)):
                gen.heartbeat(*MousePath.idle_steps((gen.mouse_x, gen.mouse_y), 1, 'abandoner', 'hesitate')[0])
        else:
            if RNG.random() < 0.30:
                for _ in range(RNG.randint(2, 6)):
                    gen.heartbeat(*MousePath.idle_steps((gen.mouse_x, gen.mouse_y), 1, 'abandoner', 'hesitate')[0])
            else:
                zone = RNG.choice(['cart_center', 'cart_bottom', 'cart_header'])
                mx, my = MousePath.random_point(zone)
                gen.heartbeat(mx, my)

            if goes_to_checkout and RNG.random() < 0.10:
                gen.toggle_shipping()

            if RNG.random() < 0.05 and gen.cart_removes < 3 and gen.cart_items:
                item = RNG.choice(gen.cart_items)
                gen.remove_from_cart(item[0], item[2], item[3])

    if goes_to_checkout:
        gen.start_checkout()
        checkout_entered_at = gen.elapsed_seconds()

        while gen.elapsed_seconds() < phase3_end and (gen.elapsed_seconds() - checkout_entered_at) < 45:
            progress_in_checkout = (gen.elapsed_seconds() - checkout_entered_at) / 45.0

            if progress_in_checkout < 0.3:
                mx, my = MousePath.random_point('checkout_options')
                gen.heartbeat(mx, my)
                if RNG.random() < 0.12:
                    if RNG.random() < 0.5:
                        gen.toggle_delivery_mode()
                    else:
                        gen.toggle_shipping()
            elif progress_in_checkout < 0.6:
                for _ in range(RNG.randint(2, 5)):
                    gen.heartbeat(*MousePath.idle_steps((gen.mouse_x, gen.mouse_y), 1, 'abandoner', 'frustrate')[0])
                mx, my = MousePath.random_point('checkout_form')
                gen.heartbeat(mx, my)
                if RNG.random() < 0.08 and gen.page_regressions < 2:
                    gen.back_to_cart()
                    for _ in range(RNG.randint(3, 6)):
                        mx, my = MousePath.random_point('cart_center')
                        gen.heartbeat(mx, my)
                    gen.start_checkout()
                    checkout_entered_at = gen.elapsed_seconds()
            else:
                mx, my = MousePath.random_point('checkout_form')
                gen.heartbeat(mx, my)
                if RNG.random() < 0.15:
                    gen.toggle_shipping()

    phase4_start = max(gen.elapsed_seconds(), phase3_end)
    while phase4_start < total_duration_s:
        gen.advance(RNG.randint(100, 300))
        mx, my = MousePath.random_point('exit_top_right')
        gen.heartbeat(mx, my)
        gen.exit_intent_count += 1
        gen.mouse_click_count += 1
        phase4_start = gen.elapsed_seconds()

    gen.abandon()
    return gen


def generate_session() -> Tuple[List[Dict], SessionGenerator]:
    is_abandon = RNG.random() < ABANDON_RATE_TARGET

    if is_abandon:
        gen = generate_abandoner_session()
    else:
        gen = generate_purchaser_session()

    events = gen.events
    gen.events = events
    return events, gen


def calculate_velocity(x1, y1, x2, y2, dt_s):
    if dt_s <= 0:
        return 0.0
    dist = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    return dist / dt_s


def safe_mouse(event: Dict, key: str, default=0):
    val = event.get(key)
    if val is None:
        return default
    return val


def compute_session_features(events: List[Dict]) -> Optional[Dict]:
    sorted_events = sorted(events, key=lambda e: e['timestamp'])
    heartbeats = [e for e in sorted_events if e.get('event_type') == 'heartbeat']
    if len(heartbeats) < 2:
        return None

    velocities = []
    accelerations = []
    idle_total_ms = 0
    prev_velocity = None
    velocity_trends = []
    exit_intent_count = 0
    dwell_segments = []
    dwell_start = None
    dwell_count = 0

    for i in range(1, len(heartbeats)):
        prev = heartbeats[i - 1]
        curr = heartbeats[i]

        prev_ts = datetime.fromisoformat(prev['timestamp'].replace('Z', '+00:00'))
        curr_ts = datetime.fromisoformat(curr['timestamp'].replace('Z', '+00:00'))
        dt_s = (curr_ts - prev_ts).total_seconds()
        dt_ms = int(dt_s * 1000)
        if dt_s <= 0:
            dt_s = 0.25
            dt_ms = 250
        elif dt_s > 10:
            dt_s = 0.25
            dt_ms = 250

        vel = calculate_velocity(
            safe_mouse(prev, 'mouse_x'), safe_mouse(prev, 'mouse_y'),
            safe_mouse(curr, 'mouse_x'), safe_mouse(curr, 'mouse_y'),
            dt_s
        )
        velocities.append(vel)

        if vel < 5:
            idle_total_ms += dt_ms

        if prev_velocity is not None:
            acc = (vel - prev_velocity) / dt_s if dt_s > 0 else 0
            accelerations.append(acc)

            if vel < prev_velocity * 0.8:
                velocity_trends.append('decreasing')
            elif vel > prev_velocity * 1.2:
                velocity_trends.append('increasing')
            else:
                velocity_trends.append('stable')

        prev_velocity = vel

        if safe_mouse(curr, 'mouse_y', 500) < 100 and vel > 200:
            exit_intent_count += 1

        dx = abs(safe_mouse(curr, 'mouse_x') - safe_mouse(prev, 'mouse_x'))
        dy = abs(safe_mouse(curr, 'mouse_y') - safe_mouse(prev, 'mouse_y'))
        is_static = dx == 0 and dy == 0
        if is_static:
            if dwell_start is None:
                dwell_start = prev_ts
            dwell_count += 1
        else:
            if dwell_start is not None and dwell_count > 0:
                dwell_segments.append({
                    'start': dwell_start,
                    'end': prev_ts,
                    'count': dwell_count
                })
                dwell_start = None
                dwell_count = 0

    velocity_avg = statistics.mean(velocities) if velocities else 0.0
    velocity_max = max(velocities) if velocities else 0.0
    velocity_std = statistics.stdev(velocities) if len(velocities) >= 2 else 0.0
    acceleration_avg = statistics.mean(accelerations) if accelerations else 0.0
    acceleration_max = max(accelerations) if accelerations else 0.0

    if len(velocities) >= 10:
        slope = np.polyfit(range(len(velocities)), velocities, 1)[0]
        velocity_trend = 'decreasing' if slope < -10 else ('increasing' if slope > 10 else 'stable')
    else:
        d_count = velocity_trends.count('decreasing') if velocity_trends else 0
        i_count = velocity_trends.count('increasing') if velocity_trends else 0
        if d_count > i_count:
            velocity_trend = 'decreasing'
        elif i_count > d_count:
            velocity_trend = 'increasing'
        else:
            velocity_trend = 'stable'

    total_dwell_ms = sum(
        int((s['end'] - s['start']).total_seconds() * 1000) for s in dwell_segments
    )
    total_dwell_segments = len(dwell_segments)

    first_ts = min(datetime.fromisoformat(e['timestamp'].replace('Z', '+00:00')) for e in sorted_events)
    last_ts = max(datetime.fromisoformat(e['timestamp'].replace('Z', '+00:00')) for e in sorted_events)
    session_duration_s = (last_ts - first_ts).total_seconds()
    click_frequency = sum(e.get('mouse_click_count', 0) for e in sorted_events) / max(session_duration_s, 1)

    total_dist = sum(
        math.sqrt(
            (safe_mouse(sorted_events[i], 'mouse_x') - safe_mouse(sorted_events[i - 1], 'mouse_x'))**2 +
            (safe_mouse(sorted_events[i], 'mouse_y') - safe_mouse(sorted_events[i - 1], 'mouse_y'))**2
        )
        for i in range(1, len(sorted_events))
    )

    return {
        'velocity_avg': round(velocity_avg, 2),
        'velocity_max': round(velocity_max, 2),
        'velocity_std': round(velocity_std, 2),
        'acceleration_avg': round(acceleration_avg, 2),
        'acceleration_max': round(acceleration_max, 2),
        'idle_total_ms': idle_total_ms,
        'distance_total': round(total_dist, 2),
        'velocity_trend': velocity_trend,
        'exit_intent_count': exit_intent_count,
        'dwell_total_ms': total_dwell_ms,
        'dwell_segments': total_dwell_segments,
        'click_frequency': round(click_frequency, 4),
        'heartbeat_count': len(heartbeats),
        'session_duration_s': round(session_duration_s, 2),
    }


def compute_cart_features(events: List[Dict], gen: SessionGenerator) -> Dict:
    heartbeats = [e for e in events if e.get('event_type') == 'heartbeat']
    cart_delta = 0.0
    shipping_switches = 0
    product_removals = {}
    product_additions = {}

    if len(heartbeats) >= 2:
        last = heartbeats[-1]
        prev = heartbeats[-2]
        cart_delta = last.get('cart_value', 0) - prev.get('cart_value', 0)
        shipping_values = [e.get('shipping_option_selected', 'standard') for e in heartbeats]
        shipping_switches = sum(1 for i in range(1, len(shipping_values)) if shipping_values[i] != shipping_values[i - 1])
        for e in events:
            if e.get('event_type') == 'add_to_cart':
                pid = e.get('product_id', 'unknown')
                product_additions[pid] = product_additions.get(pid, 0) + 1
            if e.get('event_type') == 'remove_from_cart':
                pid = e.get('product_id', 'unknown')
                product_removals[pid] = product_removals.get(pid, 0) + 1

    return {
        'cart_delta': round(cart_delta, 2),
        'product_removals': json.dumps(product_removals),
        'product_additions': json.dumps(product_additions),
        'shipping_switches': shipping_switches,
    }


def compute_funnel_features(events: List[Dict]) -> Dict:
    pages = [e.get('page') for e in events if e.get('page')]
    page_regression = sum(1 for i in range(1, len(pages)) if pages[i] == 'cart' and pages[i - 1] == 'checkout')

    checkout_events = [e for e in events if e.get('page') == 'checkout']
    hesitation_ms = 0
    payment_switches = 0
    if checkout_events:
        sorted_ce = sorted(checkout_events, key=lambda e: e['timestamp'])
        first = datetime.fromisoformat(sorted_ce[0]['timestamp'].replace('Z', '+00:00'))
        last = datetime.fromisoformat(sorted_ce[-1]['timestamp'].replace('Z', '+00:00'))
        hesitation_ms = int((last - first).total_seconds() * 1000)
        pmethods = [e.get('payment_method_selected') for e in sorted_ce if e.get('payment_method_selected')]
        payment_switches = sum(1 for i in range(1, len(pmethods)) if pmethods[i] != pmethods[i - 1])

    return {
        'page_regression_count': page_regression,
        'payment_hesitation_ms': hesitation_ms,
        'payment_method_switches': payment_switches,
    }


def session_has_terminal(events: List[Dict]) -> Optional[str]:
    for e in events:
        if e.get('event_type') in ('purchase', 'abandon'):
            return e['event_type']
    return None


def build_session_row(events: List[Dict], gen: SessionGenerator, idx: int) -> Dict:
    features = compute_session_features(events)
    cart_feat = compute_cart_features(events, gen)
    funnel_feat = compute_funnel_features(events)
    is_abandon = 1 if session_has_terminal(events) == 'abandon' else 0

    row = {
        'session_id': gen.session_id,
        'user_id': gen.user_id,
        'device': gen.device,
        'event_count': len(events),
        'abandoned': is_abandon,
        'abandon_reason': gen.abandon_reason or '',
        'payment_method': gen.payment_method or '',
        'has_checkout': int(any(e.get('page') == 'checkout' for e in events)),
    }

    if features:
        row.update({
            'velocity_avg': features['velocity_avg'],
            'velocity_max': features['velocity_max'],
            'velocity_std': features['velocity_std'],
            'acceleration_avg': features['acceleration_avg'],
            'acceleration_max': features['acceleration_max'],
            'idle_total_ms': features['idle_total_ms'],
            'distance_total': features['distance_total'],
            'velocity_trend': features['velocity_trend'],
            'exit_intent_count': features['exit_intent_count'],
            'dwell_total_ms': features['dwell_total_ms'],
            'dwell_segments': features['dwell_segments'],
            'click_frequency': features['click_frequency'],
            'session_duration_s': features['session_duration_s'],
        })

    row.update({
        'cart_delta': cart_feat['cart_delta'],
        'product_removals': cart_feat['product_removals'],
        'product_additions': cart_feat['product_additions'],
    })

    row.update({
        'shipping_switches': cart_feat['shipping_switches'],
        'page_regression_count': funnel_feat['page_regression_count'],
        'payment_hesitation_ms': funnel_feat['payment_hesitation_ms'],
        'payment_method_switches': funnel_feat['payment_method_switches'],
    })

    row['index'] = idx
    return row


def write_ndjson_line(f, event: Dict):
    f.write(json.dumps(event, ensure_ascii=False, default=str) + '\n')


def main():
    base_dir = Path(__file__).parent
    raw_dir = base_dir / 'raw'
    processed_dir = base_dir / 'processed'
    meta_dir = base_dir / 'metadata'

    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    meta_dir.mkdir(parents=True, exist_ok=True)

    ndjson_path = raw_dir / 'all_events.ndjson'
    parquet_path = processed_dir / 'sessions.parquet'
    report_path = meta_dir / 'generation_report.json'

    all_rows = []
    stats = defaultdict(int)
    total_events = 0
    total_abandons = 0

    print(f"Generando {SESSION_COUNT} sesiones (max {MAX_SESSION_SECONDS}s c/u)...")
    start_time = time.time()

    with open(ndjson_path, 'w', encoding='utf-8') as ndjson_f:
        for i in range(SESSION_COUNT):
            if (i + 1) % 500 == 0:
                pct = (i + 1) / SESSION_COUNT * 100
                elapsed = time.time() - start_time
                rate = (i + 1) / elapsed if elapsed > 0 else 0
                print(f"  {i+1}/{SESSION_COUNT} ({pct:.0f}%) | {rate:.0f} sesiones/s")

            events, gen = generate_session()

            for evt in events:
                write_ndjson_line(ndjson_f, evt)

            row = build_session_row(events, gen, i)
            all_rows.append(row)

            total_events += len(events)
            term = session_has_terminal(events)
            if term == 'abandon':
                total_abandons += 1
                stats['abandon'] += 1
            elif term == 'purchase':
                stats['purchase'] += 1
            else:
                stats['unknown'] += 1

            heartbeats = sum(1 for e in events if e.get('event_type') == 'heartbeat')
            stats['total_heartbeats'] += heartbeats
            stats['total_adds'] += sum(1 for e in events if e.get('event_type') == 'add_to_cart')
            stats['total_removes'] += sum(1 for e in events if e.get('event_type') == 'remove_from_cart')
            stats['total_checkouts'] += sum(1 for e in events if e.get('event_type') == 'start_checkout')
            stats['total_abandon_events'] += sum(1 for e in events if e.get('event_type') == 'abandon')
            stats['total_purchases'] += sum(1 for e in events if e.get('event_type') == 'purchase')

    elapsed_total = time.time() - start_time
    print(f"\nNDJSON escrito: {ndjson_path}")
    ndjson_size = ndjson_path.stat().st_size
    print(f"  Tamano: {ndjson_size / 1024 / 1024:.1f} MB")

    df = pl.DataFrame(all_rows)
    df.write_parquet(parquet_path)
    print(f"Parquet escrito: {parquet_path}")
    print(f"  Filas: {df.shape[0]}, Columnas: {df.shape[1]}")

    actual_rate = total_abandons / SESSION_COUNT * 100
    avg_events = total_events / SESSION_COUNT
    avg_heartbeats = stats['total_heartbeats'] / SESSION_COUNT

    report = {
        'session_count': SESSION_COUNT,
        'total_events': total_events,
        'avg_events_per_session': round(avg_events, 1),
        'avg_heartbeats_per_session': round(avg_heartbeats, 1),
        'abandon_count': stats['abandon'],
        'purchase_count': stats['purchase'],
        'abandon_rate_pct': round(actual_rate, 2),
        'abandon_reason_distribution': {},
        'feature_stats': {},
        'elapsed_seconds': round(elapsed_total, 1),
        'generation_rate': round(SESSION_COUNT / elapsed_total, 1),
    }

    if stats['abandon'] > 0:
        abandon_df = df.filter(pl.col('abandoned') == 1)
        reason_counts = abandon_df['abandon_reason'].value_counts()
        for row in reason_counts.iter_rows():
            report['abandon_reason_distribution'][str(row[0])] = int(row[1])

    numeric_cols = [s for s in df.schema if df[s].dtype in (pl.Float64, pl.Int64, pl.Float32, pl.Int32)]
    for col in numeric_cols:
        try:
            vals = df[col].drop_nulls()
            if len(vals) > 0:
                report['feature_stats'][col] = {
                    'mean': round(float(vals.mean()), 2),
                    'std': round(float(vals.std()), 2),
                    'min': round(float(vals.min()), 2),
                    'max': round(float(vals.max()), 2),
                }
        except Exception:
            pass

    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\nReporte: {report_path}")
    print(f"  Eventos totales: {total_events}")
    print(f"  Promedio eventos/sesion: {avg_events:.1f}")
    print(f"  Promedio heartbeats/sesion: {avg_heartbeats:.1f}")
    print(f"  Duracion promedio sesion (estimada): {total_events / avg_heartbeats * 0.25:.1f}s")
    print(f"  Abandonos: {stats['abandon']} ({actual_rate:.1f}%)")
    print(f"  Purchases: {stats['purchase']}")
    print(f"  Tiempo total: {elapsed_total:.1f}s")


if __name__ == '__main__':
    main()
