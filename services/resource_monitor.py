import re
import subprocess
from datetime import datetime, timezone


def _parse_systemd_timestamp(active_timestamp: str) -> datetime:
    """Parsează timestamp-ul systemd în timpul local al sistemului."""
    # systemd folosește forma „Tue 2026-11-18 22:00:00 UTC”, însă pe
    # distribuțiile locale poate folosi abrevieri precum EEST/CET, pe care
    # datetime.strptime nu le recunoaște în mod fiabil. Timestamp-ul afișat
    # este deja în fusul local, deci calculăm diferența cu timpul local.
    match = re.fullmatch(
        r"\w{3}\s+(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2})(?:\s+(\S+))?",
        active_timestamp.strip(),
    )
    if not match:
        raise ValueError("Format systemd necunoscut")

    date_part, time_part, zone_part = match.groups()
    zone = (zone_part or "UTC").upper()
    local_value = datetime.strptime(f"{date_part} {time_part}", "%Y-%m-%d %H:%M:%S")

    if zone in ("UTC", "GMT", "Z"):
        return local_value.replace(tzinfo=timezone.utc)

    # Pentru fusurile locale, datetime.astimezone folosește fusul sistemului
    # și reglează corect offset-ul DST pentru data respectivă.
    return local_value.astimezone()


def formateaza_uptime(active_timestamp: str | None) -> str:
    """Formatează timestamp-ul systemd într-un string citibil."""
    if not active_timestamp or active_timestamp.lower() == "n/a":
        return "Uptime indisponibil"

    try:
        pornit_la = _parse_systemd_timestamp(active_timestamp)
        diferenta = datetime.now(pornit_la.tzinfo) - pornit_la
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
    except (TypeError, ValueError):
        return "Uptime indisponibil"


def obtine_consum_resurse() -> str:
    """Încearcă să obțină consumul de RAM/VRAM pentru procesele Ollama."""
    ram_mb = 0.0
    vram_mb = 0.0

    # Încearcă nvidia-smi pentru VRAM
    try:
        rezultat = subprocess.run(
            ["nvidia-smi", "--query-compute-apps=pid,used_memory", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=3
        )
        for linie in rezultat.stdout.strip().splitlines():
            parti = [p.strip() for p in linie.split(",")]
            if len(parti) >= 2:
                try:
                    pid = int(parti[0])
                    mem = int(parti[1])
                    try:
                        with open(f"/proc/{pid}/cmdline", "r") as f:
                            cmdline = f.read()
                        if "ollama" in cmdline.lower():
                            vram_mb += mem
                    except Exception:
                        pass
                except ValueError:
                    pass
    except Exception:
        pass

    # Încearcă să obțină RAM folosit de procesele ollama
    try:
        rezultat = subprocess.run(
            ["ps", "-eo", "pid,rss,comm,args="],
            capture_output=True, text=True, timeout=2
        )
        for linie in rezultat.stdout.strip().splitlines():
            parti = linie.split()
            if len(parti) < 3:
                continue
            try:
                comm = parti[2].lower()
                args = " ".join(parti[3:]).lower()
                if "ollama" in comm or "ollama" in args:
                    rss_kb = int(parti[1])
                    ram_mb += rss_kb / 1024
            except (ValueError, IndexError):
                pass
    except Exception:
        pass

    if ram_mb == 0 and vram_mb == 0:
        return "—"

    parti = []
    if ram_mb > 0:
        parti.append(f"RAM: {ram_mb:.1f} MB")
    if vram_mb > 0:
        parti.append(f"VRAM: {vram_mb:.1f} MB")

    return " | ".join(parti)
