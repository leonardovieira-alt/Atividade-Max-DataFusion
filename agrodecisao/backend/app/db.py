"""Acesso aos armazenamentos.

- MongoDB: talhões, clima bruto (JSON da API) e clima diário tratado.
- SQLite:  histórico tabular (produtividade e cotações), carregado pelo Apache Hop.
- DuckDB:  usado em analytics.py (em memória, não precisa de arquivo).
"""
import csv
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from pymongo import MongoClient

from . import config

SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS produtividade (
    talhao_id           INTEGER NOT NULL,
    safra               TEXT    NOT NULL,
    produtividade_t_ha  REAL    NOT NULL,
    custo_ha_brl        REAL    NOT NULL,
    PRIMARY KEY (talhao_id, safra)
);
CREATE TABLE IF NOT EXISTS cotacoes (
    data     TEXT NOT NULL,      -- AAAA-MM-DD
    produto  TEXT NOT NULL,
    preco    REAL NOT NULL,
    unidade  TEXT NOT NULL,
    PRIMARY KEY (data, produto)
);
"""

_client = None


def mongo():
    global _client
    if _client is None:
        _client = MongoClient(config.MONGO_URI, serverSelectionTimeoutMS=5000)
    return _client[config.MONGO_DB]


@contextmanager
def sqlite():
    conn = sqlite3.connect(config.SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def iniciar_sqlite():
    Path(config.SQLITE_PATH).parent.mkdir(parents=True, exist_ok=True)
    with sqlite() as c:
        c.executescript(SCHEMA_SQLITE)


def iniciar_mongo() -> int:
    """Cria índices e carrega os talhões de exemplo se a coleção estiver vazia."""
    m = mongo()
    m.clima_diario.create_index([("talhao_id", 1), ("data", 1)], unique=True)
    if m.talhoes.count_documents({}) > 0:
        return 0
    with open(config.DATA_DIR / "talhoes.csv", newline="", encoding="utf-8") as f:
        docs = [{
            "_id": int(r["id"]), "nome": r["nome"], "cultura": r["cultura"],
            "area_ha": float(r["area_ha"]), "lat": float(r["lat"]), "lon": float(r["lon"]),
            "data_plantio": r["data_plantio"],
        } for r in csv.DictReader(f)]
    m.talhoes.insert_many(docs)
    return len(docs)


def iniciar():
    iniciar_sqlite()
    iniciar_mongo()
