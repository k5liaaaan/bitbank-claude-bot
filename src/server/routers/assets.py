from fastapi import APIRouter, Query

from database import get_asset_history

router = APIRouter()


@router.get("/assets/history")
async def get_assets_history(days: int = Query(30, ge=1, le=365)):
    history = await get_asset_history(days=days)
    return {"history": history}
