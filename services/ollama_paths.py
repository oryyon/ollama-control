"""Detectarea directorului în care serverul Ollama păstrează modelele.

Ollama poate stoca modelele în mai multe locuri, în funcție de modul de
instalare și de variabilele de mediu:

- instalare oficială cu serviciu systemd: ``/usr/share/ollama/.ollama/models``;
- instalare cu ``ollama serve`` pornit de utilizator: ``~/.ollama/models``;
- override prin variabila de mediu ``OLLAMA_MODELS``.

Pe aceeași mașină pot exista simultan mai multe variante, iar unele pot fi
goale. De aceea alegem directorul care conține efectiv manifestele modelelor
raportate de server, nu doar primul existent.
"""

import os
import subprocess
from pathlib import Path
from typing import TypedDict

from utils.logging_config import logger

#: Formatele de manifest folosite de Ollama. Versiunile noi scriu în
#: `manifests-v2/<domeniu>/library/`, iar cele vechi în
#: `manifests/registry.ollama.ai/library/`. Pe aceeași mașină pot exista
#: simultan ambele, pentru că formatul nou nu șterge formatul vechi.
MANIFEST_LAYOUTS = (
    ("manifests-v2", "ollama.com", "library"),
    ("manifests", "registry.ollama.ai", "library"),
)


#: Locația implicită pentru instalarea oficială (serviciu systemd, user `ollama`).
SYSTEM_MODELS_DIR = Path("/usr/share/ollama/.ollama/models")

#: Locația implicită pentru o rulare cu drepturi de utilizator.
USER_MODELS_DIR = Path.home() / ".ollama" / "models"


class ModelsDirectoryInfo(TypedDict):
    """Informațiile afișate în dialogul cu calea modelelor."""

    path: str
    exists: bool
    model_count: int


def _din_environment() -> Path | None:
    """Directorul setat explicit prin variabila de mediu `OLLAMA_MODELS`."""
    valoare = os.environ.get("OLLAMA_MODELS", "").strip()
    if not valoare:
        return None
    return Path(valoare).expanduser()


def _candidati() -> list[Path]:
    """Toate locațiile posibile, în ordinea preferinței."""
    candidati: list[Path] = []

    din_env = _din_environment()
    if din_env is not None:
        candidati.append(din_env)

    candidati.append(SYSTEM_MODELS_DIR)
    candidati.append(USER_MODELS_DIR)

    # Eliminăm duplicatele păstrând ordinea.
    unice: list[Path] = []
    for candidat in candidati:
        if candidat not in unice:
            unice.append(candidat)
    return unice


def _manifest_pentru(director: Path, model: str) -> Path | None:
    """Calea manifestului unui model în structura Ollama.

    Numele din `ollama list` pot fi `nume:tag` sau doar `nume`. Se caută
    în toate formatele de manifest (vechi și nou), fiindcă o mașină
    poate avea simultan modele descărcate cu versiuni diferite de Ollama.
    """
    if ":" in model:
        nume, tag = model.rsplit(":", 1)
    else:
        nume, tag = model, "latest"

    for director_manifeste, domeniu, subdirector in MANIFEST_LAYOUTS:
        candidat = director / director_manifeste / domeniu / subdirector / nume / tag
        if candidat.exists():
            return candidat

    return None


def _modele_in(director: Path) -> int:
    """Câte modele are serverul în directorul dat."""
    try:
        rezultat = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception:
        return 0

    if rezultat.returncode != 0:
        return 0

    modele: list[str] = []
    for linie in (rezultat.stdout or "").splitlines()[1:]:
        parti = linie.split()
        if parti:
            modele.append(parti[0])

    if not modele:
        return 0

    gasite = 0
    for model in modele:
        if _manifest_pentru(director, model) is not None:
            gasite += 1
    return gasite


def get_models_directory() -> Path:
    """Directorul în care serverul Ollama ține modelele.

    Preferă directorul care conține manifestele modelelor raportate de
    `ollama list`. Dacă serverul nu răspunde, revine la prima locație
    existentă, iar dacă niciuna nu există, la locația implicită de sistem.
    """
    candidati = _candidati()

    # 1. Directorul confirmat de server: conține manifestele modelelor.
    for candidat in candidati:
        if candidat.is_dir() and _modele_in(candidat) > 0:
            logger.info("Ollama models directory confirmed: %s", candidat)
            return candidat

    # 2. Prima locație existentă.
    for candidat in candidati:
        if candidat.is_dir():
            logger.info("Ollama models directory (fallback, existing): %s", candidat)
            return candidat

    # 3. Nimic existent — folosim implicitul de sistem.
    logger.info("Ollama models directory (fallback, default): %s", SYSTEM_MODELS_DIR)
    return SYSTEM_MODELS_DIR


def get_models_directory_info() -> ModelsDirectoryInfo:
    """Informații despre directorul modelelor, pentru afișare în UI."""
    director = get_models_directory()
    exista = director.is_dir()

    nume_modele = 0
    try:
        rezultat = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if rezultat.returncode == 0:
            linii = [l for l in (rezultat.stdout or "").splitlines()[1:] if l.split()]
            nume_modele = len(linii)
    except Exception:
        logger.exception("Failed to count Ollama models")

    return {
        "path": str(director),
        "exists": exista,
        "model_count": nume_modele,
    }
