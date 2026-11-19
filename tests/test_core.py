import subprocess
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from config import settings as settings_config
from core import ollama_models
from core.state_manager import _service_refresh_ms
from services import ollama_info
from services.resource_monitor import formateaza_uptime
from ui.settings_window import _is_valid_keepalive
from utils.helpers import extract_params, format_size


class OllamaModelsTests(unittest.TestCase):
    def setUp(self) -> None:
        ollama_models.invalidate_ollama_models_cache()

    def test_parse_models_uses_size_column_instead_of_id(self) -> None:
        output = (
            "NAME                       ID              SIZE      MODIFIED\n"
            "llama3:latest              365c0bd3cde    4.7 GB    2 weeks ago\n"
            "qwen3:8b                   a1b2c3d4e5f6    6.2 GB    3 days ago\n"
        )

        models = ollama_models._parse_ollama_models_output(output)

        self.assertEqual(
            models,
            [
                {
                    "name": "llama3:latest",
                    "path": None,
                    "size": "4.7 GB",
                    "params": "N/A",
                },
                {
                    "name": "qwen3:8b",
                    "path": None,
                    "size": "6.2 GB",
                    "params": "8B",
                },
            ],
        )

    def test_get_models_reports_cli_error_as_failure(self) -> None:
        result = subprocess.CompletedProcess(
            args=["ollama", "list"],
            returncode=1,
            stdout="",
            stderr="permission denied",
        )

        with patch.object(ollama_models.subprocess, "run", return_value=result):
            models, success = ollama_models.get_ollama_models()

        self.assertFalse(success)
        self.assertEqual(models, [])

    def test_get_models_handles_empty_server_list(self) -> None:
        result = subprocess.CompletedProcess(
            args=["ollama", "list"],
            returncode=0,
            stdout="NAME    ID    SIZE    MODIFIED\n",
            stderr="",
        )

        with patch.object(ollama_models.subprocess, "run", return_value=result):
            models, success = ollama_models.get_ollama_models()

        self.assertTrue(success)
        self.assertEqual(models, [])


class ActiveModelDetectionTests(unittest.TestCase):
    """Pot exista mai multe modele încărcate simultan (keepalive lung)."""

    PS_OUTPUT = (
        "NAME                                            ID              SIZE      PROCESSOR    CONTEXT    UNTIL             \n"
        "Phi-4-mini-reasoning-Q4_K_M.gguf:latest         619fdf0d77a8    3.1 GB    100% CPU     4096       6 hours from now     \n"
        "Qwen2.5-Coder-3B-Instruct-Q4_K_M.gguf:latest    9aba0d51298e    2.2 GB    100% CPU     4096       9 minutes from now   \n"
    )

    def test_modelele_activate_include_toate_randurile(self) -> None:
        from services.ollama_info import obtine_modelele_activate

        result = subprocess.CompletedProcess(
            args=["ollama", "ps"], returncode=0, stdout=self.PS_OUTPUT, stderr=""
        )

        with patch.object(ollama_info.subprocess, "run", return_value=result):
            modele = obtine_modelele_activate()

        self.assertEqual(
            modele,
            [
                "Phi-4-mini-reasoning-Q4_K_M.gguf:latest",
                "Qwen2.5-Coder-3B-Instruct-Q4_K_M.gguf:latest",
            ],
        )

    def test_modelul_al_doilea_rand_e_recunoscut_ca_activ(self) -> None:
        """Regresie: modelul nou se încărca, dar aplicația raporta eșec.

        Verificarea privea doar primul rând din `ollama ps`; cu keepalive
        lung, modelul vechi rămâne primul, iar cel nou (al doilea) era
        raportat ca „nu s-a încărcat” — deși era încărcat corect.
        """
        from ui.model_actions import _is_expected_model_active

        result = subprocess.CompletedProcess(
            args=["ollama", "ps"], returncode=0, stdout=self.PS_OUTPUT, stderr=""
        )

        with patch.object(ollama_info.subprocess, "run", return_value=result):
            gasit, text = _is_expected_model_active(
                "Qwen2.5-Coder-3B-Instruct-Q4_K_M.gguf:latest"
            )

        self.assertTrue(gasit, text)
        self.assertIn("Qwen2.5-Coder", text)

    def test_lista_de_modele_nu_se_goleste_la_timeout(self) -> None:
        """La timeout păstrăm ultima listă — modelele nu au dispărut."""
        ollama_models.invalidate_ollama_models_cache()
        ok_result = subprocess.CompletedProcess(
            args=["ollama", "list"],
            returncode=0,
            stdout=(
                "NAME                       ID              SIZE      MODIFIED\n"
                "llama3:latest              365c0bd3cde    4.7 GB    2 weeks ago\n"
            ),
            stderr="",
        )
        with patch.object(ollama_models.subprocess, "run", return_value=ok_result):
            ollama_models.get_ollama_models()

        # cache-ul trebuie să fie „vechi”, ca să ajungem pe ramura de timeout
        ollama_models._ollama_models_cache_time = 0

        with patch.object(
            ollama_models.subprocess,
            "run",
            side_effect=subprocess.TimeoutExpired(cmd="ollama list", timeout=45),
        ):
            modele, success = ollama_models.get_ollama_models()

        self.assertFalse(success)
        self.assertEqual(len(modele), 1, "lista trebuie păstrată, nu golită")
        self.assertEqual(modele[0]["name"], "llama3:latest")


