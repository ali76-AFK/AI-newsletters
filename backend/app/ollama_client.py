from __future__ import annotations

from typing import Any, Dict

import requests

from .config import load_settings

_settings = load_settings()


class OllamaError(Exception):
    pass


def ollama_generate(prompt: str, system: str | None = None) -> str:
    url = "http://127.0.0.1:11434/api/generate"
    payload: Dict[str, Any] = {
        "model": _settings.ollama_model,
        "prompt": prompt,
        "stream": False,
    }
    if system:
        payload["system"] = system

    try:
        resp = requests.post(url, json=payload, timeout=20)
        resp.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        raise OllamaError(f"Ollama request failed: {exc}") from exc

    data = resp.json()
    return data.get("response", "")
