import subprocess


def ruleaza_si_citeste(comanda: list[str]) -> str:
    """Rulează o comandă și returnează stdout curățat."""
    rezultat = subprocess.run(
        comanda,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    return rezultat.stdout.strip()
