from __future__ import annotations

from typing import Any

import requests

from .config import load_settings

_settings = load_settings()


class GroqError(Exception):
    pass


def groq_generate(prompt: str, system: str | None = None) -> str:
    if not _settings.groq_api_key:
        raise GroqError("GROQ_API_KEY is not set")

    if not _settings.groq_model or _settings.groq_model.startswith("replace_"):
        raise GroqError(
            "GROQ_MODEL is not configured. Set GROQ_MODEL in your environment to a supported Groq model."
        )

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {_settings.groq_api_key}",
        "Content-Type": "application/json",
    }

    messages: list[dict[str, Any]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": _settings.groq_model,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 512,
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
    except Exception as exc:  # noqa: BLE001
        raise GroqError(f"Groq request failed before response: {exc}") from exc

    if not resp.ok:
        raise GroqError(
            f"Groq HTTP {resp.status_code}: {resp.text.strip() or '<empty response>'}"
        )

    data = resp.json()
    return (
        data.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
    )
