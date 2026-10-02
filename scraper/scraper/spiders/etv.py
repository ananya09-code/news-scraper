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

from db.insert import ensure_source, insert_article  # noqa: E402

logger = logging.getLogger(__name__)

SOURCE_ID = ensure_source(
    name="EBC",
    type="outlet",
    website="https://www.ebc.et",
    language="am",
)

CONTENT_SELECTOR = "div.post-content"


def extract_paragraphs(response) -> list[str]:
    """Pull the article body out of the post content container.

    EBC is inconsistent: some articles use <p>, others use
    <div dir="auto"> (Facebook-pasted posts with obfuscated class names).
    Try each shape in turn and use the first that yields text.
    """
    for selector in (
        f"{CONTENT_SELECTOR} p::text",
        f"{CONTENT_SELECTOR} div[dir='auto'] *::text",
        f"{CONTENT_SELECTOR} ::text",
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


def parse_published_at(raw: str | None) -> datetime:
    """Parse the listing date into an aware datetime.

    The listing exposes an ISO timestamp on the timeago element
    (e.g. '2026-10-02T13:20:03.9900000'). Falls back to scrape time so the
    row still satisfies the NOT NULL column instead of blowing up.
    """
    if not raw:
        return datetime.now(timezone.utc)

    try:
        return datetime.fromisoformat(raw.strip()).astimezone(timezone.utc)
    except ValueError:
        logger.warning("Could not parse date %r, using scrape time", raw)
        return datetime.now(timezone.utc)


class EtvSpider(scrapy.Spider):
    name = "etv"

    page = 1
    catid = 1

    start_urls = [
        f"https://www.ebc.et/Home/CategorialNews?CatId={catid}&page={page}"
    ]

    def parse(self, response):
        for item in response.css("article.news-card"):

            title = item.css(
                "div.news-content h2.news-title a::text"
            ).get()

            # The ISO timestamp lives in the attribute, not the text node.
            # The visible text is only 'Oct 02, 2026'.
            date = item.css(
                "div.news-content span.news-date span.timeago::attr(datetime)"
            ).get()

            url = item.css(
                "div.news-content h2.news-title a::attr(href)"
            ).get()

            if not (url and title):
                continue

            yield response.follow(
                url,
                callback=self.parse_article,
                meta={
                    "title": " ".join(title.split()),
                    "date": date,
                },
            )

    def parse_article(self, response):

        content = "\n\n".join(extract_paragraphs(response))

        # The detail page carries no title/date of its own, so both come
        # from the listing meta passed through parse().
        article = insert_article(
            source_id=SOURCE_ID,
            title=response.meta["title"],
            url=response.url,
            author=None,
            summary=None,
            content=content,
            published_at=parse_published_at(response.meta["date"]),
            language="am",
        )

        yield {
            "id": article.id,
            "title": article.title,
            "url": article.url,
        }
