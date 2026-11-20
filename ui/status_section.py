import customtkinter as ctk


def build_status_section(main_frame, ui_uptime_icon, ui_status_icon) -> dict:
    """Construiește secțiunea de status (stare serviciu, uptime, badge)."""
    status_frame = ctk.CTkFrame(
        main_frame,
        fg_color="#0b1220",
        corner_radius=22,
        border_width=1,
        border_color="#1e293b"
    )
    status_frame.pack(pady=5, padx=24, fill="x")
    status_frame.grid_columnconfigure(1, weight=1)

    status_dot = ctk.CTkLabel(
        status_frame,
        text="●",
        font=ctk.CTkFont(size=22, weight="bold")
    )
    status_dot.grid(row=0, column=0, sticky="w", padx=(18, 0), pady=(14, 6))

    status_label = ctk.CTkLabel(
        status_frame,
        text="Se verifică starea...",
        font=ctk.CTkFont(size=21, weight="bold"),
        text_color="#f8fafc"
    )
    status_label.grid(row=0, column=1, sticky="w", padx=(10, 10), pady=(14, 6))

    status_badge = ctk.CTkLabel(
        status_frame,
        text="CHECKING",
        corner_radius=999,
        fg_color="#1f2937",
        text_color="#cbd5e1",
        font=ctk.CTkFont(size=11, weight="bold"),
        padx=12,
        pady=4
    )
    status_badge.grid(row=0, column=2, sticky="e", padx=(10, 18), pady=(14, 6))

    subtitle_label = ctk.CTkLabel(
        status_frame,
        text="Așteaptă răspunsul sistemului",
        font=ctk.CTkFont(size=12),
        text_color="#9fb0c7"
    )
    subtitle_label.grid(row=1, column=0, columnspan=3, sticky="w", padx=20)

    detail_uptime_title = ctk.CTkLabel(
        status_frame,
        text=" UPTIME",
        image=ui_uptime_icon,
        compound="left",
        font=ctk.CTkFont(size=10, weight="bold"),
        text_color="#64748b"
    )
    detail_uptime_title.grid(row=2, column=0, sticky="w", padx=(18, 24), pady=(12, 0))

    uptime_value_label = ctk.CTkLabel(
        status_frame,
        text="Uptime indisponibil",
        font=ctk.CTkFont(size=13, weight="bold"),
        text_color="#93c5fd"
    )
    uptime_value_label.grid(row=3, column=0, sticky="w", padx=(18, 24), pady=(1, 14))

    detail_state_title = ctk.CTkLabel(
        status_frame,
        text=" STATUS",
        image=ui_status_icon,
        compound="left",
        font=ctk.CTkFont(size=10, weight="bold"),
        text_color="#64748b"
    )
    detail_state_title.grid(row=2, column=1, columnspan=2, sticky="w", pady=(12, 0))

    detail_state_value = ctk.CTkLabel(
        status_frame,
        text="Checking · Pending",
        font=ctk.CTkFont(size=13, weight="bold"),
        text_color="#cbd5e1"
    )
    detail_state_value.grid(row=3, column=1, columnspan=2, sticky="w", pady=(1, 14))

    return {
        "status_dot": status_dot,
        "status_badge": status_badge,
        "status_label": status_label,
        "subtitle_label": subtitle_label,
        "uptime_value_label": uptime_value_label,
        "detail_state_value": detail_state_value,
    }
