"""Client minimal pentru API-ul HTTP al Ollama.

Folosim API-ul direct în locul CLI-ului pentru încărcarea modelelor,
pentru că `ollama run` este o comandă interactivă: încearcă să citească
din `/dev/stdin` și eșuează cu „bad file descriptor" atunci când
aplicația este lansată din meniul desktop, fără terminal.

API-ul oferă același efect (`keep_alive` menține modelul în memorie) și
ne permite un timeout explicit, deci aplicația nu poate rămâne blocată.
"""

import json
import os
import urllib.error
import urllib.request

from utils.logging_config import logger

#: Adresa implicită a serverului Ollama local.
DEFAULT_HOST = "http://127.0.0.1:11434"

#: Timeout implicit pentru o cerere de încărcare (secunde).
DEFAULT_TIMEOUT = 300.0


def _host() -> str:
    """Adresa serverului Ollama, respectând variabila `OLLAMA_HOST`."""
    valoare = os.environ.get("OLLAMA_HOST", "").strip()
    if not valoare:
        return DEFAULT_HOST

    # `OLLAMA_HOST` poate fi doar „host:port" sau o adresă completă.
    if not valoare.startswith(("http://", "https://")):
        valoare = f"http://{valoare}"
    return valoare.rstrip("/")


def _request(cale: str, corp: dict | None = None, timeout: float = DEFAULT_TIMEOUT) -> dict:
    """Face o cerere JSON către API-ul Ollama."""
    adresa = f"{_host()}{cale}"
    date = None
    antet = {}

    if corp is not None:
        date = json.dumps(corp).encode("utf-8")
        antet["Content-Type"] = "application/json"

    cerere = urllib.request.Request(adresa, data=date, headers=antet)
    with urllib.request.urlopen(cerere, timeout=timeout) as raspuns:
        continut = raspuns.read().decode("utf-8", errors="ignore")

    if not continut.strip():
        return {}

    try:
        return json.loads(continut)
    except json.JSONDecodeError:
        return {}


def server_disponibil(timeout: float = 3.0) -> bool:
    """Răspunde serverul Ollama?"""
    try:
        _request("/api/version", timeout=timeout)
        return True
    except Exception:
        return False


def load_model(
    model: str,
    keepalive: str = "10m",
    timeout: float = DEFAULT_TIMEOUT,
) -> tuple[bool, str | None]:
    """Încarcă un model în memorie și îl menține activ.

    Trimite o cerere de generare cu prompt gol și `keep_alive`, ceea ce
    încarcă modelul fără să producă ieșire. Întoarce `(succes, mesaj)`.
    """
    corp = {
        "model": model,
        "prompt": "",
        "stream": False,
        "keep_alive": keepalive,
    }

    logger.info("Loading model via the Ollama HTTP API: model=%s keepalive=%s", model, keepalive)

    try:
        raspuns = _request("/api/generate", corp=corp, timeout=timeout)
    except urllib.error.HTTPError as e:
        detaliu = ""
        try:
            detaliu = e.read().decode("utf-8", errors="ignore").strip()
        except Exception:
            pass
        mesaj = f"Serverul Ollama a refuzat modelul '{model}' (HTTP {e.code})."
        if detaliu:
            mesaj = f"{mesaj} {detaliu}"
        logger.error("Ollama API load failed for %s: %s", model, mesaj)
        return False, mesaj
    except urllib.error.URLError as e:
        mesaj = (
            f"Nu se poate contacta serverul Ollama pentru modelul '{model}'. "
            f"Verifică dacă serviciul este pornit. ({e.reason})"
        )
        logger.error("Ollama API unreachable for %s: %s", model, e.reason)
        return False, mesaj
    except Exception as e:
        mesaj = f"Eroare la încărcarea modelului '{model}': {e}"
        logger.exception("Unexpected error while loading the model via the Ollama API")
        return False, mesaj

    if "error" in raspuns:
        mesaj = f"Ollama a raportat o eroare la încărcarea modelului '{model}': {raspuns['error']}"
        logger.error("Ollama API returned an error for %s: %s", model, raspuns["error"])
        return False, mesaj

    logger.info("Model loaded via the Ollama HTTP API: model=%s", model)
    return True, None


def modele_incarcate() -> list[str]:
    """Numele modelelor încărcate acum în memorie."""
    try:
        raspuns = _request("/api/ps", timeout=5.0)
    except Exception:
        logger.exception("Failed to read the list of loaded models")
        return []

    modele: list[str] = []
    for model in raspuns.get("models", []) or []:
        nume = model.get("model") or model.get("name")
        if nume:
            modele.append(str(nume))
    return modele
