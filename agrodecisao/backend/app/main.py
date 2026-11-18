from contextlib import asynccontextmanager
from datetime import date

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import analytics, db, etl
from .clima import buscar_dolar
from .regras import gerar_recomendacoes


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Cria tabelas do SQLite, índices do MongoDB e carrega os talhões de exemplo.
    try:
        db.iniciar()
    except Exception as e:
        print(f"AVISO: não foi possível inicializar os bancos: {e}")
    yield


app = FastAPI(title="AgroDecisão API", version="2.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def _talhao_dict(t: dict) -> dict:
    return {"id": t["_id"], **{k: v for k, v in t.items() if k != "_id"}}


def _talhao(talhao_id: int) -> dict:
    t = db.mongo().talhoes.find_one({"_id": talhao_id})
    if not t:
        raise HTTPException(404, "Talhão não encontrado")
    return _talhao_dict(t)


def _clima(talhao_id: int) -> list[dict]:
    cursor = db.mongo().clima_diario.find(
        {"talhao_id": talhao_id}, {"_id": 0, "atualizado_em": 0}
    ).sort("data", 1)
    return list(cursor)


def _todos_talhoes() -> list[dict]:
    return [_talhao_dict(t) for t in db.mongo().talhoes.find().sort("_id", 1)]


@app.get("/api/health")
def health():
    status = {}
    try:
        db.mongo().command("ping")
        status["mongodb"] = "ok"
    except Exception as e:
        status["mongodb"] = f"erro: {e}"
    try:
        with db.sqlite() as c:
            c.execute("SELECT 1")
        status["sqlite"] = "ok"
    except Exception as e:
        status["sqlite"] = f"erro: {e}"
    status["duckdb"] = "ok"
    return status


@app.get("/api/talhoes")
def talhoes():
    return _todos_talhoes()


@app.post("/api/etl/clima")
def rodar_etl():
    """Integração: Open-Meteo -> MongoDB (bruto) -> MongoDB (tratado)."""
    return etl.sincronizar_todos()


@app.get("/api/talhoes/{talhao_id}/clima")
def clima(talhao_id: int):
    _talhao(talhao_id)
    return _clima(talhao_id)


@app.get("/api/talhoes/{talhao_id}/recomendacoes")
def recomendacoes(talhao_id: int):
    t = _talhao(talhao_id)
    return gerar_recomendacoes(_clima(talhao_id), t["cultura"], hoje=str(date.today()))


@app.get("/api/resumo")
def resumo():
    """Alertas de maior severidade de todos os talhões, para a tela inicial."""
    saida = []
    for t in _todos_talhoes():
        recs = gerar_recomendacoes(_clima(t["id"]), t["cultura"], hoje=str(date.today()))
        criticos = [r for r in recs if r["severidade"] in ("alta", "media")]
        saida.append({"talhao_id": t["id"], "nome": t["nome"], "cultura": t["cultura"],
                      "alertas": len(criticos), "proximo": criticos[0] if criticos else None})
    return saida


@app.get("/api/cotacoes")
def cotacoes():
    with db.sqlite() as c:
        rows = c.execute("""
            SELECT c.produto, c.data, c.preco, c.unidade
            FROM cotacoes c
            JOIN (SELECT produto, MAX(data) AS d FROM cotacoes GROUP BY produto) m
              ON m.produto = c.produto AND m.d = c.data
            ORDER BY c.produto
        """).fetchall()
    return {"ultimas": [dict(r) for r in rows], "dolar": buscar_dolar()}


@app.get("/api/analytics/margem")
def margem():
    """DuckDB cruza talhões (MongoDB) com produtividade e cotações (SQLite)."""
    with db.sqlite() as c:
        prod = [dict(r) for r in c.execute("SELECT * FROM produtividade")]
        cot = [dict(r) for r in c.execute("SELECT * FROM cotacoes")]
    return analytics.margem_por_talhao(_todos_talhoes(), prod, cot)
