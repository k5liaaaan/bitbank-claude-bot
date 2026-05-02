import os

from fastapi import APIRouter

from config import config
from database import get_all_settings, get_setting, set_setting
from models import RulesUpdate, SettingsUpdate

router = APIRouter()


@router.get("/settings")
async def get_settings():
    settings = await get_all_settings()
    # APIキーはマスク表示
    for key in ("bitbank_api_key", "bitbank_api_secret", "anthropic_api_key"):
        val = settings.get(key, "")
        if val:
            settings[key] = "••••" + val[-4:]
    return settings


@router.put("/settings")
async def update_settings(data: SettingsUpdate):
    mapping = {
        "bitbank_api_key": data.bitbank_api_key,
        "bitbank_api_secret": data.bitbank_api_secret,
        "anthropic_api_key": data.anthropic_api_key,
        "polling_interval_minutes": (
            str(data.polling_interval_minutes)
            if data.polling_interval_minutes is not None
            else None
        ),
        "log_retention_days": (
            str(data.log_retention_days) if data.log_retention_days is not None else None
        ),
        "global_stop_base_asset_jpy": (
            str(data.global_stop_base_asset_jpy)
            if data.global_stop_base_asset_jpy is not None
            else None
        ),
        "global_stop_loss_pct": (
            str(data.global_stop_loss_pct)
            if data.global_stop_loss_pct is not None
            else None
        ),
        "order_amount_jpy": (
            str(data.order_amount_jpy) if data.order_amount_jpy is not None else None
        ),
    }
    if data.dry_run is not None:
        mapping["dry_run"] = "true" if data.dry_run else "false"
    if data.global_stop_enabled is not None:
        mapping["global_stop_enabled"] = "true" if data.global_stop_enabled else "false"

    for key, value in mapping.items():
        if value is not None:
            await set_setting(key, value)

    return {"message": "設定を保存しました"}


@router.get("/rules")
async def get_rules():
    try:
        with open(config.CONFIG_PATH, "r", encoding="utf-8") as f:
            return {"content": f.read()}
    except FileNotFoundError:
        return {"content": ""}


@router.put("/rules")
async def update_rules(data: RulesUpdate):
    try:
        os.makedirs(os.path.dirname(config.CONFIG_PATH), exist_ok=True)
        with open(config.CONFIG_PATH, "w", encoding="utf-8") as f:
            f.write(data.content)
        return {"message": "取引ルールを保存しました"}
    except Exception as e:
        return {"error": str(e)}
