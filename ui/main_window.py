import tkinter as tk
import customtkinter as ctk
import subprocess
import time
from pathlib import Path

from config.settings import BASE_DIR, settings, salveaza_setari
from core.app_state import AppState
from ui.notifications import arata_notificare
from ui.status_section import build_status_section
from ui.meta_section import build_meta_section
from ui.buttons_section import build_buttons_section

try:
    from PIL import Image
except ImportError:
    Image = None

from utils.logging_config import LOG_PATH, logger


def incarca_imagine_ctk(nume_fisier: str, size: tuple[int, int]) -> ctk.CTkImage | None:
    cale = BASE_DIR / nume_fisier
    if Image is not None:
        imagine = Image.open(cale)
        return ctk.CTkImage(light_image=imagine, dark_image=imagine, size=size)
    return None


def deschide_log(app, widgets: dict) -> None:
    try:
        logger.info("Open log requested from UI: %s", LOG_PATH)
        subprocess.Popen(["xdg-open", str(LOG_PATH)])
        arata_notificare(
            f"Se deschide logul: {LOG_PATH}",
            "info",
            app,
            widgets["notification_frame"],
            widgets["notification_label"],
        )
    except Exception:
        logger.exception("Failed to open application log: %s", LOG_PATH)
        arata_notificare(
            f"Nu s-a putut deschide logul: {LOG_PATH}",
            "error",
            app,
            widgets["notification_frame"],
            widgets["notification_label"],
        )


def arata_incarcare_model(state: AppState, widgets: dict, app) -> None:
    state.model_incarcare_in_curs = True
    state.model_incarcare_inceput = time.monotonic()
    widgets["loading_model_frame"].pack(padx=24, pady=(0, 10), fill="x")
    widgets["loading_model_bar"].start()


def ascunde_incarcare_model(state: AppState, widgets: dict) -> None:
    state.model_incarcare_in_curs = False
    state.model_incarcare_inceput = 0.0
    try:
        widgets["loading_model_bar"].stop()
        widgets["loading_model_frame"].pack_forget()
    except Exception:
        pass


def update_active_model(state: AppState, widgets: dict, model_name: str, app) -> None:
    state.selected_model_name = model_name
    state.model_activ_cache = model_name
    state.model_incarcare_in_curs = True
    widgets["model_label"].configure(text=model_name)
    arata_incarcare_model(state, widgets, app)

    keepalive = str(settings.get("ollama_keepalive", "10m")).strip() or "10m"
    arata_notificare(
        f"Modelul '{model_name}' a fost confirmat de Ollama și rămâne încărcat pentru {keepalive}.",
        "success",
        app,
        widgets["notification_frame"],
        widgets["notification_label"],
    )

    recente = settings.get("recent_models", [])
    if model_name in recente:
        recente.remove(model_name)
    recente.insert(0, model_name)
    recente = recente[:5]
    settings["recent_models"] = recente
    salveaza_setari()


def eject_active_model(state: AppState, widgets: dict, app) -> None:
    if not state.selected_model_name and state.model_activ_cache in ("Se verifică...", "Indisponibil", "niciun model încărcat"):
        arata_notificare("Niciun model activ de ejectat", "warning", app, widgets["notification_frame"], widgets["notification_label"])
        return

    def after_eject(success: bool) -> None:
        state.selected_model_name = None
        state.model_incarcare_in_curs = False
        ascunde_incarcare_model(state, widgets)
        if success:
            state.model_activ_cache = "niciun model încărcat"
            widgets["model_label"].configure(text=state.model_activ_cache)
            from ui.model_window import notify_model_loader_active_model
            notify_model_loader_active_model(None)
            arata_notificare("Model ejectat cu succes", "success", app, widgets["notification_frame"], widgets["notification_label"])
        else:
            arata_notificare("Eroare la ejectare — modelul nu a pornit încă. Așteaptă câteva secunde.", "error", app, widgets["notification_frame"], widgets["notification_label"])

    from ui.model_window import eject_model
    eject_model(after_eject)


