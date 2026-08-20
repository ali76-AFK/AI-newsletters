from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from backend.app.news_ingestion import (
    NewsIngestionError,
    fetch_rss_articles,
    get_articles,
)


RSS_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>SPIEGEL Technik</title>
    <item>
      <guid>spiegel-rss-001</guid>
      <title>AI systems are evaluated</title>
      <link>https://www.spiegel.de/wissenschaft/technik/test-article-a-1.html</link>
      <description>Researchers describe a benchmark for AI systems.</description>
      <pubDate>Thu, 20 Aug 2026 10:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""


def test_fetch_rss_articles_normalizes_allowlisted_feed():
    response = Mock()
    response.content = RSS_XML
    response.raise_for_status.return_value = None

    with patch(
        "backend.app.news_ingestion.requests.get",
        return_value=response,
    ) as mock_get:
        articles = fetch_rss_articles(
            source="Spiegel",
            topic="ai_news",
        )

    assert len(articles) == 1

    article = articles[0]
    assert article.source == "Spiegel"
    assert article.topic == "ai_news"
    assert article.external_id == "spiegel-rss-001"
    assert article.url.startswith("https://www.spiegel.de/")
    assert article.title == "AI systems are evaluated"
    assert "benchmark" in article.body

    mock_get.assert_called_once()


def test_fetch_rss_articles_rejects_unknown_source():
    with pytest.raises(NewsIngestionError, match="not allowlisted"):
        fetch_rss_articles(
            source="Unknown Source",
            topic="ai_news",
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
