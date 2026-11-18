"""Camada analítica em DuckDB.

Recebe dados vindos de dois armazenamentos diferentes (talhões do MongoDB;
produtividade e cotações do SQLite) e os cruza com SQL analítico em memória,
calculando receita e margem por talhão e safra.
"""
import duckdb

# fator de conversão: produtividade em t/ha -> sacas/ha, por cultura
SACAS_POR_TONELADA = {"cafe": 1000 / 60, "milho": 1000 / 60, "soja": 1000 / 60, "batata": 1000 / 50}

COLUNAS = ["talhao_id", "nome", "cultura", "safra", "produtividade_t_ha", "sacas_ha",
           "preco_saca", "receita_ha", "custo_ha", "margem_ha", "margem_total"]


def margem_por_talhao(talhoes: list[dict], produtividade: list[dict], cotacoes: list[dict]) -> list[dict]:
    if not (talhoes and produtividade and cotacoes):
        return []
    con = duckdb.connect(":memory:")
    con.execute("CREATE TABLE talhoes(id INTEGER, nome VARCHAR, cultura VARCHAR, area_ha DOUBLE)")
    con.executemany("INSERT INTO talhoes VALUES (?,?,?,?)",
                    [(t["id"], t["nome"], t["cultura"], float(t["area_ha"])) for t in talhoes])
    con.execute("CREATE TABLE produtividade(talhao_id INTEGER, safra VARCHAR, "
                "produtividade_t_ha DOUBLE, custo_ha_brl DOUBLE)")
    con.executemany("INSERT INTO produtividade VALUES (?,?,?,?)",
                    [(p["talhao_id"], p["safra"], float(p["produtividade_t_ha"]),
                      float(p["custo_ha_brl"])) for p in produtividade])
    con.execute("CREATE TABLE cotacoes(data VARCHAR, produto VARCHAR, preco DOUBLE, unidade VARCHAR)")
    con.executemany("INSERT INTO cotacoes VALUES (?,?,?,?)",
                    [(c["data"], c["produto"], float(c["preco"]), c["unidade"]) for c in cotacoes])
    con.execute("CREATE TABLE fator(cultura VARCHAR, sacas_t DOUBLE)")
    con.executemany("INSERT INTO fator VALUES (?,?)", list(SACAS_POR_TONELADA.items()))

    rows = con.execute("""
        WITH preco_atual AS (
            SELECT produto, arg_max(preco, data) AS preco FROM cotacoes GROUP BY produto
        )
        SELECT t.id, t.nome, t.cultura, p.safra,
               p.produtividade_t_ha,
               round(p.produtividade_t_ha * f.sacas_t, 1)                              AS sacas_ha,
               pa.preco                                                                 AS preco_saca,
               round(p.produtividade_t_ha * f.sacas_t * pa.preco, 0)                    AS receita_ha,
               p.custo_ha_brl                                                           AS custo_ha,
               round(p.produtividade_t_ha * f.sacas_t * pa.preco - p.custo_ha_brl, 0)   AS margem_ha,
               round(t.area_ha * (p.produtividade_t_ha * f.sacas_t * pa.preco - p.custo_ha_brl), 0)
                                                                                        AS margem_total
        FROM produtividade p
        JOIN talhoes t       ON t.id = p.talhao_id
        JOIN fator f         ON f.cultura = t.cultura
        JOIN preco_atual pa  ON pa.produto = t.cultura
        ORDER BY t.id, p.safra
    """).fetchall()
    return [dict(zip(COLUNAS, r)) for r in rows]
