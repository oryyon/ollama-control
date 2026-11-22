import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any

import customtkinter as ctk

#: Directorul temporar în care PyInstaller extrage resursele (doar în build).
#: Atributul există doar la rularea din executabilul înglobat, de aceea îl
#: citim dinamic — `sys._MEIPASS` nu este un atribut cunoscut de tipizator.
_MEIPASS: str | None = getattr(sys, "_MEIPASS", None)

if getattr(sys, "frozen", False) and _MEIPASS:
    BASE_DIR = Path(_MEIPASS)
    APP_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent.parent
    APP_DIR = BASE_DIR

#: Numele aplicației în configurațiile XDG.
APP_NAME = "ollama-control"

#: Directorul în care sunt păstrate setările utilizatorului.
#:
#: Setările nu pot trăi lângă executabil: odată instalată în `/usr/lib`
#: sau montată într-un AppImage, acea locație nu este scrisibilă fără
#: privilegii de root. Folosim `~/.config/ollama-control/` (standard XDG).
def _config_dir() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or ""
    root = Path(base).expanduser() if base else Path.home() / ".config"
    return root / APP_NAME


CONFIG_DIR = _config_dir()
SETTINGS_PATH = CONFIG_DIR / "settings.json"

#: Locația veche a setărilor (înainte de migrarea la XDG). O folosim
#: o singură dată, pentru a prelua setările existente ale utilizatorului.
LEGACY_SETTINGS_PATH = APP_DIR / "settings.json"


def _migrate_legacy_settings() -> None:
    """Mută setările din vechea locație în cea XDG, dacă e cazul."""
    legacy = LEGACY_SETTINGS_PATH
    if legacy == SETTINGS_PATH or not legacy.exists() or SETTINGS_PATH.exists():
        return
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(legacy, SETTINGS_PATH)
    except OSError:
        pass

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
    _migrate_legacy_settings()
    if SETTINGS_PATH.exists():
        try:
            with SETTINGS_PATH.open("r", encoding="utf-8") as f:
                date = json.load(f)
            return {**DEFAULT_SETTINGS, **date}
        except Exception:
            return DEFAULT_SETTINGS.copy()
    return DEFAULT_SETTINGS.copy()


def salveaza_setari() -> None:
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with SETTINGS_PATH.open("w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except OSError:
        # Directorul de configurare poate fi inscriptibil în mod restricționat;
        # pierderea setărilor nu trebuie să oprească aplicația.
        pass


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
