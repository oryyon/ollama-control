import json
import re
import sys
from pathlib import Path
from typing import Any

import customtkinter as ctk

if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    BASE_DIR = Path(sys._MEIPASS)
    APP_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent.parent
    APP_DIR = BASE_DIR

SETTINGS_PATH = APP_DIR / "settings.json"

#: Durata implicită de keepalive pentru modelele Ollama: zece minute.
#: Punct unic de adevăr — folosit de interfață, de validare și de rulare.
KEEPALIVE_DEFAULT = "10m"

#: Formatul acceptat pentru keepalive: număr + unitate (s/m/h/d).
_KEEPALIVE_RE = re.compile(r"\d+[smhd]", re.IGNORECASE)


def is_valid_keepalive(value: str) -> bool:
    """Verifică dacă o durată de keepalive are formatul acceptat."""
    return bool(_KEEPALIVE_RE.fullmatch(str(value).strip()))

DEFAULT_SETTINGS: dict[str, Any] = {
    "auto_refresh_interval": 5,
    "confirm_before_stop": True,
    "theme": "dark",
    "ollama_keepalive": KEEPALIVE_DEFAULT,
    "recent_models": [],
    "model_contexts": {},
}

AUTO_REFRESH_MS: int | None = 5000
settings: dict[str, Any] = {}


def incarca_setari() -> dict[str, Any]:
    if SETTINGS_PATH.exists():
        try:
            with SETTINGS_PATH.open("r", encoding="utf-8") as f:
                date = json.load(f)
            return {**DEFAULT_SETTINGS, **date}
        except Exception:
            return DEFAULT_SETTINGS.copy()
    return DEFAULT_SETTINGS.copy()


def salveaza_setari() -> None:
    with SETTINGS_PATH.open("w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)


def aplica_interval_auto_refresh() -> None:
    global AUTO_REFRESH_MS
    interval = settings.get("auto_refresh_interval", 5)
    if interval == 0:
        AUTO_REFRESH_MS = None
    else:
        AUTO_REFRESH_MS = int(interval) * 1000


def aplica_tema() -> None:
    tema = settings.get("theme", "dark")
    ctk.set_appearance_mode(tema)
