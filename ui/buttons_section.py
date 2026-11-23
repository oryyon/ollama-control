import customtkinter as ctk


def build_buttons_section(main_frame) -> dict:
    """Construiește butoanele principale și zona de notificări."""
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

    return {
        "buttons_frame": buttons_frame,
        "notification_frame": notification_frame,
        "notification_label": notification_label,
    }
