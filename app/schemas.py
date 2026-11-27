from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

ResourceId = Annotated[int, Field(gt=0, le=2**63 - 1)]


class Input(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class Output(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class VisitanteCreate(Input):
    nome: Annotated[str, StringConstraints(min_length=1, max_length=120)]
    documento: Annotated[str, StringConstraints(min_length=1, max_length=40)]
    telefone: Annotated[str, StringConstraints(min_length=1, max_length=40)] | None = (
        None
    )


class VisitorSummary(Output):
    id: int
    nome: str


class Visitante(VisitorSummary):
    documento: str
    telefone: str | None


class CondominioCreate(Input):
    nome: Annotated[str, StringConstraints(min_length=1, max_length=120)]
    endereco: Annotated[str, StringConstraints(min_length=1, max_length=240)]


class CondominiumSummary(Output):
    id: int
    nome: str
    endereco: str


class UnidadeCreate(Input):
    numero: Annotated[str, StringConstraints(min_length=1, max_length=40)]
    bloco: Annotated[str, StringConstraints(min_length=1, max_length=40)] | None = None
    condominio_id: ResourceId


class UnitSummary(Output):
    id: int
    numero: str
    bloco: str | None
    condominio_id: int


class Condominio(CondominiumSummary):
    unidades: list[UnitSummary] = Field(default_factory=list)


class MovimentacaoCreate(Input):
    visitante_id: ResourceId
    unidade_id: ResourceId
    observacoes: Annotated[str, StringConstraints(max_length=500)] | None = None


class MovementSummary(Output):
    id: int
    visitante_id: int
    unidade_id: int
    observacoes: str | None
    data_hora_entrada: datetime
    data_hora_saida: datetime | None
    ativa: bool


class Movimentacao(MovementSummary):
    visitante: VisitorSummary
    unidade: UnitSummary


class Unidade(UnitSummary):
    condominio: CondominiumSummary
    movimentacoes: list[MovementSummary] = Field(default_factory=list)
