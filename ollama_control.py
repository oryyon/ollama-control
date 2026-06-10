#!/usr/bin/env python3
import tkinter as tk
import customtkinter as ctk
import subprocess
import threading
from datetime import datetime
from pathlib import Path
import sys

try:
    from PIL import Image
except ImportError:
    Image = None


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

AUTO_REFRESH_MS = 5000
notification_after_id = None
comanda_in_curs = False
versiune_ollama_cache = "Se verifică versiunea..."
model_activ_cache = "Se verifică..."
info_ollama_incarcare = False
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    BASE_DIR = Path(sys._MEIPASS)
else:
    BASE_DIR = Path(__file__).resolve().parent



def incarca_imagine_ctk(nume_fisier, size):
    cale = BASE_DIR / nume_fisier
    if Image is not None:
        imagine = Image.open(cale)
        return ctk.CTkImage(light_image=imagine, dark_image=imagine, size=size)
    return None



def seteaza_stare_butoane(activ):
    stare = "normal" if activ else "disabled"
    start_button.configure(state=stare)
    refresh_button.configure(state=stare)
    stop_button.configure(state=stare)



def finalizeaza_comanda(comanda, succes):
    global comanda_in_curs
    comanda_in_curs = False
    seteaza_stare_butoane(True)
    actualizeaza_stare()

    if succes:
        if comanda == "start":
            arata_notificare("Pornire Ollama reușită", "success")
        elif comanda == "stop":
            arata_notificare("Oprire Ollama reușită", "success")
        else:
            arata_notificare("Comandă executată", "success")
    else:
        arata_notificare("Operațiune anulată sau eșuată", "warning")



def executa_comanda_in_fundal(comanda):
    succes = False
    try:
        subprocess.run(["pkexec", "systemctl", comanda, "ollama"], check=True)
        succes = True
    except subprocess.CalledProcessError:
        succes = False
    finally:
        app.after(0, lambda: finalizeaza_comanda(comanda, succes))



def ruleaza_comanda(comanda):
    """Rulează o comandă de sistem cu drepturi de administrator fără să blocheze UI-ul."""
    global comanda_in_curs

    if comanda_in_curs:
        return

    comanda_in_curs = True
    seteaza_stare_butoane(False)
    arata_notificare("Se execută comanda...", "info")
    status_label.configure(text="Se execută comanda...", text_color="#f1c40f")
    subtitle_label.configure(text="Așteaptă confirmarea sistemului", text_color="#f1c40f")
    app.update_idletasks()

    threading.Thread(target=executa_comanda_in_fundal, args=(comanda,), daemon=True).start()


