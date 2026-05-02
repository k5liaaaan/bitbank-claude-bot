import asyncio
from typing import Dict, Optional

import python_bitbankcc

from database import get_setting


async def _get_credentials() -> tuple[str, str]:
    key = await get_setting("bitbank_api_key")
    secret = await get_setting("bitbank_api_secret")
    return key, secret


class BitbankClient:
    async def get_ticker(self) -> Dict:
        loop = asyncio.get_event_loop()
        pub = python_bitbankcc.public()
        result = await loop.run_in_executor(None, lambda: pub.get_ticker("btc_jpy"))
        return result.get("data", {})

    async def get_balance(self) -> Dict:
        key, secret = await _get_credentials()
        if not key or not secret:
            raise ValueError("bitbank APIキーが設定されていません")
        loop = asyncio.get_event_loop()
        prv = python_bitbankcc.private(key, secret)
        result = await loop.run_in_executor(None, prv.get_assets)
        assets = result.get("data", {}).get("assets", [])
        return {
            a["asset"]: {
                "free": float(a["free_amount"]),
                "locked": float(a["locked_amount"]),
                "total": float(a["onhand_amount"]),
            }
            for a in assets
        }

    async def place_order(
        self, side: str, price: float, amount_btc: float
    ) -> Optional[str]:
        key, secret = await _get_credentials()
        if not key or not secret:
            raise ValueError("bitbank APIキーが設定されていません")
        loop = asyncio.get_event_loop()
        prv = python_bitbankcc.private(key, secret)
        result = await loop.run_in_executor(
            None,
            lambda: prv.order(
                "btc_jpy",
                str(int(price)),
                f"{amount_btc:.8f}",
                side,
                "limit",
            ),
        )
        return str(result.get("data", {}).get("order_id", ""))


bitbank_client = BitbankClient()
