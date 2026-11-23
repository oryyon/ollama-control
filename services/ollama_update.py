"""Verificarea versiunii Ollama și actualizarea ei.

Ollama se instalează, pe Linux, prin scriptul oficial: binarul ajunge în
`/usr/local/bin/ollama`, iar bibliotecile în `/usr/local/lib/ollama/`.
Nu este un pachet al distribuției, deci actualizarea se face descărcând
arhiva oficială și înlocuind fișierele.

Versiunea cea mai recentă o citim din API-ul GitHub, folosit și de
scriptul oficial de instalare.
"""

import json
import os
import platform
import re
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request
from pathlib import Path
from typing import TypedDict

from utils.logging_config import logger

#: Adresa API-ului GitHub pentru ultima versiune lansată.
LATEST_RELEASE_URL = "https://api.github.com/repos/ollama/ollama/releases/latest"

#: Baza de la care se descarcă arhiva oficială.
DOWNLOAD_BASE_URL = "https://ollama.com/download"

#: Dimensiunea unei bucăți citite din rețea.
CHUNK_SIZE = 1024 * 1024


class UpdateInfo(TypedDict):
    """Starea versiunilor: ce e instalat și ce e disponibil."""

    installed: str
    latest: str | None
    update_available: bool
    error: str | None


def _versiune_numerica(versiune: str) -> tuple[int, ...]:
    """Transformă „0.40.17" într-un tuplu comparabil."""
    cifre = re.findall(r"\d+", versiune or "")
    return tuple(int(c) for c in cifre)


def este_versiune_mai_noua(versiune_noua: str, versiune_veche: str) -> bool:
    """Este `versiune_noua` mai recentă decât `versiune_veche`?"""
    noua = _versiune_numerica(versiune_noua)
    veche = _versiune_numerica(versiune_veche)
    if not noua or not veche:
        return False
    # Completăm cu zerouri ca „0.40" să fie mai mic decât „0.40.1".
    lungime = max(len(noua), len(veche))
    noua = noua + (0,) * (lungime - len(noua))
    veche = veche + (0,) * (lungime - len(veche))
    return noua > veche


def get_installed_version() -> str:
    """Versiunea Ollama instalată, ca număr (ex: „0.30.6")."""
    try:
        rezultat = subprocess.run(
            ["ollama", "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=10,
        )
    except Exception:
        logger.exception("Failed to read the installed Ollama version")
        return ""

    for linie in (rezultat.stdout or "").splitlines():
        potrivire = re.search(r"(\d+\.\d+(?:\.\d+)*)", linie)
        if potrivire:
            return potrivire.group(1)

    return ""


def get_latest_version(timeout: float = 15.0) -> str | None:
    """Versiunea Ollama cea mai recentă, din API-ul GitHub."""
    cerere = urllib.request.Request(
        LATEST_RELEASE_URL,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "OllamaControl"},
    )
    try:
        with urllib.request.urlopen(cerere, timeout=timeout) as raspuns:
            date = json.loads(raspuns.read().decode("utf-8", errors="ignore"))
    except Exception:
        logger.exception("Failed to read the latest Ollama version")
        return None

    eticheta = date.get("tag_name") or ""
    return eticheta.lstrip("v") or None


def check_for_update() -> UpdateInfo:
    """Compară versiunea instalată cu cea mai recentă disponibilă."""
    instalata = get_installed_version()

    if not instalata:
        return {
            "installed": "",
            "latest": None,
            "update_available": False,
            "error": "Versiunea Ollama instalată nu a putut fi determinată.",
        }

    ultima = get_latest_version()
    if not ultima:
        return {
            "installed": instalata,
            "latest": None,
            "update_available": False,
            "error": "Nu se poate contacta serverul pentru a verifica versiunea nouă.",
        }

    return {
        "installed": instalata,
        "latest": ultima,
        "update_available": este_versiune_mai_noua(ultima, instalata),
        "error": None,
    }


def _arhitectura() -> str:
    """Arhitectura folosită de arhivele oficiale."""
    masina = platform.machine().lower()
    if masina in ("x86_64", "amd64"):
        return "amd64"
    if masina in ("aarch64", "arm64"):
        return "arm64"
    return masina or "amd64"


def _descarca(url: str, destinatie: Path, on_progress, on_status) -> None:
    """Descarcă un fișier, raportând progresul în octeți."""
    cerere = urllib.request.Request(url, headers={"User-Agent": "OllamaControl"})
    with urllib.request.urlopen(cerere, timeout=60) as raspuns:
        total = int(raspuns.headers.get("Content-Length") or 0)
        descarcat = 0
        with open(destinatie, "wb") as fisier:
            while True:
                bucata = raspuns.read(CHUNK_SIZE)
                if not bucata:
                    break
                fisier.write(bucata)
                descarcat += len(bucata)
                if on_progress:
                    on_progress(descarcat, total)


