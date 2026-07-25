import json
import os
import uuid
import time
import pytest
import boto3
from botocore.config import Config
from datetime import datetime, timezone

AWS_ENDPOINT_URL = os.environ.get('AWS_ENDPOINT_URL', 'http://localhost:4566')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
API_ID = os.environ.get('API_ID', 'c75ed91dd2')
API_URL = f"http://localhost:4566/restapis/{API_ID}/prod/_user_request_/events"
S3_BUCKET = 'clickstream-bucket'
DYNAMODB_TABLE = 'clickstream-sessions'

config = Config(region_name=AWS_REGION, s3={'addressing_style': 'path'})
s3 = boto3.client('s3', endpoint_url=AWS_ENDPOINT_URL, config=config)
dynamodb = boto3.resource('dynamodb', endpoint_url=AWS_ENDPOINT_URL, config=Config(region_name=AWS_REGION))
table = dynamodb.Table(DYNAMODB_TABLE)

import urllib.request


def api_post(body):
    data = json.dumps(body).encode('utf-8')
    req = urllib.request.Request(
        API_URL, data=data,
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    resp = urllib.request.urlopen(req, timeout=10)
    return json.loads(resp.read().decode('utf-8'))


def make_event(event_type='heartbeat', **overrides):
    base = {
        'event_type': event_type,
        'session_id': f"int-test-{uuid.uuid4().hex[:8]}",
        'user_id': f"user-{uuid.uuid4().hex[:8]}",
        'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.') + '000Z',
        'cart_value': 100.0,
        'product_count': 1,
        'product_quantities': {'prod_001': 1},
        'shipping_option_selected': 'standard',
        'mouse_click_count': 0,
        'mouse_x': 100,
        'mouse_y': 200,
        'page': 'cart'
    }
    base.update(overrides)
    return base


