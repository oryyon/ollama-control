import subprocess

from services.utils import ruleaza_si_citeste


def obtine_detalii_serviciu() -> dict[str, str]:
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


def executa_comanda_sistem(comanda: str) -> bool:
    """Execută o comandă systemd (start/stop/restart) pentru Ollama."""
    try:
        subprocess.run(["pkexec", "systemctl", comanda, "ollama"], check=True)
        return True
    except subprocess.CalledProcessError:
        return False
