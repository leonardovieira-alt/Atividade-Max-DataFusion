"""Carregador de contingência: faz o mesmo que o pipeline do Apache Hop.

Lê produtividade.csv e cotacoes.csv e grava no SQLite. Use somente se o Hop
não estiver disponível (ex.: máquina sem Java). O fluxo oficial do projeto é
hop/pipeline_agro.hpl.

    python -m app.carga_csv
"""
import csv

from . import config, db


def _ler(nome: str) -> list[dict]:
    with open(config.DATA_DIR / nome, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def carregar():
    db.iniciar_sqlite()
    prod = _ler("produtividade.csv")
    cot = _ler("cotacoes.csv")
    with db.sqlite() as c:
        c.execute("DELETE FROM produtividade")
        c.executemany(
            "INSERT INTO produtividade VALUES (?,?,?,?)",
            [(int(r["talhao_id"]), r["safra"], float(r["produtividade_t_ha"]),
              float(r["custo_ha_brl"])) for r in prod],
        )
        c.execute("DELETE FROM cotacoes")
        c.executemany(
            "INSERT INTO cotacoes VALUES (?,?,?,?)",
            [(r["data"], r["produto"], float(r["preco"]), r["unidade"]) for r in cot],
        )
    print(f"Carga concluída: {len(prod)} linhas de produtividade, {len(cot)} cotações.")


if __name__ == "__main__":
    carregar()
