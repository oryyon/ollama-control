"""Monitorizarea progresului real de încărcare a unui model Ollama.

Ollama nu expune un eveniment de progres prin API-ul HTTP: cererea
`/api/generate` rămâne fără răspuns până când modelul este complet
încărcat în RAM. Singura informație disponibilă este procesul
`llama-server`, a cărui memorie rezidentă (RSS) crește treptat pe
măsură ce tensorii sunt citiți de pe disc.

Pe baza acestei creșteri calculăm procentul de model încărcat, așa cum
procedează aplicațiile de management local de modele. Funcționează și
pentru serverul pornit de `systemd` cu utilizatorul `ollama`, fiindcă
`/proc/<pid>/status` este lizibil de oricine.
"""

import os
import time
from pathlib import Path

from utils.logging_config import logger

#: Câte eșantioane luăm pe secundă pentru calculul procentului.
POLL_INTERVAL_SECONDS = 0.5

#: Subprocesele Ollama care țin modelul în memorie.
RUNNER_PATTERNS = ("llama-server", "ollama runner")


def _runner_pids() -> list[int]:
    """PID-urile proceselor care țin modelele Ollama în memorie."""
    pids: list[int] = []
    try:
        entries = os.listdir("/proc")
    except OSError:
        return pids

    for entry in entries:
        if not entry.isdigit():
            continue
        try:
            with open(f"/proc/{entry}/cmdline", "rb") as f:
                cmdline = f.read().replace(b"\0", b" ").decode(errors="ignore").strip()
        except OSError:
            continue

        if any(pattern in cmdline for pattern in RUNNER_PATTERNS):
            pids.append(int(entry))

    return pids


def _rss_bytes(pid: int) -> int:
    """Memoria rezidentă a unui proces, în octeți."""
    try:
        with open(f"/proc/{pid}/status", "r") as f:
            for linie in f:
                if linie.startswith("VmRSS:"):
                    return int(linie.split()[1]) * 1024
    except (OSError, ValueError, IndexError):
        pass
    return 0


def _rss_total(pids: list[int]) -> int:
    return sum(_rss_bytes(pid) for pid in pids)


def _model_din_cmdline(pid: int) -> str | None:
    """Blob-ul modelului încărcat de un runner, dacă se poate citi."""
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            parti = f.read().split(b"\0")
    except OSError:
        return None

    for index, parte in enumerate(parti):
        if parte == b"--model" and index + 1 < len(parti):
            return parti[index + 1].decode(errors="ignore")
    return None


def _dimensiune_model(director: Path, digest: str | None) -> int:
    """Dimensiunea modelului în octeți, din blob-ul său."""
    if not digest:
        return 0

    nume = digest.rsplit("/", 1)[-1]
    if not nume.startswith("sha256-"):
        return 0

    blob = director / "blobs" / nume
    try:
        return blob.stat().st_size
    except OSError:
        return 0


class LoadProgressMonitor:
    """Urmărește creșterea memoriei runner-ului pentru a estima procentul.

    Strategie: pornim de la memoria totală a runner-ului înainte de
    încărcare, apoi urmărim cât s-a alocat. Procentul este raportul
    dintre memoria alocată suplimentar și dimensiunea modelului.
    """

    def __init__(self, model_size_bytes: int, models_directory: Path) -> None:
        self.model_size_bytes = max(model_size_bytes, 0)
        self.models_directory = models_directory
        self.baseline_bytes = _rss_total(_runner_pids())
        self.peak_bytes = 0
        self.last_percent = 0
        self._stop = False

    def stop(self) -> None:
        self._stop = True

    def _dimensiune_din_runner(self) -> int:
        """Dimensiunea modelului identificat din command line-ul runner-ului."""
        for pid in _runner_pids():
            digest = _model_din_cmdline(pid)
            dimensiune = _dimensiune_model(self.models_directory, digest)
            if dimensiune:
                return dimensiune
        return 0

    def sample(self) -> int:
        """Eșantionează starea și întoarce procentul estimat (0-100)."""
        if self._stop:
            return self.last_percent

        curent = _rss_total(_runner_pids())
        if curent > self.peak_bytes:
            self.peak_bytes = curent

        alocat = self.peak_bytes - self.baseline_bytes
        if alocat <= 0:
            return self.last_percent

        if self.model_size_bytes <= 0:
            self.model_size_bytes = self._dimensiune_din_runner()

        if self.model_size_bytes <= 0:
            # Fără dimensiune cunoscută, nu putem calcula un procent exact.
            return self.last_percent

        procent = int(alocat * 100 / self.model_size_bytes)
        procent = max(0, min(procent, 99))

        if procent > self.last_percent:
            self.last_percent = procent
            logger.info(
                "Load progress for model: %d%% (%d MiB / %d MiB)",
                procent,
                alocat // (1024 * 1024),
                self.model_size_bytes // (1024 * 1024),
            )

        return self.last_percent


def monitor_load_progress(
    model_size_bytes: int,
    models_directory: Path,
    on_progress,
    stop_event,
    interval: float = POLL_INTERVAL_SECONDS,
) -> None:
    """Rulează monitorul de progres până când `stop_event` este setat.

    `on_progress` primește procentul (0-100). Erorile sunt ignorate:
    monitorizarea e doar informativă și nu trebuie să întrerupă
    încărcarea modelului.
    """
    monitor = LoadProgressMonitor(model_size_bytes, models_directory)

    try:
        while not stop_event.is_set():
            try:
                procent = monitor.sample()
                if procent:
                    on_progress(procent)
            except Exception:
                logger.exception("Failed to sample the Ollama load progress")
            stop_event.wait(interval)
    finally:
        monitor.stop()
