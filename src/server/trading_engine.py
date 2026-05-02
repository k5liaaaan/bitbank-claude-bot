from datetime import datetime, timezone
from typing import Optional

from bitbank_client import bitbank_client
from claude_client import claude_client
from config import config
from database import (
    get_recent_trades,
    get_setting,
    purge_old_data,
    save_asset_snapshot,
    save_log,
    save_trade,
)
from models import AssetSnapshot, TradeRecord
from redis_client import get_price, publish, set_price


class TradingEngine:
    def __init__(self):
        self.is_running = False
        self.last_signal_at: Optional[str] = None
        self.next_signal_at: Optional[str] = None
        self.last_action: Optional[str] = None
        self.last_reason: Optional[str] = None

    async def update_price(self):
        try:
            ticker = await bitbank_client.get_ticker()
            price_data = {
                "pair": "btc_jpy",
                "last": ticker.get("last", "0"),
                "buy": ticker.get("buy", "0"),
                "sell": ticker.get("sell", "0"),
                "high": ticker.get("high", "0"),
                "low": ticker.get("low", "0"),
                "vol": ticker.get("vol", "0"),
                "timestamp": ticker.get("timestamp", 0),
            }
            await set_price(price_data)
            await publish("price", price_data)
        except Exception as e:
            await self._log("WARNING", f"価格取得失敗: {e}")

    async def run_trading_cycle(self):
        if not self.is_running:
            return

        now = datetime.now(timezone.utc).isoformat()
        self.last_signal_at = now
        await self._log("INFO", "取引サイクル開始")

        try:
            price_data = await get_price()
            if not price_data:
                await self._log("WARNING", "価格データなし。サイクルをスキップ")
                return

            current_price = float(price_data.get("last", 0))
            if current_price <= 0:
                await self._log("WARNING", "無効な価格データ")
                return

            is_dry_run = (await get_setting("dry_run", "true")).lower() == "true"

            btc_balance = 0.0
            jpy_balance = 100000.0  # dry run default

            if not is_dry_run:
                try:
                    balance = await bitbank_client.get_balance()
                    btc_balance = balance.get("btc", {}).get("free", 0.0)
                    jpy_balance = balance.get("jpy", {}).get("free", 0.0)
                except Exception as e:
                    await self._log("ERROR", f"残高取得失敗: {e}")
                    return

            total_jpy = jpy_balance + btc_balance * current_price

            snapshot = AssetSnapshot(
                timestamp=now,
                btc_balance=btc_balance,
                jpy_balance=jpy_balance,
                btc_price=current_price,
                total_jpy=total_jpy,
            )
            await save_asset_snapshot(snapshot)

            # グローバルストップチェック
            if (await get_setting("global_stop_enabled", "true")).lower() == "true":
                base = float(await get_setting("global_stop_base_asset_jpy", "100000"))
                stop_pct = float(await get_setting("global_stop_loss_pct", "20"))
                threshold = base * (1 - stop_pct / 100)
                if total_jpy <= threshold:
                    await self._log(
                        "WARNING",
                        f"グローバルストップ発動: 総資産 ¥{total_jpy:,.0f} <= 閾値 ¥{threshold:,.0f}",
                    )
                    await self._publish_status()
                    return

            # 取引ルール読み込み
            try:
                with open(config.CONFIG_PATH, "r", encoding="utf-8") as f:
                    rules_content = f.read()
            except FileNotFoundError:
                rules_content = "取引ルールが設定されていません。慎重に判断してください。"

            recent_trades = await get_recent_trades(limit=5)
            trades_summary = self._format_trades(recent_trades)

            market_context = (
                f"現在のBTC/JPY価格: ¥{current_price:,.0f}\n"
                f"高値(24h): ¥{float(price_data.get('high', 0)):,.0f}\n"
                f"安値(24h): ¥{float(price_data.get('low', 0)):,.0f}\n"
                f"出来高(24h): {float(price_data.get('vol', 0)):.4f} BTC\n\n"
                f"残高:\n"
                f"- BTC: {btc_balance:.8f} BTC\n"
                f"- JPY: ¥{jpy_balance:,.0f}\n"
                f"- 総資産(JPY換算): ¥{total_jpy:,.0f}\n\n"
                f"直近の取引履歴:\n{trades_summary}\n\n"
                f"現在時刻: {datetime.now().strftime('%Y-%m-%d %H:%M')} JST"
            )

            await self._log("INFO", "Claude APIに問い合わせ中...")
            signal = await claude_client.get_signal(rules_content, market_context)
            action = signal.get("action", "hold")
            reason = signal.get("reason", "")

            self.last_action = action
            self.last_reason = reason
            await self._log("INFO", f"Claudeシグナル: {action.upper()} - {reason}")

            order_id = None
            if action in ("buy", "sell") and not is_dry_run:
                order_id = await self._execute_order(
                    action, current_price, jpy_balance, btc_balance
                )

            if action in ("buy", "sell"):
                order_amount_jpy = float(await get_setting("order_amount_jpy", "10000"))
                amount_btc = order_amount_jpy / current_price

                trade = TradeRecord(
                    timestamp=now,
                    action=action,
                    price=current_price,
                    amount_btc=amount_btc,
                    amount_jpy=order_amount_jpy,
                    reason=reason,
                    is_dry_run=is_dry_run,
                    order_id=order_id,
                )
                await save_trade(trade)
                await publish(
                    "bot",
                    {
                        "event": "trade",
                        "action": action,
                        "price": current_price,
                        "amount_jpy": order_amount_jpy,
                        "is_dry_run": is_dry_run,
                        "reason": reason,
                    },
                )

            retention_days = int(await get_setting("log_retention_days", "365"))
            await purge_old_data(retention_days)
            await self._log("INFO", f"取引サイクル完了: {action.upper()}")

        except Exception as e:
            await self._log("ERROR", f"取引サイクルエラー: {e}")
        finally:
            await self._publish_status()

    async def _execute_order(
        self, side: str, price: float, jpy_balance: float, btc_balance: float
    ) -> Optional[str]:
        try:
            order_amount_jpy = float(await get_setting("order_amount_jpy", "10000"))
            if side == "buy":
                if jpy_balance < order_amount_jpy:
                    await self._log("WARNING", f"残高不足: ¥{jpy_balance:,.0f}")
                    return None
                amount_btc = order_amount_jpy / price
            else:
                amount_btc = min(btc_balance, order_amount_jpy / price)
                if amount_btc <= 0:
                    await self._log("WARNING", "売却するBTCがありません")
                    return None

            order_id = await bitbank_client.place_order(side, price, round(amount_btc, 8))
            await self._log(
                "INFO",
                f"注文実行: {side.upper()} {amount_btc:.8f} BTC @ ¥{price:,.0f}",
            )
            return order_id
        except Exception as e:
            await self._log("ERROR", f"注文失敗: {e}")
            return None

    def _format_trades(self, trades: list) -> str:
        if not trades:
            return "取引履歴なし"
        lines = []
        for t in trades:
            flag = "[DRY]" if t.get("is_dry_run") else ""
            lines.append(
                f"- {t['timestamp'][:16]}: {t['action'].upper()} "
                f"¥{t['amount_jpy']:,.0f} @ ¥{t['price']:,.0f} {flag}"
            )
        return "\n".join(lines)

    async def _log(self, level: str, message: str):
        await save_log(level, message)
        ts = datetime.now(timezone.utc).isoformat()
        await publish("logs", {"timestamp": ts, "level": level, "message": message})

    async def _publish_status(self):
        await publish(
            "bot",
            {
                "event": "status",
                "is_running": self.is_running,
                "last_action": self.last_action,
                "last_reason": self.last_reason,
                "last_signal_at": self.last_signal_at,
            },
        )

    async def start(self):
        self.is_running = True
        await self._log("INFO", "自動取引ボット開始")
        await self._publish_status()

    async def stop(self):
        self.is_running = False
        await self._log("INFO", "自動取引ボット停止")
        await self._publish_status()


trading_engine = TradingEngine()
