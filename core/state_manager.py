import threading
import time

from core.app_state import AppState
from services.systemd_service import obtine_detalii_serviciu
from services.ollama_info import normalize_model_name, obtine_versiune_ollama, obtine_model_activ
from services.resource_monitor import formateaza_uptime, obtine_consum_resurse
from ui.notifications import arata_notificare
from utils.logging_config import logger
import config.settings as app_settings

info_lock = threading.Lock()
service_lock = threading.Lock()
auto_refresh_job: int | None = None
MIN_SERVICE_REFRESH_MS = 15000
VERSION_REFRESH_MS = 60000
RESOURCE_REFRESH_MS = 20000

#: Cât timp (în secunde) poate dura bara de încărcare a modelului înainte
#: să fie ascunsă oricum. Modelele mari se încarcă lent, dar nu atât de
#: mult; timpul exact depinde de disk și de dimensiunea modelului.
MODEL_LOAD_BAR_TIMEOUT_SECONDS = 600.0


def _incarcare_expirata(state: AppState) -> bool:
    """A expirat timpul de așteptare pentru modelul încărcat?"""
    if not state.model_incarcare_in_curs or not state.model_incarcare_inceput:
        return False
    return (time.monotonic() - state.model_incarcare_inceput) > MODEL_LOAD_BAR_TIMEOUT_SECONDS


def _service_refresh_ms() -> int:
    refresh_ms = app_settings.AUTO_REFRESH_MS
    if refresh_ms is None:
        return MIN_SERVICE_REFRESH_MS
    return max(refresh_ms * 3, MIN_SERVICE_REFRESH_MS)


def _should_refresh(last_refresh_monotonic: float, refresh_ms: int) -> bool:
    if not last_refresh_monotonic:
        return True
    return (time.monotonic() - last_refresh_monotonic) * 1000 >= refresh_ms


def scurteaza_versiune(text: str) -> str:
    if not text or "indisponibil" in text.lower() or "verifică" in text.lower():
        return text

    parti = text.split()
    for parte in parti:
        if parte and parte[0].isdigit():
            return f"Client {parte}"
    return text


def scurteaza_model(text: str) -> str:
    if not text or ":" not in text:
        return text

    prefix, valoare = text.split(":", 1)
    valoare = valoare.strip()
    if not valoare:
        return text
    return valoare


def actualizeaza_info_ollama_ui(
    state: AppState,
    widgets: dict,
    versiune_text: str,
    model_text: str,
    resurse_text: str = "—"
) -> None:
    state.versiune_ollama_cache = scurteaza_versiune(versiune_text)
    actual_model_name = scurteaza_model(model_text)
    normalized_actual_model_name = normalize_model_name(actual_model_name)
    normalized_selected_model_name = normalize_model_name(state.selected_model_name or "")

    if state.model_incarcare_in_curs and state.selected_model_name and actual_model_name in ("Se verifică...", "Indisponibil", "niciun model încărcat"):
        state.model_activ_cache = state.selected_model_name
    else:
        state.model_activ_cache = actual_model_name

    with info_lock:
        state.info_ollama_incarcare = False

    state.resurse_cache = resurse_text
    widgets["version_label"].configure(text=state.versiune_ollama_cache)
    widgets["model_label"].configure(text=state.model_activ_cache)
    widgets["resurse_label"].configure(text=state.resurse_cache)

    if state.model_incarcare_in_curs and state.selected_model_name and normalized_actual_model_name == normalized_selected_model_name:
        from ui.main_window import ascunde_incarcare_model
        ascunde_incarcare_model(state, widgets)
    elif state.model_incarcare_in_curs and _incarcare_expirata(state):
        # Plasa de siguranță: dacă modelul încărcat nu apare niciodată în
        # lista serverului, bara nu trebuie să rămână la nesfârșit.
        logger.info("Hiding the model loading bar: the load took too long")
        from ui.main_window import ascunde_incarcare_model
        ascunde_incarcare_model(state, widgets)


