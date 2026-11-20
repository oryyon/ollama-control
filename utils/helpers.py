import re


def format_size(size_bytes: int | None) -> str:
    """Convertește bytes în MB sau GB cu 1 zecimală."""
    if size_bytes is None or size_bytes == 0:
        return "N/A"
    if size_bytes >= 1024 ** 3:
        return f"{size_bytes / (1024 ** 3):.1f} GB"
    return f"{size_bytes / (1024 ** 2):.1f} MB"


def extract_params(name: str | None) -> str:
    """Extrage numărul de parametri din numele modelului (ex: 8B, 70B)."""
    if not name:
        return "N/A"
    match = re.search(r'(\d+(?:\.\d+)?)\s*[Bb]\b', name)
    if match:
        return match.group(0).upper()
    return "N/A"
