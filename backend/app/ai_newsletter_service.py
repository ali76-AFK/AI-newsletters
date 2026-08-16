from __future__ import annotations

import json
import re
from .config import load_settings
from .ollama_client import ollama_generate
from .groq_client import groq_generate





_settings = load_settings()





class AIServiceError(Exception):
    pass


def _mock_classify(title: str, body: str) -> dict:
    text = f"{title}\n{body}".lower()
    topic = "ai_news"
    if "robot" in text:
        topic = "robotics"
    elif "data" in text:
        topic = "data_eng"
    return {
        "risk_level": "low",
        "topic": topic,
        "reason": "Mock classifier: deterministic local fallback.",
    }


def _mock_summary(title: str, body: str) -> str:
    snippet = body.strip().splitlines()[0][:220] if body.strip() else ""
    return f"Summary: {title}. {snippet}".strip()


def _mock_refine(base_subject: str, base_body: str, subscriber_name: str | None) -> dict:
    subject = f"{base_subject} for {subscriber_name or 'you'}"
    body = base_body.strip()
    return {"subject": subject, "body": body}


def _llm_call(prompt: str, system: str | None = None) -> str:
    provider = _settings.llm_provider.lower()

    if provider == "mock":
        raise AIServiceError("mock provider does not use live LLM calls")
    if provider == "ollama":
        return ollama_generate(prompt, system=system)
    if provider == "groq":
        return groq_generate(prompt, system=system)

    raise AIServiceError(f"Unsupported LLM provider: {provider}")


def _extract_json_block(text: str) -> str:
    """Extract bare JSON from a model response that may contain ```json fences."""
    # Look for ```json ... ``` fenced block
    match = re.search(r"```json\s*(\{.*\})\s*```", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    # Fallback: just strip whitespace
    return text.strip()




def classify_newsletter_text(title: str, body: str) -> dict:
    if _settings.llm_provider.lower() == "mock":
        return _mock_classify(title, body)

    system = (
        "Return JSON only. "
        "risk_level must be exactly one of: low, medium, high, critical."
    )
    prompt = (
        f"Title: {title[:120]}\n"
        f"Body: {body[:700]}\n"
        "JSON keys: risk_level, topic, reason"
    )
    raw = _llm_call(prompt, system=system)

    cleaned = _extract_json_block(raw)

    try:
        data = json.loads(cleaned)
    except Exception as exc:  # noqa: BLE001
        raise AIServiceError(
            f"Failed to parse classification JSON: {exc}; raw={cleaned}"
        ) from exc

    risk = data.get("risk_level", "low")
    topic = data.get("topic", "ai_news")
    reason = data.get("reason", "")

    if risk not in ("low", "medium", "high", "critical"):
        risk = "low"

    return {
        "risk_level": risk,
        "topic": topic,
        "reason": reason,
    }


def summarize_newsletter_text(title: str, body: str) -> str:
    if _settings.llm_provider.lower() == "mock":
        return _mock_summary(title, body)

    system = "Write a 2 sentence summary."
    prompt = f"Title: {title[:120]}\nBody: {body[:900]}"
    return _llm_call(prompt, system=system)


def refine_newsletter_draft(
    base_subject: str,
    base_body: str,
    subscriber_name: str | None = None,
) -> dict:
    if _settings.llm_provider.lower() == "mock":
        return _mock_refine(base_subject, base_body, subscriber_name)

    system = "Improve newsletter draft. Return Subject and Body. No extra text."
    prompt = (
        f"Subject: {base_subject[:140]}\n"
        f"Body: {base_body[:1000]}\n"
        f"Recipient: {subscriber_name or 'subscriber'}"
    )
    raw = _llm_call(prompt, system=system)

    subject = base_subject
    body = base_body

    lines = raw.splitlines()
    current_section = None
    subj_buf = []
    body_buf = []

    for line in lines:
        if line.strip().lower().startswith("subject:"):
            current_section = "subject"
            subj_buf.append(line.split(":", 1)[1].strip())
        elif line.strip().lower().startswith("body:"):
            current_section = "body"
        else:
            if current_section == "subject":
                subj_buf.append(line.strip())
            elif current_section == "body":
                body_buf.append(line)

    if subj_buf:
        subject = " ".join(subj_buf).strip()
    if body_buf:
        body = "\n".join(body_buf).strip()

    return {"subject": subject, "body": body}
