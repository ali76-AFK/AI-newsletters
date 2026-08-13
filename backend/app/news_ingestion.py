from __future__ import annotations

from typing import Dict


class NewsIngestionError(Exception):
    pass


def build_stub_newsletter_content(source: str, topic: str) -> Dict[str, str]:
    """
    Stub for news ingestion. Returns a title and body based on source and topic.

    Later, replace this with real API calls to a news provider.
    """
    source_lower = source.lower()
    topic_lower = topic.lower()

    title = f"{source} – {topic.capitalize()} highlights"

    body = f"""
Dies ist eine automatisch generierte Newsletter-Zusammenfassung für das Thema '{topic_lower}' von der Quelle '{source_lower}'.

Sie können diesen Text später durch Inhalte aus einer echten News-API ersetzen. Aktuell dient er nur als Platzhalter, um den
Automatisierungs- und Workflow-Prozess zu demonstrieren.

Stichpunkte:
- Quelle: {source}
- Thema: {topic}
- Dieser Newsletter wurde automatisch erstellt, klassifiziert, geprüft und für den Versand vorbereitet.
"""

    return {"title": title.strip(), "body": body.strip()}
