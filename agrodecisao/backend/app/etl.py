"""ETL de clima: API Open-Meteo -> MongoDB (bruto) -> MongoDB (tratado)."""
from datetime import datetime, timezone

from . import db
from .clima import buscar_clima, normalizar_clima


def sincronizar_talhao(talhao: dict) -> int:
    # 1) Extract: consulta a API usando as coordenadas do talhão
    bruto = buscar_clima(talhao["lat"], talhao["lon"])
    agora = datetime.now(timezone.utc)

    # 2) Load raw: guarda o JSON original (auditoria e reprocessamento)
    db.mongo().clima_raw.insert_one({
        "talhao_id": talhao["_id"],
        "buscado_em": agora,
        "fonte": "open-meteo",
        "payload": bruto,
    })

    # 3) Transform + Load: série diária limpa, com upsert (não duplica ao reexecutar)
    linhas = normalizar_clima(bruto)
    col = db.mongo().clima_diario
    for l in linhas:
        col.update_one(
            {"talhao_id": talhao["_id"], "data": l["data"]},
            {"$set": {**l, "talhao_id": talhao["_id"], "atualizado_em": agora}},
            upsert=True,
        )
    return len(linhas)


def sincronizar_todos() -> dict:
    resultado = {}
    for t in db.mongo().talhoes.find().sort("_id", 1):
        try:
            resultado[t["_id"]] = {"ok": True, "linhas": sincronizar_talhao(t)}
        except Exception as e:  # falha de API em um talhão não derruba os demais
            resultado[t["_id"]] = {"ok": False, "erro": str(e)}
    return resultado


if __name__ == "__main__":
    db.iniciar()
    print(sincronizar_todos())
