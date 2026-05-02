import asyncio
import json
import re
from typing import Dict

import anthropic

from config import config
from database import get_setting

_SYSTEM = """あなたはBTC/JPY自動取引ボットのシグナル判断エンジンです。
与えられた市場情報と取引ルールに基づき、以下のJSON形式のみで回答してください：
{"action": "buy" | "sell" | "hold", "reason": "判断理由（日本語・50字以内）"}

注意:
- 必ず上記JSON形式のみで回答すること（説明文不要）
- actionはbuy/sell/holdのいずれか一つ
- 確信が持てない場合は必ずholdを選ぶこと"""


class ClaudeClient:
    async def get_signal(self, rules_content: str, market_context: str) -> Dict[str, str]:
        api_key = await get_setting("anthropic_api_key") or config.ANTHROPIC_API_KEY
        if not api_key:
            return {"action": "hold", "reason": "Anthropic APIキー未設定"}

        def _call() -> str:
            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=256,
                system=_SYSTEM,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": f"## 取引ルール\n\n{rules_content}",
                                "cache_control": {"type": "ephemeral"},
                            },
                            {
                                "type": "text",
                                "text": f"## 現在の市場情報\n\n{market_context}",
                            },
                        ],
                    }
                ],
            )
            return response.content[0].text

        try:
            loop = asyncio.get_event_loop()
            raw = await loop.run_in_executor(None, _call)
            match = re.search(r"\{[^}]+\}", raw, re.DOTALL)
            if match:
                return json.loads(match.group())
            return {"action": "hold", "reason": "Claude応答パースエラー"}
        except Exception as e:
            return {"action": "hold", "reason": f"Claude APIエラー: {str(e)[:30]}"}


claude_client = ClaudeClient()
