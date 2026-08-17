from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable


class NewsIngestionError(Exception):
    pass


@dataclass(frozen=True)
class NewsArticle:
    source: str
    external_id: str
    url: str
    published_at: str
    topic: str
    title: str
    body: str

    @property
    def content_hash(self) -> str:
        raw = (
            f"{self.source}|{self.external_id}|{self.url}|"
            f"{self.title}|{self.body}"
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


STUB_ARTICLES: tuple[NewsArticle, ...] = (
    NewsArticle(
        source="Spiegel",
        external_id="spiegel-ai-001",
        url="https://example.invalid/spiegel/ai-001",
        published_at="2026-08-17T08:00:00Z",
        topic="ai_news",
        title="AI research collaboration highlights",
        body=(
            "A research consortium published a summary of its latest work on "
            "evaluating language-model reliability. The report describes test "
            "methodology, limitations, and plans for independent replication."
        ),
    ),
    NewsArticle(
        source="Spiegel",
        external_id="spiegel-ai-002",
        url="https://example.invalid/spiegel/ai-002",
        published_at="2026-08-17T10:00:00Z",
        topic="ai_news",
        title="New dataset supports AI safety research",
        body=(
            "Researchers released documentation for a benchmark dataset used "
            "to evaluate factual consistency in generated summaries. The "
            "documentation includes known limitations and licensing details."
        ),
    ),
    NewsArticle(
        source="Spiegel",
        external_id="spiegel-ai-003",
        url="https://example.invalid/spiegel/ai-003",
        published_at="2026-08-17T12:00:00Z",
        topic="ai_news",
        title="Public consultation on AI transparency opens",
        body=(
            "A public consultation invites comments on transparency practices "
            "for automated systems. The announcement describes the submission "
            "process and the consultation timetable."
        ),
    ),
)


def get_stub_articles(
    source: str | None = None,
    topic: str | None = None,
) -> list[NewsArticle]:
    """Return deterministic local articles for development and demo use."""
    articles: Iterable[NewsArticle] = STUB_ARTICLES

    if source:
        articles = (
            article
            for article in articles
            if article.source.lower() == source.lower()
        )

    if topic:
        articles = (
            article
            for article in articles
            if article.topic == topic
        )

    return list(articles)


def build_stub_newsletter_content(source: str, topic: str) -> dict[str, str]:
    """
    Backward-compatible helper used by the existing manual source endpoint.

    The automation tick will use get_stub_articles() directly.
    """
    articles = get_stub_articles(source=source, topic=topic)

    if not articles:
        raise NewsIngestionError(
            f"No local stub articles for source={source!r}, topic={topic!r}."
        )

    article = articles[0]

    return {
        "title": article.title,
        "body": article.body,
        "source": article.source,
        "source_external_id": article.external_id,
        "source_url": article.url,
        "content_hash": article.content_hash,
        "published_at": article.published_at,
    }
