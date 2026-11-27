import os
from collections.abc import Iterator
from sqlite3 import Connection

from fastapi import Request
from sqlalchemy import URL, create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session


class Base(DeclarativeBase):
    pass


def build_engine(path: str | None = None) -> Engine:
    url = URL.create("sqlite", database=path or os.getenv("DATABASE_PATH", "test.db"))
    engine = create_engine(url, hide_parameters=True)

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection: Connection, _: object) -> None:
        connection.execute("PRAGMA foreign_keys = ON")

    return engine


def get_db(request: Request) -> Iterator[Session]:
    with Session(request.app.state.engine, expire_on_commit=False) as session:
        yield session
