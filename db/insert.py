import logging
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert

from db.database import SessionLocal
from db.models import Article, Source

logger = logging.getLogger(__name__)


def ensure_source(
    name: str,
    type: str = "outlet",
    website: str | None = None,
    language: str | None = None,
) -> int:
    """Return the id of the source with this name, creating it if missing.

    Never hardcode source ids in a spider: they depend on what already
    exists in the `sources` table.
    """
    db = SessionLocal()

    try:
        source = db.query(Source).filter(Source.name == name).one_or_none()

        if source is None:
            source = Source(
                name=name,
                type=type,
                website=website,
                language=language,
            )
            db.add(source)
            db.commit()
            db.refresh(source)

        return source.id

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


def insert_article(
    source_id: int,
    title: str,
    url: str,
    author: str | None,
    summary: str | None,
    content: str,
    published_at: datetime,
    language: str | None = None,
):
    """Insert an article, or update it if this source+url already exists.

    `articles` has UNIQUE (source_id, url), so re-scraping the same story on
    a later day must not raise. This upserts instead: a plain INSERT ... ON
    CONFLICT DO UPDATE.

    Empty incoming values never overwrite good stored data - a layout change
    that yields a blank body will not wipe out the article text we already
    have. published_at always refreshes, since it is a real timestamp.
    """
    db = SessionLocal()

    try:
        values = {
            "source_id": source_id,
            "url": url,
            "title": title,
            "author": author,
            "snippet": summary,
            "content": content,
            "language": language,
            "published_at": published_at,
        }

        stmt = pg_insert(Article).values(**values)

        # Only overwrite a column when we actually scraped something, so a
        # layout change that yields a blank body cannot wipe good data.
        updates = {
            key: func.coalesce(
                func.nullif(stmt.excluded[key], ""),
                Article.__table__.c[key],
            )
            for key in ("title", "author", "snippet", "content", "language")
        }
        updates["published_at"] = stmt.excluded["published_at"]

        stmt = stmt.on_conflict_do_update(
            index_elements=[Article.source_id, Article.url],
            set_=updates,
        ).returning(Article)

        article = db.execute(stmt).scalar_one()
        db.commit()

        logger.info("Saved article %s (%s)", article.id, article.url)

        return article

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()
