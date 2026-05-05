import asyncio

from fastapi import APIRouter
from pydantic import BaseModel

from database import get_setting
from trading_engine import trading_engine

router = APIRouter()


class DecisionInput(BaseModel):
    action: str  # "buy", "sell", "hold"
    reason: str = ""


@router.get("/bot/status")
async def get_bot_status():
    is_dry_run = (await get_setting("dry_run", "true")).lower() == "true"
    mode = await get_setting("trading_mode", "manual")
    return {
        "is_running": trading_engine.is_running,
        "is_dry_run": is_dry_run,
        "trading_mode": mode,
        "last_signal_at": trading_engine.last_signal_at,
        "last_action": trading_engine.last_action,
        "last_reason": trading_engine.last_reason,
        "has_pending": trading_engine.pending_prompt is not None,
        "pending_prompt": trading_engine.pending_prompt,
        "pending_price": trading_engine.pending_price,
        "pending_timestamp": trading_engine.pending_timestamp,
    }


@router.post("/bot/start")
async def start_bot():
    await trading_engine.start()
    return {"message": "started"}


@router.post("/bot/stop")
async def stop_bot():
    await trading_engine.stop()
    return {"message": "stopped"}


@router.post("/bot/trigger")
async def trigger_cycle():
    asyncio.create_task(trading_engine.run_trading_cycle(force=True))
    return {"message": "triggered"}


@router.post("/bot/decision")
async def submit_decision(data: DecisionInput):
    if data.action not in ("buy", "sell", "hold"):
        return {"error": "action must be buy, sell, or hold"}
    await trading_engine.execute_manual_decision(data.action, data.reason)
    return {"message": "ok"}
