from fastapi import APIRouter, Query

from database import get_trades

router = APIRouter()


@router.get("/trades")
async def list_trades(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    trades = await get_trades(limit=limit, offset=offset)
    return {"trades": trades, "count": len(trades)}
