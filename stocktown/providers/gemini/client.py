from __future__ import annotations

import json
from typing import Any, Final

import httpx

from stocktown.config import get_gemini_credentials

GEMINI_BASE_URL: Final[str] = "https://generativelanguage.googleapis.com/v1beta"
REQUEST_TIMEOUT_SECONDS: Final[float] = 30.0
# Low temperature: steady, factual wording rather than creative variety.
TEMPERATURE: Final[float] = 0.2


def generate_json(
    *, model: str, system_instruction: str, prompt: str, response_schema: dict[str, Any]
) -> dict[str, Any]:
    """One call to the given Gemini model, constrained to a JSON reply of the given schema."""
    credentials = get_gemini_credentials()
    with httpx.Client(
        base_url=GEMINI_BASE_URL,
        # a header, not the ?key= query parameter, so the key never lands in access logs
        headers={"x-goog-api-key": credentials.api_key},
        timeout=REQUEST_TIMEOUT_SECONDS,
    ) as client:
        response = client.post(
            f"/models/{model}:generateContent",
            json={
                "systemInstruction": {"parts": [{"text": system_instruction}]},
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "responseSchema": response_schema,
                    "temperature": TEMPERATURE,
                },
            },
        )
        response.raise_for_status()
    reply_text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(reply_text)
