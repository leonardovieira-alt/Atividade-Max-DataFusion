"""Teste de ponta a ponta da API com MongoDB simulado (mongomock) e SQLite temporário.

A chamada à Open-Meteo é substituída por um payload fixo, então o teste não
depende de internet nem de um servidor MongoDB.
"""
from datetime import date, timedelta

import mongomock
import pytest
from fastapi.testclient import TestClient

from app import config, db, etl, main
from app.carga_csv import carregar


def payload_fake():
    hoje = date.today()
    dias = [hoje + timedelta(days=i) for i in range(-7, 7)]  # 7 passados + 7 futuros
    n = len(dias)
    tmin = [14.0] * n
    tmin[9] = 0.5  # índice 9 = hoje + 2 dias: geada forte
    return {"daily": {
        "time": [d.isoformat() for d in dias],
        "temperature_2m_max": [26.0] * n,
        "temperature_2m_min": tmin,
        "precipitation_sum": [0.0] * n,
        "precipitation_probability_max": [10] * n,
        "wind_speed_10m_max": [6.0] * n,
        "et0_fao_evapotranspiration": [3.0] * n,
    }}


@pytest.fixture
def client(tmp_path, monkeypatch):
    mdb = mongomock.MongoClient()["agro_teste"]
    monkeypatch.setattr(db, "mongo", lambda: mdb)
    monkeypatch.setattr(config, "SQLITE_PATH", str(tmp_path / "teste.sqlite"))
    monkeypatch.setattr(etl, "buscar_clima", lambda lat, lon: payload_fake())
    monkeypatch.setattr(main, "buscar_dolar",
                        lambda: {"valor": 5.0, "variacao_pct": 0.1, "atualizado_em": "x"})
    db.iniciar()
    carregar()
    return TestClient(main.app), mdb


def test_health(client):
    c, _ = client
    assert c.get("/api/health").json() == {"mongodb": "ok", "sqlite": "ok", "duckdb": "ok"}


def test_talhoes_semeados(client):
    c, _ = client
    r = c.get("/api/talhoes").json()
    assert len(r) == 4 and r[0]["id"] == 1 and r[0]["cultura"] == "cafe"


def test_etl_grava_bruto_e_tratado_no_mongo(client):
    c, mdb = client
    r = c.post("/api/etl/clima").json()
    assert all(v["ok"] for v in r.values()) and len(r) == 4
    assert mdb.clima_raw.count_documents({}) == 4          # JSON bruto
    assert mdb.clima_diario.count_documents({}) == 4 * 14   # série tratada
    c.post("/api/etl/clima")                                 # reexecutar não duplica (upsert)
    assert mdb.clima_diario.count_documents({}) == 4 * 14


def test_clima_e_recomendacoes(client):
    c, _ = client
    c.post("/api/etl/clima")
    assert len(c.get("/api/talhoes/1/clima").json()) == 14
    recs = c.get("/api/talhoes/1/recomendacoes").json()
    assert any(r["tipo"] == "geada" and r["severidade"] == "alta" for r in recs)
    assert any(r["tipo"] == "pulverizacao" for r in recs)


def test_resumo_aponta_alertas(client):
    c, _ = client
    c.post("/api/etl/clima")
    r = c.get("/api/resumo").json()
    assert len(r) == 4 and all(x["alertas"] >= 1 for x in r)


def test_cotacoes_mais_recentes_e_dolar(client):
    c, _ = client
    r = c.get("/api/cotacoes").json()
    assert len(r["ultimas"]) == 4
    assert {x["data"] for x in r["ultimas"]} == {"2026-11-13"}
    assert r["dolar"]["valor"] == 5.0


def test_margem_cruza_mongo_sqlite_duckdb(client):
    c, _ = client
    r = c.get("/api/analytics/margem").json()
    assert len(r) == 16 and all("margem_ha" in x for x in r)


def test_talhao_inexistente(client):
    c, _ = client
    assert c.get("/api/talhoes/99/clima").status_code == 404
