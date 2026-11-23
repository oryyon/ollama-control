import tkinter as tk
import customtkinter as ctk

from config.settings import (KEEPALIVE_DEFAULT, aplica_interval_auto_refresh,
                             aplica_tema, is_valid_keepalive, salveaza_setari,
                             settings)
from ui.notifications import arata_notificare

settings_window: ctk.CTkToplevel | None = None


def _is_valid_keepalive(value: str) -> bool:
    """Alias păstrat pentru compatibilitate — validarea stă în `config`."""
    return is_valid_keepalive(value)


def _centraza_fereastra(fereastra: ctk.CTkToplevel, app, latime: int, inaltime: int) -> None:
    """Așază fereastra pe centrul ferestrei principale (sau al ecranului)."""
    try:
        if app is not None and app.winfo_width() > 1 and app.winfo_height() > 1:
            x = app.winfo_rootx() + (app.winfo_width() - latime) // 2
            y = app.winfo_rooty() + (app.winfo_height() - inaltime) // 2
        else:
            x = (fereastra.winfo_screenwidth() - latime) // 2
            y = (fereastra.winfo_screenheight() - inaltime) // 2
        fereastra.geometry(f"{latime}x{inaltime}+{max(x, 0)}+{max(y, 0)}")
    except Exception:
        fereastra.geometry(f"{latime}x{inaltime}")


def deschide_setari(app, widgets) -> None:
    global settings_window

    if settings_window is not None and settings_window.winfo_exists():
        settings_window.focus()
        return

    settings_window = ctk.CTkToplevel(app)
    settings_window.title("Setări")
    settings_window.configure(fg_color="#0f172a")
    settings_window.transient(app)
    settings_window.lift()
    settings_window.focus_force()

    frame = ctk.CTkFrame(
        settings_window,
        corner_radius=18,
        fg_color="#111827",
        border_width=1,
        border_color="#1f2937"
    )
    frame.pack(fill="both", expand=True, padx=18, pady=18)

    title = ctk.CTkLabel(
        frame,
        text="Setări",
        font=ctk.CTkFont(size=22, weight="bold"),
        text_color="#f8fafc"
    )
    title.pack(anchor="w", padx=18, pady=(18, 14))

    interval_salvat = settings.get("auto_refresh_interval", 5)
    interval_initial = "Off" if interval_salvat == 0 else str(interval_salvat)
    interval_var = tk.StringVar(value=interval_initial)
    confirm_stop_var = tk.BooleanVar(value=settings.get("confirm_before_stop", True))
    keepalive_var = tk.StringVar(value=settings.get("ollama_keepalive", KEEPALIVE_DEFAULT))
    keepalive_custom_var = tk.StringVar(value="")

    interval_label = ctk.CTkLabel(
        frame,
        text="Auto-refresh rapid",
        font=ctk.CTkFont(size=13, weight="bold"),
        text_color="#cbd5e1"
    )
    interval_label.pack(anchor="w", padx=18)

    interval_menu = ctk.CTkOptionMenu(
        frame,
        values=["Off", "2 sec", "5 sec", "10 sec", "30 sec"],
        variable=interval_var,
        width=120
    )
    interval_menu.pack(anchor="w", padx=18, pady=(6, 4))

    ctk.CTkLabel(
        frame,
        text="Starea și resursele se verifică oricum la 60 de secunde.",
        font=ctk.CTkFont(size=11),
        text_color="#64748b"
    ).pack(anchor="w", padx=18, pady=(0, 12))

    confirm_stop_switch = ctk.CTkSwitch(
        frame,
        text="Confirmare înainte de Stop/Restart",
        variable=confirm_stop_var,
        onvalue=True,
        offvalue=False,
        text_color="#cbd5e1"
    )
    confirm_stop_switch.pack(anchor="w", padx=18, pady=(0, 10))

    keepalive_label = ctk.CTkLabel(
        frame,
        text="Durată keepalive Ollama",
        font=ctk.CTkFont(size=13, weight="bold"),
        text_color="#cbd5e1"
    )
    keepalive_label.pack(anchor="w", padx=18)

    keepalive_menu = ctk.CTkOptionMenu(
        frame,
        values=["-1m", "0m", "1m", "5m", "10m", "30m", "1h", "6h", "12h", "1d"],
        variable=keepalive_var,
        width=120
    )
    keepalive_menu.pack(anchor="w", padx=18, pady=(6, 14))

    keepalive_custom_label = ctk.CTkLabel(
        frame,
        text="Sau introdu o durată custom (ex: 45s, 15m, 2h, 1d)",
        font=ctk.CTkFont(size=11),
        text_color="#94a3b8"
    )
    keepalive_custom_label.pack(anchor="w", padx=18)

    keepalive_custom_entry = ctk.CTkEntry(
        frame,
        textvariable=keepalive_custom_var,
        width=140,
        placeholder_text="ex: 15m"
    )
    keepalive_custom_entry.pack(anchor="w", padx=18, pady=(6, 14))

    theme_var = tk.BooleanVar(value=(settings.get("theme", "dark") == "light"))
    theme_switch = ctk.CTkSwitch(
        frame,
        text="Mod luminos",
        variable=theme_var,
        onvalue=True,
        offvalue=False,
        text_color="#cbd5e1"
    )
    theme_switch.pack(anchor="w", padx=18, pady=(0, 18))

    recente = settings.get("recent_models", [])
    if recente:
        recent_frame = ctk.CTkFrame(frame, fg_color="transparent")
        recent_frame.pack(anchor="w", padx=18, pady=(0, 10), fill="x")

        recent_title = ctk.CTkLabel(
            recent_frame,
            text="Modele recente:",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#64748b"
        )
        recent_title.pack(anchor="w")

        for model in recente[:3]:
            model_label = ctk.CTkLabel(
                recent_frame,
                text=f"  • {model}",
                font=ctk.CTkFont(size=11),
                text_color="#64748b"
            )
            model_label.pack(anchor="w")

    buttons = ctk.CTkFrame(frame, fg_color="transparent")
    buttons.pack(anchor="e", padx=18, pady=(0, 18))

    def inchide_fereastra() -> None:
        global settings_window
        if settings_window is not None and settings_window.winfo_exists():
            try:
                # Dezactivăm doar widget-urile interactive: etichetele și
                # ramurile CustomTkinter nu acceptă parametrul `state`.
                for child in settings_window.winfo_children():
                    try:
                        if isinstance(child, (ctk.CTkButton, ctk.CTkEntry,
                                              ctk.CTkOptionMenu, ctk.CTkSwitch)):
                            child.configure(state="disabled")
                    except Exception:
                        pass
                settings_window.destroy()
            except Exception:
                pass
        settings_window = None

    def salveaza_din_ui() -> None:
        valoare = interval_var.get()
        if valoare == "Off":
            settings["auto_refresh_interval"] = 0
        else:
            try:
                interval = int(valoare.split()[0])
                if interval < 1:
                    interval = 1
                elif interval > 300:
                    interval = 300
                settings["auto_refresh_interval"] = interval
            except ValueError:
                settings["auto_refresh_interval"] = 5

        settings["confirm_before_stop"] = bool(confirm_stop_var.get())

        keepalive_custom = keepalive_custom_var.get().strip()
        if keepalive_custom:
            if not _is_valid_keepalive(keepalive_custom):
                arata_notificare(
                    "Durata keepalive este invalidă. Folosește formate precum 45s, 10m sau 2h.",
                    "error",
                    app,
                    widgets["notification_frame"],
                    widgets["notification_label"],
                )
                return
            settings["ollama_keepalive"] = keepalive_custom.lower()
        else:
            settings["ollama_keepalive"] = keepalive_var.get().strip() or "10m"

        tema_noua = "light" if theme_var.get() else "dark"
        settings["theme"] = tema_noua
        ctk.set_appearance_mode(tema_noua)

        aplica_interval_auto_refresh()
        salveaza_setari()
        from core.state_manager import programeaza_auto_refresh
        programeaza_auto_refresh(app, widgets)
        arata_notificare("Setările au fost salvate", "success", app, widgets["notification_frame"], widgets["notification_label"])
        inchide_fereastra()

    cancel_button = ctk.CTkButton(
        buttons,
        text="Anulează",
        width=90,
        fg_color="#1f2937",
        hover_color="#334155",
        command=inchide_fereastra
    )
    cancel_button.pack(side="left", padx=(0, 8))

    save_button = ctk.CTkButton(
        buttons,
        text="Salvează",
        width=90,
        fg_color="#2563eb",
        hover_color="#1d4ed8",
        command=salveaza_din_ui
    )
    save_button.pack(side="left")

    _ajusteaza_dimensiunile(settings_window, frame, app)


