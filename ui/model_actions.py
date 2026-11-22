import subprocess
import threading
import time
from typing import Callable

from config.settings import KEEPALIVE_DEFAULT, is_valid_keepalive, settings
from services.ollama_info import (normalize_model_name, obtine_model_activ,
                                   obtine_modelele_activate, _log_active_model_once,
                                   _log_no_active_model_once)
from utils.logging_config import logger

active_model_callback: Callable[[str], None] | None = None
OLLAMA_RUN_CONFIRMATION_TIMEOUT_SECONDS = 90.0
OLLAMA_RUN_POST_EXIT_GRACE_SECONDS = 20.0


def _activation_timeout_message(name: str) -> str:
    return f"Confirmarea Ollama pentru modelul '{name}' a expirat. Modelul poate porni mai lent sau Ollama nu l-a confirmat încă."


def _process_failed_message(name: str, stderr_text: str | None) -> str:
    details = (stderr_text or "").strip().splitlines()
    last_line = details[-1] if details else ""
    if last_line:
        return f"Procesul Ollama pentru modelul '{name}' a eșuat imediat: {last_line}"
    return f"Procesul Ollama pentru modelul '{name}' a eșuat imediat înainte de confirmarea activării."


def get_ollama_keepalive() -> str:
    """Durata de keepalive folosită la pornirea unui model.

    Implicitul e 10 minute (`KEEPALIVE_DEFAULT`). O valoare invalidă — de
    exemplu editată manual în `settings.json` — ar face `ollama run` să
    eșueze, deci cade pe implicit în loc să treacă mai departe.
    """
    keepalive = str(settings.get("ollama_keepalive", KEEPALIVE_DEFAULT)).strip()
    if not keepalive or not is_valid_keepalive(keepalive):
        logger.warning("Invalid ollama keepalive %r — using %s", keepalive, KEEPALIVE_DEFAULT)
        return KEEPALIVE_DEFAULT
    return keepalive


def set_active_model_callback(callback: Callable[[str], None] | None) -> None:
    global active_model_callback
    active_model_callback = callback
    logger.info("Active model callback updated: %s", "set" if callback else "cleared")


