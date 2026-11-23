import customtkinter as ctk


def build_meta_section(main_frame, ui_model_icon, ui_version_icon, ui_copy_icon=None) -> dict:
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

    # Numele modelului activ și butonul de copiere stau alături.
    model_box = ctk.CTkFrame(meta_frame, fg_color="transparent")
    model_box.grid(row=1, column=0, sticky="w", padx=(18, 24), pady=(2, 0))

    model_label = ctk.CTkLabel(
        model_box,
        text="Se verifică...",
        font=ctk.CTkFont(size=13, weight="bold"),
        text_color="#c4b5fd"
    )
    model_label.pack(side="left", padx=(0, 8))

    # Buton mic cu iconița de copiere, pentru numele modelului activ.
    copy_button = ctk.CTkButton(
        model_box,
        text="",
        image=ui_copy_icon,
        width=24,
        height=24,
        corner_radius=6,
        fg_color="transparent",
        hover_color="#1e293b",
        border_width=0,
        command=lambda: None,
    )
    copy_button.pack(side="left")

    resurse_label = ctk.CTkLabel(
        meta_frame,
        text="—",
        font=ctk.CTkFont(size=12),
        text_color="#94a3b8"
    )
    resurse_label.grid(row=1, column=2, sticky="w", padx=(0, 18), pady=(2, 0))

    # Versiunea și butonul de actualizare stau alături, într-un container.
    version_box = ctk.CTkFrame(meta_frame, fg_color="transparent")
    version_box.grid(row=1, column=1, sticky="w", padx=(0, 30), pady=(2, 0))

    version_label = ctk.CTkLabel(
        version_box,
        text="Se verifică versiunea...",
        font=ctk.CTkFont(size=12),
        text_color="#94a3b8"
    )
    version_label.pack(side="left", padx=(0, 12))

    # Butonul de actualizare apare doar când există o versiune nouă.
    update_button = ctk.CTkButton(
        version_box,
        text="⬆ Actualizează",
        width=110,
        height=26,
        fg_color="#b45309",
        hover_color="#92400e",
        font=ctk.CTkFont(size=11, weight="bold"),
        command=lambda: None,
    )
    update_button.pack(side="left")
    update_button.pack_forget()

    return {
        "meta_frame": meta_frame,
        "model_label": model_label,
        "version_label": version_label,
        "resurse_label": resurse_label,
        "update_button": update_button,
        "copy_button": copy_button,
    }