#: Înălțimea minimă a ferestrei de setări.
INALTIME_MINIMA = 420

#: Cât lăsăm liber pe ecran (bara de activități, margini).
SPAZIU_PENTRU_ECRAN = 80


def calculeaza_inaltime(necesar: int, ecran_inaltime: int) -> int:
    """Înălțimea ferestrei: cât cere conținutul, dar nu mai mult decât ecranul.

    Înălțimea fixă de 580 px tăia butoanele „Anulează” și „Salvează” imediat
    ce lista de modele recente avea trei intrări. Fereastra se măsoară acum
    după conținutul real, iar pe ecrane mici rămâne derulabilă prin limita
    impusă aici.
    """
    return max(INALTIME_MINIMA, min(necesar, ecran_inaltime - SPAZIU_PENTRU_ECRAN))


def _ajusteaza_dimensiunile(fereastra: ctk.CTkToplevel, frame, app) -> None:
    """Dimensionează fereastra după conținutul real."""
    latime = 420
    try:
        fereastra.update_idletasks()
        frame.update_idletasks()

        # Frame-ul e lipit cu padx=18, pady=18, deci marginea de sus și de
        # jos se adaugă la înălțimea cerută a conținutului.
        necesar = frame.winfo_reqheight() + 36
        inaltime = calculeaza_inaltime(necesar, fereastra.winfo_screenheight())

        fereastra.resizable(False, False)
        _centraza_fereastra(fereastra, app, latime, inaltime)
    except Exception:
        try:
            fereastra.geometry(f"420x{calculeaza_inaltime(620, fereastra.winfo_screenheight())}")
        except Exception:
            pass