def ruleaza_si_citeste(comanda):
    rezultat = subprocess.run(
        comanda,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    return rezultat.stdout.strip()


def obtine_detalii_serviciu():
    """Returnează starea systemd și timestamp-ul ultimei activări."""
    try:
        active_state = ruleaza_si_citeste(["systemctl", "is-active", "ollama"]) or "necunoscut"
        sub_state = ruleaza_si_citeste(["systemctl", "show", "ollama", "--property=SubState", "--value"]) or "necunoscut"
        active_timestamp = ruleaza_si_citeste(["systemctl", "show", "ollama", "--property=ActiveEnterTimestamp", "--value"])
        return {
            "active_state": active_state,
            "sub_state": sub_state,
            "active_timestamp": active_timestamp,
        }
    except Exception:
        return {
            "active_state": "necunoscut",
            "sub_state": "necunoscut",
            "active_timestamp": "",
        }


def obtine_versiune_ollama():
    """Returnează versiunea clientului Ollama."""
    try:
        rezultat = subprocess.run(
            ["ollama", "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=3
        )
        output = (rezultat.stdout or "") + "\n" + (rezultat.stderr or "")
        for linie in output.splitlines():
            linie = linie.strip()
            if "version is" in linie.lower():
                return linie.replace("Warning: ", "").strip()
            if linie.lower().startswith("ollama version"):
                return linie.strip()
        return "Versiune Ollama indisponibilă"
    except subprocess.TimeoutExpired:
        return "Versiune Ollama indisponibilă"
    except Exception:
        return "Versiune Ollama indisponibilă"


def obtine_model_activ(active_state):
    """Încearcă să detecteze modelul activ din procesele Ollama."""
    if active_state != "active":
        return "Model activ: indisponibil"

    try:
        rezultat = subprocess.run(
            ["ps", "-eo", "args="],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=2
        )
        for linie in rezultat.stdout.splitlines():
            linie_curata = linie.strip()
            if "ollama runner" not in linie_curata:
                continue

            parti = linie_curata.split()
            for index, parte in enumerate(parti):
                if parte == "--model" and index + 1 < len(parti):
                    return f"Model activ: {parti[index + 1]}"
                if parte.startswith("--model="):
                    return f"Model activ: {parte.split('=', 1)[1]}"

            return "Model activ: runner detectat"

        return "Model activ: niciun model încărcat"
    except subprocess.TimeoutExpired:
        return "Model activ: indisponibil"
    except Exception:
        return "Model activ: indisponibil"


def scurteaza_versiune(text):
    if not text or "indisponibil" in text.lower() or "verifică" in text.lower():
        return text

    parti = text.split()
    for parte in parti:
        if parte and parte[0].isdigit():
            return f"Client {parte}"
    return text



def scurteaza_model(text):
    if not text or ":" not in text:
        return text

    prefix, valoare = text.split(":", 1)
    valoare = valoare.strip()
    if not valoare:
        return text
    return valoare



def actualizeaza_info_ollama_ui(versiune_text, model_text):
    global versiune_ollama_cache, model_activ_cache, info_ollama_incarcare
    versiune_ollama_cache = scurteaza_versiune(versiune_text)
    model_activ_cache = scurteaza_model(model_text)
    info_ollama_incarcare = False
    version_label.configure(text=versiune_ollama_cache)
    model_label.configure(text=model_activ_cache)



def incarca_info_ollama_in_fundal(active_state):
    versiune_text = obtine_versiune_ollama()
    model_text = obtine_model_activ(active_state)
    app.after(0, lambda: actualizeaza_info_ollama_ui(versiune_text, model_text))



def programeaza_actualizare_info_ollama(active_state):
    global info_ollama_incarcare, model_activ_cache

    if active_state != "active":
        model_activ_cache = "Indisponibil"
        model_label.configure(text=model_activ_cache)

    if info_ollama_incarcare:
        return

    info_ollama_incarcare = True
    threading.Thread(target=incarca_info_ollama_in_fundal, args=(active_state,), daemon=True).start()


def formateaza_uptime(active_timestamp):
    if not active_timestamp or active_timestamp.lower() == "n/a":
        return "Uptime indisponibil"

    try:
        pornit_la = datetime.strptime(active_timestamp, "%a %Y-%m-%d %H:%M:%S %Z")
        diferenta = datetime.now() - pornit_la
        secunde = max(int(diferenta.total_seconds()), 0)

        zile = secunde // 86400
        ore = (secunde % 86400) // 3600
        minute = (secunde % 3600) // 60

        parti = []
        if zile:
            parti.append(f"{zile}z")
        if ore:
            parti.append(f"{ore}h")
        if minute or not parti:
            parti.append(f"{minute}m")

        return "Activ de " + " ".join(parti)
    except ValueError:
        return "Uptime indisponibil"


def arata_notificare(text, tip="info"):
    global notification_after_id

    stiluri = {
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
    notification_after_id = app.after(3200, ascunde_notificare)



def ascunde_notificare():
    global notification_after_id
    notification_frame.configure(fg_color="#111827", border_color="#1f2937")
    notification_label.configure(text="")
    notification_after_id = None



def actualizeaza_stare():
    """Actualizează textul și culoarea din interfață."""
    detalii = obtine_detalii_serviciu()
    active_state = detalii["active_state"]
    sub_state = detalii["sub_state"]
    uptime_text = formateaza_uptime(detalii["active_timestamp"])

    version_label.configure(text=versiune_ollama_cache)
    model_label.configure(text=model_activ_cache)
    programeaza_actualizare_info_ollama(active_state)

    if active_state == "active":
        status_dot.configure(text="●", text_color="#22c55e")
        status_badge.configure(text="ONLINE", fg_color="#123524", text_color="#86efac")
        status_label.configure(text="Ollama este pornit", text_color="#f8fafc")
        subtitle_label.configure(text="Rulează normal și răspunde local", text_color="#9fb0c7")
        uptime_value_label.configure(text=uptime_text, text_color="#93c5fd")
        detail_state_value.configure(text="Activ · Running", text_color="#cbd5e1")
        model_label.configure(text_color="#c4b5fd")
    elif active_state == "inactive":
        status_dot.configure(text="●", text_color="#ef4444")
        status_badge.configure(text="OFFLINE", fg_color="#3a1618", text_color="#fca5a5")
        status_label.configure(text="Ollama este oprit", text_color="#f8fafc")
        subtitle_label.configure(text="Serviciul nu rulează în acest moment", text_color="#9fb0c7")
        uptime_value_label.configure(text="Nu rulează", text_color="#fda4af")
        detail_state_value.configure(text="Inactiv · Dead", text_color="#cbd5e1")
        model_label.configure(text_color="#94a3b8")
    elif active_state == "failed":
        status_dot.configure(text="●", text_color="#f59e0b")
        status_badge.configure(text="ERROR", fg_color="#3a2608", text_color="#fcd34d")
        status_label.configure(text="Ollama este în eroare", text_color="#f8fafc")
        subtitle_label.configure(text="Serviciul a pornit cu probleme", text_color="#f0b44c")
        uptime_value_label.configure(text="Verifică jurnalul serviciului", text_color="#fcd34d")
        detail_state_value.configure(text=f"{active_state.capitalize()} · {sub_state.capitalize()}", text_color="#fcd34d")
        model_label.configure(text_color="#fcd34d")
    else:
        status_dot.configure(text="●", text_color="#94a3b8")
        status_badge.configure(text="UNKNOWN", fg_color="#1f2937", text_color="#cbd5e1")
        status_label.configure(text="Stare necunoscută", text_color="#f8fafc")
        subtitle_label.configure(text="Nu s-au putut obține detalii de la systemd", text_color="#9fb0c7")
        uptime_value_label.configure(text="Indisponibil", text_color="#94a3b8")
        detail_state_value.configure(text=f"{active_state.capitalize()} · {sub_state.capitalize()}", text_color="#cbd5e1")
        model_label.configure(text_color="#94a3b8")



def auto_refresh():
    if not comanda_in_curs:
        actualizeaza_stare()
    app.after(AUTO_REFRESH_MS, auto_refresh)


app = ctk.CTk()
icon_path = "/home/acer/ollama-control-ui/icon.png"
ui_uptime_icon = incarca_imagine_ctk("ui_uptime.png", (16, 16))
ui_status_icon = incarca_imagine_ctk("ui_status.png", (16, 16))
ui_model_icon = incarca_imagine_ctk("ui_model.png", (18, 18))
ui_version_icon = incarca_imagine_ctk("ui_version.png", (18, 18))
try:
    app.iconphoto(True, tk.PhotoImage(file=icon_path))
except Exception:
    pass

app.title("Ollama Control")
app.geometry("620x540")
app.resizable(False, False)
app.configure(fg_color="#0f172a")

main_frame = ctk.CTkFrame(
    app,
    width=560,
    height=430,
    corner_radius=24,
    fg_color="#111827",
    border_width=1,
    border_color="#1f2937"
)
main_frame.place(relx=0.5, rely=0.5, anchor="center")

title_label = ctk.CTkLabel(
    main_frame,
    text="Ollama Control",
    font=ctk.CTkFont(size=28, weight="bold"),
    text_color="#f9fafb"
)
title_label.pack(pady=(22, 2))

subtitle_top = ctk.CTkLabel(
    main_frame,
    text="Panou desktop pentru controlul serviciului local Ollama",
    font=ctk.CTkFont(size=12),
    text_color="#8ea0b8"
)
subtitle_top.pack(pady=(0, 12))

status_frame = ctk.CTkFrame(
    main_frame,
    fg_color="#0b1220",
    corner_radius=22,
    border_width=1,
    border_color="#1e293b"
)
status_frame.pack(pady=5, padx=24, fill="x")

status_header = ctk.CTkFrame(status_frame, fg_color="transparent")
status_header.pack(fill="x", padx=18, pady=(14, 6))

status_dot = ctk.CTkLabel(
    status_header,
    text="●",
    font=ctk.CTkFont(size=22, weight="bold")
)
status_dot.pack(side="left")

status_label = ctk.CTkLabel(
    status_header,
    text="Se verifică starea...",
    font=ctk.CTkFont(size=21, weight="bold"),
    text_color="#f8fafc"
)
status_label.pack(side="left", padx=(10, 10))

status_badge = ctk.CTkLabel(
    status_header,
    text="CHECKING",
    corner_radius=999,
    fg_color="#1f2937",
    text_color="#cbd5e1",
    font=ctk.CTkFont(size=11, weight="bold"),
    padx=12,
    pady=4
)
status_badge.pack(side="right")

subtitle_label = ctk.CTkLabel(
    status_frame,
    text="Așteaptă răspunsul sistemului",
    font=ctk.CTkFont(size=12),
    text_color="#9fb0c7"
)
subtitle_label.pack(anchor="w", padx=20)

details_grid = ctk.CTkFrame(status_frame, fg_color="transparent")
details_grid.pack(fill="x", padx=18, pady=(12, 14))

detail_uptime_title = ctk.CTkLabel(
    details_grid,
    text=" UPTIME",
    image=ui_uptime_icon,
    compound="left",
    font=ctk.CTkFont(size=10, weight="bold"),
    text_color="#64748b"
)
detail_uptime_title.grid(row=0, column=0, sticky="w", padx=(0, 24))

uptime_value_label = ctk.CTkLabel(
    details_grid,
    text="Uptime indisponibil",
    font=ctk.CTkFont(size=13, weight="bold"),
    text_color="#93c5fd"
)
uptime_value_label.grid(row=1, column=0, sticky="w", padx=(0, 24), pady=(1, 0))

detail_state_title = ctk.CTkLabel(
    details_grid,
    text=" STATUS",
    image=ui_status_icon,
    compound="left",
    font=ctk.CTkFont(size=10, weight="bold"),
    text_color="#64748b"
)
detail_state_title.grid(row=0, column=1, sticky="w")

detail_state_value = ctk.CTkLabel(
    details_grid,
    text="Checking · Pending",
    font=ctk.CTkFont(size=13, weight="bold"),
    text_color="#cbd5e1"
)
detail_state_value.grid(row=1, column=1, sticky="w", pady=(1, 0))

meta_frame = ctk.CTkFrame(
    main_frame,
    fg_color="#0d1526",
    corner_radius=18,
    border_width=1,
    border_color="#1e293b"
)
meta_frame.pack(padx=24, pady=(10, 0), fill="x")

meta_grid = ctk.CTkFrame(meta_frame, fg_color="transparent")
meta_grid.pack(fill="x", padx=18, pady=14)

model_title = ctk.CTkLabel(
    meta_grid,
    text="  MODEL ACTIV",
    image=ui_model_icon,
    compound="left",
    font=ctk.CTkFont(size=10, weight="bold"),
    text_color="#64748b"
)
model_title.grid(row=0, column=0, sticky="w", padx=(0, 24))

version_title = ctk.CTkLabel(
    meta_grid,
    text="  VERSIUNE OLLAMA",
    image=ui_version_icon,
    compound="left",
    font=ctk.CTkFont(size=10, weight="bold"),
    text_color="#64748b"
)
version_title.grid(row=0, column=1, sticky="w")

model_label = ctk.CTkLabel(
    meta_grid,
    text="Se verifică...",
    font=ctk.CTkFont(size=13, weight="bold"),
    text_color="#c4b5fd"
)
model_label.grid(row=1, column=0, sticky="w", padx=(0, 24), pady=(2, 0))

version_label = ctk.CTkLabel(
    meta_grid,
    text="Se verifică versiunea...",
    font=ctk.CTkFont(size=12),
    text_color="#94a3b8"
)
version_label.grid(row=1, column=1, sticky="w", pady=(2, 0))

buttons_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
buttons_frame.pack(pady=(14, 6))

start_button = ctk.CTkButton(
    buttons_frame,
    text="Pornește",
    width=150,
    height=46,
    corner_radius=16,
    fg_color="#22c55e",
    hover_color="#16a34a",
    text_color="#08130d",
    font=ctk.CTkFont(size=15, weight="bold"),
    command=lambda: ruleaza_comanda("start")
)
start_button.pack(side="left", padx=8)

refresh_button = ctk.CTkButton(
    buttons_frame,
    text="Refresh",
    width=108,
    height=46,
    corner_radius=16,
    fg_color="#1f2937",
    hover_color="#334155",
    border_width=1,
    border_color="#334155",
    text_color="#e2e8f0",
    font=ctk.CTkFont(size=14, weight="bold"),
    command=actualizeaza_stare
)
refresh_button.pack(side="left", padx=8)

stop_button = ctk.CTkButton(
    buttons_frame,
    text="Oprește",
    width=150,
    height=46,
    corner_radius=16,
    fg_color="#ef4444",
    hover_color="#dc2626",
    text_color="#ffffff",
    font=ctk.CTkFont(size=15, weight="bold"),
    command=lambda: ruleaza_comanda("stop")
)
stop_button.pack(side="left", padx=8)

notification_frame = ctk.CTkFrame(
    main_frame,
    fg_color="#111827",
    corner_radius=12,
    border_width=1,
    border_color="#1f2937",
    height=34
)
notification_frame.pack(padx=24, pady=(2, 10), fill="x")

notification_label = ctk.CTkLabel(
    notification_frame,
    text="",
    font=ctk.CTkFont(size=11, weight="bold"),
    text_color="#93c5fd"
)
notification_label.pack(anchor="w", padx=12, pady=7)

actualizeaza_stare()
app.after(AUTO_REFRESH_MS, auto_refresh)
app.mainloop()