def copiaza_nume_model(state: AppState, widgets: dict, app) -> None:
    """Copiază în clipboard numele modelului activ."""
    nume = state.model_activ_cache or state.selected_model_name or ""

    fara_model = ("", "Se verifică...", "Indisponibil", "niciun model încărcat", "—")
    if not nume or nume in fara_model:
        arata_notificare(
            "Niciun model activ de copiat",
            "warning", app, widgets["notification_frame"], widgets["notification_label"],
        )
        return

    try:
        app.clipboard_clear()
        app.clipboard_append(nume)
        # X11 are nevoie de un ciclu de evenimente ca textul să rămână
        # în clipboard după ce fereastra își pierde focusul.
        app.update_idletasks()
    except Exception:
        logger.exception("Failed to copy the active model name to the clipboard")
        arata_notificare(
            "Nu s-a putut copia numele modelului",
            "error", app, widgets["notification_frame"], widgets["notification_label"],
        )
        return

    arata_notificare(
        f"Nume copiat: {nume}",
        "success", app, widgets["notification_frame"], widgets["notification_label"],
    )


def verifica_versiune_actualizare(widgets: dict) -> None:
    """Verifică în fundal dacă există o versiune nouă de Ollama.

    Butonul de actualizare apare doar când versiunea disponibilă este mai
    recentă decât cea instalată.
    """
    import threading

    from services.ollama_update import check_for_update

    def angajament() -> None:
        try:
            info = check_for_update()
        except Exception:
            logger.exception("Failed to check for an Ollama update")
            return

        def aplica() -> None:
            try:
                button = widgets.get("update_button")
                if button is None:
                    return
                if info.get("update_available"):
                    button.pack(side="left")
                    logger.info(
                        "Ollama update available: installed=%s latest=%s",
                        info.get("installed"),
                        info.get("latest"),
                    )
                else:
                    button.pack_forget()
            except Exception:
                logger.exception("Failed to update the Ollama update button")

        try:
            widgets["_app"].after(0, aplica)
        except Exception:
            pass

    threading.Thread(target=angajament, daemon=True).start()


