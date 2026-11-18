import csv
from pathlib import Path

from app.analytics import margem_por_talhao
from app.regras import gerar_recomendacoes

DATA = Path(__file__).resolve().parents[2] / "data"


def dia(data, tmin=15, tmax=26, chuva=0, prob=10, vento=6, et0=4):
    return dict(data=data, tmin=tmin, tmax=tmax, chuva_mm=chuva, prob_chuva=prob,
                vento_kmh=vento, et0_mm=et0)


def test_geada_alta_para_cafe():
    recs = gerar_recomendacoes([dia("2026-07-10", tmin=0.5)], "cafe")
    assert any(r["tipo"] == "geada" and r["severidade"] == "alta" for r in recs)


def test_sem_geada_com_temperatura_amena():
    recs = gerar_recomendacoes([dia("2026-07-10", tmin=12)], "cafe")
    assert not any(r["tipo"] == "geada" for r in recs)


def test_janela_pulverizacao_favoravel_e_bloqueada_por_vento():
    ok = gerar_recomendacoes([dia("2026-07-10", vento=6)], "soja")
    ruim = gerar_recomendacoes([dia("2026-07-10", vento=22)], "soja")
    assert any(r["tipo"] == "pulverizacao" for r in ok)
    assert not any(r["tipo"] == "pulverizacao" for r in ruim)


def test_deficit_hidrico():
    dias = [dia(f"2026-07-{i:02d}", chuva=0, et0=5) for i in range(1, 8)]  # saldo -35 mm
    recs = gerar_recomendacoes(dias, "milho")
    assert any(r["tipo"] == "deficit_hidrico" for r in recs)


def test_colheita_adiada_com_chuva_forte():
    recs = gerar_recomendacoes([dia("2026-07-10", chuva=35)], "cafe")
    assert any(r["tipo"] == "colheita" for r in recs)


def _csv(nome):
    with open(DATA / nome, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_margem_duckdb():
    talhoes = [{"id": int(t["id"]), "nome": t["nome"], "cultura": t["cultura"],
                "area_ha": float(t["area_ha"])} for t in _csv("talhoes.csv")]
    prod = [{**p, "talhao_id": int(p["talhao_id"])} for p in _csv("produtividade.csv")]
    linhas = margem_por_talhao(talhoes, prod, _csv("cotacoes.csv"))
    assert len(linhas) == 16
    cafe = [l for l in linhas if l["cultura"] == "cafe" and l["safra"] == "2025/26"][0]
    # 3.3 t/ha * 16.667 sacas/t * R$1672 (cotação mais recente) - R$25800
    assert cafe["margem_ha"] == round(3.3 * (1000 / 60) * 1672 - 25800, 0)


def test_margem_vazia_sem_dados():
    assert margem_por_talhao([], [], []) == []