class SyntaxGuardTests(unittest.TestCase):
    """Niciun fișier Python nu trebuie să aibă erori de sintaxă.

    Codul sursă nu e versionat în git (doar artefactele de build), iar o
    editare ratată în editor putea lăsa un fișier stricat pe disc fără ca
    testele să observe. Compilarea tuturor fișierelor prinde asta imediat.
    """

    EXCLUDE = {"venv", "build", "dist", ".git", ".continue", "__pycache__"}

    def test_toate_fisierele_python_compileaza(self) -> None:
        import py_compile
        import tempfile
        from pathlib import Path

        radacina = Path(__file__).resolve().parent.parent
        erori: list[str] = []
        with tempfile.TemporaryDirectory() as temporar:
            for cale in sorted(radacina.rglob("*.py")):
                if any(part in self.EXCLUDE for part in cale.parts):
                    continue
                iesire = Path(temporar) / (cale.stem + ".pyc")
                try:
                    py_compile.compile(str(cale), doraise=True, cfile=str(iesire))
                except py_compile.PyCompileError as exc:
                    erori.append(f"{cale.relative_to(radacina)}: {exc}")
        self.assertEqual(erori, [], "erori de sintaxă:\n" + "\n".join(erori))

    def test_importurile_rada_cina_sunt_rezolvabile(self) -> None:
        """Pachetele din rădăcina proiectului se importă dintr-un director."""
        import importlib

        for pachet in ("config.settings", "core.ollama_models", "services.ollama_info",
                       "ui.model_actions", "utils.logging_config"):
            self.assertIsNotNone(importlib.import_module(pachet))


class SettingsAndRefreshTests(unittest.TestCase):
    def test_refresh_interval_is_read_dynamically(self) -> None:
        original = settings_config.AUTO_REFRESH_MS
        try:
            settings_config.AUTO_REFRESH_MS = 5000
            self.assertEqual(_service_refresh_ms(), 15000)
            settings_config.AUTO_REFRESH_MS = 30000
            self.assertEqual(_service_refresh_ms(), 90000)
            settings_config.AUTO_REFRESH_MS = None
            self.assertEqual(_service_refresh_ms(), 15000)
        finally:
            settings_config.AUTO_REFRESH_MS = original

    def test_keepalive_validation(self) -> None:
        for value in ("45s", "15m", "2h", "1d"):
            self.assertTrue(_is_valid_keepalive(value))
        for value in ("", "10", "m", "1w", "1m30s"):
            self.assertFalse(_is_valid_keepalive(value))


class ResourceMonitorTests(unittest.TestCase):
    def test_uptime_accepts_local_timezone_abbreviation(self) -> None:
        started = datetime.now() - timedelta(minutes=5)
        timestamp = started.strftime("%a %Y-%m-%d %H:%M:%S EEST")

        result = formateaza_uptime(timestamp)

        self.assertTrue(result.startswith("Activ de 5m"), result)

    def test_uptime_handles_missing_or_invalid_timestamp(self) -> None:
        for value in (None, "", "n/a", "invalid"):
            self.assertEqual(formateaza_uptime(value), "Uptime indisponibil")


class HelperTests(unittest.TestCase):
    def test_format_size(self) -> None:
        self.assertEqual(format_size(None), "N/A")
        self.assertEqual(format_size(0), "N/A")
        self.assertEqual(format_size(1024 ** 2), "1.0 MB")
        self.assertEqual(format_size(1024 ** 3), "1.0 GB")

    def test_extract_params(self) -> None:
        self.assertEqual(extract_params("qwen3:8b"), "8B")
        self.assertEqual(extract_params("model-70b-instruct"), "70B")
        self.assertEqual(extract_params("model-without-size"), "N/A")


if __name__ == "__main__":
    unittest.main()
