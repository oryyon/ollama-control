import threading
import tkinter as tk
import customtkinter as ctk

from services.ollama_update import check_for_update, perform_update
from utils.logging_config import logger


class OllamaUpdateDialog:
    """Dialog pentru verificarea și instalarea unei versiuni noi de Ollama."""

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
        self.dialog.title("Actualizare Ollama")
        self.dialog.geometry("560x430")
        self.dialog.resizable(False, False)
        self.dialog.configure(fg_color=self.DIALOG_BG)
        self.dialog.transient(parent)
        self.dialog.lift()
        self.dialog.focus_force()
        self._build_ui()
        self._verifica()

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
            text="Actualizare Ollama",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=self.TEXT,
        ).pack(anchor="w", padx=18, pady=(16, 4))

        self.verificare_label = ctk.CTkLabel(
            frame,
            text="Se verifică versiunile disponibile...",
            font=ctk.CTkFont(size=12),
            text_color=self.MUTED,
        )
        self.verificare_label.pack(anchor="w", padx=18)

        self.versiuni_frame = ctk.CTkFrame(frame, fg_color="transparent")
        self.versiuni_frame.pack(anchor="w", padx=18, pady=(14, 0))

        self.version_instalata_label = ctk.CTkLabel(
            self.versiuni_frame,
            text="Versiune instalată: —",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=self.TEXT,
        )
        self.version_instalata_label.pack(anchor="w")

        self.version_latest_label = ctk.CTkLabel(
            self.versiuni_frame,
            text="Ultima versiune: —",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=self.TEXT,
        )
        self.version_latest_label.pack(anchor="w", pady=(4, 0))

        self.status_label = ctk.CTkLabel(
            frame,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=self.MUTED,
            wraplength=500,
            justify="left",
        )
        self.status_label.pack(anchor="w", padx=18, pady=(14, 0))

        self.progress_bar = ctk.CTkProgressBar(
            frame,
            width=500,
            mode="determinate",
            progress_color=self.ACCENT,
            fg_color="#1e293b",
        )
        self.progress_bar.pack(pady=(14, 4))
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

        self.actualizeaza_button = ctk.CTkButton(
            buttons,
            text="Actualizează acum",
            width=150,
            fg_color=self.ACCENT,
            hover_color=self.ACCENT_HOVER,
            command=self._actualizeaza,
            state=tk.DISABLED,
        )
        self.actualizeaza_button.pack(side="left")

    def _verifica(self) -> None:
        """Verifică versiunile în fundal."""
        def angajament() -> None:
            info = check_for_update()
            self.dialog.after(0, lambda: self._afiseaza_info(info))

        threading.Thread(target=angajament, daemon=True).start()

    def _afiseaza_info(self, info) -> None:
        instalata = info.get("installed") or "necunoscută"
        latest = info.get("latest") or "necunoscută"

        self.verificare_label.configure(
            text="Versiunile disponibile au fost verificate.",
            text_color=self.MUTED,
        )
        self.version_instalata_label.configure(text=f"Versiune instalată: {instalata}")
        self.version_latest_label.configure(text=f"Ultima versiune: {latest}")

        if info.get("error"):
            self.status_label.configure(text=str(info["error"]), text_color=self.WARNING)
            return

        if info.get("update_available"):
            self.status_label.configure(
                text=(
                    f"Ollama {latest} este disponibilă. Actualizarea descarcă arhiva "
                    "oficială (circa 1,5 GB) și o instală cu privilegii de administrator."
                ),
                text_color=self.WARNING,
            )
            self.actualizeaza_button.configure(state=tk.NORMAL)
        else:
            self.status_label.configure(
                text="Ollama este deja la cea mai recentă versiune.",
                text_color=self.SUCCESS,
            )

    def _actualizeaza(self) -> None:
        if self.in_curs:
            return

        self.in_curs = True
        self.actualizeaza_button.configure(state=tk.DISABLED)
        self.inchide_button.configure(state=tk.DISABLED)
        self.status_label.configure(text="Se începe actualizarea...", text_color=self.MUTED)

        def angajament() -> None:
            def status(mesaj: str) -> None:
                self.dialog.after(0, lambda: self.status_label.configure(
                    text=mesaj, text_color=self.MUTED
                ))

            def progres(descarcat: int, total: int) -> None:
                if total > 0:
                    procent = int(descarcat * 100 / total)
                    eticheta = (
                        f"{descarcat // (1024 * 1024)} MB din "
                        f"{total // (1024 * 1024)} MB ({procent}%)"
                    )
                else:
                    procent = 0
                    eticheta = f"{descarcat // (1024 * 1024)} MB descărcate"

                self.dialog.after(0, lambda: self._actualizeaza_progres(procent, eticheta))

            succes, mesaj = perform_update(on_progress=progres, on_status=status)
            self.dialog.after(0, lambda: self._finalizat(succes, mesaj))

        threading.Thread(target=angajament, daemon=True).start()

    def _actualizeaza_progres(self, procent: int, eticheta: str) -> None:
        try:
            self.progress_bar.set(max(0, min(procent, 100)) / 100)
            self.progress_label.configure(text=eticheta)
        except Exception:
            pass

    def _finalizat(self, succes: bool, mesaj: str | None) -> None:
        self.in_curs = False
        self.actualizeaza_button.configure(state=tk.DISABLED)
        self.inchide_button.configure(state=tk.NORMAL)

        if succes:
            self.status_label.configure(
                text="Ollama a fost actualizată cu succes.",
                text_color=self.SUCCESS,
            )
            self.progress_bar.set(1)
            logger.info("Ollama update completed successfully")
        else:
            self.status_label.configure(
                text=str(mesaj) if mesaj else "Actualizarea Ollama a eșuat.",
                text_color=self.ERROR,
            )
            logger.error("Ollama update failed: %s", mesaj)

        if self.on_finished:
            self.on_finished(succes)

    def _inchide(self) -> None:
        try:
            if self.dialog.winfo_exists():
                self.dialog.destroy()
        except Exception:
            pass


def deschide_dialog_actualizare(parent: ctk.CTkToplevel, on_finished=None) -> OllamaUpdateDialog:
    """Deschide dialogul de actualizare Ollama."""
    return OllamaUpdateDialog(parent, on_finished=on_finished)
