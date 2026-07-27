import os
import tempfile
import joblib
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

S3_BUCKET = os.environ.get('S3_BUCKET', 'clickstream-bucket')
MODEL_S3_KEY = os.environ.get('MODEL_S3_KEY', 'models/modelo_propension.pkl')
AWS_ENDPOINT_URL = os.environ.get('AWS_ENDPOINT_URL')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')

_model_artifact = None


def get_boto_config():
    kwargs = {
        'region_name': AWS_REGION,
        'retries': {'max_attempts': 3, 'mode': 'standard'},
    }
    if AWS_ENDPOINT_URL:
        kwargs['s3'] = {'addressing_style': 'path'}
    return Config(**kwargs)


def download_model_from_s3():
    s3 = boto3.client(
        's3',
        endpoint_url=AWS_ENDPOINT_URL,
        config=get_boto_config()
    )
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.pkl')
    try:
        s3.download_file(Bucket=S3_BUCKET, Key=MODEL_S3_KEY, Filename=tmp.name)
        artifact = joblib.load(tmp.name)
        return artifact
    except ClientError as e:
        raise RuntimeError(
            f'Failed to download s3://{S3_BUCKET}/{MODEL_S3_KEY}: {e}'
        )
    finally:
        tmp.close()
        os.unlink(tmp.name)


def load_model():
    global _model_artifact
    if _model_artifact is not None:
        return _model_artifact
    _model_artifact = download_model_from_s3()
    return _model_artifact


def get_model_artifact():
    if _model_artifact is None:
        raise RuntimeError('Model not loaded. Call load_model() first.')
    return _model_artifact
