import tkinter as tk
import customtkinter as ctk
import queue
import threading

from core.ollama_models import ModelEntry, get_ollama_models
from services.ollama_info import normalize_model_name
from ui.context_menu import ataseaza_meniu_contextual
from utils.logging_config import logger


class ModelList:
    """Gestionarea listei de modele cu scroll, căutare și filtrare."""

    INDICATOR_COLUMN_WIDTH = 62
    NAME_COLUMN_WIDTH = 220
    SIZE_COLUMN_WIDTH = 90
    PARAMS_COLUMN_WIDTH = 70
    ACTIVE_ROW_FG = ("#dcfce7", "#163126")
    ACTIVE_ROW_BORDER = ("#22c55e", "#22c55e")
    ACTIVE_ROW_TEXT = ("#166534", "#ecfdf5")
    ACTIVE_ROW_INDICATOR_TEXT = ("#16a34a", "#4ade80")
    DEFAULT_ROW_FG = ("gray86", "gray17")
    DELETE_BUTTON_FG = ("#ef4444", "#dc2626")
    DELETE_BUTTON_HOVER = ("#dc2626", "#b91c1c")
    CONFIG_BUTTON_FG = ("#60a5fa", "#2563eb")
    CONFIG_BUTTON_HOVER = ("#3b82f6", "#1d4ed8")
    SELECT_BUTTON_FG = ("#3b82f6", "#2563eb")
    SELECT_BUTTON_HOVER = ("#2563eb", "#1d4ed8")
    SMALL_BUTTON_TEXT = ("#ffffff", "#ffffff")
    ACTION_BUTTON_DISABLED_FG = ("#cbd5e1", "#334155")
    ACTION_BUTTON_DISABLED_TEXT = ("#64748b", "#94a3b8")
    SEARCH_ENTRY_FG = ("#f8fafc", "#1f2937")
    SEARCH_ENTRY_BORDER = ("#94a3b8", "#475569")
    SEARCH_ENTRY_TEXT = ("#0f172a", "#f8fafc")
    SEARCH_ENTRY_PLACEHOLDER = ("#64748b", "#94a3b8")
    NAME_DISPLAY_MAX_CHARS = 34

    @staticmethod
    def _remember_button_style(button: ctk.CTkButton, fg_color, hover_color) -> None:
        # `CTkButton` nu declară aceste atribute, deci le setăm dinamic.
        # `setattr` evită și eroarea de tipizare a analizatorului static.
        setattr(button, "_enabled_fg_color", fg_color)
        setattr(button, "_enabled_hover_color", hover_color)

    def __init__(self, parent: ctk.CTkBaseClass | ctk.CTkToplevel, on_select=None, on_config=None, on_delete=None) -> None:
        self.parent = parent
        self.all_models: list[ModelEntry] = []
        self.on_select = on_select
        self.on_config = on_config
        self.on_delete = on_delete
        self.active_model_name = ""

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._on_search_change)

        self._build_search()
        self._build_header()
        self._build_list()

    def _build_search(self) -> None:
        search_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        search_frame.pack(fill="x", padx=20, pady=(0, 5))

        self.search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="Caută model...",
            textvariable=self.search_var,
            width=400,
            height=32,
            fg_color=self.SEARCH_ENTRY_FG,
            border_color=self.SEARCH_ENTRY_BORDER,
            text_color=self.SEARCH_ENTRY_TEXT,
            placeholder_text_color=self.SEARCH_ENTRY_PLACEHOLDER,
        )
        self.search_entry.pack(side="left", fill="x", expand=True)
        ataseaza_meniu_contextual(self.search_entry)

    def _build_header(self) -> None:
        header_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=(5, 0))
        header_frame.grid_columnconfigure(0, minsize=self.INDICATOR_COLUMN_WIDTH)
        header_frame.grid_columnconfigure(1, minsize=self.NAME_COLUMN_WIDTH)
        header_frame.grid_columnconfigure(2, minsize=self.SIZE_COLUMN_WIDTH)
        header_frame.grid_columnconfigure(3, minsize=self.PARAMS_COLUMN_WIDTH)

        ctk.CTkLabel(
            header_frame, text="Stare",
            font=ctk.CTkFont(size=11, weight="bold"),
            width=self.INDICATOR_COLUMN_WIDTH, anchor="w"
        ).grid(row=0, column=0, padx=(10, 4), sticky="w")

        ctk.CTkLabel(
            header_frame, text="Model",
            font=ctk.CTkFont(size=11, weight="bold"),
            width=self.NAME_COLUMN_WIDTH, anchor="w"
        ).grid(row=0, column=1, padx=(10, 0), sticky="w")

        ctk.CTkLabel(
            header_frame, text="Dimensiune",
            font=ctk.CTkFont(size=11, weight="bold"),
            width=self.SIZE_COLUMN_WIDTH, anchor="e"
        ).grid(row=0, column=2, padx=(0, 10), sticky="e")

        ctk.CTkLabel(
            header_frame, text="Parametri",
            font=ctk.CTkFont(size=11, weight="bold"),
            width=self.PARAMS_COLUMN_WIDTH, anchor="e"
        ).grid(row=0, column=3, padx=(0, 10), sticky="e")

    def _build_list(self) -> None:
        self.list_frame = ctk.CTkScrollableFrame(self.parent, width=700, height=340)
        self.list_frame.pack(pady=5, padx=10, fill="both", expand=True)
        self._bind_scroll()

    def _bind_scroll(self) -> None:
        canvas = self.list_frame._parent_canvas

        def on_mousewheel(event: tk.Event) -> str:
            if event.num == 4 or event.delta > 0:
                canvas.yview_scroll(-3, "units")
            elif event.num == 5 or event.delta < 0:
                canvas.yview_scroll(3, "units")
            return "break"

        def on_enter(_event: tk.Event) -> None:
            canvas.bind_all("<Button-4>", on_mousewheel)
            canvas.bind_all("<Button-5>", on_mousewheel)
            canvas.bind_all("<MouseWheel>", on_mousewheel)

        def on_leave(_event: tk.Event) -> None:
            canvas.unbind_all("<Button-4>")
            canvas.unbind_all("<Button-5>")
            canvas.unbind_all("<MouseWheel>")

        canvas.bind("<Enter>", on_enter)
        canvas.bind("<Leave>", on_leave)

    def _update_scrollregion(self) -> None:
        """Force the scrollable region to match the actual content and reset scroll position."""
        if not self.list_frame.winfo_exists():
            return
        canvas = self.list_frame._parent_canvas
        # Allow pending layout operations to complete
        self.parent.update_idletasks()

        # Get canvas dimensions
        canvas_width = canvas.winfo_width()
        canvas_height = canvas.winfo_height()

        # Get content bounding box
        bbox = canvas.bbox("all")
        if bbox is None:
            # No content, set scrollregion to canvas size so scrolling is disabled
            canvas.configure(scrollregion=(0, 0, canvas_width, canvas_height))
            canvas.yview_moveto(0)
            return

        content_width = bbox[2] - bbox[0]
        content_height = bbox[3] - bbox[1]

        # If content fits vertically, clamp scrollregion to canvas height
        # so yview = (0.0, 1.0) and scrolling is effectively disabled
        if content_height <= canvas_height:
            canvas.configure(scrollregion=(0, 0, max(content_width, canvas_width), canvas_height))
        else:
            canvas.configure(scrollregion=bbox)

        # Reset scroll to the top so no empty space appears above the first item
        canvas.yview_moveto(0)

    def clear(self) -> None:
        if not self.list_frame.winfo_exists():
            return
        for w in self.list_frame.winfo_children():
            w.destroy()

    def set_active_model(self, model_name: str | None) -> None:
        normalized_name = normalize_model_name((model_name or "").strip())
        if self.active_model_name == normalized_name:
            return
        self.active_model_name = normalized_name
        self._apply_filter()

    def _on_search_change(self, *args: str) -> None:
        self._apply_filter()

    def _apply_filter(self) -> None:
        query = self.search_var.get().strip().lower()
        self.clear()

        if not self.all_models:
            self.add_empty("Niciun model disponibil")
            self._update_scrollregion()
            return

        filtered = [m for m in self.all_models if query in m["name"].lower()]

        if not filtered:
            self.add_empty("Niciun model găsit")
            self._update_scrollregion()
            return

        for m in filtered:
            self.add_row(
                m["name"],
                m["size"],
                m["params"],
                self.on_select,
                self.on_config,
                self.on_delete,
                is_active=normalize_model_name(m["name"]) == self.active_model_name,
            )

        self._update_scrollregion()

    def add_empty(self, text: str) -> None:
        frame = ctk.CTkFrame(self.list_frame, fg_color="transparent")
        frame.pack(fill="x", pady=20)
        ctk.CTkLabel(frame, text=text, font=ctk.CTkFont(size=13)).pack()

    def _format_model_name(self, name: str) -> str:
        if len(name) <= self.NAME_DISPLAY_MAX_CHARS:
            return name
        return f"{name[:self.NAME_DISPLAY_MAX_CHARS - 1]}…"

    def add_row(self, name: str, size: str, params: str, command=None, config_command=None, delete_command=None, is_active: bool = False) -> None:
        frame_kwargs = {
            "fg_color": self.ACTIVE_ROW_FG if is_active else self.DEFAULT_ROW_FG,
            "border_width": 1 if is_active else 0,
        }
        if is_active:
            frame_kwargs["border_color"] = self.ACTIVE_ROW_BORDER

        frame = ctk.CTkFrame(self.list_frame, **frame_kwargs)
        frame.pack(fill="x", pady=3, padx=5)
        frame.grid_columnconfigure(0, minsize=self.INDICATOR_COLUMN_WIDTH)
        frame.grid_columnconfigure(1, minsize=self.NAME_COLUMN_WIDTH)
        frame.grid_columnconfigure(2, minsize=self.SIZE_COLUMN_WIDTH)
        frame.grid_columnconfigure(3, minsize=self.PARAMS_COLUMN_WIDTH)
        frame.grid_columnconfigure(4, weight=1)

        active_text_color = self.ACTIVE_ROW_TEXT if is_active else None

        ctk.CTkLabel(
            frame,
            text="● Activ" if is_active else "",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=self.ACTIVE_ROW_INDICATOR_TEXT if is_active else None,
            width=self.INDICATOR_COLUMN_WIDTH,
            anchor="w",
            fg_color="transparent"
        ).grid(row=0, column=0, padx=(10, 4), sticky="w")

        ctk.CTkLabel(
            frame, text=self._format_model_name(name),
            font=ctk.CTkFont(size=12),
            width=self.NAME_COLUMN_WIDTH, anchor="w",
            fg_color="transparent",
            text_color=active_text_color,
        ).grid(row=0, column=1, padx=(0, 0), sticky="w")

        ctk.CTkLabel(
            frame, text=size,
            font=ctk.CTkFont(size=12),
            width=self.SIZE_COLUMN_WIDTH, anchor="e",
            fg_color="transparent",
            text_color=active_text_color,
        ).grid(row=0, column=2, padx=(0, 10), sticky="e")

        ctk.CTkLabel(
            frame, text=params,
            font=ctk.CTkFont(size=12, weight="bold"),
            width=self.PARAMS_COLUMN_WIDTH, anchor="e",
            fg_color="transparent",
            text_color=active_text_color,
        ).grid(row=0, column=3, padx=(0, 10), sticky="e")

        buttons_frame = ctk.CTkFrame(frame, fg_color="transparent")
        buttons_frame.grid(row=0, column=4, padx=10, sticky="e")

        if delete_command:
            delete_button = ctk.CTkButton(
                buttons_frame, text="🗑️", width=36,
                fg_color=self.DELETE_BUTTON_FG,
                hover_color=self.DELETE_BUTTON_HOVER,
                text_color=self.SMALL_BUTTON_TEXT,
                text_color_disabled=self.ACTION_BUTTON_DISABLED_TEXT,
                command=lambda: delete_command(name)
            )
            self._remember_button_style(delete_button, self.DELETE_BUTTON_FG, self.DELETE_BUTTON_HOVER)
            delete_button.pack(side="left", padx=(0, 6))

        if config_command:
            config_button = ctk.CTkButton(
                buttons_frame, text="⚙️", width=36,
                fg_color=self.CONFIG_BUTTON_FG,
                hover_color=self.CONFIG_BUTTON_HOVER,
                text_color=self.SMALL_BUTTON_TEXT,
                text_color_disabled=self.ACTION_BUTTON_DISABLED_TEXT,
                command=lambda: config_command(name)
            )
            self._remember_button_style(config_button, self.CONFIG_BUTTON_FG, self.CONFIG_BUTTON_HOVER)
            config_button.pack(side="left", padx=(0, 6))

        if command:
            select_button = ctk.CTkButton(
                buttons_frame,
                text="Select",
                width=88,
                fg_color=self.SELECT_BUTTON_FG,
                hover_color=self.SELECT_BUTTON_HOVER,
                text_color=self.SMALL_BUTTON_TEXT,
                text_color_disabled=self.ACTION_BUTTON_DISABLED_TEXT,
                command=lambda: command(name)
            )
            self._remember_button_style(select_button, self.SELECT_BUTTON_FG, self.SELECT_BUTTON_HOVER)
            select_button.pack(side="left")

    def show_loading(self, text: str = "Se încarcă modelele...") -> None:
        self.clear()
        frame = ctk.CTkFrame(self.list_frame, fg_color="transparent")
        frame.pack(fill="x", pady=40)

        self._loading_label = ctk.CTkLabel(
            frame, text=text,
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self._loading_label.pack(pady=(0, 10))

        self._loading_bar = ctk.CTkProgressBar(
            frame, width=300, mode="indeterminate"
        )
        self._loading_bar.pack()
        self._loading_bar.start()

    def hide_loading(self) -> None:
        if hasattr(self, "_loading_bar"):
            try:
                self._loading_bar.stop()
            except Exception:
                pass
        self.clear()
        self._update_scrollregion()

    def load_models(self, callback) -> None:
        """Încarcă lista de modele Ollama în fundal și o livrează prin callback."""
        self.show_loading("Se încarcă modelele Ollama...")
        result_queue: queue.Queue[tuple[list, bool]] = queue.Queue(maxsize=1)
        threading.Thread(
            target=self._load_ollama_thread,
            args=(result_queue,),
            daemon=True
        ).start()
        self.parent.after(50, lambda: self._poll_ollama_models(result_queue, callback))

    def _load_ollama_thread(self, result_queue: queue.Queue[tuple[list, bool]]) -> None:
        try:
            models, success = get_ollama_models()
        except Exception as e:
            logger.error(f"Eroare la încărcarea modelelor Ollama: {e}")
            models, success = [], False
        result_queue.put((models, success))

    def _poll_ollama_models(self, result_queue: queue.Queue[tuple[list, bool]], callback) -> None:
        try:
            if not self.parent.winfo_exists():
                return
            models, success = result_queue.get_nowait()
        except queue.Empty:
            self.parent.after(50, lambda: self._poll_ollama_models(result_queue, callback))
            return
        except Exception:
            logger.exception("Eroare la prelucrearea rezultatului modelelor Ollama")
            return

        callback(models, success)

    def on_models_loaded(self, models: list[ModelEntry], success: bool) -> None:
        if not self.list_frame.winfo_exists():
            return
        self.hide_loading()
        self.all_models = models

        if not success:
            self.add_empty("Serverul Ollama nu răspunde.\nPornește serviciul Ollama mai întâi.")
            self._update_scrollregion()
            return

        if not self.all_models:
            self.add_empty("Niciun model Ollama")
            self._update_scrollregion()
            return

        self._apply_filter()
