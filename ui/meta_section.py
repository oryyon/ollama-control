import customtkinter as ctk


def build_meta_section(main_frame, ui_model_icon, ui_version_icon) -> dict:
    """Construiește secțiunea meta (model activ, versiune, resurse, butoane model)."""
    meta_frame = ctk.CTkFrame(
        main_frame,
        fg_color="#0d1526",
        corner_radius=18,
        border_width=1,
        border_color="#1e293b"
    )
    meta_frame.pack(padx=24, pady=(10, 0), fill="x")
    meta_frame.grid_columnconfigure(0, weight=1)
    meta_frame.grid_columnconfigure(1, weight=1)
    meta_frame.grid_columnconfigure(2, weight=1)

    model_title = ctk.CTkLabel(
        meta_frame,
        text="  MODEL ACTIV",
        image=ui_model_icon,
        compound="left",
        font=ctk.CTkFont(size=10, weight="bold"),
        text_color="#64748b"
    )
    model_title.grid(row=0, column=0, sticky="w", padx=(18, 24), pady=(14, 0))

    version_title = ctk.CTkLabel(
        meta_frame,
        text="  VERSIUNE OLLAMA",
        image=ui_version_icon,
        compound="left",
        font=ctk.CTkFont(size=10, weight="bold"),
        text_color="#64748b"
    )
    version_title.grid(row=0, column=1, sticky="w", padx=(0, 30), pady=(14, 0))

    resurse_title = ctk.CTkLabel(
        meta_frame,
        text="  RESURSE",
        font=ctk.CTkFont(size=10, weight="bold"),
        text_color="#64748b"
    )
    resurse_title.grid(row=0, column=2, sticky="w", padx=(0, 18), pady=(14, 0))

    model_label = ctk.CTkLabel(
        meta_frame,
        text="Se verifică...",
        font=ctk.CTkFont(size=13, weight="bold"),
        text_color="#c4b5fd"
    )
    model_label.grid(row=1, column=0, sticky="w", padx=(18, 24), pady=(2, 0))

    resurse_label = ctk.CTkLabel(
        meta_frame,
        text="—",
        font=ctk.CTkFont(size=12),
        text_color="#94a3b8"
    )
    resurse_label.grid(row=1, column=2, sticky="w", padx=(0, 18), pady=(2, 0))

    version_label = ctk.CTkLabel(
        meta_frame,
        text="Se verifică versiunea...",
        font=ctk.CTkFont(size=12),
        text_color="#94a3b8"
    )
    version_label.grid(row=1, column=1, sticky="w", padx=(0, 30), pady=(2, 0))

    return {
        "meta_frame": meta_frame,
        "model_label": model_label,
        "version_label": version_label,
        "resurse_label": resurse_label,
    }
