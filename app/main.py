import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from .crud import seed_demo
from .database import Base, build_engine
from .models import active_entry_index
from .routers import condominios, controle_acesso, visitantes


def create_app(
    database_path: str | None = None, *, seed: bool | None = None
) -> FastAPI:
    seed_demo_data = seed if seed is not None else os.getenv("SEED_DEMO_DATA") == "1"

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        engine = build_engine(database_path)
        application.state.engine = engine
        try:
            with engine.begin() as connection:
                Base.metadata.create_all(connection)
                if connection.exec_driver_sql("PRAGMA foreign_key_check").first():
                    raise RuntimeError(
                        "The SQLite database contains invalid foreign keys."
                    )
                invalid_states = connection.exec_driver_sql(
                    "SELECT 1 FROM movimentacoes WHERE visitante_id IS NULL "
                    "OR unidade_id IS NULL OR data_hora_entrada IS NULL OR ativa IS NULL "
                    "OR ativa NOT IN (0, 1) OR (ativa = 1 AND data_hora_saida IS NOT NULL) "
                    "OR (ativa = 0 AND data_hora_saida IS NULL) LIMIT 1"
                )
                if invalid_states.first():
                    raise RuntimeError(
                        "The SQLite database contains inconsistent movements."
                    )
                active_entry_index.create(connection, checkfirst=True)
            if seed_demo_data:
                with Session(engine) as db:
                    seed_demo(db)
            yield
        finally:
            engine.dispose()

    application = FastAPI(
        title="Condominium Visitor Control API",
        description="Manage visitors, units, and access movements. Use fictional data only.",
        version="1.0.0",
        lifespan=lifespan,
    )

    @application.exception_handler(RequestValidationError)
    async def validation_error(
        _: Request, error: RequestValidationError
    ) -> JSONResponse:
        detail = [
            {key: item[key] for key in ("type", "loc", "msg")}
            for item in error.errors()
        ]
        return JSONResponse({"detail": detail}, status_code=422)

    application.include_router(visitantes.router)
    application.include_router(condominios.router)
    application.include_router(controle_acesso.router)

    @application.get("/")
    def read_root() -> dict[str, str]:
        return {"message": "Bem-vindo à API de Controle de Visitantes!"}

    @application.get("/health", tags=["Health"])
    def health() -> dict[str, str]:
        with application.state.engine.connect() as connection:
            connection.execute(text("SELECT 1 FROM movimentacoes LIMIT 1")).first()
        return {"status": "ok"}

    return application


app = create_app()
