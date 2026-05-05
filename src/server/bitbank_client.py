import hashlib
import hmac
import json
import time
from typing import Dict, Optional

import aiohttp

from database import get_setting

PUBLIC_BASE = "https://public.bitbank.cc"
PRIVATE_BASE = "https://api.bitbank.cc"


async def _get_credentials() -> tuple[str, str]:
    key = await get_setting("bitbank_api_key")
    secret = await get_setting("bitbank_api_secret")
    return key, secret


def _make_headers(api_key: str, api_secret: str, sign_text: str) -> dict:
    nonce = str(int(time.time() * 1000))
    message = nonce + sign_text
    signature = hmac.new(
        api_secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    return {
        "ACCESS-KEY": api_key,
        "ACCESS-NONCE": nonce,
        "ACCESS-SIGNATURE": signature,
        "Content-Type": "application/json",
    }


class BitbankClient:
    async def get_ticker(self) -> Dict:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{PUBLIC_BASE}/btc_jpy/ticker") as resp:
                data = await resp.json(content_type=None)
                return data.get("data", {})

    async def get_balance(self) -> Dict:
        key, secret = await _get_credentials()
        if not key or not secret:
            raise ValueError("bitbank APIキーが設定されていません")

        path = "/v1/user/assets"
        headers = _make_headers(key, secret, path)

        async with aiohttp.ClientSession() as session:
            async with session.get(f"{PRIVATE_BASE}{path}", headers=headers) as resp:
                data = await resp.json(content_type=None)
                if data.get("success") != 1:
                    raise Exception(f"bitbank API error: {data}")
                assets = data.get("data", {}).get("assets", [])
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

        body_str = json.dumps({
            "pair": "btc_jpy",
            "amount": f"{amount_btc:.8f}",
            "price": str(int(price)),
            "side": side,
            "type": "limit",
        })
        headers = _make_headers(key, secret, body_str)

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{PRIVATE_BASE}/v1/user/spot/order",
                headers=headers,
                data=body_str,
            ) as resp:
                data = await resp.json(content_type=None)
                if data.get("success") != 1:
                    raise Exception(f"bitbank order error: {data}")
                return str(data.get("data", {}).get("order_id", ""))


bitbank_client = BitbankClient()
