from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from websocket_manager import ws_manager

router = APIRouter()


@router.websocket("/ws/price")
async def ws_price(websocket: WebSocket):
    await ws_manager.connect(websocket, "price")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, "price")


@router.websocket("/ws/logs")
async def ws_logs(websocket: WebSocket):
    await ws_manager.connect(websocket, "logs")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, "logs")


@router.websocket("/ws/bot")
async def ws_bot(websocket: WebSocket):
    await ws_manager.connect(websocket, "bot")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, "bot")
