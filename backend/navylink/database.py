import os
from pathlib import Path

from sqlalchemy import JSON, ForeignKey, LargeBinary, String, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


class Base(DeclarativeBase):
    pass


class Organization(Base):
    __tablename__ = "organizations"
    name: Mapped[str] = mapped_column(String, primary_key=True)


class Domain(Base):
    __tablename__ = "domains"
    name: Mapped[str] = mapped_column(String, primary_key=True)


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    organization: Mapped[str] = mapped_column(ForeignKey("organizations.name"))
    domain: Mapped[str] = mapped_column(ForeignKey("domains.name"))
    visibility: Mapped[str] = mapped_column(String, index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    vector: Mapped[bytes] = mapped_column(LargeBinary)
    encoder: Mapped[str] = mapped_column(String)


class Run(Base):
    __tablename__ = "agent_runs"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    user: Mapped[str] = mapped_column(String)
    payload: Mapped[dict] = mapped_column(JSON)


def connect(url: str | None = None):
    from dotenv import load_dotenv
    load_dotenv()
    if not url:
        path = Path(os.getenv("NAVYLINK_DB", "data/navylink.db"))
        path.parent.mkdir(parents=True, exist_ok=True)
        url = f"sqlite:///{path}"
    engine = create_engine(url, connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def pragmas(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=5000")

    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.exec_driver_sql("CREATE VIRTUAL TABLE IF NOT EXISTS project_fts USING fts5(id UNINDEXED, content)")
    return engine, sessionmaker(engine, expire_on_commit=False)