def randare_stare_serviciu_ui(widgets: dict, detalii: dict[str, str]) -> None:
    active_state = detalii["active_state"]
    sub_state = detalii["sub_state"]
    uptime_text = formateaza_uptime(detalii["active_timestamp"])

    if active_state == "checking":
        widgets["status_dot"].configure(text="●", text_color="#93c5fd")
        widgets["status_badge"].configure(text="CHECKING", fg_color="#1f2937", text_color="#cbd5e1")
        widgets["status_label"].configure(text="Se verifică serviciul...", text_color="#f8fafc")
        widgets["subtitle_label"].configure(text="Așteaptă răspunsul systemd", text_color="#9fb0c7")
        widgets["uptime_value_label"].configure(text="Se verifică...", text_color="#93c5fd")
        widgets["detail_state_value"].configure(text="Checking · Pending", text_color="#cbd5e1")
        widgets["model_label"].configure(text_color="#c4b5fd")
    elif active_state == "active":
        widgets["status_dot"].configure(text="●", text_color="#22c55e")
        widgets["status_badge"].configure(text="ONLINE", fg_color="#123524", text_color="#86efac")
        widgets["status_label"].configure(text="Ollama este pornit", text_color="#f8fafc")
        widgets["subtitle_label"].configure(text="Rulează normal și răspunde local", text_color="#9fb0c7")
        widgets["uptime_value_label"].configure(text=uptime_text, text_color="#93c5fd")
        widgets["detail_state_value"].configure(text=f"{active_state.capitalize()} · {sub_state.capitalize()}", text_color="#cbd5e1")
        widgets["model_label"].configure(text_color="#c4b5fd")
    elif active_state == "inactive":
        widgets["status_dot"].configure(text="●", text_color="#ef4444")
        widgets["status_badge"].configure(text="OFFLINE", fg_color="#3a1618", text_color="#fca5a5")
        widgets["status_label"].configure(text="Ollama este oprit", text_color="#f8fafc")
        widgets["subtitle_label"].configure(text="Serviciul nu rulează în acest moment", text_color="#9fb0c7")
        widgets["uptime_value_label"].configure(text="Nu rulează", text_color="#fda4af")
        widgets["detail_state_value"].configure(text=f"{active_state.capitalize()} · {sub_state.capitalize()}", text_color="#cbd5e1")
        widgets["model_label"].configure(text_color="#94a3b8")
    elif active_state == "failed":
        widgets["status_dot"].configure(text="●", text_color="#f59e0b")
        widgets["status_badge"].configure(text="ERROR", fg_color="#3a2608", text_color="#fcd34d")
        widgets["status_label"].configure(text="Ollama este în eroare", text_color="#f8fafc")
        widgets["subtitle_label"].configure(text="Serviciul a pornit cu probleme", text_color="#f0b44c")
        widgets["uptime_value_label"].configure(text="Verifică jurnalul serviciului", text_color="#fcd34d")
        widgets["detail_state_value"].configure(text=f"{active_state.capitalize()} · {sub_state.capitalize()}", text_color="#fcd34d")
        widgets["model_label"].configure(text_color="#fcd34d")
    else:
        widgets["status_dot"].configure(text="●", text_color="#94a3b8")
        widgets["status_badge"].configure(text="UNKNOWN", fg_color="#1f2937", text_color="#cbd5e1")
        widgets["status_label"].configure(text="Stare necunoscută", text_color="#f8fafc")
        widgets["subtitle_label"].configure(text="Nu s-au putut obține detalii de la systemd", text_color="#9fb0c7")
        widgets["uptime_value_label"].configure(text="Nu există modele încărcate", text_color="#94a3b8")
        widgets["detail_state_value"].configure(text=f"{active_state.capitalize()} · {sub_state.capitalize()}", text_color="#cbd5e1")
        widgets["model_label"].configure(text_color="#94a3b8")


def actualizeaza_stare_serviciu_ui(state: AppState, widgets: dict, detalii: dict[str, str]) -> None:
    state.service_details_cache = detalii
    state.last_service_refresh_monotonic = time.monotonic()

    with service_lock:
        state.service_info_incarcare = False

    randare_stare_serviciu_ui(widgets, detalii)


def incarca_stare_serviciu_in_fundal(state: AppState, widgets: dict, app) -> None:
    detalii = obtine_detalii_serviciu()
    app.after(0, lambda: actualizeaza_stare_serviciu_ui(state, widgets, detalii))


