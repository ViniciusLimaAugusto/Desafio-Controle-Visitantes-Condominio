from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .. import models, schemas
from . import Database, Limit, Offset, commit

router = APIRouter(prefix="/condominios", tags=["Condominiums and units"])


@router.post("/", response_model=schemas.Condominio, status_code=201)
def create_condominium(
    condominium: schemas.CondominioCreate, db: Database
) -> models.Condominio:
    record = models.Condominio(**condominium.model_dump())
    db.add(record)
    commit(db, {"SQLITE_CONSTRAINT_UNIQUE": "Condominium name already registered."})
    return record


@router.get("/", response_model=list[schemas.Condominio])
def list_condominiums(
    db: Database, skip: Offset = 0, limit: Limit = 100
) -> list[models.Condominio]:
    statement = (
        select(models.Condominio)
        .options(selectinload(models.Condominio.unidades))
        .order_by(models.Condominio.id)
        .offset(skip)
        .limit(limit)
    )
    return list(db.scalars(statement))


@router.get("/relacao/unidades", response_model=list[schemas.Condominio])
def list_condominium_units(db: Database) -> list[models.Condominio]:
    statement = (
        select(models.Condominio)
        .options(selectinload(models.Condominio.unidades))
        .order_by(models.Condominio.id)
    )
    return list(db.scalars(statement))


@router.get("/{condominio_id}", response_model=schemas.Condominio)
def read_condominium(
    condominio_id: schemas.ResourceId, db: Database
) -> models.Condominio:
    record = db.get(models.Condominio, condominio_id)
    if record is None:
        raise HTTPException(404, "Condominium not found.")
    return record


@router.get("/{condominio_id}/unidades", response_model=list[schemas.Unidade])
def list_units(
    condominio_id: schemas.ResourceId,
    db: Database,
    skip: Offset = 0,
    limit: Limit = 100,
) -> list[models.Unidade]:
    read_condominium(condominio_id, db)
    statement = (
        select(models.Unidade)
        .options(selectinload(models.Unidade.movimentacoes))
        .where(models.Unidade.condominio_id == condominio_id)
        .order_by(models.Unidade.id)
        .offset(skip)
        .limit(limit)
    )
    return list(db.scalars(statement))


@router.post(
    "/{condominio_id}/unidades/", response_model=schemas.Unidade, status_code=201
)
def create_unit(
    condominio_id: schemas.ResourceId, unidade: schemas.UnidadeCreate, db: Database
) -> models.Unidade:
    if unidade.condominio_id != condominio_id:
        raise HTTPException(400, "Condominium IDs in the URL and body must match.")
    read_condominium(condominio_id, db)
    record = models.Unidade(**unidade.model_dump())
    db.add(record)
    commit(db, {"SQLITE_CONSTRAINT_FOREIGNKEY": "Condominium no longer exists."})
    return record
