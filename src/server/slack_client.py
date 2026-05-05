import asyncio
import logging
import re
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class SlackClient:
    def __init__(self):
        self._app = None
        self._handler = None
        self._channel: Optional[str] = None
        self._on_decision: Optional[Callable] = None
        self.is_connected = False

    async def start(self, bot_token: str, app_token: str, channel: str, on_decision: Callable):
        try:
            from slack_bolt.async_app import AsyncApp
            from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
        except ImportError:
            logger.error("slack-bolt not installed")
            return

        self._channel = channel
        self._on_decision = on_decision

        logging.getLogger("slack_bolt").setLevel(logging.WARNING)
        logging.getLogger("slack_sdk").setLevel(logging.WARNING)

        self._app = AsyncApp(token=bot_token)

        async def _handle_action(action_id: str, body, client):
            action_value = action_id.replace("trade_", "")
            try:
                await client.chat_update(
                    channel=body["channel"]["id"],
                    ts=body["message"]["ts"],
                    text=f"✅ {action_value.upper()} を選択しました",
                    blocks=[{
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": f"✅ *{action_value.upper()}* を選択しました"},
                    }],
                )
            except Exception:
                pass
            if self._on_decision:
                asyncio.create_task(self._on_decision(action_value, f"Slackで{action_value.upper()}を選択"))

        @self._app.action("trade_buy")
        async def handle_buy(ack, action, body, client):
            await ack()
            await _handle_action(action["action_id"], body, client)

        @self._app.action("trade_hold")
        async def handle_hold(ack, action, body, client):
            await ack()
            await _handle_action(action["action_id"], body, client)

        @self._app.action("trade_sell")
        async def handle_sell(ack, action, body, client):
            await ack()
            await _handle_action(action["action_id"], body, client)

        try:
            self._handler = AsyncSocketModeHandler(self._app, app_token)
            await self._handler.start_async()
            self.is_connected = True
            logger.info("Slack bot connected (Socket Mode)")
        except Exception as e:
            logger.error(f"Slack bot failed to start: {e}")

    async def send_decision_message(
        self, price: float, jpy: float, btc: float, total: float,
        high: float, low: float, vol: float, trades_summary: str
    ) -> bool:
        if not self._app or not self._channel or not self.is_connected:
            return False
        try:
            blocks = [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": "⚡ BTC/JPY 取引判断の時間です", "emoji": True},
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*現在価格*\n¥{price:,.0f}"},
                        {"type": "mrkdwn", "text": f"*24h 高値 / 安値*\n¥{high:,.0f} / ¥{low:,.0f}"},
                        {"type": "mrkdwn", "text": f"*JPY残高*\n¥{jpy:,.0f}"},
                        {"type": "mrkdwn", "text": f"*BTC残高*\n{btc:.6f} BTC\n(≈ ¥{btc * price:,.0f})"},
                        {"type": "mrkdwn", "text": f"*総資産*\n¥{total:,.0f}"},
                        {"type": "mrkdwn", "text": f"*出来高 (24h)*\n{vol:.2f} BTC"},
                    ],
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*直近の取引*\n{trades_summary or '取引履歴なし'}"},
                },
                {"type": "divider"},
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "▲ BUY", "emoji": True},
                            "action_id": "trade_buy",
                            "style": "primary",
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "― HOLD", "emoji": True},
                            "action_id": "trade_hold",
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "▼ SELL", "emoji": True},
                            "action_id": "trade_sell",
                            "style": "danger",
                        },
                    ],
                },
            ]
            await self._app.client.chat_postMessage(
                channel=self._channel,
                blocks=blocks,
                text="BTC/JPY 取引判断の時間です",
            )
            return True
        except Exception as e:
            logger.error(f"Slack send failed: {e}")
            return False

    async def stop(self):
        if self._handler:
            try:
                await self._handler.close_async()
            except Exception:
                pass
        self.is_connected = False


slack_client = SlackClient()
