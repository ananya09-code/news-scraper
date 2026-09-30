from os import getenv

from dotenv import load_dotenv
from sqlalchemy import create_engine, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

load_dotenv()

DATABASE_URL = getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")

engine = create_engine(DATABASE_URL)


class Base(DeclarativeBase):
    pass


class TestTable(Base):
    __tablename__ = "test_table"

    id: Mapped[int] = mapped_column(primary_key=True)
    message: Mapped[str] = mapped_column(String(100))


Base.metadata.create_all(engine)

print("✅ Connected to Neon!")
print("✅ test_table created!")
