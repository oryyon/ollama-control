import subprocess
import threading
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from pathlib import Path

from services.ollama_paths import (cleanup_duplicate_manifests,
                                   find_duplicate_manifests,
                                   get_models_directory_info)
from utils.logging_config import logger


class ModelPathDialog:
    """Dialog care arată calea unde sunt descărcate modelele Ollama.

    Calea se detectează din starea reală a serverului (vezi
    `services.ollama_paths`), fiindcă Ollama poate folosi mai multe
    locații, iar unele pot exista fără să conțină modele.

    De aici se poate și curăța duplicaturile de manifest: Ollama scrie
    modelele noi în două formate, iar copiile din formatul vechi sunt
    redundante.
    """

    def __init__(self, parent: ctk.CTkToplevel) -> None:
        self.parent = parent
        self.info = get_models_directory_info()
        self.cale = str(self.info["path"])
        self.duplicate = find_duplicate_manifests(Path(self.cale))
        self.in_curatare = False

        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title("Calea modelelor Ollama")
        self.dialog.geometry("560x400")
        self.dialog.resizable(False, False)
        self.dialog.configure(fg_color="#0f172a")
        self.dialog.transient(parent)
        self.dialog.lift()
        self.dialog.focus_force()
        self._build_ui()
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

        ctk.CTkLabel(
            frame,
            text="Modelele sunt descărcate în:",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#cbd5e1",
        ).pack(anchor="w", padx=18, pady=(16, 6))

        cale_entry = ctk.CTkEntry(
            frame,
            textvariable=tk.StringVar(value=self.cale),
            width=500,
            fg_color="#0b1220",
            border_color="#334155",
            text_color="#f1f5f9",
        )
        cale_entry.pack(anchor="w", padx=18, pady=(0, 10))
        cale_entry.configure(state="readonly")
        cale_entry.select_range(0, tk.END)

        exista = bool(self.info["exists"])
        numar_modele = int(self.info["model_count"])

        detalii = (
            f"Directorul există și conține {numar_modele} "
            f"model{'e' if numar_modele == 1 else 'e'} instalate."
            if exista else
            "Directorul nu există încă. Va fi creat la prima descărcare."
        )

        ctk.CTkLabel(
            frame,
            text=detalii,
            font=ctk.CTkFont(size=12),
            text_color="#86efac" if exista else "#fcd34d",
        ).pack(anchor="w", padx=18, pady=(0, 4))

        ctk.CTkLabel(
            frame,
            text="Blobs (fișierele modelelor) sunt în subdirectorul „blobs”.",
            font=ctk.CTkFont(size=11),
            text_color="#64748b",
        ).pack(anchor="w", padx=18, pady=(0, 10))

        # Secțiunea de curățare a duplicaturilor de manifest.
        self.cleanup_frame = ctk.CTkFrame(
            frame,
            fg_color="#0b1220",
            corner_radius=12,
            border_width=1,
            border_color="#334155",
        )
        self.cleanup_frame.pack(anchor="w", padx=18, pady=(0, 12), fill="x")

        numar_duplicate = len(self.duplicate)
        if numar_duplicate:
            titlu = f"{numar_duplicate} model{'e' if numar_duplicate == 1 else 'e'} există în ambele formate"
            ctk.CTkLabel(
                self.cleanup_frame,
                text=titlu,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="#fcd34d",
            ).pack(anchor="w", padx=12, pady=(8, 2))

            ctk.CTkLabel(
                self.cleanup_frame,
                text=(
                    "Ollama scrie modelele noi de două ori: în formatul nou "
                    "(manifests-v2) și într-un înveliș pentru clienții vechi. "
                    "Copiile vechi pot fi eliminate fără să afecteze modelele."
                ),
                font=ctk.CTkFont(size=11),
                text_color="#94a3b8",
                wraplength=490,
                justify="left",
            ).pack(anchor="w", padx=12, pady=(0, 8))

            self.cleanup_button = ctk.CTkButton(
                self.cleanup_frame,
                text="Curăță duplicaturile",
                width=170,
                height=30,
                fg_color="#b45309",
                hover_color="#92400e",
                command=self._curata,
            )
            self.cleanup_button.pack(anchor="w", padx=12, pady=(0, 10))
        else:
            ctk.CTkLabel(
                self.cleanup_frame,
                text="Nu există duplicate de manifest în acest director.",
                font=ctk.CTkFont(size=12),
                text_color="#86efac",
            ).pack(anchor="w", padx=12, pady=(10, 10))
            self.cleanup_button = None

        buttons = ctk.CTkFrame(frame, fg_color="transparent")
        buttons.pack(anchor="e", padx=18, pady=(0, 16))

        ctk.CTkButton(
            buttons,
            text="Copiază calea",
            width=110,
            fg_color="#1f2937",
            hover_color="#334155",
            command=self._copiaza,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            buttons,
            text="Deschide folderul",
            width=130,
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            command=self._deschide,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            buttons,
            text="Închide",
            width=90,
            fg_color="#1f2937",
            hover_color="#334155",
            command=self._inchide,
        ).pack(side="left")

    def _copiaza(self) -> None:
        try:
            self.dialog.clipboard_clear()
            self.dialog.clipboard_append(self.cale)
            self.dialog.update()
            logger.info("Copied Ollama models path to clipboard: %s", self.cale)
            self._feedback("Calea a fost copiată în clipboard.")
        except Exception:
            logger.exception("Failed to copy the models path to the clipboard")
            self._feedback("Nu s-a putut copia calea în clipboard.")

    def _deschide(self) -> None:
        try:
            subprocess.Popen(["xdg-open", self.cale])
        except Exception:
            logger.exception("Failed to open the models directory")
            self._feedback("Nu s-a putut deschide folderul.")

    def _curata(self) -> None:
        """Elimină copiile redundante din formatul vechi de manifest."""
        if self.in_curatare:
            return

        numar = len(self.duplicate)
        if numar == 0:
            self._feedback("Nu există duplicate de eliminat.")
            return

        lista = ", ".join(f"{d['model']}:{d['tag']}" for d in self.duplicate)
        confirmat = messagebox.askyesno(
            "Curăță duplicaturile",
            f"Se vor elimina {numar} copii redundante:\n\n{lista}\n\n"
            "Modelele rămân instalate și funcționează normal. "
            "Se cer privilegii de administrator.",
        )
        if not confirmat:
            return

        self.in_curatare = True
        if self.cleanup_button is not None:
            self.cleanup_button.configure(state=tk.DISABLED)
        self._feedback("Se curăță duplicaturile...")

        def angajament() -> None:
            succes, mesaj = cleanup_duplicate_manifests(
                Path(self.cale),
                on_status=lambda text: self.dialog.after(
                    0, lambda: self._feedback(text)
                ),
            )
            self.dialog.after(0, lambda: self._finalizat_curatare(succes, mesaj))

        threading.Thread(target=angajament, daemon=True).start()

    def _finalizat_curatare(self, succes: bool, mesaj: str | None) -> None:
        self.in_curatare = False
        if self.cleanup_button is not None:
            self.cleanup_button.configure(state=tk.NORMAL if succes else tk.DISABLED)

        if succes:
            self.duplicate = find_duplicate_manifests(Path(self.cale))
            self._feedback(str(mesaj) if mesaj else "Duplicaturile au fost eliminate.")
        else:
            self._feedback(str(mesaj) if mesaj else "Curățarea a eșuat.")

    def _inchide(self) -> None:
        try:
            if self.dialog.winfo_exists():
                self.dialog.destroy()
        except Exception:
            pass

    def _feedback(self, mesaj: str) -> None:
        ctk.CTkLabel(
            self.dialog,
            text=mesaj,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#93c5fd",
        ).pack(pady=(0, 10))
