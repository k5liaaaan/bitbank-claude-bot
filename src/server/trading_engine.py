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
        self.last_action: Optional[str] = None
        self.last_reason: Optional[str] = None
        # 手動確認モード用
        self.pending_prompt: Optional[str] = None
        self.pending_price: Optional[float] = None
        self.pending_timestamp: Optional[str] = None

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

    async def run_trading_cycle(self, force: bool = False):
        if not self.is_running and not force:
            return

        now = datetime.now(timezone.utc).isoformat()
        self.last_signal_at = now
        await self._log("INFO", "取引サイクル開始")

        try:
            # 共通: 価格・残高・資産スナップショット取得
            market = await self._collect_market_data(now)
            if market is None:
                return

            price_data, current_price, btc_balance, jpy_balance, total_jpy, is_dry_run = market

            # グローバルストップチェック
            if await self._check_global_stop(total_jpy):
                return

            rules_content = self._load_rules()
            recent_trades = await get_recent_trades(limit=5)
            trades_summary = self._format_trades(recent_trades)

            mode = await get_setting("trading_mode", "manual")

            if mode == "api":
                await self._run_api_cycle(
                    now, price_data, current_price, btc_balance, jpy_balance,
                    total_jpy, is_dry_run, rules_content, trades_summary
                )
            else:
                await self._run_manual_cycle(
                    now, price_data, current_price, btc_balance, jpy_balance,
                    total_jpy, is_dry_run, rules_content, trades_summary
                )

            retention_days = int(await get_setting("log_retention_days", "365"))
            await purge_old_data(retention_days)

        except Exception as e:
            await self._log("ERROR", f"取引サイクルエラー: {e}")
        finally:
            await self._publish_status()

    async def _run_api_cycle(
        self, now, price_data, current_price, btc_balance, jpy_balance,
        total_jpy, is_dry_run, rules_content, trades_summary
    ):
        market_context = self._build_market_context(
            price_data, current_price, btc_balance, jpy_balance, total_jpy, trades_summary
        )
        await self._log("INFO", "Claude APIに問い合わせ中...")
        signal = await claude_client.get_signal(rules_content, market_context)
        action = signal.get("action", "hold")
        reason = signal.get("reason", "")
        await self._log("INFO", f"Claudeシグナル: {action.upper()} - {reason}")
        await self._record_and_execute(now, action, reason, current_price, jpy_balance, btc_balance, is_dry_run)

    async def _run_manual_cycle(
        self, now, price_data, current_price, btc_balance, jpy_balance,
        total_jpy, is_dry_run, rules_content, trades_summary
    ):
        prompt = self._build_prompt(
            rules_content, price_data, current_price, btc_balance, jpy_balance, total_jpy, trades_summary
        )
        self.pending_prompt = prompt
        self.pending_price = current_price
        self.pending_timestamp = now

        await self._log("INFO", f"判断待ち: ブラウザで確認してください (BTC ¥{current_price:,.0f})")
        await publish("bot", {
            "event": "prompt_ready",
            "prompt": prompt,
            "price": current_price,
            "timestamp": now,
        })

        from slack_client import slack_client
        if slack_client.is_connected:
            sent = await slack_client.send_decision_message(
                price=current_price,
                jpy=jpy_balance,
                btc=btc_balance,
                total=total_jpy,
                high=float(price_data.get("high", 0)),
                low=float(price_data.get("low", 0)),
                vol=float(price_data.get("vol", 0)),
                trades_summary=trades_summary,
            )
            if sent:
                await self._log("INFO", "Slackに取引判断を送信しました")

    async def execute_manual_decision(self, action: str, reason: str):
        """ユーザーがブラウザで入力した判断を実行する"""
        now = datetime.now(timezone.utc).isoformat()
        price = self.pending_price or 0.0

        self.pending_prompt = None
        self.pending_timestamp = None

        is_dry_run = (await get_setting("dry_run", "true")).lower() == "true"

        if not is_dry_run:
            try:
                balance = await bitbank_client.get_balance()
                jpy_balance = balance.get("jpy", {}).get("free", 0.0)
                btc_balance = balance.get("btc", {}).get("free", 0.0)
            except Exception as e:
                await self._log("ERROR", f"残高取得失敗: {e}")
                jpy_balance, btc_balance = 0.0, 0.0
        else:
            jpy_balance, btc_balance = 100000.0, 0.0

        await self._log("INFO", f"手動決定: {action.upper()} - {reason}")
        await self._record_and_execute(now, action, reason, price, jpy_balance, btc_balance, is_dry_run)
        await self._publish_status()

    async def _record_and_execute(
        self, now, action, reason, current_price, jpy_balance, btc_balance, is_dry_run
    ):
        self.last_action = action
        self.last_reason = reason

        order_id = None
        if action in ("buy", "sell") and not is_dry_run:
            order_id = await self._execute_order(action, current_price, jpy_balance, btc_balance)

        order_amount_jpy = float(await get_setting("order_amount_jpy", "10000"))
        amount_btc = order_amount_jpy / current_price if action != "hold" and current_price > 0 else 0.0

        trade = TradeRecord(
            timestamp=now,
            action=action,
            price=current_price,
            amount_btc=amount_btc,
            amount_jpy=order_amount_jpy if action != "hold" else 0.0,
            reason=reason,
            is_dry_run=is_dry_run,
            order_id=order_id,
        )
        await save_trade(trade)
        await publish("bot", {
            "event": "trade",
            "action": action,
            "price": current_price,
            "amount_jpy": order_amount_jpy if action != "hold" else 0.0,
            "is_dry_run": is_dry_run,
            "reason": reason,
        })
        await self._log("INFO", f"取引サイクル完了: {action.upper()}")

    async def _collect_market_data(self, now):
        price_data = await get_price()
        if not price_data:
            await self._log("WARNING", "価格データなし。スキップ")
            return None

        current_price = float(price_data.get("last", 0))
        if current_price <= 0:
            await self._log("WARNING", "無効な価格データ")
            return None

        is_dry_run = (await get_setting("dry_run", "true")).lower() == "true"
        btc_balance, jpy_balance = 0.0, 100000.0

        if not is_dry_run:
            try:
                balance = await bitbank_client.get_balance()
                btc_balance = balance.get("btc", {}).get("free", 0.0)
                jpy_balance = balance.get("jpy", {}).get("free", 0.0)
            except Exception as e:
                await self._log("ERROR", f"残高取得失敗: {e}")
                return None

        total_jpy = jpy_balance + btc_balance * current_price
        snapshot = AssetSnapshot(
            timestamp=now,
            btc_balance=btc_balance,
            jpy_balance=jpy_balance,
            btc_price=current_price,
            total_jpy=total_jpy,
        )
        await save_asset_snapshot(snapshot)
        return price_data, current_price, btc_balance, jpy_balance, total_jpy, is_dry_run

    async def _check_global_stop(self, total_jpy: float) -> bool:
        if (await get_setting("global_stop_enabled", "true")).lower() != "true":
            return False
        base = float(await get_setting("global_stop_base_asset_jpy", "100000"))
        stop_pct = float(await get_setting("global_stop_loss_pct", "20"))
        threshold = base * (1 - stop_pct / 100)
        if total_jpy <= threshold:
            await self._log("WARNING", f"グローバルストップ発動: ¥{total_jpy:,.0f} <= ¥{threshold:,.0f}")
            return True
        return False

    def _load_rules(self) -> str:
        try:
            with open(config.CONFIG_PATH, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return "取引ルールが設定されていません。慎重に判断してください。"

    def _build_market_context(self, price_data, current_price, btc_balance, jpy_balance, total_jpy, trades_summary) -> str:
        return (
            f"現在のBTC/JPY価格: ¥{current_price:,.0f}\n"
            f"高値(24h): ¥{float(price_data.get('high', 0)):,.0f}\n"
            f"安値(24h): ¥{float(price_data.get('low', 0)):,.0f}\n"
            f"出来高(24h): {float(price_data.get('vol', 0)):.4f} BTC\n\n"
            f"残高:\n- BTC: {btc_balance:.8f} BTC\n"
            f"- JPY: ¥{jpy_balance:,.0f}\n"
            f"- 総資産(JPY換算): ¥{total_jpy:,.0f}\n\n"
            f"直近の取引履歴:\n{trades_summary}\n\n"
            f"現在時刻: {datetime.now().strftime('%Y-%m-%d %H:%M')} JST"
        )

    def _build_prompt(self, rules_content, price_data, current_price, btc_balance, jpy_balance, total_jpy, trades_summary) -> str:
        market = self._build_market_context(price_data, current_price, btc_balance, jpy_balance, total_jpy, trades_summary)
        return (
            f"## BTC/JPY 取引判断をお願いします\n\n"
            f"### 取引ルール\n{rules_content}\n\n"
            f"### 現在の市場情報\n{market}\n\n"
            f"### 依頼\n"
            f"上記の情報をもとに、今すぐ BUY / SELL / HOLD のどれが適切か教えてください。\n"
            f"以下の形式で回答してください:\n\n"
            f"判断: BUY または SELL または HOLD\n"
            f"理由: （30字以内）"
        )

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

    async def _execute_order(self, side, price, jpy_balance, btc_balance) -> Optional[str]:
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
            await self._log("INFO", f"注文実行: {side.upper()} {amount_btc:.8f} BTC @ ¥{price:,.0f}")
            return order_id
        except Exception as e:
            await self._log("ERROR", f"注文失敗: {e}")
            return None

    async def _log(self, level: str, message: str):
        await save_log(level, message)
        ts = datetime.now(timezone.utc).isoformat()
        await publish("logs", {"timestamp": ts, "level": level, "message": message})

    async def _publish_status(self):
        is_dry_run = (await get_setting("dry_run", "true")).lower() == "true"
        mode = await get_setting("trading_mode", "manual")
        await publish("bot", {
            "event": "status",
            "is_running": self.is_running,
            "is_dry_run": is_dry_run,
            "trading_mode": mode,
            "last_action": self.last_action,
            "last_reason": self.last_reason,
            "last_signal_at": self.last_signal_at,
            "has_pending": self.pending_prompt is not None,
        })

    async def start(self):
        self.is_running = True
        await self._log("INFO", "自動取引ボット開始")
        await self._publish_status()

    async def stop(self):
        self.is_running = False
        self.pending_prompt = None
        await self._log("INFO", "自動取引ボット停止")
        await self._publish_status()


trading_engine = TradingEngine()
