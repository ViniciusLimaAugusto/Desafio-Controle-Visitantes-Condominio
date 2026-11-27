from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from .. import crud, models, schemas
from . import Database, Limit, Offset

router = APIRouter(prefix="/controle-acesso", tags=["Access control"])


@router.post("/entrada", response_model=schemas.Movimentacao, status_code=201)
def register_entry(
    entry: schemas.MovimentacaoCreate, db: Database
) -> models.Movimentacao:
    if db.get(models.Visitante, entry.visitante_id) is None:
        raise HTTPException(404, "Visitor not found.")
    if db.get(models.Unidade, entry.unidade_id) is None:
        raise HTTPException(404, "Unit not found.")
    try:
        movement = crud.record_entry(db, entry)
    except IntegrityError as error:
        db.rollback()
        if (
            getattr(error.orig, "sqlite_errorname", "")
            == "SQLITE_CONSTRAINT_FOREIGNKEY"
        ):
            raise HTTPException(409, "Visitor or unit no longer exists.") from error
        raise
    if movement is None:
        raise HTTPException(409, "Visitor already has an active entry for this unit.")
    return movement


@router.put("/saida/{movimentacao_id}", response_model=schemas.Movimentacao)
def register_exit(
    movimentacao_id: schemas.ResourceId, db: Database
) -> models.Movimentacao:
    movement = crud.record_exit(db, movimentacao_id)
    if movement is not None:
        return movement
    if db.get(models.Movimentacao, movimentacao_id) is None:
        raise HTTPException(404, "Movement not found.")
    raise HTTPException(409, "Movement has already been closed.")


@router.get(
    "/unidades/{unidade_id}/movimentacoes", response_model=list[schemas.Movimentacao]
)
def list_history(
    unidade_id: schemas.ResourceId, db: Database, skip: Offset = 0, limit: Limit = 100
) -> list[models.Movimentacao]:
    if db.get(models.Unidade, unidade_id) is None:
        raise HTTPException(404, "Unit not found.")
    statement = (
        select(models.Movimentacao)
        .options(
            joinedload(models.Movimentacao.visitante),
            joinedload(models.Movimentacao.unidade),
        )
        .where(models.Movimentacao.unidade_id == unidade_id)
        .order_by(models.Movimentacao.id)
        .offset(skip)
        .limit(limit)
    )
    return list(db.scalars(statement))
