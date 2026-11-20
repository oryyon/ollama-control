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


def deschide_setari(app, widgets) -> None:
    global settings_window

    if settings_window is not None and settings_window.winfo_exists():
        settings_window.focus()
        return

    settings_window = ctk.CTkToplevel(app)
    settings_window.title("Setări")
    settings_window.geometry("420x580")
    settings_window.resizable(False, False)
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
        text="Auto-refresh",
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
    interval_menu.pack(anchor="w", padx=18, pady=(6, 14))

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
                for child in settings_window.winfo_children():
                    try:
                        if hasattr(child, 'configure'):
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
