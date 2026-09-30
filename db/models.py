from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    """created_at / updated_at, set by the database (timezone-aware)."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Source(TimestampMixin, Base):
    """A news outlet or an individual creator/journalist."""

    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    # outlet | creator | journalist
    type: Mapped[str] = mapped_column(String(20), default="outlet")
    website: Mapped[str | None] = mapped_column(Text)
    logo_url: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(String(10))  # am, om, ti, en
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    social_accounts: Mapped[list["SocialAccount"]] = relationship(
        back_populates="source", cascade="all, delete-orphan"
    )
    articles: Mapped[list["Article"]] = relationship(
        back_populates="source", cascade="all, delete-orphan"
    )


class SocialAccount(TimestampMixin, Base):
    """A TikTok / YouTube account that belongs to a source."""

    __tablename__ = "social_accounts"
    __table_args__ = (
        UniqueConstraint("platform", "username",
                         name="uq_social_platform_username"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(
        ForeignKey("sources.id", ondelete="CASCADE"), index=True
    )
    platform: Mapped[str] = mapped_column(String(20))  # tiktok | youtube
    username: Mapped[str] = mapped_column(String(255))
    platform_id: Mapped[str | None] = mapped_column(String(255))
    display_name: Mapped[str | None] = mapped_column(String(255))
    profile_url: Mapped[str | None] = mapped_column(Text)
    profile_image_url: Mapped[str | None] = mapped_column(Text)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    followers: Mapped[int] = mapped_column(BigInteger, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    source: Mapped["Source"] = relationship(back_populates="social_accounts")
    videos: Mapped[list["Video"]] = relationship(
        back_populates="social_account", cascade="all, delete-orphan"
    )


class Article(TimestampMixin, Base):
    """News article. `snippet` is for feed lists, `content` is the full text."""

    __tablename__ = "articles"
    __table_args__ = (
        UniqueConstraint("source_id", "url", name="uq_article_source_url"),
        Index("ix_articles_published", "published_at"),
        Index("ix_articles_lang_published", "language", "published_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(
        ForeignKey("sources.id", ondelete="CASCADE"))
    url: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    snippet: Mapped[str | None] = mapped_column(
        Text)  # short text for feed cards
    content: Mapped[str | None] = mapped_column(
        Text)  # full article (you have permission)
    author: Mapped[str | None] = mapped_column(String(255))
    image_url: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(String(10))
    # If the site gives no date, use the scrape time so the feed sorts correctly.
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    raw_data: Mapped[dict | None] = mapped_column(JSONB)

    source: Mapped["Source"] = relationship(back_populates="articles")


class Video(TimestampMixin, Base):
    __tablename__ = "videos"
    __table_args__ = (
        UniqueConstraint(
            "social_account_id", "external_id", name="uq_video_account_external_id"
        ),
        Index("ix_videos_published", "published_at"),
        Index("ix_videos_lang_published", "language", "published_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    social_account_id: Mapped[int] = mapped_column(
        ForeignKey("social_accounts.id", ondelete="CASCADE")
    )
    external_id: Mapped[str] = mapped_column(String(255))
    url: Mapped[str] = mapped_column(Text)
    caption: Mapped[str | None] = mapped_column(Text)
    thumbnail_url: Mapped[str | None] = mapped_column(
        Text)  # TikTok URLs expire
    language: Mapped[str | None] = mapped_column(String(10))
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    views: Mapped[int] = mapped_column(BigInteger, default=0)
    likes: Mapped[int] = mapped_column(BigInteger, default=0)
    comments: Mapped[int] = mapped_column(BigInteger, default=0)
    shares: Mapped[int] = mapped_column(BigInteger, default=0)
    raw_data: Mapped[dict | None] = mapped_column(JSONB)

    social_account: Mapped["SocialAccount"] = relationship(
        back_populates="videos")
