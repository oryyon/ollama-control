import threading
import tkinter as tk
import customtkinter as ctk
import weakref

from ui.model_list import ModelList
from ui.model_actions import (
    set_active_model_callback,
    eject_model,
    run_model,
    import_and_run_lmstudio,
)
from ui.model_config_dialog import ModelConfigDialog
from core.model_config import create_model_with_context_threaded
from core.ollama_models import delete_ollama_model
from config.settings import settings
from services.ollama_info import normalize_model_name, obtine_model_activ
from utils.logging_config import logger

_open_model_windows: weakref.WeakSet = weakref.WeakSet()


def notify_model_loader_active_model(model_name: str | None) -> None:
    for window in list(_open_model_windows):
        try:
            window.sync_active_model_indicator(model_name)
        except Exception:
            logger.exception("Failed to sync active model indicator for an open Model Loader window")


def open_model_window(root: ctk.CTk) -> None:
    ModelWindow(root)


class ModelWindow:

    HEADER_BUTTON_FG = ("#60a5fa", "#2563eb")
    HEADER_BUTTON_HOVER = ("#3b82f6", "#1d4ed8")
    CANCEL_BUTTON_FG = ("#ef4444", "#dc2626")
    CANCEL_BUTTON_HOVER = ("#dc2626", "#b91c1c")
    BUTTON_TEXT = ("#ffffff", "#ffffff")
    BUTTON_DISABLED_FG = ("#cbd5e1", "#334155")
    BUTTON_DISABLED_TEXT = ("#64748b", "#94a3b8")
    BUTTON_SELECTED_FG = ("#93c5fd", "#1d4ed8")
    BUTTON_SELECTED_TEXT = ("#1e3a8a", "#dbeafe")
    PROGRESS_TEXT = ("#1e293b", "#e2e8f0")
    PROGRESS_ACCENT = ("#2563eb", "#38bdf8")
    PROGRESS_TRACK = ("#dbeafe", "#1e293b")

    def __init__(self, root: ctk.CTk) -> None:
        self.root = root
        self.win = ctk.CTkToplevel(root)
        self.win.title("Model Loader")
        self.win.geometry("750x520")
        _open_model_windows.add(self)

        self.mode = tk.StringVar(value="lmstudio")
        self.active_mode_button: ctk.CTkButton | None = None

        self._build_header()
        self._build_progress_container()
        self.model_list = ModelList(
            self.win,
            on_select=self._on_select,
            on_config=self._on_config_model if self.mode.get() == "ollama" else None,
            on_delete=self._on_delete_model if self.mode.get() == "ollama" else None,
        )
        self._apply_mode_button_states()
        self.load_models()

    def _build_progress_container(self) -> None:
        self.progress_container = ctk.CTkFrame(self.win, fg_color="transparent")
        # Nu facem pack aici — containerul va apărea doar când e necesar

    def _build_header(self) -> None:
        title = ctk.CTkLabel(
            self.win,
            text="Selectează sursa modelelor",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title.pack(pady=10)

        switch = ctk.CTkFrame(self.win, fg_color="transparent")
        switch.pack(pady=10)

        self.lm_button = ctk.CTkButton(
            switch,
            text="LM Studio",
            fg_color=self.HEADER_BUTTON_FG,
            hover_color=self.HEADER_BUTTON_HOVER,
            text_color=self.BUTTON_TEXT,
            text_color_disabled=self.BUTTON_SELECTED_TEXT,
            command=lambda: self.switch("lmstudio")
        )
        self.lm_button.pack(side="left", padx=10)

        self.ollama_button = ctk.CTkButton(
            switch,
            text="Ollama",
            fg_color=self.HEADER_BUTTON_FG,
            hover_color=self.HEADER_BUTTON_HOVER,
            text_color=self.BUTTON_TEXT,
            text_color_disabled=self.BUTTON_SELECTED_TEXT,
            command=lambda: self.switch("ollama")
        )
        self.ollama_button.pack(side="left", padx=10)

        self.cancel_button = ctk.CTkButton(
            switch,
            text="Anulează",
            fg_color=self.CANCEL_BUTTON_FG,
            hover_color=self.CANCEL_BUTTON_HOVER,
            text_color=self.BUTTON_TEXT,
            text_color_disabled=self.BUTTON_DISABLED_TEXT,
            command=self.safe_destroy
        )
        self.cancel_button.pack(side="left", padx=10)

    def _iter_buttons(self, parent) -> list[ctk.CTkButton]:
        buttons: list[ctk.CTkButton] = []
        try:
            for child in parent.winfo_children():
                if isinstance(child, ctk.CTkButton):
                    buttons.append(child)
                buttons.extend(self._iter_buttons(child))
        except Exception:
            return buttons
        return buttons

    def _style_button(self, button: ctk.CTkButton, fg_color, hover_color, text_color) -> None:
        button.configure(fg_color=fg_color, hover_color=hover_color, text_color=text_color)

    def _style_header_buttons_for_mode(self) -> None:
        for mode_name, button in {"lmstudio": self.lm_button, "ollama": self.ollama_button}.items():
            if self.mode.get() == mode_name:
                self._style_button(button, self.BUTTON_SELECTED_FG, self.BUTTON_SELECTED_FG, self.BUTTON_SELECTED_TEXT)
                button.configure(state=tk.DISABLED)
            else:
                self._style_button(button, self.HEADER_BUTTON_FG, self.HEADER_BUTTON_HOVER, self.BUTTON_TEXT)
                button.configure(state=tk.NORMAL)

    def _style_list_buttons(self, enabled: bool) -> None:
        for button in self._iter_buttons(self.model_list.list_frame):
            enabled_fg = getattr(button, "_enabled_fg_color", self.HEADER_BUTTON_FG)
            enabled_hover = getattr(button, "_enabled_hover_color", self.HEADER_BUTTON_HOVER)
            if enabled:
                self._style_button(button, enabled_fg, enabled_hover, self.BUTTON_TEXT)
                button.configure(state=tk.NORMAL)
            else:
                self._style_button(button, self.BUTTON_DISABLED_FG, self.BUTTON_DISABLED_FG, self.BUTTON_DISABLED_TEXT)
                button.configure(state=tk.DISABLED)

    def _apply_mode_button_states(self) -> None:
        self._style_header_buttons_for_mode()

    def _set_buttons_enabled(self, enabled: bool) -> None:
        if enabled:
            self._apply_mode_button_states()
            self._style_button(self.cancel_button, self.CANCEL_BUTTON_FG, self.CANCEL_BUTTON_HOVER, self.BUTTON_TEXT)
            self.cancel_button.configure(state=tk.NORMAL)
        else:
            self._style_button(self.lm_button, self.BUTTON_DISABLED_FG, self.BUTTON_DISABLED_FG, self.BUTTON_DISABLED_TEXT)
            self.lm_button.configure(state=tk.DISABLED)
            self._style_button(self.ollama_button, self.BUTTON_DISABLED_FG, self.BUTTON_DISABLED_FG, self.BUTTON_DISABLED_TEXT)
            self.ollama_button.configure(state=tk.DISABLED)
            self._style_button(self.cancel_button, self.BUTTON_DISABLED_FG, self.BUTTON_DISABLED_FG, self.BUTTON_DISABLED_TEXT)
            self.cancel_button.configure(state=tk.DISABLED)

        self._style_list_buttons(enabled)

    def switch(self, mode: str) -> None:
        logger.info("Model Loader switched to source=%s", mode)
        if mode == "lmstudio":
            self.mode.set(mode)
            self.active_mode_button = self.lm_button
            self.model_list.on_config = None
            self.model_list.on_delete = None
        else:
            self.mode.set(mode)
            self.active_mode_button = self.ollama_button
            self.model_list.on_config = self._on_config_model
            self.model_list.on_delete = self._on_delete_model

        self._apply_mode_button_states()
        self.load_models()

    def load_models(self) -> None:
        if self.mode.get() == "lmstudio":
            self.model_list.load_models("lmstudio", None)
        else:
            self.model_list.load_models("ollama", self._on_ollama_loaded)

    def _on_ollama_loaded(self, models, success) -> None:
        self.win.after(0, lambda: self._finish_ollama_loaded(models, success))

    def _finish_ollama_loaded(self, models, success) -> None:
        if self.mode.get() != "ollama":
            return
        self.model_list.on_models_loaded(models, success)
        if success:
            self._refresh_active_model_indicator()

    def _refresh_active_model_indicator(self) -> None:
        model_text = obtine_model_activ("active")
        if not model_text.startswith("Model activ:"):
            self.sync_active_model_indicator(None)
            return

        active_name = normalize_model_name(model_text.split(":", 1)[1].strip())
        if active_name in ("", "indisponibil", "niciun model încărcat", "runner detectat"):
            self.sync_active_model_indicator(None)
            return

        self.sync_active_model_indicator(active_name)

    def sync_active_model_indicator(self, model_name: str | None) -> None:
        if not self.win.winfo_exists():
            return
        self.win.after(0, lambda: self.model_list.set_active_model(model_name))

    def _on_select(self, name: str, path: str | None) -> None:
        size_gb = self._get_model_size_gb(name)
        logger.info("Model Loader select clicked: source=%s name=%s path=%s size_gb=%.2f", self.mode.get(), name, path, size_gb)
        if self.mode.get() == "lmstudio":
            self._show_progress("Se importă modelul în Ollama...", determinate=True)
            import_and_run_lmstudio(
                name, path, self._on_import_done,
                progress_callback=self._update_progress,
                size_gb=size_gb
            )
        else:
            self._show_progress("Se așteaptă confirmarea Ollama pentru încărcarea modelului...", determinate=False)
            threading.Thread(
                target=lambda: self._run_ollama_model(name, size_gb),
                daemon=True,
            ).start()

    def _run_ollama_model(self, name: str, size_gb: float) -> None:
        try:
            success, error_message = run_model(name, progress_callback=self._update_progress, size_gb=size_gb)
            self.win.after(0, lambda: self._on_run_model_done(success, name, error_message))
        except Exception as e:
            logger.exception("Unexpected exception while loading Ollama model %s", name)
            self.win.after(0, lambda: self._on_run_model_done(False, name, f"Eroare neașteptată la încărcarea modelului '{name}'."))

    def _on_run_model_done(self, success: bool, name: str, error_message: str | None = None) -> None:
        logger.info("Model Loader Ollama flow finished: name=%s success=%s", name, success)
        if success:
            keepalive = settings.get("ollama_keepalive", "10m")
            notify_model_loader_active_model(name)
            self._hide_progress()
            self._show_message(
                f"Modelul '{name}' a fost confirmat de Ollama și rămâne încărcat pentru {keepalive}.",
                text_color="#16a34a"
            )
            self._after_id = self.win.after(1600, self.safe_destroy)
        else:
            self._hide_progress()
            self._show_error(error_message or f"Eroare la încărcarea modelului '{name}'.")

    def _get_model_size_gb(self, name: str) -> float:
        from core.ollama_models import _parse_size_to_gb
        for model in self.model_list.all_models:
            if model["name"] == name:
                size_str = model.get("size", "")
                if size_str and size_str != "N/A":
                    return _parse_size_to_gb(size_str)
        return 0.0

    def _on_import_done(self, success: bool, model_name: str) -> None:
        try:
            self.win.after(0, lambda: self._finish_import_done(success, model_name))
        except Exception:
            pass

    def _finish_import_done(self, success: bool, model_name: str) -> None:
        logger.info("Model Loader LM Studio flow finished: name=%s success=%s", model_name, success)
        self._hide_progress()
        if not success:
            self._show_error(f"Importul modelului '{model_name}' a eșuat.")
            return
        self.safe_destroy()

    def _on_config_model(self, name: str) -> None:
        def on_apply(model_name: str, num_ctx: int) -> None:
            self._show_progress(f"Se configurează {model_name} (ctx={num_ctx})...", determinate=False)

            def on_done(success: bool, derived_name: str) -> None:
                self.win.after(0, lambda: self._on_config_done(success, derived_name))

            create_model_with_context_threaded(model_name, num_ctx, callback=on_done)

        ModelConfigDialog(self.win, name, on_apply=on_apply)

    def _on_config_done(self, success: bool, derived_name: str) -> None:
        self._hide_progress()
        if success:
            self._show_message(f"Modelul '{derived_name}' a fost creat cu succes.", text_color="#16a34a")
            # Reîncarcă lista de modele Ollama
            self.load_models()
        else:
            self._show_error(f"Eroare la crearea modelului '{derived_name}'.")

    def _on_delete_model(self, name: str) -> None:
        from tkinter import messagebox
        confirmed = messagebox.askyesno(
            "Confirmare ștergere",
            f"Sigur vrei să ștergi modelul '{name}'?\n\nAceastă acțiune este ireversibilă."
        )
        if not confirmed:
            return

        self._show_progress(f"Se șterge modelul '{name}'...", determinate=False)

        def on_done(success: bool, deleted_name: str) -> None:
            self.win.after(0, lambda: self._on_delete_done(success, deleted_name))

        threading.Thread(
            target=lambda: delete_ollama_model(name, callback=on_done),
            daemon=True
        ).start()

    def _on_delete_done(self, success: bool, deleted_name: str) -> None:
        self._hide_progress()
        if success:
            self._show_message(f"Modelul '{deleted_name}' a fost șters.", text_color="#16a34a")
            # Reîncarcă lista de modele Ollama
            self.load_models()
        else:
            self._show_error(f"Eroare la ștergerea modelului '{deleted_name}'.")

    def _show_progress(self, text: str = "Se încarcă modelul...", determinate: bool = False) -> None:
        # Golește containerul înainte de a adăuga elemente noi
        for child in self.progress_container.winfo_children():
            child.destroy()

        # Afișează containerul (pack) doar când e necesar, înaintea listei de modele
        try:
            search_frame = self.model_list.search_entry.master
            self.progress_container.pack(pady=(0, 5), before=search_frame)
        except Exception:
            self.progress_container.pack(pady=(0, 5))

        self.progress_frame = ctk.CTkFrame(self.progress_container, fg_color="transparent")
        self.progress_frame.pack(pady=(0, 5))

        self.progress_label = ctk.CTkLabel(
            self.progress_frame, text=text,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=self.PROGRESS_TEXT,
        )
        self.progress_label.pack(pady=(0, 5))

        self.progress_pct_label = ctk.CTkLabel(
            self.progress_frame, text="0%",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.PROGRESS_ACCENT,
        )
        self.progress_pct_label.pack(pady=(0, 3))

        mode = "determinate" if determinate else "indeterminate"
        self.progress_bar = ctk.CTkProgressBar(
            self.progress_frame,
            width=400,
            mode=mode,
            progress_color=self.PROGRESS_ACCENT,
            fg_color=self.PROGRESS_TRACK,
        )
        self.progress_bar.pack()
        if not determinate:
            self.progress_bar.start()
        else:
            self.progress_bar.set(0)

        self._set_buttons_enabled(False)

    def _update_progress(self, pct: int) -> None:
        def _do_update() -> None:
            try:
                if hasattr(self, "progress_bar") and self.progress_bar.winfo_exists():
                    self.progress_bar.set(pct / 100)
                if hasattr(self, "progress_pct_label") and self.progress_pct_label.winfo_exists():
                    self.progress_pct_label.configure(text=f"{pct}%")
            except Exception:
                pass

        try:
            self.win.after(0, _do_update)
        except Exception:
            pass

    def _hide_progress(self) -> None:
        try:
            for child in self.progress_container.winfo_children():
                try:
                    child.destroy()
                except Exception:
                    pass
            # Ascunde containerul pentru a nu ocupa spațiu
            self.progress_container.pack_forget()
        except Exception:
            pass
        self._set_buttons_enabled(True)

    def safe_destroy(self) -> None:
        try:
            _open_model_windows.discard(self)
            self._set_buttons_enabled(False)
            if hasattr(self, '_after_id') and self._after_id:
                try:
                    self.win.after_cancel(self._after_id)
                except Exception:
                    pass
                self._after_id = None
            if self.win.winfo_exists():
                self.win.destroy()
        except Exception:
            pass

    def _show_error(self, message: str) -> None:
        self._show_message(message, text_color="#dc2626")

    def _show_message(self, message: str, text_color: str) -> None:
        message_label = ctk.CTkLabel(
            self.win, text=message,
            text_color=text_color,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        message_label.pack(pady=(0, 10))
        self.win.after(3000, message_label.destroy)
