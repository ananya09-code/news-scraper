import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add the project root to sys.path BEFORE importing `db`, otherwise
# `db` is not importable when Scrapy loads this module.
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import scrapy  # noqa: E402

logger = logging.getLogger(__name__)

from db.insert import ensure_source, insert_article  # noqa: E402

SOURCE_ID = ensure_source(
    name="FANA",
    type="outlet",
    website="https://www.fanamc.com/",
    language="am",
)


def parse_published_at(raw: str | None) -> datetime:
    """Parse the listing date into an aware datetime.

    Fana renders dates like 'Oct 2, 2026'. Falls back to scrape time so the
    row still satisfies the NOT NULL column instead of blowing up.
    """
    if not raw:
        return datetime.now(timezone.utc)

    try:
        return datetime.strptime(raw.strip(), "%b %d, %Y").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        logger.warning("Could not parse date %r, using scrape time", raw)
        return datetime.now(timezone.utc)


CONTENT_SELECTOR = "div.entry-content.single-post-content"


def extract_paragraphs(response) -> list[str]:
    """Pull the article body out of the post content container.

    Fana is inconsistent: some articles use <p>, others use
    <div dir="auto"> (Facebook-pasted posts with obfuscated class names).
    Try each shape in turn and use the first that yields text.
    """
    for selector in (
        f"{CONTENT_SELECTOR} p::text",
        f"{CONTENT_SELECTOR} div[dir='auto']::text",
        f"{CONTENT_SELECTOR} div *::text",
    ):
        paragraphs = [
            text.strip()
            for text in response.css(selector).getall()
            if text.strip()
        ]

        if paragraphs:
            return paragraphs

    logger.warning("No article body found at %s", response.url)
    return []


class FanaSpider(scrapy.Spider):
    name = "fana"

    start_urls = [
        "https://www.fanamc.com/archives/category/localnews"
    ]

    def parse(self, response):

        for item in response.css("article.listing-item-blog"):

            url = item.css("h2.title a::attr(href)").get()

            yield response.follow(
                url,
                callback=self.parse_article,
                meta={
                    "url": url,
                    "title": item.css("h2.title a::text").get(),
                    "author": item.css(
                        "div.post-meta a.post-author-a "
                        "i.post-author.author::text"
                    ).get(),
                    "date": item.css(
                        "div.post-meta span.time "
                        "time.post-published.updated::text"
                    ).get(),
                    "summary": item.css(
                        "div.post-summary::text"
                    ).get(),
                },
            )

    def parse_article(self, response):

        paragraphs = extract_paragraphs(response)

        title = response.meta["title"].strip()
        author = response.meta["author"]
        summary = response.meta["summary"]
        url = response.meta["url"]

        if author:
            author = author.strip()

        if summary:
            summary = summary.strip()

        # Save article to database
        article = insert_article(
            source_id=SOURCE_ID,
            title=title,
            url=url,
            author=author,
            summary=summary,
            content="\n\n".join(paragraphs),
            published_at=parse_published_at(response.meta["date"]),
            language="am",
        )

        yield {
            "id": article.id,
            "title": article.title,
            "url": article.url,
        }
