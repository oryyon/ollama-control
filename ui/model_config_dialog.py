import tkinter as tk
import customtkinter as ctk

from core.model_config import get_model_context


class ModelConfigDialog:
    """Dialog pentru configurarea context length a unui model Ollama."""

    CONTEXT_OPTIONS = [2048, 4096, 8192, 16384, 32768, 65536, 128000]

    def __init__(self, parent: ctk.CTkToplevel, model_name: str, on_apply=None) -> None:
        self.model_name = model_name
        self.on_apply = on_apply
        self.result: int | None = None

        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title(f"Configurare {model_name}")
        self.dialog.geometry("480x280")
        self.dialog.resizable(False, False)
        self.dialog.configure(fg_color="#0f172a")
        self.dialog.transient(parent)
        self.dialog.lift()
        self.dialog.focus_force()
        self._build_ui()
        # grab_set amânat până când fereastra e vizibilă
        self.dialog.after(100, self._set_grab)

    def _set_grab(self) -> None:
        try:
            if self.dialog.winfo_exists():
                self.dialog.grab_set()
        except Exception:
            pass

    def _build_ui(self) -> None:
        frame = ctk.CTkFrame(
            self.dialog,
            corner_radius=18,
            fg_color="#111827",
            border_width=1,
            border_color="#1f2937",
        )
        frame.pack(fill="both", expand=True, padx=18, pady=18)

        title = ctk.CTkLabel(
            frame,
            text=f"Configurare\n{self.model_name}",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#f8fafc",
        )
        title.pack(pady=(14, 10))

        current_ctx = get_model_context(self.model_name)

        label = ctk.CTkLabel(
            frame,
            text="Context length (num_ctx):",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#cbd5e1",
        )
        label.pack(anchor="w", padx=18, pady=(10, 6))

        self.ctx_var = tk.IntVar(value=current_ctx)

        # Slider
        self.slider = ctk.CTkSlider(
            frame,
            from_=0,
            to=len(self.CONTEXT_OPTIONS) - 1,
            number_of_steps=len(self.CONTEXT_OPTIONS) - 1,
            command=self._on_slider_change,
            width=300,
        )
        self.slider.pack(padx=18, pady=(0, 4))

        # Setează poziția slider-ului la valoarea curentă
        try:
            idx = self.CONTEXT_OPTIONS.index(current_ctx)
            self.slider.set(idx)
        except ValueError:
            self.slider.set(1)  # default 4096

        # Label cu valoarea selectată
        self.value_label = ctk.CTkLabel(
            frame,
            text=f"{current_ctx} tokens",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#38bdf8",
        )
        self.value_label.pack(pady=(0, 14))

        buttons = ctk.CTkFrame(frame, fg_color="transparent")
        buttons.pack(anchor="e", padx=18, pady=(0, 14))

        ctk.CTkButton(
            buttons,
            text="Anulează",
            width=90,
            fg_color="#1f2937",
            hover_color="#334155",
            command=self._cancel,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            buttons,
            text="Aplică",
            width=90,
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            command=self._apply,
        ).pack(side="left")

    def _on_slider_change(self, value: float) -> None:
        idx = int(round(value))
        idx = max(0, min(idx, len(self.CONTEXT_OPTIONS) - 1))
        num_ctx = self.CONTEXT_OPTIONS[idx]
        self.ctx_var.set(num_ctx)
        self.value_label.configure(text=f"{num_ctx} tokens")

    def _apply(self) -> None:
        self.result = self.ctx_var.get()
        if self.on_apply:
            self.on_apply(self.model_name, self.result)
        self.dialog.destroy()

    def _cancel(self) -> None:
        self.result = None
        self.dialog.destroy()
