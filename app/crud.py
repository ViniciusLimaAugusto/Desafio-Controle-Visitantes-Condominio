from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from .models import Condominio, Movimentacao, Unidade, Visitante
from .schemas import MovimentacaoCreate


def record_entry(db: Session, entry: MovimentacaoCreate) -> Movimentacao | None:
    statement = (
        insert(Movimentacao)
        .values(**entry.model_dump(), data_hora_entrada=utc_now(), ativa=True)
        .on_conflict_do_nothing(
            index_elements=[Movimentacao.visitante_id, Movimentacao.unidade_id],
            index_where=Movimentacao.ativa == 1,
        )
        .returning(Movimentacao)
    )
    movement = db.scalars(statement).one_or_none()
    db.commit()
    return movement


def record_exit(db: Session, movement_id: int) -> Movimentacao | None:
    statement = (
        update(Movimentacao)
        .where(Movimentacao.id == movement_id, Movimentacao.ativa.is_(True))
        .values(ativa=False, data_hora_saida=utc_now())
        .returning(Movimentacao)
    )
    movement = db.scalars(statement).one_or_none()
    db.commit()
    return movement


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def seed_demo(db: Session) -> None:
    if db.scalar(select(Condominio.id).limit(1)) is not None:
        return

    db.add_all(
        [
            Condominio(
                nome="Demo Condominium",
                endereco="100 Example Street",
                unidades=[Unidade(numero="101", bloco="A")],
            ),
            Visitante(nome="Demo Visitor", documento="DEMO-001"),
        ]
    )
    db.commit()
