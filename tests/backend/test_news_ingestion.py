from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from backend.app.crud_subscribers import ALLOWED_TOPICS
from backend.app.news_ingestion import (
    NewsArticle,
    NewsIngestionError,
    fetch_rss_articles,
    filter_relevant_articles,
    get_articles,
    is_relevant_for_topic,
)


RSS_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>SPIEGEL Technik</title>
    <item>
      <guid>spiegel-rss-ai</guid>
      <title>AI systems are evaluated</title>
      <link>https://www.spiegel.de/wissenschaft/technik/test-ai.html</link>
      <description>
        Researchers describe a machine learning benchmark for AI systems.
      </description>
      <pubDate>Thu, 20 Aug 2026 10:00:00 GMT</pubDate>
    </item>
    <item>
      <guid>spiegel-rss-aviation</guid>
      <title>Airport runway maintenance expands</title>
      <link>https://www.spiegel.de/wissenschaft/technik/test-flight.html</link>
      <description>
        Engineers inspect runway surfaces before the winter season.
      </description>
      <pubDate>Thu, 20 Aug 2026 11:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""


def make_article(
    title: str,
    body: str,
) -> NewsArticle:
    return NewsArticle(
        source="Spiegel",
        external_id="test-id",
        url="https://www.spiegel.de/wissenschaft/technik/test.html",
        published_at="2026-08-20T10:00:00Z",
        topic="ai_news",
        title=title,
        body=body,
    )


def test_allowed_topics_include_general_news_categories():
    assert "technology_science" in ALLOWED_TOPICS
    assert "business" in ALLOWED_TOPICS
    assert "world_news" in ALLOWED_TOPICS


def test_ai_relevance_filter_matches_ai_article():
    article = make_article(
        "AI systems are evaluated",
        "Researchers describe a machine learning benchmark.",
    )

    assert is_relevant_for_topic(article, "ai_news") is True


def test_ai_relevance_filter_excludes_unrelated_article():
    article = make_article(
        "Airport runway maintenance expands",
        "Engineers inspect surfaces before winter.",
    )

    assert is_relevant_for_topic(article, "ai_news") is False


def test_technology_science_accepts_broad_technology_article():
    article = make_article(
        "Airport runway maintenance expands",
        "Engineers inspect surfaces before winter.",
    )

    assert is_relevant_for_topic(
        article,
        "technology_science",
    ) is True


def test_filter_relevant_articles_keeps_only_ai_matches():
    articles = [
        make_article(
            "AI systems are evaluated",
            "A machine learning benchmark is released.",
        ),
        make_article(
            "Airport runway maintenance expands",
            "Engineers inspect surfaces before winter.",
        ),
    ]

    filtered = filter_relevant_articles(articles, "ai_news")

    assert len(filtered) == 1
    assert filtered[0].title == "AI systems are evaluated"


def test_fetch_rss_articles_filters_allowlisted_feed_by_topic():
    response = Mock()
    response.content = RSS_XML
    response.raise_for_status.return_value = None

    with patch(
        "backend.app.news_ingestion.requests.get",
        return_value=response,
    ):
        articles = fetch_rss_articles(
            source="Spiegel",
            topic="ai_news",
        )

    assert len(articles) == 1
    assert articles[0].external_id == "spiegel-rss-ai"
    assert articles[0].title == "AI systems are evaluated"


def test_fetch_rss_articles_rejects_topic_without_allowlisted_feed():
    with pytest.raises(
        NewsIngestionError,
        match="not allowlisted",
    ):
        fetch_rss_articles(
            source="Spiegel",
            topic="business",
        )


def test_get_articles_uses_stub_mode(monkeypatch):
    monkeypatch.setenv("NEWS_SOURCE_MODE", "stub")

    articles = get_articles(
        source="Spiegel",
        topic="ai_news",
    )

    assert len(articles) == 3
    assert all(article.source == "Spiegel" for article in articles)


def test_get_articles_rejects_unknown_mode(monkeypatch):
    monkeypatch.setenv("NEWS_SOURCE_MODE", "unsupported")

    with pytest.raises(
        NewsIngestionError,
        match="Unsupported NEWS_SOURCE_MODE",
    ):
        get_articles(
            source="Spiegel",
            topic="ai_news",
        )
