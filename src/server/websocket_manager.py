import json
from typing import Dict, List

import redis.asyncio as redis
from fastapi import WebSocket

from config import config

CHANNELS = ("price", "logs", "bot")


class WebSocketManager:
    def __init__(self):
        self._connections: Dict[str, List[WebSocket]] = {ch: [] for ch in CHANNELS}

    async def connect(self, websocket: WebSocket, channel: str):
        await websocket.accept()
        self._connections.setdefault(channel, []).append(websocket)

    def disconnect(self, websocket: WebSocket, channel: str):
        conns = self._connections.get(channel, [])
        self._connections[channel] = [ws for ws in conns if ws is not websocket]

    async def broadcast(self, channel: str, data: dict):
        dead: List[WebSocket] = []
        for ws in list(self._connections.get(channel, [])):
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws, channel)

    async def start_redis_listener(self):
        import asyncio
        while True:
            try:
                r = redis.from_url(config.REDIS_URL, decode_responses=True)
                pubsub = r.pubsub()
                await pubsub.subscribe(*CHANNELS)
                async for message in pubsub.listen():
                    if message["type"] != "message":
                        continue
                    channel = message["channel"]
                    try:
                        data = json.loads(message["data"])
                        await self.broadcast(channel, data)
                    except Exception:
                        pass
            except Exception:
                await asyncio.sleep(2)


ws_manager = WebSocketManager()