def _extrage(arhiva: Path, director: Path, on_status) -> None:
    """Extrage arhiva `.tar.zst` în directorul dat."""
    if shutil.which("zstd") is None:
        raise RuntimeError(
            "Instrumentul `zstd` lipsește. Instalează-l cu `sudo apt-get install zstd`."
        )

    on_status("Se extrage arhiva...")

    decodat = subprocess.Popen(
        ["zstd", "-dc", str(arhiva)],
        stdout=subprocess.PIPE,
    )
    try:
        with tarfile.open(fileobj=decodat.stdout, mode="r|") as tar:
            tar.extractall(path=str(director))
    finally:
        if decodat.stdout:
            decodat.stdout.close()
        decodat.wait()

    if decodat.returncode not in (0, None):
        raise RuntimeError("Extragerea arhivei a eșuat.")


def _script_instalare(sursa: Path, versiune: str) -> str:
    """Scriptul de instalare rulat cu privilegii de root."""
    return f"""#!/bin/sh
set -e

echo "Opreste serviciul Ollama..."
systemctl stop ollama 2>/dev/null || true

echo "Instaleaza binarul nou..."
install -o0 -g0 -m755 -d /usr/local/bin
install -o0 -g0 -m755 "{sursa}/bin/ollama" /usr/local/bin/ollama

echo "Actualizeaza bibliotecile..."
rm -rf /usr/local/lib/ollama
install -o0 -g0 -m755 -d /usr/local/lib/ollama
cp -a "{sursa}/lib/ollama/." /usr/local/lib/ollama/

echo "Porneste serviciul Ollama..."
systemctl start ollama 2>/dev/null || true

echo "Actualizare la versiunea {versiune} finalizata."
"""


def perform_update(
    on_progress=None,
    on_status=None,
    version: str | None = None,
) -> tuple[bool, str | None]:
    """Actualizează Ollama la cea mai recentă versiune.

    `on_progress(descarcat, total)` primește octeții descărcați și totalul
    (0 dacă serverul nu anunță dimensiunea). `on_status(mesaj)` primește
    mesaje de stare pentru interfață.
    """
    def raporteaza_status(mesaj: str) -> None:
        logger.info("Ollama update: %s", mesaj)
        if on_status:
            on_status(mesaj)

    if os.geteuid() == 0:
        return False, (
            "Actualizarea nu poate rula cu privilegii de root. "
            "Pornește aplicația ca utilizator normal."
        )

    if shutil.which("pkexec") is None:
        return False, "Instrumentul `pkexec` lipsește, deci nu se pot cere privilegii."

    arhitectura = _arhitectura()
    versiune_tinta = version or get_latest_version()
    if not versiune_tinta:
        return False, "Nu se poate determina cea mai recentă versiune de Ollama."

    instalata = get_installed_version()
    if instalata and not este_versiune_mai_noua(versiune_tinta, instalata):
        raporteaza_status(f"Ollama este deja la versiunea {instalata}.")
        return True, None

    raporteaza_status(f"Se descarcă Ollama {versiune_tinta}...")

    director_temporar = Path(tempfile.mkdtemp(prefix="ollama-update-"))
    try:
        arhiva = director_temporar / f"ollama-linux-{arhitectura}.tar.zst"
        url = f"{DOWNLOAD_BASE_URL}/ollama-linux-{arhitectura}.tar.zst"

        try:
            _descarca(url, arhiva, on_progress, raporteaza_status)
        except Exception as e:
            logger.exception("Failed to download the Ollama archive")
            return False, f"Descărcarea arhivei Ollama a eșuat: {e}"

        if not arhiva.exists() or arhiva.stat().st_size < 1024:
            return False, "Arhiva Ollama descărcată este goală sau coruptă."

        try:
            _extrage(arhiva, director_temporar / "extracted", raporteaza_status)
        except Exception as e:
            logger.exception("Failed to extract the Ollama archive")
            return False, f"Extragerea arhivei Ollama a eșuat: {e}"

        sursa = director_temporar / "extracted"
        if not (sursa / "bin" / "ollama").exists():
            return False, "Arhiva Ollama nu conține binarul așteptat."

        raporteaza_status("Se cer privilegiile de administrator...")

        script = director_temporar / "instaleaza.sh"
        script.write_text(_script_instalare(sursa, versiune_tinta), encoding="utf-8")
        script.chmod(0o755)

        rezultat = subprocess.run(
            ["pkexec", "/bin/sh", str(script)],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=900,
        )

        if rezultat.returncode != 0:
            detaliu = (rezultat.stderr or "").strip() or (rezultat.stdout or "").strip()
            logger.error("Ollama update script failed: %s", detaliu)
            if rezultat.returncode in (126, 127):
                return False, "Actualizarea a fost anulată sau nu ai drepturi suficiente."
            return False, f"Actualizarea Ollama a eșuat: {detaliu}"

        noua_versiune = get_installed_version()
        raporteaza_status(f"Actualizare finalizată: Ollama {noua_versiune}.")

        if noua_versiune and not este_versiune_mai_noua(noua_versiune, instalata):
            return False, (
                f"Actualizarea s-a încheiat, dar versiunea instalată este în continuare {noua_versiune}."
            )

        return True, None
    finally:
        shutil.rmtree(director_temporar, ignore_errors=True)

