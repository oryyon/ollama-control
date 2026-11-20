from pathlib import Path

from utils.helpers import format_size, extract_params

LMSTUDIO_PATH = Path.home() / ".lmstudio" / "models"


def get_lmstudio_models() -> list[dict[str, str | None]]:
    models: list[dict[str, str | None]] = []

    if LMSTUDIO_PATH.exists():
        for f in LMSTUDIO_PATH.rglob("*.gguf"):
            models.append({
                "name": f.name,
                "path": str(f),
                "size": format_size(f.stat().st_size),
                "params": extract_params(f.name),
            })

    return sorted(models, key=lambda x: x["name"].lower())
