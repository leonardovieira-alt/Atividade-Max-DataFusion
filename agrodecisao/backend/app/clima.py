"""Consumo das APIs externas: Open-Meteo (clima) e AwesomeAPI (dólar)."""
import httpx

from .config import AWESOME_API_URL, OPEN_METEO_URL

DAILY_VARS = [
    "temperature_2m_max", "temperature_2m_min", "precipitation_sum",
    "precipitation_probability_max", "wind_speed_10m_max",
    "et0_fao_evapotranspiration",
]


def buscar_clima(lat: float, lon: float, dias_passados: int = 7, dias_futuros: int = 7) -> dict:
    """Retorna o JSON bruto da Open-Meteo (gratuita, sem chave)."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": ",".join(DAILY_VARS),
        "timezone": "America/Sao_Paulo",
        "past_days": dias_passados,
        "forecast_days": dias_futuros,
    }
    r = httpx.get(OPEN_METEO_URL, params=params, timeout=20)
    r.raise_for_status()
    return r.json()


def normalizar_clima(bruto: dict) -> list[dict]:
    """Transforma o JSON colunar da API em uma lista de linhas diárias."""
    d = bruto["daily"]
    linhas = []
    for i, data in enumerate(d["time"]):
        linhas.append({
            "data": data,
            "tmax": d["temperature_2m_max"][i],
            "tmin": d["temperature_2m_min"][i],
            "chuva_mm": d["precipitation_sum"][i],
            "prob_chuva": d["precipitation_probability_max"][i],
            "vento_kmh": d["wind_speed_10m_max"][i],
            "et0_mm": d["et0_fao_evapotranspiration"][i],
        })
    return linhas


def buscar_dolar() -> dict | None:
    """Cotação USD/BRL; o dólar influencia o preço de commodities (soja, milho, café)."""
    try:
        r = httpx.get(AWESOME_API_URL, timeout=10)
        r.raise_for_status()
        u = r.json()["USDBRL"]
        return {"valor": float(u["bid"]), "variacao_pct": float(u["pctChange"]),
                "atualizado_em": u["create_date"]}
    except Exception:
        return None
