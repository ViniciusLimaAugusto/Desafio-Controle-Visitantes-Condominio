from typing import Annotated

from fastapi import Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db

Database = Annotated[Session, Depends(get_db)]
Offset = Annotated[int, Query(ge=0, le=2**63 - 1)]
Limit = Annotated[int, Query(ge=1, le=100)]


def commit(db: Session, conflicts: dict[str, str]) -> None:
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        message = conflicts.get(getattr(error.orig, "sqlite_errorname", ""))
        if message is None:
            raise
        raise HTTPException(409, message) from error
