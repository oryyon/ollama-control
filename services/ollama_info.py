import subprocess

from utils.logging_config import logger

_last_logged_service_state: str | None = None
_last_logged_active_model: str | None = None
_active_model_timeout_logged: bool = False


def _log_service_state_once(active_state: str) -> None:
    global _last_logged_service_state, _active_model_timeout_logged
    if _last_logged_service_state != active_state:
        logger.info("Active model check skipped because service state is %s", active_state)
        _last_logged_service_state = active_state
    _active_model_timeout_logged = False


def _log_active_model_once(model_name: str) -> None:
    global _last_logged_active_model, _last_logged_service_state, _active_model_timeout_logged
    if _last_logged_active_model != model_name or _last_logged_service_state != "active":
        logger.info("Detected active model: %s", model_name)
        _last_logged_active_model = model_name
        _last_logged_service_state = "active"
    _active_model_timeout_logged = False


def _log_no_active_model_once() -> None:
    global _last_logged_active_model, _last_logged_service_state, _active_model_timeout_logged
    if _last_logged_active_model is not None or _last_logged_service_state != "active":
        logger.info("No active model detected")
        _last_logged_active_model = None
        _last_logged_service_state = "active"
    _active_model_timeout_logged = False


def _log_active_model_timeout_once() -> None:
    global _active_model_timeout_logged, _last_logged_service_state
    if not _active_model_timeout_logged:
        logger.warning("Timed out while detecting active model")
        _active_model_timeout_logged = True
    _last_logged_service_state = "active"


def normalize_model_name(name: str) -> str:
    if not name:
        return ""
    return name.removesuffix(":latest")


def obtine_versiune_ollama() -> str:
    """Returnează versiunea clientului Ollama."""
    try:
        rezultat = subprocess.run(
            ["ollama", "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=3
        )
        output = (rezultat.stdout or "") + "\n" + (rezultat.stderr or "")
        for linie in output.splitlines():
            linie = linie.strip()
            if "version is" in linie.lower():
                return linie.replace("Warning: ", "").strip()
            if linie.lower().startswith("ollama version"):
                return linie.strip()
        return "Versiune Ollama indisponibilă"
    except subprocess.TimeoutExpired:
        return "Versiune Ollama indisponibilă"
    except Exception:
        return "Versiune Ollama indisponibilă"


def obtine_model_activ(active_state: str) -> str:
    """Încearcă să detecteze modelul activ din procesele Ollama.

    Returnează primul model încărcat (pentru afișare). Pentru verificări
    folosiți `obtine_modelele_activate` — pot exista mai multe modele
    încărcate simultan (keepalive lung), și primul nu e neapărat cel căutat.
    """
    if active_state != "active":
        _log_service_state_once(active_state)
        return "Model activ: indisponibil"

    modele = obtine_modelele_activate()
    if modele:
        _log_active_model_once(modele[0])
        return f"Model activ: {modele[0]}"
    if modele is not None:
        _log_no_active_model_once()
        return "Model activ: niciun model încărcat"
    return "Model activ: indisponibil"


def obtine_modelele_activate() -> list[str] | None:
    """Modelele încărcate în serverul Ollama (toate, nu doar primul).

    `ollama ps` poate afișa mai multe modele simultan — cu un keepalive lung
    (ex.: 6h), modelul vechi rămâne în memorie, iar cel nou se adaugă
    după el. Un model nou e deci „încărcat” chiar dacă nu e primul în listă.

    Întoarce:
      - lista numelor de model (posibil vidă) — serverul răspunde;
      - `None` — serverul nu poate fi consultat (eroare/timeout).
    """
    try:
        rezultat = subprocess.run(
            ["ollama", "ps"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=3
        )
        logger.debug("Ran 'ollama ps' with return code %s", rezultat.returncode)
        if rezultat.returncode == 0:
            lines = [line.strip() for line in rezultat.stdout.splitlines() if line.strip()]
            # prima linie e antetul; restul sunt modelele (una pe linie)
            return [line.split()[0] for line in lines[1:] if line.split()]
    except subprocess.TimeoutExpired:
        _log_active_model_timeout_once()
        return None
    except Exception:
        logger.exception("Unexpected error while detecting active models")
        return None

    # Fallback: scanăm procesele „ollama runner” (utilitarul e învechit sau
    # serverul nu răspunde la „ollama ps”, dar runnerul rulează).
    try:
        rezultat = subprocess.run(
            ["ps", "-eo", "args="],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=2
        )
        logger.debug("Falling back to process scan for active model detection")
        modele: list[str] = []
        for linie in rezultat.stdout.splitlines():
            linie_curata = linie.strip()
            if "ollama runner" not in linie_curata:
                continue
            parti = linie_curata.split()
            for index, parte in enumerate(parti):
                if parte == "--model" and index + 1 < len(parti):
                    nume = parti[index + 1]
                    if nume not in modele:
                        modele.append(nume)
                elif parte.startswith("--model="):
                    nume = parte.split('=', 1)[1]
                    if nume not in modele:
                        modele.append(nume)
        if modele:
            return modele
    except subprocess.TimeoutExpired:
        _log_active_model_timeout_once()
        return None
    except Exception:
        logger.exception("Unexpected error while detecting active models")
        return None
    return None
