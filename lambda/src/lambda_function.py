import json
import os
import sys
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Any, Optional, List

import boto3
from botocore.config import Config

sys.path.append(os.path.join(os.path.dirname(__file__)))

from features import extract_all_features, prepare_inference_payload

S3_BUCKET = os.environ.get('S3_BUCKET', 'clickstream-bucket')
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE', 'clickstream-sessions')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
AWS_ENDPOINT_URL = os.environ.get('AWS_ENDPOINT_URL', 'http://localhost:4566')
ECS_ENDPOINT = os.environ.get('ECS_ENDPOINT', 'http://localhost:8080')

DEFAULT_BOTO_CONFIG = Config(
    region_name=AWS_REGION,
    retries={'max_attempts': 3, 'mode': 'standard'},
    s3={'addressing_style': 'path'}
)

s3 = boto3.client('s3', endpoint_url=AWS_ENDPOINT_URL, config=DEFAULT_BOTO_CONFIG)


def connect_dynamodb() -> object:
    resource = boto3.resource('dynamodb', endpoint_url=AWS_ENDPOINT_URL, config=Config(
        region_name=AWS_REGION,
        retries={'max_attempts': 3, 'mode': 'standard'}
    ))
    return resource.Table(DYNAMODB_TABLE)


table = connect_dynamodb()

REQUIRED_FIELDS = [
    'event_type', 'session_id', 'user_id', 'timestamp'
]

HEARTBEAT_REQUIRED = [
    'cart_value', 'product_count', 'product_quantities',
    'shipping_option_selected', 'mouse_click_count', 'mouse_x', 'mouse_y', 'page'
]

EVENT_TYPE_SCHEMAS = {
    'heartbeat': REQUIRED_FIELDS + HEARTBEAT_REQUIRED,
    'page_view': REQUIRED_FIELDS + ['page', 'cart_value', 'product_count', 'product_quantities', 'shipping_option_selected', 'mouse_click_count'],
    'add_to_cart': REQUIRED_FIELDS + ['product_id', 'category', 'price', 'cart_value', 'product_count', 'product_quantities', 'shipping_option_selected', 'mouse_click_count'],
    'remove_from_cart': REQUIRED_FIELDS + ['cart_value', 'product_count', 'product_quantities', 'shipping_option_selected', 'mouse_click_count'],
    'start_checkout': REQUIRED_FIELDS + ['cart_value', 'product_count', 'product_quantities', 'shipping_option_selected', 'mouse_click_count'],
    'purchase': REQUIRED_FIELDS + ['cart_value', 'product_count', 'product_quantities', 'shipping_option_selected', 'mouse_click_count', 'payment_method'],
    'abandon': REQUIRED_FIELDS + ['cart_value', 'product_count', 'product_quantities', 'shipping_option_selected', 'mouse_click_count', 'abandon_reason'],
    'view_product': REQUIRED_FIELDS + ['product_id', 'category', 'price']
}


def validate_event(event_data: Dict[str, Any]) -> tuple:
    event_type = event_data.get('event_type')
    if event_type not in EVENT_TYPE_SCHEMAS:
        return False, f"Invalid event_type: {event_type}"

    required = EVENT_TYPE_SCHEMAS[event_type]
    missing = [field for field in required if field not in event_data]
    if missing:
        return False, f"Missing required fields: {missing}"

    return True, None


def generate_s3_key(event_type: str, session_id: str, timestamp: str, prefix: str = 'raw') -> str:
    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    date_path = dt.strftime('%Y/%m/%d')
    event_id = str(uuid.uuid4())[:8]
    return f"{prefix}/{date_path}/{event_type}_{session_id}_{event_id}.json"


def store_event_s3(event_data: Dict[str, Any], s3_key: str) -> None:
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=s3_key,
        Body=json.dumps(event_data, default=str).encode('utf-8'),
        ContentType='application/json'
    )


def store_enriched_event_s3(
    event_data: Dict[str, Any],
    features: Optional[Dict[str, Any]],
    inference_response: Dict[str, Any],
    heartbeat_history: List[Dict[str, Any]],
    s3_raw_key: str
) -> str:
    dt = datetime.fromisoformat(event_data['timestamp'].replace('Z', '+00:00'))
    date_path = dt.strftime('%Y/%m/%d')
    event_id = str(uuid.uuid4())[:8]
    enriched_key = f"enriched/{date_path}/{event_data['session_id']}_{event_data['event_type']}_{event_id}.json"

    enriched = {
        'raw_event': event_data,
        'raw_s3_key': s3_raw_key,
        'features': features,
        'inference': inference_response,
        'heartbeat_count': len(heartbeat_history),
        'processed_at': datetime.now(timezone.utc).isoformat()
    }

    s3.put_object(
        Bucket=S3_BUCKET,
        Key=enriched_key,
        Body=json.dumps(enriched, default=str).encode('utf-8'),
        ContentType='application/json'
    )
    return enriched_key


