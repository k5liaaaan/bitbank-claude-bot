from fastapi import APIRouter, Query

from database import get_logs

router = APIRouter()


@router.get("/logs")
async def list_logs(limit: int = Query(200, ge=1, le=1000)):
    logs = await get_logs(limit=limit)
    return {"logs": logs}