def eject_model(callback: Callable[[bool], None] | None = None) -> None:
    """Oprește modelul activ prin terminarea proceselor Ollama runner.

    Pot exista mai multe modele încărcate (keepalive lung): oprim pe cel
    raportat ca activ — primul din `ollama ps` — nu doar pe primul găsit.
    """
    stopped = False
    model_text = obtine_model_activ("active")
    active_name = ""
    if model_text.startswith("Model activ:"):
        active_name = model_text.split(":", 1)[1].strip()
    active_name_normalized = normalize_model_name(active_name)

    logger.info("Eject requested. detected_model=%s normalized=%s", active_name or "<none>", active_name_normalized or "<none>")

    if active_name and active_name not in ("indisponibil", "niciun model încărcat", "runner detectat"):
        try:
            result = subprocess.run(
                ["ollama", "stop", active_name_normalized or active_name],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                deadline = time.monotonic() + 5.0
                while time.monotonic() < deadline:
                    current_text = obtine_model_activ("active")
                    current_name = ""
                    if current_text.startswith("Model activ:"):
                        current_name = current_text.split(":", 1)[1].strip()
                    if normalize_model_name(current_name) != active_name_normalized:
                        stopped = True
                        break
                    time.sleep(0.25)

            if stopped:
                logger.info("Eject completed successfully for model=%s", active_name)
            else:
                logger.warning("Eject did not clear active model=%s stderr=%s", active_name, (result.stderr or "").strip())
        except Exception:
            logger.exception("Eject raised an unexpected error for model=%s", active_name)
    else:
        logger.warning("Eject skipped because no stoppable active model was detected")

    if callback:
        callback(stopped)


def _is_expected_model_active(name: str) -> tuple[bool, str]:
    """Modelul cerut e încărcat? (căutăm printre TOATE modelele active)

    Pot exista mai multe modele încărcate simultan: cu un keepalive lung
    (ex.: 6h), modelul vechi rămâne în memorie, iar cel nou se adaugă
    după el. Verificând doar primul rând din `ollama ps`, aplicația
    raporta eșec deși modelul ales fusese încărcat corect.
    """
    modele = obtine_modelele_activate()
    if modele is None:
        return False, "Model activ: indisponibil"

    if not modele:
        _log_no_active_model_once()
        return False, "Model activ: niciun model încărcat"

    asteptat = normalize_model_name(name)
    for activ in modele:
        if normalize_model_name(activ) == asteptat:
            logger.info("Expected model found among active models: %s", activ)
            _log_active_model_once(activ)
            return True, f"Model activ: {activ}"

    _log_active_model_once(modele[0])
    return False, f"Model activ: {modele[0]}"


def run_model(name: str, progress_callback: Callable[[int], None] | None = None, size_gb: float = 0.0) -> tuple[bool, str | None]:
    """Pornește un model Ollama."""
    keepalive = get_ollama_keepalive()
    logger.info("Select requested for Ollama model=%s size_gb=%.2f keepalive=%s", name, size_gb, keepalive)
    process_started = threading.Event()
    process_failed = threading.Event()
    process_result: subprocess.CompletedProcess[str] | None = None

    def _run() -> None:
        nonlocal process_result
        try:
            process_result = subprocess.run(
                ["ollama", "run", name, "", "--keepalive", keepalive],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
            )
            process_started.set()
            logger.info(
                "Completed non-interactive 'ollama run' for model=%s returncode=%s keepalive=%s",
                name,
                process_result.returncode if process_result else "?",
                keepalive,
            )
        except Exception:
            process_failed.set()
            logger.exception("Failed to start 'ollama run' for model=%s", name)

    def _simulate_progress() -> None:
        return

    run_thread = threading.Thread(target=_run, daemon=True)
    run_thread.start()

    if progress_callback:
        progress_thread = threading.Thread(target=_simulate_progress, daemon=True)
        progress_thread.start()

    run_thread.join()

    if process_failed.is_set() or not process_started.is_set():
        logger.error("Model load failed before startup confirmation for model=%s", name)
        return False, f"Ollama nu a putut porni procesul pentru modelul '{name}'."

    if process_result is None:
        logger.error("Model load finished without a process result for model=%s", name)
        return False, f"Ollama nu a furnizat un rezultat pentru modelul '{name}'."

    if process_result.returncode != 0:
        logger.error(
            "Non-interactive 'ollama run' failed for model=%s returncode=%s stderr=%s",
            name,
            process_result.returncode,
            (process_result.stderr or "").strip(),
        )
        return False, _process_failed_message(name, process_result.stderr)

    wait_deadline = time.monotonic() + max(size_gb * 8, OLLAMA_RUN_CONFIRMATION_TIMEOUT_SECONDS)
    post_exit_deadline = time.monotonic() + OLLAMA_RUN_POST_EXIT_GRACE_SECONDS
    last_logged_model_text: str | None = None
    logger.info(
        "Waiting for Ollama activation confirmation after successful run completion: model=%s grace_seconds=%.1f timeout_seconds=%.1f",
        name,
        OLLAMA_RUN_POST_EXIT_GRACE_SECONDS,
        max(size_gb * 8, OLLAMA_RUN_CONFIRMATION_TIMEOUT_SECONDS),
    )
    while time.monotonic() < wait_deadline:
        is_active, model_text = _is_expected_model_active(name)
        if model_text != last_logged_model_text:
            logger.info("Active model verification state changed for expected=%s got='%s'", name, model_text)
            last_logged_model_text = model_text

        if is_active:
            logger.info("Model became active: %s", name)
            if active_model_callback:
                active_model_callback(name)
            return True, None

        if time.monotonic() >= post_exit_deadline:
            logger.error(
                "Model was still not active after successful run completion grace period: model=%s returncode=%s",
                name,
                process_result.returncode,
            )
            return False, _activation_timeout_message(name)

        time.sleep(0.5)

    success, model_text = _is_expected_model_active(name)
    if success:
        logger.info("Model activation confirmed at timeout boundary: %s", name)
    else:
        logger.error("Timed out waiting for model activation: %s last_seen='%s'", name, model_text)
    if success and active_model_callback:
        active_model_callback(name)
    return success, None if success else _activation_timeout_message(name)
