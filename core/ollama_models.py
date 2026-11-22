import subprocess
import threading
import time
from typing import Callable, TypedDict

from utils.logging_config import logger
from utils.helpers import extract_params


class ModelEntry(TypedDict):
    """Un model Ollama, așa cum apare în lista aplicației.

    Folosim un `TypedDict` în locul unui `dict[str, str | None]` ca să fie
    clar ce câmpuri există mereu: `name`, `size` și `params` sunt întotdeauna
    șiruri, chiar dacă valoarea este „N/A" sau un gol.
    """

    name: str
    size: str
    params: str


_ollama_models_cache: list[ModelEntry] | None = None
_ollama_models_cache_time: float = 0
_ollama_models_cache_lock = threading.Lock()
OLLAMA_CACHE_TTL: int = 60  # secunde


def invalidate_ollama_models_cache() -> None:
    global _ollama_models_cache, _ollama_models_cache_time
    with _ollama_models_cache_lock:
        _ollama_models_cache = None
        _ollama_models_cache_time = 0


def is_ollama_server_running() -> bool:
    """Verifică rapid dacă serverul Ollama răspunde pe localhost:11434."""
    try:
        result = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "http://localhost:11434"],
            capture_output=True,
            text=True,
            timeout=2
        )
        return result.returncode == 0 and result.stdout.strip() == "200"
    except Exception:
        return False


def _parse_ollama_models_output(output: str) -> list[ModelEntry]:
    """Parsează output-ul tabelului ``ollama list`` în structura aplicației."""
    lines = output.splitlines()
    if not lines:
        return []

    models: list[ModelEntry] = []
    for line in lines[1:]:
        parts = line.split()
        if not parts:
            continue

        name = parts[0]
        size_str = "N/A"

        # Formatul curent este: NAME ID SIZE [UNIT] MODIFIED. Nu folosim
        # poziția antetului ca indice în linie, deoarece lățimea coloanei
        # NAME variază și astfel am extrage greșit ID-ul în locul dimensiunii.
        if len(parts) >= 3:
            size_value = parts[2]
            if len(parts) >= 4 and parts[3].upper() in ("GB", "MB", "TB", "KB", "B"):
                size_str = f"{size_value} {parts[3].upper()}"
            else:
                size_str = size_value

        models.append({
            "name": name,
            "size": size_str,
            "params": extract_params(name),
        })

    return models


def _modele_din_cache() -> list[ModelEntry]:
    """Ultima listă de modele cunoscută (evită golirea listei la timeout)."""
    with _ollama_models_cache_lock:
        return list(_ollama_models_cache or [])


def get_ollama_models() -> tuple[list[ModelEntry], bool]:
    """Returnează (modele, success). Dacă success=False, a fost o eroare de conectare."""
    global _ollama_models_cache, _ollama_models_cache_time

    now = time.time()
    with _ollama_models_cache_lock:
        if _ollama_models_cache is not None and (now - _ollama_models_cache_time) < OLLAMA_CACHE_TTL:
            logger.debug("Returning cached ollama models")
            return list(_ollama_models_cache), True

    try:
        r = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=45
        )

        stderr_lower = (r.stderr or "").lower()
        if r.returncode != 0:
            if "could not connect" in stderr_lower or "connection refused" in stderr_lower:
                logger.warning("Ollama server not running")
            else:
                logger.warning(
                    "Could not list Ollama models: returncode=%s stderr=%s",
                    r.returncode,
                    (r.stderr or "").strip(),
                )
            return _modele_din_cache(), False

        models = _parse_ollama_models_output(r.stdout or "")
        with _ollama_models_cache_lock:
            _ollama_models_cache = list(models)
            _ollama_models_cache_time = now
        logger.info(f"Cached {len(models)} ollama models")
        return models, True

    except subprocess.TimeoutExpired:
        # Serverul poate fi ocupat (încărcă un model) → „ollama list” nu
        # răspunde în timp. Nu golim lista: modelele nu au dispărut, doar
        # serverul nu răspunde acum — altfel utilizatorul vedea „Niciun
        # model” și credea că modelele au fost șterse.
        logger.warning("Timeout while listing Ollama models")
        return _modele_din_cache(), False
    except Exception as e:
        logger.error(f"Error getting ollama models: {e}")
        return _modele_din_cache(), False


def _parse_size_to_gb(size_str: str) -> float:
    """Convertește un string de dimensiune (ex: '4.4 GB') în GB float."""
    try:
        parts = size_str.strip().split()
        if len(parts) >= 2:
            val = float(parts[0])
            unit = parts[1].upper()
            if unit == "KB":
                return val / (1024 * 1024)
            elif unit == "MB":
                return val / 1024
            elif unit == "GB":
                return val
            elif unit == "TB":
                return val * 1024
        return float(size_str)
    except Exception:
        return 0.0


def delete_ollama_model(
    name: str,
    callback: Callable[[bool, str], None] | None = None,
) -> None:
    """Șterge un model Ollama folosind 'ollama rm'."""
    try:
        result = subprocess.run(
            ["ollama", "rm", name],
            capture_output=True,
            text=True,
            timeout=30,
        )
        success = result.returncode == 0
        if not success:
            print(f"Eroare la ștergerea modelului {name}:", result.stderr)
        else:
            invalidate_ollama_models_cache()
        if callback:
            callback(success, name)
    except Exception as e:
        print(f"Eroare la ștergerea modelului {name}:", e)
        if callback:
            callback(False, name)
