import json
import os
import sys
import pytest
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from lambda_function import lambda_handler


@pytest.fixture
def lambda_event():
    return {
        'body': json.dumps({
            'event_type': 'heartbeat',
            'session_id': 'test-session-123',
            'user_id': 'test-user-456',
            'timestamp': '2026-07-24T18:30:00.000Z',
            'cart_value': 1200.50,
            'product_count': 2,
            'product_quantities': {'prod_001': 1, 'prod_003': 1},
            'shipping_option_selected': 'standard',
            'mouse_click_count': 15,
            'mouse_x': 320,
            'mouse_y': 180,
            'page': 'cart'
        })
    }


@pytest.fixture
def context():
    return Mock()


@patch.dict(os.environ, {
    'S3_BUCKET': 'test-bucket',
    'DYNAMODB_TABLE': 'test-table',
    'AWS_ENDPOINT_URL': 'http://localhost:4566'
})
@patch('lambda_function.s3')
@patch('lambda_function.table')
def test_lambda_handler_valid_event(mock_table, mock_s3, lambda_event, context):
    mock_table.put_item.return_value = {}
    mock_s3.put_object.return_value = {}

    response = lambda_handler(lambda_event, context)

    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body['trigger_retention'] is False
    assert body['abandon_probability'] == 0.0

    assert mock_s3.put_object.call_count == 2
    mock_table.put_item.assert_called_once()


@patch.dict(os.environ, {
    'S3_BUCKET': 'test-bucket',
    'DYNAMODB_TABLE': 'test-table',
    'AWS_ENDPOINT_URL': 'http://localhost:4566'
})
@patch('lambda_function.s3')
@patch('lambda_function.table')
def test_lambda_handler_missing_fields(mock_table, mock_s3, context):
    event = {'body': json.dumps({'event_type': 'heartbeat'})}

    response = lambda_handler(event, context)

    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert 'error' in body


@patch.dict(os.environ, {
    'S3_BUCKET': 'test-bucket',
    'DYNAMODB_TABLE': 'test-table',
    'AWS_ENDPOINT_URL': 'http://localhost:4566'
})
@patch('lambda_function.s3')
@patch('lambda_function.table')
def test_lambda_handler_invalid_json(mock_table, mock_s3, context):
    event = {'body': 'not valid json'}

    response = lambda_handler(event, context)

    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert 'error' in body


@patch.dict(os.environ, {
    'S3_BUCKET': 'test-bucket',
    'DYNAMODB_TABLE': 'test-table',
    'AWS_ENDPOINT_URL': 'http://localhost:4566'
})
@patch('lambda_function.s3')
@patch('lambda_function.table')
def test_lambda_handler_different_event_types(mock_table, mock_s3, context):
    mock_table.put_item.return_value = {}
    mock_s3.put_object.return_value = {}

    event_configs = {
        'page_view': {
            'page': 'cart',
            'cart_value': 100.0,
            'product_count': 1,
            'product_quantities': {'prod_001': 1},
            'shipping_option_selected': 'standard',
            'mouse_click_count': 5
        },
        'add_to_cart': {
            'product_id': 'prod_002',
            'category': 'perifericos',
            'price': 85.0,
            'cart_value': 185.0,
            'product_count': 2,
            'product_quantities': {'prod_001': 1, 'prod_002': 1},
            'shipping_option_selected': 'standard',
            'mouse_click_count': 8
        },
        'remove_from_cart': {
            'cart_value': 100.0,
            'product_count': 1,
            'product_quantities': {'prod_001': 1},
            'shipping_option_selected': 'standard',
            'mouse_click_count': 5
        },
        'start_checkout': {
            'cart_value': 100.0,
            'product_count': 1,
            'product_quantities': {'prod_001': 1},
            'shipping_option_selected': 'standard',
            'mouse_click_count': 12
        },
        'purchase': {
            'cart_value': 100.0,
            'product_count': 1,
            'product_quantities': {'prod_001': 1},
            'shipping_option_selected': 'standard',
            'mouse_click_count': 15,
            'payment_method': 'credit_card'
        },
        'abandon': {
            'cart_value': 100.0,
            'product_count': 1,
            'product_quantities': {'prod_001': 1},
            'shipping_option_selected': 'standard',
            'mouse_click_count': 8,
            'abandon_reason': 'Costo de envio muy alto'
        },
        'view_product': {
            'product_id': 'prod_002',
            'category': 'perifericos',
            'price': 85.0
        }
    }

    for event_type, extra_fields in event_configs.items():
        event = {
            'body': json.dumps({
                'event_type': event_type,
                'session_id': 'test-session',
                'user_id': 'test-user',
                'timestamp': '2026-07-24T18:30:00.000Z',
                **extra_fields
            })
        }
        response = lambda_handler(event, context)
        assert response['statusCode'] == 200


