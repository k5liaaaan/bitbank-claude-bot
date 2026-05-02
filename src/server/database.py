import aiosqlite
import os
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional

from config import config

DB_PATH = config.DB_PATH


async def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                action TEXT NOT NULL,
                price REAL NOT NULL,
                amount_btc REAL NOT NULL,
                amount_jpy REAL NOT NULL,
                reason TEXT DEFAULT '',
                is_dry_run INTEGER NOT NULL DEFAULT 1,
                order_id TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS asset_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                btc_balance REAL NOT NULL,
                jpy_balance REAL NOT NULL,
                btc_price REAL NOT NULL,
                total_jpy REAL NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bot_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                level TEXT NOT NULL DEFAULT 'INFO',
                message TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        await db.commit()


async def get_setting(key: str, default: str = "") -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT value FROM app_settings WHERE key = ?", (key,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else default


async def set_setting(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)",
            (key, value),
        )
        await db.commit()


async def get_all_settings() -> Dict[str, str]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT key, value FROM app_settings") as cursor:
            rows = await cursor.fetchall()
            return {row[0]: row[1] for row in rows}


async def save_trade(trade) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO trades
               (timestamp, action, price, amount_btc, amount_jpy, reason, is_dry_run, order_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                trade.timestamp,
                trade.action,
                trade.price,
                trade.amount_btc,
                trade.amount_jpy,
                trade.reason,
                1 if trade.is_dry_run else 0,
                trade.order_id,
            ),
        )
        await db.commit()
        return cursor.lastrowid


async def get_trades(limit: int = 100, offset: int = 0) -> List[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM trades ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_recent_trades(limit: int = 10) -> List[Dict]:
    return await get_trades(limit=limit)


async def save_asset_snapshot(snapshot):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO asset_snapshots
               (timestamp, btc_balance, jpy_balance, btc_price, total_jpy)
               VALUES (?, ?, ?, ?, ?)""",
            (
                snapshot.timestamp,
                snapshot.btc_balance,
                snapshot.jpy_balance,
                snapshot.btc_price,
                snapshot.total_jpy,
            ),
        )
        await db.commit()


async def get_asset_history(days: int = 30) -> List[Dict]:
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM asset_snapshots WHERE timestamp >= ? ORDER BY timestamp ASC",
            (since,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def save_log(level: str, message: str):
    timestamp = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO bot_logs (timestamp, level, message) VALUES (?, ?, ?)",
            (timestamp, level, message),
        )
        await db.commit()


async def get_logs(limit: int = 100) -> List[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM bot_logs ORDER BY timestamp DESC LIMIT ?", (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def purge_old_data(retention_days: int = 365):
    cutoff = (datetime.now(timezone.utc) - timedelta(days=retention_days)).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM trades WHERE timestamp < ?", (cutoff,))
        await db.execute("DELETE FROM asset_snapshots WHERE timestamp < ?", (cutoff,))
        await db.execute("DELETE FROM bot_logs WHERE timestamp < ?", (cutoff,))
        await db.commit()
