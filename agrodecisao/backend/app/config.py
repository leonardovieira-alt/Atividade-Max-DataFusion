import os
from pathlib import Path

# MongoDB: local (padrão) ou MongoDB Atlas (mongodb+srv://usuario:senha@cluster.mongodb.net/)
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "agro")

DATA_DIR = Path(os.getenv("DATA_DIR", Path(__file__).resolve().parents[2] / "data"))
# SQLite é só um arquivo: não precisa instalar nem subir servidor
SQLITE_PATH = os.getenv("SQLITE_PATH", str(DATA_DIR / "agro.sqlite"))

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
AWESOME_API_URL = "https://economia.awesomeapi.com.br/json/last/USD-BRL"
