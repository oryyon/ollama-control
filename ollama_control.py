#!/usr/bin/env python3
import customtkinter as ctk

from config.settings import settings, incarca_setari, aplica_interval_auto_refresh, aplica_tema
from ui.main_window import build_main_window, update_active_model
from ui.model_window import notify_model_loader_active_model, set_active_model_callback
from core.state_manager import actualizeaza_stare, programeaza_auto_refresh

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
settings.update(incarca_setari())
aplica_interval_auto_refresh()
aplica_tema()

state, widgets = build_main_window(app)

def _pe_model_activ(name: str) -> None:
    """Actualizează interfața când Ollama confirmă modelul activ."""
    app.after(
        0,
        lambda: (
            update_active_model(state, widgets, name, app),
            notify_model_loader_active_model(name),
        ),
    )


set_active_model_callback(_pe_model_activ)

actualizeaza_stare(state, widgets, app)
programeaza_auto_refresh(app, widgets)

app.mainloop()
