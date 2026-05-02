from fastapi import APIRouter

from redis_client import get_price

router = APIRouter()


@router.get("/price")
async def get_current_price():
    price = await get_price()
    if not price:
        return {"error": "価格データがまだ取得されていません"}
    return price