def to_dynamo_value(value):
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, dict):
        return {k: to_dynamo_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_dynamo_value(v) for v in value]
    return value


SESSION_CACHE_TTL_SECONDS = 3600

DYNAMODB_FIELDS = [
    'device', 'delivery_mode', 'shipping_type', 'shipping_cost',
    'abandon_reason', 'payment_method', 'product_id', 'category', 'price',
    'cart_value', 'product_count', 'product_quantities',
    'shipping_option_selected', 'mouse_click_count', 'mouse_x', 'mouse_y',
    'page', 'user_id', 'event_type'
]


def store_session_state(event_data: Dict[str, Any], s3_key: str) -> None:
    dt = datetime.fromisoformat(event_data['timestamp'].replace('Z', '+00:00'))
    item = {
        'session_id': event_data['session_id'],
        'timestamp': Decimal(str(dt.timestamp())),
        's3_key': s3_key,
        'ttl': int(datetime.now(timezone.utc).timestamp()) + SESSION_CACHE_TTL_SECONDS
    }
    for field in DYNAMODB_FIELDS:
        if field in event_data:
            val = event_data[field]
            if isinstance(val, float):
                val = Decimal(str(val))
            elif isinstance(val, dict):
                val = to_dynamo_value(val)
            elif isinstance(val, (list, tuple)):
                val = to_dynamo_value(val)
            item[field] = val
    table.put_item(Item=item)


SESSION_WINDOW_SECONDS = 86400


def get_session_history(session_id: str) -> Dict[str, Any]:
    now_ts = datetime.now(timezone.utc).timestamp()
    cutoff = Decimal(str(now_ts - SESSION_WINDOW_SECONDS))
    response = table.query(
        KeyConditionExpression='session_id = :sid AND #ts >= :cutoff',
        ExpressionAttributeNames={'#ts': 'timestamp'},
        ExpressionAttributeValues={
            ':sid': session_id,
            ':cutoff': cutoff,
        },
        ScanIndexForward=False,
    )
    return {
        'items': response.get('Items', []),
        'session_id': session_id
    }


def invoke_inference(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        import requests
        response = requests.post(
            f"{ECS_ENDPOINT}/predict",
            json=payload,
            timeout=5
        )
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Inference error: {e}")
    return {'abandon_probability': 0.0, 'trigger_retention': False}


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    try:
        if 'body' not in event:
            return {'statusCode': 400, 'body': json.dumps({'error': 'Missing body'})}

        body = event['body']
        if isinstance(body, str):
            event_data = json.loads(body)
        else:
            event_data = body

        valid, error = validate_event(event_data)
        if not valid:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': error})
            }

        s3_key = generate_s3_key(event_data['event_type'], event_data['session_id'], event_data['timestamp'])

        store_event_s3(event_data, s3_key)
        store_session_state(event_data, s3_key)

        session_history = get_session_history(event_data['session_id'])

        session_data = {
            'session_id': event_data['session_id'],
            'user_id': event_data['user_id'],
            'cart_value': event_data.get('cart_value', 0),
            'product_count': event_data.get('product_count', 0),
            'product_quantities': event_data.get('product_quantities', {}) if isinstance(event_data.get('product_quantities'), dict) else {},
            'shipping_option_selected': event_data.get('shipping_option_selected', 'standard'),
            'delivery_mode': event_data.get('delivery_mode', 'shipping'),
            'shipping_type': event_data.get('shipping_type', 'standard'),
            'shipping_cost': event_data.get('shipping_cost', 0),
            'mouse_click_count': event_data.get('mouse_click_count', 0),
            'page': event_data.get('page', 'cart'),
            'heartbeats': [],
            'current_event': event_data
        }

        for item in session_history['items']:
            if item.get('event_type') == 'heartbeat':
                session_data['heartbeats'].append({
                    'event_type': 'heartbeat',
                    'mouse_x': int(item.get('mouse_x', 0)),
                    'mouse_y': int(item.get('mouse_y', 0)),
                    'timestamp': datetime.fromtimestamp(float(item['timestamp']), tz=timezone.utc).isoformat(),
                    'cart_value': float(item.get('cart_value', 0)),
                    'product_count': int(item.get('product_count', 0)),
                    'product_quantities': item.get('product_quantities', {}) if isinstance(item.get('product_quantities'), dict) else {},
                    'shipping_option_selected': item.get('shipping_option_selected', 'standard'),
                    'mouse_click_count': int(item.get('mouse_click_count', 0)),
                    'page': item.get('page', 'cart')
                })

        features = extract_all_features(session_data)

        inference_response = {'abandon_probability': 0.0, 'trigger_retention': False}
        if features:
            payload = prepare_inference_payload(session_data, features)
            inference_response = invoke_inference(payload)

        store_enriched_event_s3(
            event_data, features, inference_response,
            session_data['heartbeats'], s3_key
        )

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(inference_response)
        }

    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Invalid JSON'})
        }
    except Exception as e:
        error_msg = f"Lambda error: {e}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': str(e)})
        }