import os
import logging

from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager

from schema import PredictRequest, PredictResponse, HealthResponse
from model_loader import load_model, get_model_artifact
from inference import run_inference

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_S3_KEY = os.environ.get('MODEL_S3_KEY', 'models/modelo_propension.pkl')


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info('Loading model from S3')
    try:
        load_model()
        logger.info('Model loaded successfully')
    except Exception as e:
        logger.error('Model loading failed: %s', e)
        raise
    yield


app = FastAPI(
    title='Clickstream Inference Service',
    version='1.0.0',
    lifespan=lifespan,
)


@app.get('/health', response_model=HealthResponse)
def health():
    try:
        artifact = get_model_artifact()
        loaded = True
    except RuntimeError:
        loaded = False
    return HealthResponse(
        status='healthy' if loaded else 'degraded',
        model_loaded=loaded,
        model_key=MODEL_S3_KEY,
        device='cpu',
    )


@app.post('/predict', response_model=PredictResponse)
def predict(request: PredictRequest):
    try:
        artifact = get_model_artifact()
    except RuntimeError:
        raise HTTPException(status_code=503, detail='Model not loaded')

    payload = request.model_dump()
    payload['device'] = 'desktop'

    try:
        result = run_inference(
            payload,
            artifact['model'],
            artifact['scaler'],
            artifact['encoders'],
            artifact['feature_cols'],
        )
        return PredictResponse(**result)
    except Exception as e:
        logger.error('Inference error: %s', e)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == '__main__':
    import uvicorn
    port = int(os.environ.get('PORT', '8080'))
    uvicorn.run('main:app', host='0.0.0.0', port=port, log_level='info')
