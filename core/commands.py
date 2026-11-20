import subprocess
import threading
from tkinter import messagebox

from core.app_state import AppState
from ui.notifications import arata_notificare, notificare_desktop
from config.settings import settings
from utils.logging_config import LOG_PATH, logger

comanda_lock = threading.Lock()


_BUTTON_KEYS = (
    "settings_button",
    "logs_button",
    "start_button",
    "refresh_button",
    "restart_button",
    "stop_button",
    "load_model_button",
    "eject_button",
)


def seteaza_stare_butoane(activ: bool, widgets: dict) -> None:
    stare = "normal" if activ else "disabled"
    for key in _BUTTON_KEYS:
        widget = widgets.get(key)
        if widget is not None:
            try:
                widget.configure(state=stare)
            except Exception:
                pass


def finalizeaza_comanda(
    comanda: str,
    succes: bool,
    anulat: bool,
    state: AppState,
    widgets: dict,
    app
) -> None:
    logger.info(
        "Service command finalized: command=%s success=%s cancelled=%s log_path=%s",
        comanda,
        succes,
        anulat,
        LOG_PATH,
    )
    with comanda_lock:
        state.comanda_in_curs = False
    seteaza_stare_butoane(True, widgets)
    from core.state_manager import actualizeaza_stare
    actualizeaza_stare(state, widgets, app, force_service_refresh=True)

    if succes:
        if comanda == "start":
            arata_notificare("Pornire Ollama reușită", "success", app, widgets["notification_frame"], widgets["notification_label"])
            notificare_desktop("Ollama Control", "Pornire Ollama reușită")
        elif comanda == "stop":
            arata_notificare("Oprire Ollama reușită", "success", app, widgets["notification_frame"], widgets["notification_label"])
            notificare_desktop("Ollama Control", "Oprire Ollama reușită")
        elif comanda == "restart":
            arata_notificare("Restart Ollama reușit", "success", app, widgets["notification_frame"], widgets["notification_label"])
            notificare_desktop("Ollama Control", "Restart Ollama reușit")
        else:
            arata_notificare("Comandă executată", "success", app, widgets["notification_frame"], widgets["notification_label"])
    else:
        if anulat:
            arata_notificare("Autentificare anulată", "warning", app, widgets["notification_frame"], widgets["notification_label"])
        else:
            arata_notificare("Parolă incorectă sau insuficiente drepturi", "error", app, widgets["notification_frame"], widgets["notification_label"])


def executa_comanda_in_fundal(
    comanda: str,
    state: AppState,
    widgets: dict,
    app
) -> None:
    succes = False
    anulat = False
    try:
        logger.info("Executing service command via pkexec: %s", comanda)
        rezultat = subprocess.run(["pkexec", "systemctl", comanda, "ollama"], capture_output=True, text=True)
        logger.info(
            "Service command completed: command=%s returncode=%s stdout=%s stderr=%s",
            comanda,
            rezultat.returncode,
            (rezultat.stdout or "").strip(),
            (rezultat.stderr or "").strip(),
        )
        if rezultat.returncode != 0:
            if rezultat.returncode in (126, 127) or "not authorized" in (rezultat.stderr or "").lower():
                anulat = True
        else:
            succes = True
    except subprocess.CalledProcessError:
        logger.exception("Service command raised CalledProcessError: %s", comanda)
        succes = False
    except Exception:
        logger.exception("Unexpected error while executing service command: %s", comanda)
        succes = False
    finally:
        app.after(0, lambda: finalizeaza_comanda(comanda, succes, anulat, state, widgets, app))


def executa_restart_in_fundal(state: AppState, widgets: dict, app) -> None:
    """Execută restart Ollama (stop apoi start) în fundal."""
    stop_ok = False
    logger.info("Executing service restart via pkexec")
    try:
        rezultat = subprocess.run(["pkexec", "systemctl", "stop", "ollama"], capture_output=True, text=True)
        stop_ok = rezultat.returncode == 0
        logger.info(
            "Service restart stop step completed: returncode=%s stdout=%s stderr=%s",
            rezultat.returncode,
            (rezultat.stdout or "").strip(),
            (rezultat.stderr or "").strip(),
        )
    except Exception:
        logger.exception("Unexpected error during service restart stop step")
        pass

    if stop_ok:
        try:
            rezultat = subprocess.run(["pkexec", "systemctl", "start", "ollama"], capture_output=True, text=True)
            start_ok = rezultat.returncode == 0
            logger.info(
                "Service restart start step completed: returncode=%s stdout=%s stderr=%s",
                rezultat.returncode,
                (rezultat.stdout or "").strip(),
                (rezultat.stderr or "").strip(),
            )
        except Exception:
            logger.exception("Unexpected error during service restart start step")
            start_ok = False
    else:
        logger.warning("Service restart aborted because stop step failed")
        start_ok = False

    app.after(0, lambda: finalizeaza_comanda("restart", stop_ok and start_ok, False, state, widgets, app))


def ruleaza_comanda(
    comanda: str,
    state: AppState,
    widgets: dict,
    app
) -> None:
    """Rulează o comandă de sistem cu drepturi de administrator fără să blocheze UI-ul."""
    with comanda_lock:
        if state.comanda_in_curs:
            logger.warning("Ignored service command because another command is already running: %s", comanda)
            return
        state.comanda_in_curs = True

    logger.info("Service command requested from UI: %s", comanda)

    if comanda in ("stop", "restart") and settings.get("confirm_before_stop", True):
        actiune = "oprirea" if comanda == "stop" else "restart-ul"
        confirmat = messagebox.askyesno(
            "Confirmare",
            f"Sigur vrei să execuți {actiune} serviciului Ollama?"
        )
        if not confirmat:
            logger.info("Service command cancelled by user before pkexec: %s", comanda)
            with comanda_lock:
                state.comanda_in_curs = False
            return

    seteaza_stare_butoane(False, widgets)
    arata_notificare("Se execută comanda...", "info", app, widgets["notification_frame"], widgets["notification_label"])
    widgets["status_label"].configure(text="Se execută comanda...", text_color="#f1c40f")
    widgets["subtitle_label"].configure(text="Așteaptă confirmarea sistemului", text_color="#f1c40f")
    app.update_idletasks()

    if comanda == "restart":
        threading.Thread(target=executa_restart_in_fundal, args=(state, widgets, app), daemon=True).start()
    else:
        threading.Thread(target=executa_comanda_in_fundal, args=(comanda, state, widgets, app), daemon=True).start()
