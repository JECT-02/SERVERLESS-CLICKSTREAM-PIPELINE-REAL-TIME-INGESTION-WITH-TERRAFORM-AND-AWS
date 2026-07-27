import json
import os
from pathlib import Path
import boto3
from botocore.config import Config

S3_BUCKET = os.environ.get('S3_BUCKET', 'clickstream-bucket')
AWS_ENDPOINT_URL = os.environ.get('AWS_ENDPOINT_URL', 'http://localhost:4566')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
RAW_DIR = Path('data/raw')

config = Config(region_name=AWS_REGION, s3={'addressing_style': 'path'})


def download_from_s3() -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    output_path = RAW_DIR / 'all_events.ndjson'

    try:
        s3 = boto3.client('s3', endpoint_url=AWS_ENDPOINT_URL, config=config)
        s3.head_bucket(Bucket=S3_BUCKET)
    except Exception:
        local_path = Path('data/raw/all_events.ndjson')
        if local_path.exists():
            return local_path
        raise RuntimeError(
            f'Cannot connect to S3 at {AWS_ENDPOINT_URL} and no local fallback found'
        )

    try:
        ndjson_obj = s3.get_object(Bucket=S3_BUCKET, Key='raw/all_events.ndjson')
        raw_bytes = ndjson_obj['Body'].read()
        output_path.write_bytes(raw_bytes)
        return output_path
    except Exception:
        pass

    paginator = s3.get_paginator('list_objects_v2')
    event_count = 0

    with open(output_path, 'w', encoding='utf-8') as out:
        for page in paginator.paginate(Bucket=S3_BUCKET, Prefix='raw/'):
            for obj in page.get('Contents', []):
                key = obj['Key']
                if not key.endswith('.json'):
                    continue
                response = s3.get_object(Bucket=S3_BUCKET, Key=key)
                event = json.loads(response['Body'].read().decode('utf-8'))
                out.write(json.dumps(event, ensure_ascii=False) + '\n')
                event_count += 1

    return output_path


if __name__ == '__main__':
    download_from_s3()
