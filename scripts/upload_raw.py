import os
import sys
import pathlib
import boto3
from boto3.s3.transfer import TransferConfig
from botocore.config import Config

RAW_LOCAL_PATH = pathlib.Path('data/raw/all_events.ndjson')
S3_BUCKET = os.environ.get('S3_BUCKET', 'clickstream-bucket')
S3_KEY = os.environ.get('RAW_S3_KEY', 'raw/all_events.ndjson')
AWS_ENDPOINT_URL = os.environ.get('AWS_ENDPOINT_URL', 'http://localhost:4566')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')

SINGLE_PART_THRESHOLD = 1024 * 1024 * 1024


def upload_raw():
    if not RAW_LOCAL_PATH.exists():
        print(f'Raw data not found at {RAW_LOCAL_PATH} — skipping upload', file=sys.stderr)
        return

    config = Config(region_name=AWS_REGION, s3={'addressing_style': 'path'})
    s3 = boto3.client('s3', endpoint_url=AWS_ENDPOINT_URL, config=config)
    transfer_config = TransferConfig(multipart_threshold=SINGLE_PART_THRESHOLD)

    try:
        s3.head_bucket(Bucket=S3_BUCKET)
    except Exception:
        s3.create_bucket(Bucket=S3_BUCKET)

    try:
        s3.upload_file(str(RAW_LOCAL_PATH), S3_BUCKET, S3_KEY, Config=transfer_config)
        print(f's3://{S3_BUCKET}/{S3_KEY}')
    except Exception as e:
        print(f'WARN: upload_raw falló ({e}) — el pipeline continúa sin raw data en S3', file=sys.stderr)


if __name__ == '__main__':
    upload_raw()
