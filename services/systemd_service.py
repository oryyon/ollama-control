import subprocess

from services.utils import ruleaza_si_citeste

#: Proprietatile systemd citite intr-un singur apel.
_PROPRIETATI_SERVICIU = "ActiveState,SubState,ActiveEnterTimestamp"


def obtine_detalii_serviciu() -> dict[str, str]:
    """Returneaza starea systemd si timestamp-ul ultimei activari.

    Toate valorile sunt citite printr-un singur apel `systemctl show`:
    trei apeluri separate costau ~92 ms, unul singur ~23 ms. Diferenta se
    vede la fiecare verificare a starii serviciului.
    """
    try:
        rezultat = ruleaza_si_citeste([
            "systemctl", "show", "ollama",
            f"--property={_PROPRIETATI_SERVICIU}",
        ])

        valori: dict[str, str] = {}
        for linie in rezultat.splitlines():
            cheie, separator, valoare = linie.partition("=")
            if separator:
                valori[cheie.strip()] = valoare.strip()

        return {
            "active_state": valori.get("ActiveState") or "necunoscut",
            "sub_state": valori.get("SubState") or "necunoscut",
            "active_timestamp": valori.get("ActiveEnterTimestamp") or "",
        }
    except Exception:
        return {
            "active_state": "necunoscut",
            "sub_state": "necunoscut",
            "active_timestamp": "",
        }


def executa_comanda_sistem(comanda: str) -> bool:
    """Executa o comanda systemd (start/stop/restart) pentru Ollama."""
    try:
        subprocess.run(["pkexec", "systemctl", comanda, "ollama"], check=True)
        return True
    except subprocess.CalledProcessError:
        return False