def programeaza_actualizare_stare_serviciu(
    state: AppState,
    widgets: dict,
    app,
    force_refresh: bool = False,
) -> None:
    now = time.monotonic()
    refresh_due = (now - state.last_service_refresh_monotonic) * 1000 >= _service_refresh_ms()

    with service_lock:
        if state.service_info_incarcare:
            return
        if not force_refresh and state.last_service_refresh_monotonic and not refresh_due:
            return
        state.service_info_incarcare = True

    threading.Thread(
        target=incarca_stare_serviciu_in_fundal,
        args=(state, widgets, app),
        daemon=True,
    ).start()


def incarca_info_ollama_in_fundal(state: AppState, widgets: dict, active_state: str, app) -> None:
    versiune_text = state.versiune_ollama_cache
    if _should_refresh(state.last_version_refresh_monotonic, VERSION_REFRESH_MS):
        versiune_text = obtine_versiune_ollama()
        state.last_version_refresh_monotonic = time.monotonic()

    model_text = obtine_model_activ(active_state)

    if active_state == "active":
        resurse_text = state.resurse_cache
        if _should_refresh(state.last_resource_refresh_monotonic, RESOURCE_REFRESH_MS):
            resurse_text = obtine_consum_resurse()
            state.last_resource_refresh_monotonic = time.monotonic()
    else:
        resurse_text = "—"
        state.last_resource_refresh_monotonic = 0.0

    app.after(0, lambda: actualizeaza_info_ollama_ui(state, widgets, versiune_text, model_text, resurse_text))


def programeaza_actualizare_info_ollama(state: AppState, widgets: dict, active_state: str, app) -> None:
    if active_state != "active":
        state.selected_model_name = None
        state.model_activ_cache = "Indisponibil"
        widgets["model_label"].configure(text=state.model_activ_cache)
        # Serviciul oprit: niciun model nu se mai încarcă, deci bara de
        # progres trebuie ascunsă. Altfel rămâne vizibilă la nesfârșit.
        if state.model_incarcare_in_curs:
            from ui.main_window import ascunde_incarcare_model
            ascunde_incarcare_model(state, widgets)

    with info_lock:
        if state.info_ollama_incarcare:
            return
        state.info_ollama_incarcare = True
    threading.Thread(target=incarca_info_ollama_in_fundal, args=(state, widgets, active_state, app), daemon=True).start()


def actualizeaza_stare(state: AppState, widgets: dict, app=None, force_service_refresh: bool = False) -> None:
    """Actualizează textul și culoarea din interfață."""
    try:
        if app is not None and not app.winfo_exists():
            return
        if not widgets["version_label"].winfo_exists():
            return
    except Exception:
        return

    detalii = state.service_details_cache
    active_state = detalii["active_state"]

    widgets["version_label"].configure(text=state.versiune_ollama_cache)
    widgets["model_label"].configure(text=state.model_activ_cache)
    widgets["resurse_label"].configure(text=state.resurse_cache)
    randare_stare_serviciu_ui(widgets, detalii)
    if app is not None:
        programeaza_actualizare_stare_serviciu(state, widgets, app, force_refresh=force_service_refresh)
        programeaza_actualizare_info_ollama(state, widgets, active_state, app)


def auto_refresh(state: AppState, widgets: dict, app) -> None:
    global auto_refresh_job
    auto_refresh_job = None

    try:
        if not app.winfo_exists():
            return
    except Exception:
        return

    try:
        if not app.focus_displayof() and not state.comanda_in_curs:
            refresh_ms = app_settings.AUTO_REFRESH_MS
            if refresh_ms is not None:
                auto_refresh_job = app.after(refresh_ms, lambda: auto_refresh(state, widgets, app))
            return
    except Exception:
        pass

    if not state.comanda_in_curs:
        actualizeaza_stare(state, widgets, app)
    refresh_ms = app_settings.AUTO_REFRESH_MS
    if refresh_ms is not None:
        auto_refresh_job = app.after(refresh_ms, lambda: auto_refresh(state, widgets, app))


def programeaza_auto_refresh(app, widgets) -> None:
    global auto_refresh_job
    try:
        if not app.winfo_exists():
            return
    except Exception:
        return

    if auto_refresh_job is not None:
        try:
            app.after_cancel(auto_refresh_job)
        except Exception:
            pass
        auto_refresh_job = None

    refresh_ms = app_settings.AUTO_REFRESH_MS
    if refresh_ms is not None:
        state = widgets.get("_state")
        if state:
            auto_refresh_job = app.after(refresh_ms, lambda: auto_refresh(state, widgets, app))
