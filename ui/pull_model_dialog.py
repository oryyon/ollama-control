import threading
import tkinter as tk
import customtkinter as ctk

from services.ollama_api import pull_model
from utils.logging_config import logger


class PullModelDialog:
    """Dialog pentru descărcarea unui model din registry-ul Ollama."""

    DIALOG_BG = "#0f172a"
    FRAME_BG = "#111827"
    BORDER = "#1f2937"
    TEXT = "#f8fafc"
    MUTED = "#94a3b8"
    ACCENT = "#2563eb"
    ACCENT_HOVER = "#1d4ed8"
    DARK_BG = "#1f2937"
    DARK_HOVER = "#334155"
    SUCCESS = "#16a34a"
    WARNING = "#f59e0b"
    ERROR = "#dc2626"

    def __init__(self, parent: ctk.CTkToplevel, on_finished=None) -> None:
        self.parent = parent
        self.on_finished = on_finished
        self.in_curs = False

        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title("Descarcă model Ollama")
        self.dialog.geometry("540x330")
        self.dialog.resizable(False, False)
        self.dialog.configure(fg_color=self.DIALOG_BG)
        self.dialog.transient(parent)
        self.dialog.lift()
        self.dialog.focus_force()
        self._build_ui()
        self.model_entry.focus_set()

    def _build_ui(self) -> None:
        frame = ctk.CTkFrame(
            self.dialog,
            corner_radius=18,
            fg_color=self.FRAME_BG,
            border_width=1,
            border_color=self.BORDER,
        )
        frame.pack(fill="both", expand=True, padx=18, pady=18)

        ctk.CTkLabel(
            frame,
            text="Descarcă model",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=self.TEXT,
        ).pack(anchor="w", padx=18, pady=(16, 4))

        ctk.CTkLabel(
            frame,
            text="Scrie numele modelului exact, așa cum apare pe ollama.com:",
            font=ctk.CTkFont(size=12),
            text_color=self.MUTED,
        ).pack(anchor="w", padx=18)

        self.model_var = tk.StringVar()
        self.model_entry = ctk.CTkEntry(
            frame,
            textvariable=self.model_var,
            width=480,
            height=34,
            placeholder_text="ex: qwen3:8b",
            fg_color="#0b1220",
            border_color=self.BORDER,
            text_color=self.TEXT,
        )
        self.model_entry.pack(anchor="w", padx=18, pady=(8, 4))

        ctk.CTkLabel(
            frame,
            text="Poți găsi modelele pe ollama.com/search",
            font=ctk.CTkFont(size=11),
            text_color="#64748b",
        ).pack(anchor="w", padx=18)

        self.status_label = ctk.CTkLabel(
            frame,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=self.MUTED,
            wraplength=480,
            justify="left",
        )
        self.status_label.pack(anchor="w", padx=18, pady=(12, 0))

        self.progress_bar = ctk.CTkProgressBar(
            frame,
            width=480,
            mode="determinate",
            progress_color=self.ACCENT,
            fg_color="#1e293b",
        )
        self.progress_bar.pack(pady=(12, 4))
        self.progress_bar.set(0)

        self.progress_label = ctk.CTkLabel(
            frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=self.MUTED,
        )
        self.progress_label.pack(pady=(0, 6))

        buttons = ctk.CTkFrame(frame, fg_color="transparent")
        buttons.pack(anchor="e", padx=18, pady=(0, 16))

        self.inchide_button = ctk.CTkButton(
            buttons,
            text="Închide",
            width=90,
            fg_color=self.DARK_BG,
            hover_color=self.DARK_HOVER,
            command=self._inchide,
        )
        self.inchide_button.pack(side="left", padx=(0, 8))

        self.descarca_button = ctk.CTkButton(
            buttons,
            text="Descarcă",
            width=120,
            fg_color=self.ACCENT,
            hover_color=self.ACCENT_HOVER,
            command=self._descarca,
        )
        self.descarca_button.pack(side="left")

    def _descarca(self) -> None:
        if self.in_curs:
            return

        model = self.model_var.get().strip()
        if not model:
            self.status_label.configure(
                text="Scrie numele modelului pe care vrei să-l descărci.",
                text_color=self.WARNING,
            )
            return

        self.in_curs = True
        self.descarca_button.configure(state=tk.DISABLED)
        self.inchide_button.configure(state=tk.DISABLED)
        self.status_label.configure(text=f"Se descarcă modelul '{model}'...", text_color=self.MUTED)
        self.progress_bar.set(0)

        def angajament() -> None:
            def status(mesaj: str) -> None:
                self.dialog.after(0, lambda: self.status_label.configure(
                    text=mesaj, text_color=self.MUTED
                ))

            def progres(descarcat: int, total: int) -> None:
                if total > 0:
                    procent = int(descarcat * 100 / total)
                    if total >= 1024 * 1024:
                        eticheta = (
                            f"{descarcat // (1024 * 1024)} MB din "
                            f"{total // (1024 * 1024)} MB ({procent}%)"
                        )
                    else:
                        eticheta = (
                            f"{descarcat // 1024} KB din "
                            f"{total // 1024} KB ({procent}%)"
                        )
                else:
                    procent = 0
                    eticheta = f"{descarcat // 1024} KB descărcate"

                self.dialog.after(0, lambda: self._actualizeaza_progres(procent, eticheta))

            succes, mesaj = pull_model(model, on_progress=progres, on_status=status)
            self.dialog.after(0, lambda: self._finalizat(succes, mesaj, model))

        threading.Thread(target=angajament, daemon=True).start()

    def _actualizeaza_progres(self, procent: int, eticheta: str) -> None:
        try:
            self.progress_bar.set(max(0, min(procent, 100)) / 100)
            self.progress_label.configure(text=eticheta)
        except Exception:
            pass

    def _finalizat(self, succes: bool, mesaj: str | None, model: str) -> None:
        self.in_curs = False
        self.descarca_button.configure(state=tk.DISABLED)
        self.inchide_button.configure(state=tk.NORMAL)

        if succes:
            self.status_label.configure(
                text=f"Modelul '{model}' a fost descărcat cu succes.",
                text_color=self.SUCCESS,
            )
            self.progress_bar.set(1)
            logger.info("Model pulled successfully from the UI: %s", model)
        else:
            self.status_label.configure(
                text=str(mesaj) if mesaj else "Descărcarea modelului a eșuat.",
                text_color=self.ERROR,
            )
            logger.error("Model pull failed from the UI: %s", mesaj)

        if self.on_finished:
            self.on_finished(succes)

    def _inchide(self) -> None:
        try:
            if self.dialog.winfo_exists():
                self.dialog.destroy()
        except Exception:
            pass


def deschide_dialog_descarcare(parent: ctk.CTkToplevel, on_finished=None) -> PullModelDialog:
    """Deschide dialogul de descărcare a unui model."""
    return PullModelDialog(parent, on_finished=on_finished)
