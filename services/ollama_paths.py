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
import shutil
import subprocess
import tempfile
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


class DuplicateManifest(TypedDict):
    """Un model prezent în ambele formate de manifest."""

    model: str
    tag: str
    old_path: str
    new_path: str


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


def _baza_layout(director: Path, layout: tuple[str, str, str]) -> Path:
    director_manifeste, domeniu, subdirector = layout
    return director / director_manifeste / domeniu / subdirector


def find_duplicate_manifests(models_directory: Path) -> list[DuplicateManifest]:
    """Modelele care există atât în formatul vechi, cât și în cel nou.

    Ollama 0.40.x scrie fiecare model nou în două locuri: în
    `manifests-v2/<domeniu>/library/` (manifestul propriu-zis, referit
    printr-un symlink către blob) și în `manifests/<domeniu>/library/` (un
    înveliș pentru clienții vechi, care indică spre blob).

    Copiile din formatul vechi sunt redundante pentru versiunile noi de
    Ollama, dar nu pot fi eliminate automat: la descărcare, serverul le
    scrie din nou.
    """
    layout_nou, layout_vechi = MANIFEST_LAYOUTS[0], MANIFEST_LAYOUTS[1]
    baza_noua = _baza_layout(models_directory, layout_nou)
    baza_veche = _baza_layout(models_directory, layout_vechi)

    if not baza_noua.is_dir() or not baza_veche.is_dir():
        return []

    duplicate: list[DuplicateManifest] = []
    try:
        modele = sorted(p.name for p in baza_noua.iterdir() if p.is_dir())
    except OSError:
        return []

    for model in modele:
        director_model_nou = baza_noua / model
        director_model_vechi = baza_veche / model
        if not director_model_vechi.is_dir():
            continue

        try:
            taguri = sorted(p.name for p in director_model_nou.iterdir())
        except OSError:
            continue

        for tag in taguri:
            cale_noua = director_model_nou / tag
            cale_veche = director_model_vechi / tag

            if not cale_veche.is_file():
                continue
            # Noua intrare trebuie să fie un symlink valid către un blob
            # existent; altfel nu o considerăm o înlocuire sigură.
            if not cale_noua.is_symlink():
                continue
            if not cale_noua.resolve().exists():
                continue

            duplicate.append({
                "model": model,
                "tag": tag,
                "old_path": str(cale_veche),
                "new_path": str(cale_noua),
            })

    return duplicate


def _script_curatare(director: Path, duplicate: list[DuplicateManifest]) -> str:
    """Scriptul de curățare rulat cu privilegii de root."""
    linii = ["#!/bin/sh", "set -e", ""]
    for intrare in duplicate:
        linii.append(f'rm -f "{intrare["old_path"]}"')
    linii.append("")
    # Directorii de model rămși goi sunt eliminați.
    linii.append(f'find "{director / MANIFEST_LAYOUTS[1][0]}" -mindepth 2 -type d -empty -delete 2>/dev/null || true')
    linii.append("")
    return "\n".join(linii)


def cleanup_duplicate_manifests(
    models_directory: Path,
    on_status=None,
) -> tuple[bool, str | None]:
    """Elimină copiile redundante din formatul vechi de manifest.

    Se păstrează întotdeauna formatul nou (`manifests-v2`), pentru că
    serverul Ollama îl preferă, iar blob-urile — datele modelelor — nu
    sunt atinse deloc.
    """
    duplicate = find_duplicate_manifests(models_directory)
    if not duplicate:
        mesaj = "Nu există duplicate de eliminat."
        logger.info("Ollama cleanup: %s", mesaj)
        return True, mesaj

    if shutil.which("pkexec") is None:
        return False, "Instrumentul `pkexec` lipsește, deci nu se pot cere privilegii."

    logger.info("Ollama cleanup: removing %d duplicate manifests", len(duplicate))

    director_temporar = Path(tempfile.mkdtemp(prefix="ollama-cleanup-"))
    try:
        script = director_temporar / "curata.sh"
        script.write_text(_script_curatare(models_directory, duplicate), encoding="utf-8")
        script.chmod(0o755)

        if on_status:
            on_status(
                f"Se elimină {len(duplicate)} duplicate de manifest..."
            )

        rezultat = subprocess.run(
            ["pkexec", "/bin/sh", str(script)],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=300,
        )

        if rezultat.returncode != 0:
            detaliu = (rezultat.stderr or "").strip()
            logger.error("Ollama cleanup failed: %s", detaliu)
            if rezultat.returncode in (126, 127):
                return False, "Curățarea a fost anulată sau nu ai drepturi suficiente."
            return False, f"Curățarea a eșuat: {detaliu}"

        ramase = find_duplicate_manifests(models_directory)
        if ramase:
            return False, (
                f"Au rămas {len(ramase)} duplicate. "
                "Verifică dacă serverul Ollama rulează și încearcă din nou."
            )

        mesaj = f"Eliminate {len(duplicate)} duplicate de manifest."
        logger.info("Ollama cleanup: %s", mesaj)
        return True, mesaj
    finally:
        shutil.rmtree(director_temporar, ignore_errors=True)