def build_main_window(app) -> tuple[AppState, dict]:
    state = AppState()

    icon_path = str(BASE_DIR / "icon.png")
    ui_uptime_icon = incarca_imagine_ctk("ui_uptime.png", (16, 16))
    ui_status_icon = incarca_imagine_ctk("ui_status.png", (16, 16))
    ui_model_icon = incarca_imagine_ctk("ui_model.png", (18, 18))
    ui_version_icon = incarca_imagine_ctk("ui_version.png", (18, 18))
    ui_copy_icon = incarca_imagine_ctk("ui_copy.png", (16, 16))
    try:
        app.iconphoto(True, tk.PhotoImage(file=icon_path))
    except Exception:
        pass

    app.title("Ollama Control")
    app.geometry("760x580")
    app.resizable(False, False)
    app.configure(fg_color="#0f172a")

    main_frame = ctk.CTkFrame(
        app, width=680, height=430,
        corner_radius=24, fg_color="#111827",
        border_width=1, border_color="#1e293b"
    )
    main_frame.place(relx=0.5, rely=0.5, anchor="center")

    title_label = ctk.CTkLabel(
        main_frame, text="Ollama Control",
        font=ctk.CTkFont(size=28, weight="bold"), text_color="#f9fafb"
    )
    title_label.pack(pady=(22, 2))

    subtitle_top = ctk.CTkLabel(
        main_frame,
        text="Panou desktop pentru controlul serviciului local Ollama",
        font=ctk.CTkFont(size=12), text_color="#8ea0b8"
    )
    subtitle_top.pack(pady=(0, 12))

    status_widgets = build_status_section(main_frame, ui_uptime_icon, ui_status_icon)
    meta_widgets = build_meta_section(main_frame, ui_model_icon, ui_version_icon, ui_copy_icon)
    buttons_widgets = build_buttons_section(main_frame)

    # Butonul de actualizare Ollama apare când există o versiune nouă.
    def deschide_actualizare() -> None:
        from ui.ollama_update_dialog import deschide_dialog_actualizare

        try:
            deschide_dialog_actualizare(
                app,
                on_finished=lambda succes: app.after(0, lambda: verifica_versiune_actualizare(widgets)),
            )
        except Exception:
            logger.exception("Failed to open the Ollama update dialog")

    meta_widgets["update_button"].configure(command=deschide_actualizare)

    # Butonul de copiere preia numele modelului activ din stare.
    meta_widgets["copy_button"].configure(
        command=lambda: copiaza_nume_model(state, widgets, app)
    )

    # Butoane model
    load_model_button = ctk.CTkButton(
        meta_widgets["meta_frame"],
        text="Încarcă Model", width=150, height=32,
        fg_color="#2563eb", hover_color="#1d4ed8",
        font=ctk.CTkFont(size=12, weight="bold"),
        command=lambda: open_model_window(app)
    )
    load_model_button.grid(row=2, column=0, sticky="w", padx=(18, 8), pady=(8, 14))

    eject_button = ctk.CTkButton(
        meta_widgets["meta_frame"],
        text="Eject Model", width=100, height=32,
        fg_color="#ef4444", hover_color="#dc2626",
        font=ctk.CTkFont(size=12, weight="bold"),
        command=lambda: eject_active_model(state, widgets, app)
    )
    eject_button.grid(row=2, column=1, sticky="w", padx=(0, 30), pady=(8, 14))

    # Butoane principale
    settings_button = ctk.CTkButton(
        buttons_widgets["buttons_frame"],
        text="Setări", width=90, height=46, corner_radius=16,
        fg_color="#0f172a", hover_color="#1e293b",
        border_width=1, border_color="#334155", text_color="#e2e8f0",
        font=ctk.CTkFont(size=13, weight="bold"),
        command=lambda: deschide_setari(app, widgets)
    )
    settings_button.pack(side="left", padx=4)

    logs_button = ctk.CTkButton(
        buttons_widgets["buttons_frame"],
        text="Log", width=80, height=46, corner_radius=16,
        fg_color="#0f172a", hover_color="#1e293b",
        border_width=1, border_color="#334155", text_color="#e2e8f0",
        font=ctk.CTkFont(size=13, weight="bold"),
        command=lambda: deschide_log(app, widgets)
    )
    logs_button.pack(side="left", padx=4)

    start_button = ctk.CTkButton(
        buttons_widgets["buttons_frame"],
        text="Pornește", width=110, height=46, corner_radius=16,
        fg_color="#22c55e", hover_color="#16a34a", text_color="#08130d",
        font=ctk.CTkFont(size=14, weight="bold"),
        command=lambda: ruleaza_comanda("start", state, widgets, app)
    )
    start_button.pack(side="left", padx=4)

    restart_button = ctk.CTkButton(
        buttons_widgets["buttons_frame"],
        text="Restart", width=110, height=46, corner_radius=16,
        fg_color="#f59e0b", hover_color="#d97706", text_color="#1a1206",
        font=ctk.CTkFont(size=14, weight="bold"),
        command=lambda: ruleaza_comanda("restart", state, widgets, app)
    )
    restart_button.pack(side="left", padx=4)

    refresh_button = ctk.CTkButton(
        buttons_widgets["buttons_frame"],
        text="Reîmprospătează", width=90, height=46, corner_radius=16,
        fg_color="#1f2937", hover_color="#334155",
        border_width=1, border_color="#334155", text_color="#e2e8f0",
        font=ctk.CTkFont(size=13, weight="bold"),
        command=lambda: actualizeaza_stare(state, widgets, app, force_service_refresh=True)
    )
    refresh_button.pack(side="left", padx=4)

    stop_button = ctk.CTkButton(
        buttons_widgets["buttons_frame"],
        text="Oprește", width=110, height=46, corner_radius=16,
        fg_color="#ef4444", hover_color="#dc2626", text_color="#ffffff",
        font=ctk.CTkFont(size=14, weight="bold"),
        command=lambda: ruleaza_comanda("stop", state, widgets, app)
    )
    stop_button.pack(side="left", padx=4)

    widgets = {
        **status_widgets,
        **meta_widgets,
        **buttons_widgets,
        "settings_button": settings_button,
        "logs_button": logs_button,
        "start_button": start_button,
        "refresh_button": refresh_button,
        "restart_button": restart_button,
        "stop_button": stop_button,
        "load_model_button": load_model_button,
        "eject_button": eject_button,
        "_state": state,
        "_app": app,
    }

    # Verificarea versiunii noi se face în fundal, la pornire.
    verifica_versiune_actualizare(widgets)

    return state, widgets


from core.commands import ruleaza_comanda
from core.state_manager import actualizeaza_stare
from ui.settings_window import deschide_setari
from ui.model_window import open_model_window
