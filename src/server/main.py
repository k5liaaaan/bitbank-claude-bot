import asyncio
import os
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from config import config
from database import get_setting, init_db, set_setting
from routers import assets, balance, bot, logs, price, trades, ws
from routers import settings as settings_api
from slack_client import slack_client
from trading_engine import trading_engine
from websocket_manager import ws_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await _init_settings_from_env()

    polling_minutes = int(await get_setting("polling_interval_minutes", "15"))

    scheduler = AsyncIOScheduler(timezone="Asia/Tokyo")
    scheduler.add_job(trading_engine.update_price, "interval", seconds=30, id="price_poll")
    scheduler.add_job(
        trading_engine.run_trading_cycle,
        "interval",
        minutes=polling_minutes,
        id="trading_cycle",
    )
    # 毎朝8時（JST）に強制実行 — Slack通知を含む
    scheduler.add_job(
        trading_engine.run_trading_cycle,
        "cron",
        hour=8,
        minute=0,
        timezone="Asia/Tokyo",
        id="daily_slack",
        kwargs={"force": True},
    )
    scheduler.start()

    asyncio.create_task(ws_manager.start_redis_listener())
    asyncio.create_task(trading_engine.update_price())

    # Slack Bot起動（トークンが設定されている場合のみ）
    slack_bot_token = await get_setting("slack_bot_token", "")
    slack_app_token = await get_setting("slack_app_token", "")
    slack_channel = await get_setting("slack_channel", "")
    if slack_bot_token and slack_app_token and slack_channel:
        asyncio.create_task(slack_client.start(
            slack_bot_token, slack_app_token, slack_channel,
            on_decision=trading_engine.execute_manual_decision,
        ))

    yield

    scheduler.shutdown()


async def _init_settings_from_env():
    defaults = {
        "bitbank_api_key": config.BITBANK_API_KEY,
        "bitbank_api_secret": config.BITBANK_API_SECRET,
        "anthropic_api_key": config.ANTHROPIC_API_KEY,
        "dry_run": "true" if config.DRY_RUN else "false",
        "polling_interval_minutes": str(config.POLLING_INTERVAL_MINUTES),
        "log_retention_days": str(config.LOG_RETENTION_DAYS),
        "global_stop_enabled": "true",
        "global_stop_base_asset_jpy": "100000",
        "global_stop_loss_pct": "20",
        "order_amount_jpy": "10000",
    }
    for key, value in defaults.items():
        if value and not await get_setting(key):
            await set_setting(key, value)


app = FastAPI(title="BTC Auto Trader", lifespan=lifespan)

app.include_router(price.router, prefix="/api")
app.include_router(balance.router, prefix="/api")
app.include_router(trades.router, prefix="/api")
app.include_router(bot.router, prefix="/api")
app.include_router(assets.router, prefix="/api")
app.include_router(settings_api.router, prefix="/api")
app.include_router(logs.router, prefix="/api")
app.include_router(ws.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


web_path = config.WEB_PATH
if os.path.exists(web_path):
    app.mount("/static", StaticFiles(directory=web_path), name="static")

    @app.get("/")
    async def dashboard():
        return FileResponse(f"{web_path}/index.html")

    @app.get("/trades")
    async def trades_page():
        return FileResponse(f"{web_path}/trades.html")

    @app.get("/logs")
    async def logs_page():
        return FileResponse(f"{web_path}/logs.html")

    @app.get("/settings")
    async def settings_page():
        return FileResponse(f"{web_path}/settings.html")
