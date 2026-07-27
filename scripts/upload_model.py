import os
import sys
import pathlib
import boto3
from botocore.config import Config

MODEL_LOCAL_PATH = pathlib.Path('data/models/modelo_propension.pkl')
S3_BUCKET = os.environ.get('S3_BUCKET', 'clickstream-bucket')
S3_KEY = os.environ.get('MODEL_S3_KEY', 'models/modelo_propension.pkl')
AWS_ENDPOINT_URL = os.environ.get('AWS_ENDPOINT_URL', 'http://localhost:4566')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
MODEL_S3_PATH = f's3://{S3_BUCKET}/{S3_KEY}'


def upload_model():
    if not MODEL_LOCAL_PATH.exists():
        print(f'Model not found at {MODEL_LOCAL_PATH}', file=sys.stderr)
        sys.exit(1)

    config = Config(region_name=AWS_REGION, s3={'addressing_style': 'path'})
    s3 = boto3.client('s3', endpoint_url=AWS_ENDPOINT_URL, config=config)

    try:
        s3.head_bucket(Bucket=S3_BUCKET)
    except Exception:
        s3.create_bucket(Bucket=S3_BUCKET)

    s3.upload_file(str(MODEL_LOCAL_PATH), S3_BUCKET, S3_KEY)

    print(f'MODEL_S3_PATH={MODEL_S3_PATH}')


if __name__ == '__main__':
    upload_model()