@patch.dict(os.environ, {
    'S3_BUCKET': 'test-bucket',
    'DYNAMODB_TABLE': 'test-table',
    'AWS_ENDPOINT_URL': 'http://localhost:4566'
})
@patch('lambda_function.s3')
@patch('lambda_function.table')
def test_lambda_handler_s3_key_format(mock_table, mock_s3, lambda_event, context):
    mock_table.put_item.return_value = {}
    mock_s3.put_object.return_value = {}

    lambda_handler(lambda_event, context)

    call_args_list = mock_s3.put_object.call_args_list
    raw_call = call_args_list[0]
    enriched_call = call_args_list[1]
    raw_key = raw_call[1]['Key']
    enriched_key = enriched_call[1]['Key']
    assert raw_key.startswith('raw/')
    assert '.json' in raw_key
    assert enriched_key.startswith('enriched/')
    assert '.json' in enriched_key


@patch.dict(os.environ, {
    'S3_BUCKET': 'test-bucket',
    'DYNAMODB_TABLE': 'test-table',
    'AWS_ENDPOINT_URL': 'http://localhost:4566'
})
@patch('lambda_function.s3')
@patch('lambda_function.table')
def test_lambda_handler_dynamodb_item_structure(mock_table, mock_s3, lambda_event, context):
    mock_table.put_item.return_value = {}
    mock_s3.put_object.return_value = {}

    lambda_handler(lambda_event, context)

    call_args = mock_table.put_item.call_args
    item = call_args[1]['Item']

    assert item['session_id'] == 'test-session-123'
    assert item['user_id'] == 'test-user-456'
    assert 'ttl' in item
    assert item['event_type'] == 'heartbeat'
    assert item['cart_value'] == 1200.50
    assert item['product_count'] == 2
    assert item['product_quantities'] == {'prod_001': 1, 'prod_003': 1}
    assert item['shipping_option_selected'] == 'standard'
    assert item['mouse_click_count'] == 15
    assert item['mouse_x'] == 320
    assert item['mouse_y'] == 180
    assert item['page'] == 'cart'
    assert item['s3_key'] is not None


@patch.dict(os.environ, {
    'S3_BUCKET': 'test-bucket',
    'DYNAMODB_TABLE': 'test-table',
    'AWS_ENDPOINT_URL': 'http://localhost:4566'
})
@patch('lambda_function.s3')
@patch('lambda_function.table')
def test_lambda_handler_response_structure(mock_table, mock_s3, lambda_event, context):
    mock_table.put_item.return_value = {}
    mock_s3.put_object.return_value = {}

    response = lambda_handler(lambda_event, context)

    assert response['statusCode'] == 200
    assert 'Content-Type' in response['headers']
    assert response['headers']['Content-Type'] == 'application/json'

    body = json.loads(response['body'])
    assert 'abandon_probability' in body
    assert 'trigger_retention' in body
    assert isinstance(body['trigger_retention'], bool)
    assert isinstance(body['abandon_probability'], float)