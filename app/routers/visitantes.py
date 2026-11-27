from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import select

from .. import models, schemas
from . import Database, Limit, Offset, commit

router = APIRouter(prefix="/visitantes", tags=["Visitors"])
document_conflict = {"SQLITE_CONSTRAINT_UNIQUE": "Visitor document already registered."}


@router.post("/", response_model=schemas.Visitante, status_code=201)
def create_visitor(visitor: schemas.VisitanteCreate, db: Database) -> models.Visitante:
    record = models.Visitante(**visitor.model_dump())
    db.add(record)
    commit(db, document_conflict)
    return record


@router.get("/", response_model=list[schemas.Visitante])
def list_visitors(
    db: Database, skip: Offset = 0, limit: Limit = 100
) -> list[models.Visitante]:
    statement = (
        select(models.Visitante).order_by(models.Visitante.id).offset(skip).limit(limit)
    )
    return list(db.scalars(statement))


@router.get("/{visitante_id}", response_model=schemas.Visitante)
def read_visitor(visitante_id: schemas.ResourceId, db: Database) -> models.Visitante:
    visitor = db.get(models.Visitante, visitante_id)
    if visitor is None:
        raise HTTPException(404, "Visitor not found.")
    return visitor


@router.put("/{visitante_id}", response_model=schemas.Visitante)
def update_visitor(
    visitante_id: schemas.ResourceId, visitor: schemas.VisitanteCreate, db: Database
) -> models.Visitante:
    record = read_visitor(visitante_id, db)
    record.nome = visitor.nome
    record.documento = visitor.documento
    record.telefone = visitor.telefone
    commit(db, document_conflict)
    return record


@router.delete("/{visitante_id}", status_code=204)
def delete_visitor(visitante_id: schemas.ResourceId, db: Database) -> Response:
    db.delete(read_visitor(visitante_id, db))
    commit(db, {"SQLITE_CONSTRAINT_FOREIGNKEY": "Visitor has access history."})
    return Response(status_code=204)
