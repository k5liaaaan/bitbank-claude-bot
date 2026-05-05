from pydantic import BaseModel
from typing import Optional


class TradeRecord(BaseModel):
    id: Optional[int] = None
    timestamp: str
    action: str  # "buy", "sell", "hold"
    price: float
    amount_btc: float
    amount_jpy: float
    reason: str = ""
    is_dry_run: bool = True
    order_id: Optional[str] = None


class AssetSnapshot(BaseModel):
    id: Optional[int] = None
    timestamp: str
    btc_balance: float
    jpy_balance: float
    btc_price: float
    total_jpy: float


class LogEntry(BaseModel):
    id: Optional[int] = None
    timestamp: str
    level: str
    message: str


class SettingsUpdate(BaseModel):
    bitbank_api_key: Optional[str] = None
    bitbank_api_secret: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    dry_run: Optional[bool] = None
    polling_interval_minutes: Optional[int] = None
    log_retention_days: Optional[int] = None
    global_stop_enabled: Optional[bool] = None
    global_stop_base_asset_jpy: Optional[float] = None
    global_stop_loss_pct: Optional[float] = None
    order_amount_jpy: Optional[float] = None
    trading_mode: Optional[str] = None  # "manual" or "api"
    slack_bot_token: Optional[str] = None
    slack_app_token: Optional[str] = None
    slack_channel: Optional[str] = None


class RulesUpdate(BaseModel):
    content: str
