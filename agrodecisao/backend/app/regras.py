"""Motor de regras agronômicas.

Recebe a série diária de clima de um talhão (lista de dicts) e devolve
recomendações acionáveis. Funções puras: não dependem de banco nem de rede,
o que facilita teste e explicação na apresentação.
"""
from __future__ import annotations

# Culturas sensíveis a geada
CULTURAS_SENSIVEIS_GEADA = {"cafe", "batata", "milho", "soja"}

LIMITE_GEADA_ALTA = 1.0     # °C de mínima
LIMITE_GEADA_MEDIA = 3.0
VENTO_MAX_PULVERIZACAO = 10.0   # km/h
PROB_CHUVA_MAX_PULVERIZACAO = 30.0  # %
TMAX_PULVERIZACAO = 30.0    # °C
CHUVA_ADIAR_COLHEITA = 20.0  # mm
DEFICIT_HIDRICO_ALERTA = -15.0  # mm (chuva - evapotranspiração, 7 dias)


def _num(valor, padrao=0.0):
    return padrao if valor is None else float(valor)


def risco_geada(dias: list[dict], cultura: str) -> list[dict]:
    if cultura not in CULTURAS_SENSIVEIS_GEADA:
        return []
    saida = []
    for d in dias:
        tmin = d.get("tmin")
        if tmin is None:
            continue
        if tmin <= LIMITE_GEADA_ALTA:
            sev = "alta"
        elif tmin <= LIMITE_GEADA_MEDIA:
            sev = "media"
        else:
            continue
        saida.append({
            "tipo": "geada",
            "severidade": sev,
            "data": str(d["data"]),
            "mensagem": f"Mínima prevista de {tmin:.1f}°C: risco de geada em {cultura}. "
                        "Avalie proteção/irrigação noturna.",
        })
    return saida


def janelas_pulverizacao(dias: list[dict]) -> list[dict]:
    saida = []
    for d in dias:
        vento = _num(d.get("vento_kmh"), 99)
        prob = _num(d.get("prob_chuva"), 100)
        tmax = _num(d.get("tmax"), 99)
        if vento <= VENTO_MAX_PULVERIZACAO and prob <= PROB_CHUVA_MAX_PULVERIZACAO \
                and tmax <= TMAX_PULVERIZACAO:
            saida.append({
                "tipo": "pulverizacao",
                "severidade": "info",
                "data": str(d["data"]),
                "mensagem": f"Janela favorável para pulverização: vento {vento:.0f} km/h, "
                            f"chuva {prob:.0f}%, máx {tmax:.0f}°C.",
            })
    return saida


def balanco_hidrico(dias: list[dict], janela: int = 7) -> list[dict]:
    """Soma chuva - ET0 nos últimos `janela` dias com dados."""
    recorte = dias[-janela:]
    if not recorte:
        return []
    chuva = sum(_num(d.get("chuva_mm")) for d in recorte)
    et0 = sum(_num(d.get("et0_mm")) for d in recorte)
    saldo = chuva - et0
    if saldo <= DEFICIT_HIDRICO_ALERTA:
        return [{
            "tipo": "deficit_hidrico",
            "severidade": "alta" if saldo <= 2 * DEFICIT_HIDRICO_ALERTA else "media",
            "data": str(recorte[-1]["data"]),
            "mensagem": f"Balanço hídrico de {saldo:.0f} mm em {len(recorte)} dias "
                        f"(chuva {chuva:.0f} mm vs. evapotranspiração {et0:.0f} mm). "
                        "Considere irrigar.",
        }]
    return []


def alerta_colheita(dias: list[dict], cultura: str, hoje: str | None = None) -> list[dict]:
    """Chuva forte prevista: adiar colheita/operações de campo."""
    saida = []
    for d in dias:
        if hoje and str(d["data"]) < hoje:
            continue
        if _num(d.get("chuva_mm")) >= CHUVA_ADIAR_COLHEITA:
            saida.append({
                "tipo": "colheita",
                "severidade": "media",
                "data": str(d["data"]),
                "mensagem": f"Chuva de {_num(d.get('chuva_mm')):.0f} mm prevista: "
                            f"evite colher/operar máquinas em {cultura} neste dia.",
            })
    return saida


def gerar_recomendacoes(dias: list[dict], cultura: str, hoje: str | None = None) -> list[dict]:
    futuros = [d for d in dias if not hoje or str(d["data"]) >= hoje]
    recs = (
        risco_geada(futuros, cultura)
        + janelas_pulverizacao(futuros)
        + balanco_hidrico(dias)
        + alerta_colheita(dias, cultura, hoje)
    )
    ordem = {"alta": 0, "media": 1, "info": 2}
    return sorted(recs, key=lambda r: (ordem[r["severidade"]], r["data"]))