class TestIntegrationFloci:
    def test_single_heartbeat_returns_response(self):
        event = make_event()
        resp = api_post(event)
        assert 'abandon_probability' in resp
        assert 'trigger_retention' in resp
        assert isinstance(resp['abandon_probability'], float)
        assert isinstance(resp['trigger_retention'], bool)

    def test_single_heartbeat_creates_s3_raw(self):
        event = make_event()
        api_post(event)
        time.sleep(0.5)
        result = s3.list_objects_v2(
            Bucket=S3_BUCKET, Prefix='raw/'
        )
        keys = [obj['Key'] for obj in result.get('Contents', [])]
        matching = [k for k in keys if k.endswith('.json') and event['session_id'] in k]
        assert len(matching) >= 1, f"No raw file found for session {event['session_id']} in keys {keys}"

    def test_single_heartbeat_creates_s3_enriched(self):
        event = make_event()
        api_post(event)
        time.sleep(0.5)
        result = s3.list_objects_v2(
            Bucket=S3_BUCKET, Prefix='enriched/'
        )
        keys = [obj['Key'] for obj in result.get('Contents', [])]
        matching = [k for k in keys if k.endswith('.json') and event['session_id'] in k]
        assert len(matching) >= 1, f"No enriched file found for session {event['session_id']}"

    def test_enriched_contains_features_when_enough_heartbeats(self):
        event = make_event()
        session_id = event['session_id']

        for i in range(6):
            e = event.copy()
            e['mouse_x'] = 100 + i * 20
            e['mouse_y'] = 200 + i * 10
            e['timestamp'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.') + f"{i:03d}Z"
            api_post(e)
            time.sleep(0.3)

        time.sleep(1)
        result = s3.list_objects_v2(
            Bucket=S3_BUCKET, Prefix=f"enriched/{datetime.now(timezone.utc).strftime('%Y/%m/%d')}/"
        )
        enriched_files = [obj['Key'] for obj in result.get('Contents', []) if session_id in obj['Key']]
        last_enriched = sorted(enriched_files)[-1]
        obj = s3.get_object(Bucket=S3_BUCKET, Key=last_enriched)
        enriched = json.loads(obj['Body'].read().decode('utf-8'))
        assert enriched['features'] is not None, "Features should not be None with >= 2 heartbeats"
        assert 'velocity_avg' in enriched['features']
        assert 'heartbeat_count' in enriched
        assert enriched['heartbeat_count'] >= 2

    def test_missing_fields_returns_400(self):
        event = {'event_type': 'heartbeat'}
        req = urllib.request.Request(
            API_URL,
            data=json.dumps(event).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        try:
            resp = urllib.request.urlopen(req, timeout=10)
            body = json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            body = json.loads(e.read().decode('utf-8'))
            assert e.code == 400
        assert 'error' in body

    def test_invalid_json_returns_400(self):
        req = urllib.request.Request(
            API_URL,
            data=b'not valid json',
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        try:
            resp = urllib.request.urlopen(req, timeout=10)
            body = json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            body = json.loads(e.read().decode('utf-8'))
            assert e.code == 400
        assert 'error' in body

    def test_dynamodb_session_created(self):
        event = make_event()
        api_post(event)
        time.sleep(0.5)
        result = table.query(
            KeyConditionExpression='session_id = :sid',
            ExpressionAttributeValues={':sid': event['session_id']}
        )
        assert len(result['Items']) >= 1
        item = result['Items'][0]
        assert item['event_type'] == 'heartbeat'
        assert 'ttl' in item
        assert item['ttl'] > int(time.time())

    def test_different_event_types_all_accepted(self):
        event_specs = [
            ('page_view', {}),
            ('add_to_cart', {'product_id': 'prod_001', 'category': 'computacion', 'price': 200.0}),
            ('remove_from_cart', {}),
            ('start_checkout', {}),
            ('view_product', {'product_id': 'prod_001', 'category': 'computacion', 'price': 200.0}),
        ]
        for event_type, extra in event_specs:
            event = make_event(event_type=event_type, **extra)
            resp = api_post(event)
            assert 'abandon_probability' in resp, f"Event type {event_type} failed"

    def test_raw_file_content_matches_event(self):
        event = make_event(
            page='checkout',
            cart_value=250.0,
            product_count=3,
            product_quantities={'prod_001': 2, 'prod_002': 1},
            shipping_option_selected='express'
        )
        api_post(event)
        time.sleep(0.5)
        result = s3.list_objects_v2(
            Bucket=S3_BUCKET, Prefix='raw/'
        )
        keys = [obj['Key'] for obj in result.get('Contents', []) if event['session_id'] in obj['Key']]
        assert len(keys) >= 1
        latest = sorted(keys)[-1]
        obj = s3.get_object(Bucket=S3_BUCKET, Key=latest)
        raw = json.loads(obj['Body'].read().decode('utf-8'))
        assert raw['session_id'] == event['session_id']
        assert raw['event_type'] == 'heartbeat'
        assert raw['cart_value'] == 250.0
        assert raw['page'] == 'checkout'

    def test_dynamodb_stores_all_fields_from_event(self):
        event = make_event(
            page='checkout',
            cart_value=250.0,
            product_count=3,
            product_quantities={'prod_001': 2, 'prod_002': 1},
            shipping_option_selected='express',
            device='mobile',
            delivery_mode='shipping',
            shipping_type='express',
            shipping_cost=15.0
        )
        api_post(event)
        time.sleep(0.5)
        result = table.query(
            KeyConditionExpression='session_id = :sid',
            ExpressionAttributeValues={':sid': event['session_id']}
        )
        assert len(result['Items']) >= 1
        item = result['Items'][0]
        assert item['device'] == 'mobile'
        assert item['delivery_mode'] == 'shipping'
        assert item['shipping_type'] == 'express'
        assert float(item['shipping_cost']) == 15.0
        assert item['page'] == 'checkout'
        assert float(item['cart_value']) == 250.0
        assert int(item['product_count']) == 3

    def test_dynamodb_event_type_specific_fields(self):
        event = make_event(
            event_type='purchase',
            cart_value=300.0,
            product_count=2,
            product_quantities={'prod_001': 1, 'prod_002': 1},
            payment_method='credit_card'
        )
        api_post(event)
        time.sleep(0.5)
        result = table.query(
            KeyConditionExpression='session_id = :sid',
            ExpressionAttributeValues={':sid': event['session_id']}
        )
        assert len(result['Items']) >= 1
        item = result['Items'][0]
        assert item['payment_method'] == 'credit_card'

        event2 = make_event(
            event_type='abandon',
            cart_value=150.0,
            product_count=1,
            product_quantities={'prod_001': 1},
            abandon_reason='Costo de envio muy alto'
        )
        api_post(event2)
        time.sleep(0.5)
        result2 = table.query(
            KeyConditionExpression='session_id = :sid',
            ExpressionAttributeValues={':sid': event2['session_id']}
        )
        assert len(result2['Items']) >= 1
        item2 = result2['Items'][0]
        assert item2['abandon_reason'] == 'Costo de envio muy alto'

    def test_dynamodb_ttl_is_future_timestamp(self):
        event = make_event()
        api_post(event)
        time.sleep(0.5)
        result = table.query(
            KeyConditionExpression='session_id = :sid',
            ExpressionAttributeValues={':sid': event['session_id']}
        )
        assert len(result['Items']) >= 1
        item = result['Items'][0]
        assert 'ttl' in item
        assert int(item['ttl']) > int(time.time()) + 3000

    def test_dynamodb_multiple_heartbeats_per_session(self):
        session_id = f"multi-session-{uuid.uuid4().hex[:8]}"
        user_id = f"multi-user-{uuid.uuid4().hex[:8]}"

        for i in range(3):
            e = make_event(
                session_id=session_id,
                user_id=user_id,
                mouse_x=100 + i * 50,
                mouse_y=200,
                cart_value=100 + i * 50,
                timestamp=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.') + f"{i:03d}Z"
            )
            api_post(e)
            time.sleep(0.3)

        time.sleep(0.5)
        result = table.query(
            KeyConditionExpression='session_id = :sid',
            ExpressionAttributeValues={':sid': session_id}
        )
        assert len(result['Items']) == 3
        timestamps = sorted([float(i['timestamp']) for i in result['Items']])
        assert timestamps[0] < timestamps[1] < timestamps[2]