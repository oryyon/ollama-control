import customtkinter as ctk


def build_buttons_section(main_frame) -> dict:
    """Construiește butoanele principale, notificările și bara de loading."""
    buttons_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
    buttons_frame.pack(pady=(14, 6))

    notification_frame = ctk.CTkFrame(
        main_frame,
        fg_color="#111827",
        corner_radius=12,
        border_width=1,
        border_color="#1f293b"
    )
    notification_frame.pack(padx=24, pady=(2, 10), fill="x")

    notification_label = ctk.CTkLabel(
        notification_frame,
        text="",
        font=ctk.CTkFont(size=11, weight="bold"),
        text_color="#93c5fd"
    )
    notification_label.pack(anchor="w", padx=12, pady=7)

    loading_model_frame = ctk.CTkFrame(
        main_frame,
        fg_color="#0f172a",
        corner_radius=12,
        border_width=1,
        border_color="#1e293b"
    )
    loading_model_frame.pack(padx=24, pady=(0, 10), fill="x")
    loading_model_frame.pack_forget()

    loading_model_label = ctk.CTkLabel(
        loading_model_frame,
        text="Se încarcă modelul...",
        font=ctk.CTkFont(size=12, weight="bold"),
        text_color="#93c5fd"
    )
    loading_model_label.pack(anchor="w", padx=12, pady=(8, 4))

    loading_model_bar = ctk.CTkProgressBar(
        loading_model_frame,
        width=400,
        mode="indeterminate"
    )
    loading_model_bar.pack(anchor="w", padx=12, pady=(0, 8))

    return {
        "buttons_frame": buttons_frame,
        "notification_frame": notification_frame,
        "notification_label": notification_label,
        "loading_model_frame": loading_model_frame,
        "loading_model_bar": loading_model_bar,
    }
