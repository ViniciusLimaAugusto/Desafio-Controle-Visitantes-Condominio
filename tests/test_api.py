from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(str(tmp_path / "test.db"), seed=False)) as test_client:
        yield test_client


def create_visitor(client, document="DEMO-001"):
    response = client.post(
        "/visitantes/", json={"nome": "Example Visitor", "documento": document}
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_unit(client):
    response = client.post(
        "/condominios/", json={"nome": "Demo", "endereco": "Example Street"}
    )
    assert response.status_code == 201, response.text
    condominium = response.json()
    response = client.post(
        f"/condominios/{condominium['id']}/unidades/",
        json={"numero": "101", "condominio_id": condominium["id"]},
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
def entry(client):
    return {
        "visitante_id": create_visitor(client)["id"],
        "unidade_id": create_unit(client)["id"],
    }


def test_visit_management_and_unique_document(client):
    visitor = create_visitor(client)
    other = create_visitor(client, "DEMO-002")
    url = f"/visitantes/{visitor['id']}"
    assert client.get(url).json() == visitor
    assert client.post("/visitantes/", json=visitor).status_code == 409
    assert client.put(url, json=other).status_code == 409
    changed = visitor | {"nome": "Updated visitor", "telefone": "555-0100"}
    assert client.put(url, json=changed).json() == changed
    assert client.put(url, json=visitor).json()["telefone"] is None
    response = client.delete(url)
    assert response.status_code == 204 and not response.content
    assert client.get(url).status_code == 404


def test_condominium_unit_relationship(client):
    unit = create_unit(client)
    url = f"/condominios/{unit['condominio_id']}"
    assert client.get(f"{url}/unidades").json() == [unit]
    assert client.get(f"{url}/unidades", params={"skip": 100}).json() == []
    summary = client.get(url).json()
    assert summary["unidades"][0]["id"] == unit["id"]
    assert client.get("/condominios/relacao/unidades").json() == [summary]
    body = {"numero": "202", "condominio_id": 999}
    assert client.post(f"{url}/unidades/", json=body).status_code == 400
    assert client.post("/condominios/999/unidades/", json=body).status_code == 404
    assert client.get("/condominios/999/unidades").status_code == 404


def test_entry_exit_history_and_integrity(client, entry):
    response = client.post("/controle-acesso/entrada", json=entry)
    assert response.status_code == 201, response.text
    movement = response.json()
    assert movement["ativa"] and movement["data_hora_saida"] is None
    assert set(movement["visitante"]) == {"id", "nome"}
    assert client.post("/controle-acesso/entrada", json=entry).status_code == 409
    visitor_url = f"/visitantes/{entry['visitante_id']}"
    assert client.delete(visitor_url).status_code == 409
    exit_url = f"/controle-acesso/saida/{movement['id']}"
    response = client.put(exit_url)
    assert response.status_code == 200, response.text
    closed = response.json()
    assert not closed["ativa"] and closed["data_hora_saida"] is not None
    assert client.put(exit_url).status_code == 409
    assert client.delete(visitor_url).status_code == 409
    history = f"/controle-acesso/unidades/{entry['unidade_id']}/movimentacoes"
    assert client.get(history).json() == [closed]
    assert client.post("/controle-acesso/entrada", json=entry).status_code == 201
    assert len(client.get(history).json()) == 2


@pytest.mark.parametrize(
    ("method", "path", "payload", "status"),
    [
        ("POST", "/visitantes/", {"nome": " ", "documento": "DEMO-001"}, 422),
        ("POST", "/visitantes/", {"nome": "Example"}, 422),
        ("POST", "/controle-acesso/entrada", {"visitante_id": 0, "unidade_id": 1}, 422),
        ("GET", "/visitantes/9223372036854775808", None, 422),
        ("GET", "/visitantes/?limit=101", None, 422),
        ("GET", "/visitantes/?skip=-1", None, 422),
        ("GET", "/condominios/999", None, 404),
        ("PUT", "/controle-acesso/saida/999", None, 404),
        ("GET", "/controle-acesso/unidades/999/movimentacoes", None, 404),
    ],
)
def test_invalid_requests(client, method, path, payload, status):
    response = client.request(method, path, json=payload)
    assert response.status_code == status, response.text
    if status == 422:
        assert all("input" not in error for error in response.json()["detail"])


@pytest.mark.parametrize("field", ["visitante_id", "unidade_id"])
def test_entry_requires_existing_resources(client, entry, field):
    assert (
        client.post("/controle-acesso/entrada", json=entry | {field: 999}).status_code
        == 404
    )


def test_simultaneous_entries_and_exits(client, entry):
    def parallel(request):
        barrier = Barrier(2)

        def send(_):
            barrier.wait(timeout=5)
            return request().status_code

        with ThreadPoolExecutor(max_workers=2) as pool:
            return sorted(pool.map(send, range(2)))

    assert parallel(lambda: client.post("/controle-acesso/entrada", json=entry)) == [
        201,
        409,
    ]
    history = f"/controle-acesso/unidades/{entry['unidade_id']}/movimentacoes"
    (movement,) = client.get(history).json()
    url = f"/controle-acesso/saida/{movement['id']}"
    assert parallel(lambda: client.put(url)) == [200, 409]


def test_health_and_repeatable_opt_in_seed(tmp_path):
    database_path = str(tmp_path / "demo.db")
    for _ in range(2):
        with TestClient(create_app(database_path, seed=True)) as client:
            assert client.get("/health").json() == {"status": "ok"}
            assert len(client.get("/condominios/relacao/unidades").json()) == 1
            assert len(client.get("/visitantes/").json()) == 1


def test_adds_active_entry_index_to_existing_database(tmp_path):
    from sqlite3 import connect

    path = tmp_path / "existing.db"
    with connect(path) as db:
        db.executescript("""
            CREATE TABLE visitantes (
                id INTEGER PRIMARY KEY, nome TEXT, documento TEXT UNIQUE, telefone TEXT
            );
            CREATE TABLE condominios (
                id INTEGER PRIMARY KEY, nome TEXT UNIQUE, endereco TEXT
            );
            CREATE TABLE unidades (
                id INTEGER PRIMARY KEY, numero TEXT, bloco TEXT,
                condominio_id INTEGER REFERENCES condominios(id)
            );
            CREATE TABLE movimentacoes (
                id INTEGER PRIMARY KEY, visitante_id INTEGER REFERENCES visitantes(id),
                unidade_id INTEGER REFERENCES unidades(id), data_hora_entrada DATETIME,
                data_hora_saida DATETIME, observacoes TEXT, ativa BOOLEAN
            );
            INSERT INTO visitantes VALUES (1, 'Legacy Visitor', 'DEMO-LEGACY', NULL);
            INSERT INTO condominios VALUES (1, 'Legacy Condominium', 'Example Street');
            INSERT INTO unidades VALUES (1, '101', 'A', 1);
            INSERT INTO movimentacoes VALUES (1, 1, 1, '2025-01-01 10:00:00', NULL, NULL, 1);
        """)
    with TestClient(create_app(str(path), seed=False)) as client:
        history = client.get("/controle-acesso/unidades/1/movimentacoes")
        (movement,) = history.json()
        assert movement["id"] == 1 and movement["ativa"] is True
        entry = {"visitante_id": 1, "unidade_id": 1}
        assert client.post("/controle-acesso/entrada", json=entry).status_code == 409
        assert client.delete("/visitantes/1").status_code == 409
        assert client.put("/controle-acesso/saida/1").status_code == 200
        assert client.post("/controle-acesso/entrada", json=entry).status_code == 201
