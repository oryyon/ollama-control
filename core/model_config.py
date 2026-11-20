import subprocess
import tempfile
import os
import threading
from typing import Callable

from config.settings import settings, salveaza_setari
from core.ollama_models import invalidate_ollama_models_cache


def get_model_context(name: str) -> int:
    """Returnează context length configurat pentru un model, sau 4096 (default)."""
    contexts = settings.get("model_contexts", {})
    return contexts.get(name, 4096)


def save_model_context(name: str, num_ctx: int) -> None:
    """Salvează context length pentru un model în settings."""
    if "model_contexts" not in settings:
        settings["model_contexts"] = {}
    settings["model_contexts"][name] = num_ctx
    salveaza_setari()


def create_model_with_context(
    base_name: str,
    num_ctx: int,
    callback: Callable[[bool, str], None] | None = None,
) -> None:
    """Creează un model derivat cu context length custom.

    Ex: base_name='llama3', num_ctx=8192 → creează 'llama3-ctx8192'
    """
    derived_name = f"{base_name}-ctx{num_ctx}"
    modelfile_path: str | None = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".modelfile") as f:
            modelfile_path = f.name
            f.write(f"FROM {base_name}\n")
            f.write(f"PARAMETER num_ctx {num_ctx}\n")

        subprocess.run(
            ["ollama", "create", derived_name, "-f", modelfile_path],
            check=True,
            capture_output=True,
            text=True,
        )

        save_model_context(base_name, num_ctx)
        invalidate_ollama_models_cache()

        if callback:
            callback(True, derived_name)

    except Exception as e:
        print(f"Eroare la crearea modelului {derived_name}:", e)
        if callback:
            callback(False, derived_name)

    finally:
        if modelfile_path and os.path.exists(modelfile_path):
            try:
                os.unlink(modelfile_path)
            except Exception:
                pass


def create_model_with_context_threaded(
    base_name: str,
    num_ctx: int,
    callback: Callable[[bool, str], None] | None = None,
) -> None:
    """Rulează create_model_with_context într-un thread separat."""
    threading.Thread(
        target=lambda: create_model_with_context(base_name, num_ctx, callback),
        daemon=True,
    ).start()
