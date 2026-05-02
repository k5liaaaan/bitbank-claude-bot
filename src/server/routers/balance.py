from fastapi import APIRouter

from bitbank_client import bitbank_client
from database import get_setting

router = APIRouter()


@router.get("/balance")
async def get_balance():
    is_dry_run = (await get_setting("dry_run", "true")).lower() == "true"
    if is_dry_run:
        return {"dry_run": True, "message": "DRYモードでは実際の残高は取得されません"}
    try:
        return await bitbank_client.get_balance()
    except Exception as e:
        return {"error": str(e)}
