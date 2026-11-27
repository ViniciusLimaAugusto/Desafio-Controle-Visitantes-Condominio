from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Visitante(Base):
    __tablename__ = "visitantes"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str]
    documento: Mapped[str] = mapped_column(unique=True)
    telefone: Mapped[str | None]


class Condominio(Base):
    __tablename__ = "condominios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(unique=True)
    endereco: Mapped[str]

    unidades: Mapped[list["Unidade"]] = relationship(
        back_populates="condominio", order_by="Unidade.id"
    )


class Unidade(Base):
    __tablename__ = "unidades"

    id: Mapped[int] = mapped_column(primary_key=True)
    numero: Mapped[str]
    bloco: Mapped[str | None]
    condominio_id: Mapped[int] = mapped_column(ForeignKey("condominios.id"), index=True)

    condominio: Mapped[Condominio] = relationship(back_populates="unidades")
    movimentacoes: Mapped[list["Movimentacao"]] = relationship(
        back_populates="unidade", order_by="Movimentacao.id"
    )


class Movimentacao(Base):
    __tablename__ = "movimentacoes"
    __table_args__ = (
        CheckConstraint(
            "(ativa = 1 AND data_hora_saida IS NULL) OR "
            "(ativa = 0 AND data_hora_saida IS NOT NULL)",
            name="ck_movement_exit_state",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    visitante_id: Mapped[int] = mapped_column(ForeignKey("visitantes.id"), index=True)
    unidade_id: Mapped[int] = mapped_column(ForeignKey("unidades.id"), index=True)
    data_hora_entrada: Mapped[datetime]
    data_hora_saida: Mapped[datetime | None]
    observacoes: Mapped[str | None]
    ativa: Mapped[bool]

    visitante: Mapped[Visitante] = relationship()
    unidade: Mapped[Unidade] = relationship(back_populates="movimentacoes")


active_entry_index = Index(
    "uq_movement_active_visitor_unit",
    Movimentacao.visitante_id,
    Movimentacao.unidade_id,
    unique=True,
    sqlite_where=Movimentacao.ativa == 1,
)
