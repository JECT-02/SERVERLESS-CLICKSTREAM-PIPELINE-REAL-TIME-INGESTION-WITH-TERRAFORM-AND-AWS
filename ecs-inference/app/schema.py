from pydantic import BaseModel, Field
from typing import Dict, Any, Optional


class WindowFeatures(BaseModel):
    velocity_avg: float = 0.0
    velocity_max: float = 0.0
    velocity_std: float = 0.0
    total_clicks: int = 0
    idle_ratio: float = 0.0
    heartbeat_count: int = 0


class PredictRequest(BaseModel):
    session_id: str
    user_id: str
    cart_value: float = 0.0
    product_count: int = 0
    product_quantities: Dict[str, int] = {}
    shipping_option_selected: str = 'standard'
    delivery_mode: str = 'shipping'
    shipping_type: str = 'standard'
    shipping_cost: float = 0.0
    mouse_click_count: int = 0
    page: str = 'cart'
    velocity_avg: float = 0.0
    velocity_max: float = 0.0
    velocity_std: float = 0.0
    acceleration_avg: float = 0.0
    acceleration_max: float = 0.0
    idle_seconds: float = 0.0
    distance_total: float = 0.0
    velocity_trend: str = 'stable'
    exit_intent_count: int = 0
    dwell_seconds: float = 0.0
    dwell_segments: int = 0
    click_frequency: float = 0.0
    cart_delta: float = 0.0
    shipping_switches: int = 0
    page_regression_count: int = 0
    payment_hesitation_seconds: float = 0.0
    payment_method_switches: int = 0
    window_5s: Optional[WindowFeatures] = None
    window_10s: Optional[WindowFeatures] = None
    window_30s: Optional[WindowFeatures] = None


class PredictResponse(BaseModel):
    abandon_probability: float
    trigger_retention: bool
    retention_type: Optional[str] = None


class HealthResponse(BaseModel):
    status: str = 'healthy'
    model_loaded: bool = False
    model_key: str = ''
    device: str = ''


class ErrorResponse(BaseModel):
    error: str
