import threading

try:
    from plyer import notification  # type: ignore
    PLYER_AVAILABLE = True
except ImportError:
    PLYER_AVAILABLE = False

notification_after_id: int | None = None


def _widget_exists(widget) -> bool:
    try:
        return widget is not None and bool(widget.winfo_exists())
    except Exception:
        return False


def notificare_desktop(titlu: str, mesaj: str) -> None:
    """Afișează notificare desktop nativă dacă plyer e disponibil."""
    if PLYER_AVAILABLE:
        try:
            notification.notify(
                title=titlu,
                message=mesaj,
                timeout=3,
                app_name="Ollama Control"
            )
        except Exception:
            pass


def arata_notificare(text: str, tip: str = "info", app=None, notification_frame=None, notification_label=None) -> None:
    global notification_after_id

    if not _widget_exists(app) or not _widget_exists(notification_frame) or not _widget_exists(notification_label):
        notification_after_id = None
        return

    stiluri: dict[str, dict[str, str]] = {
        "success": {"fg": "#0f2f22", "border": "#1f7a4d", "text": "#86efac"},
        "warning": {"fg": "#332008", "border": "#a16207", "text": "#fcd34d"},
        "error": {"fg": "#341212", "border": "#b91c1c", "text": "#fca5a5"},
        "info": {"fg": "#10243f", "border": "#2563eb", "text": "#93c5fd"},
    }
    stil = stiluri.get(tip, stiluri["info"])

    if notification_after_id is not None:
        try:
            app.after_cancel(notification_after_id)
        except Exception:
            pass

    notification_frame.configure(fg_color=stil["fg"], border_color=stil["border"])
    notification_label.configure(text=text, text_color=stil["text"])
    notification_after_id = app.after(3200, lambda: ascunde_notificare(app, notification_frame, notification_label))


def ascunde_notificare(app, notification_frame, notification_label) -> None:
    global notification_after_id
    if not _widget_exists(notification_frame) or not _widget_exists(notification_label):
        notification_after_id = None
        return
    notification_frame.configure(fg_color="#111827", border_color="#1f2937")
    notification_label.configure(text="")
    notification_after_id = None
