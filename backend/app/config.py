import os
from pathlib import Path

# Lädt Werte aus einer .env-Datei (falls vorhanden), ohne zusätzliche Abhängigkeit.
def _load_dotenv(path: Path):
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


BASE_DIR = Path(__file__).resolve().parent.parent
_load_dotenv(BASE_DIR / ".env")


class Settings:
    tankerkoenig_api_key: str = os.environ.get("TANKERKOENIG_API_KEY", "")
    db_path: str = os.environ.get("DB_PATH", str(BASE_DIR / "spritpreis.db"))
    poll_intervall_sekunden: int = int(os.environ.get("POLL_INTERVALL_SEKUNDEN", "300"))
    cors_origins: list[str] = os.environ.get("CORS_ORIGINS", "*").split(",")


settings = Settings()
