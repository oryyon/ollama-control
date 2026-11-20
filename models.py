"""Wrapper pentru compatibilitate — exportă funcțiile principale din ui.model_actions și ui.model_window."""

from ui.model_actions import (
    set_active_model_callback,
    eject_model,
)
from ui.model_window import open_model_window

__all__ = ["set_active_model_callback", "open_model_window", "eject_model"]
