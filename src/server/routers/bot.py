from fastapi import APIRouter

from database import get_setting
from trading_engine import trading_engine

router = APIRouter()


@router.get("/bot/status")
async def get_bot_status():
    is_dry_run = (await get_setting("dry_run", "true")).lower() == "true"
    return {
        "is_running": trading_engine.is_running,
        "is_dry_run": is_dry_run,
        "last_signal_at": trading_engine.last_signal_at,
        "next_signal_at": trading_engine.next_signal_at,
        "last_action": trading_engine.last_action,
        "last_reason": trading_engine.last_reason,
    }


@router.post("/bot/start")
async def start_bot():
    await trading_engine.start()
    return {"message": "ボットを開始しました"}


@router.post("/bot/stop")
async def stop_bot():
    await trading_engine.stop()
    return {"message": "ボットを停止しました"}
