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
                    "size": "4.7 GB",
                    "params": "N/A",
                },
                {
                    "name": "qwen3:8b",
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
        "phi4-mini-reasoning:latest                     619fdf0d77a8    3.1 GB    100% CPU     4096       6 hours from now     \n"
        "qwen2.5-coder:3b                               9aba0d51298e    2.2 GB    100% CPU     4096       9 minutes from now   \n"
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
                "phi4-mini-reasoning:latest",
                "qwen2.5-coder:3b",
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
            gasit, text = _is_expected_model_active("qwen2.5-coder:3b")

        self.assertTrue(gasit, text)
        self.assertIn("qwen2.5-coder", text)

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


class KeepaliveTests(unittest.TestCase):
    """Durata keepalive (implicit 10 minute) ajunge la `ollama run`."""

    def test_implicitul_este_zece_zece_zece_minute(self) -> None:
        from ui import model_actions

        with patch.dict(settings_config.settings, {}, clear=True):
            self.assertEqual(model_actions.get_ollama_keepalive(), "10m")
            self.assertEqual(settings_config.KEEPALIVE_DEFAULT, "10m")

    def test_valoare_invalida_cade_pe_implicit(self) -> None:
        """O setare editată manual nu trebuie să ajungă la `ollama run`."""
        from ui import model_actions

        for valoare in ("abc", "10", "", "   "):
            with patch.dict(settings_config.settings,
                            {"ollama_keepalive": valoare}, clear=True):
                self.assertEqual(model_actions.get_ollama_keepalive(), "10m")

    def test_valoarea_valida_e_pastra(self) -> None:
        from ui import model_actions

        with patch.dict(settings_config.settings,
                        {"ollama_keepalive": "30m"}, clear=True):
            self.assertEqual(model_actions.get_ollama_keepalive(), "30m")

    def test_incarcarea_trimite_keepalive_la_api(self) -> None:
        """Keepalive-ul configurat ajunge la cererea de încărcare."""
        from ui import model_actions

        captate: dict[str, object] = {}

        def fake_load(model, keepalive="10m", timeout=300.0):
            captate["model"] = model
            captate["keepalive"] = keepalive
            return True, None

        with patch.dict(settings_config.settings,
                        {"ollama_keepalive": "30m"}, clear=True):
            with patch.object(model_actions, "load_model", side_effect=fake_load):
                with patch.object(model_actions, "obtine_modelele_activate",
                                  return_value=["qwen3:8b"]):
                    ok, eroare = model_actions.run_model("qwen3:8b")

        self.assertTrue(ok, eroare)
        self.assertEqual(captate["model"], "qwen3:8b")
        self.assertEqual(captate["keepalive"], "30m")

    def test_incarcarea_fara_server_rupe_graceful(self) -> None:
        """Dacă serverul nu răspunde, se întoarce o eroare clară."""
        from ui import model_actions

        def fake_load(model, keepalive="10m", timeout=300.0):
            return False, "Serverul Ollama nu răspunde."

        with patch.object(model_actions, "load_model", side_effect=fake_load):
            ok, eroare = model_actions.run_model("qwen3:8b")

        self.assertFalse(ok)
        self.assertIn("nu răspunde", str(eroare))


class ResourceMonitorTests(unittest.TestCase):
    def test_uptime_accepts_local_timezone_abbreviation(self) -> None:
        started = datetime.now() - timedelta(minutes=5)
        timestamp = started.strftime("%a %Y-%m-%d %H:%M:%S EEST")

        result = formateaza_uptime(timestamp)

        self.assertTrue(result.startswith("Activ de 5m"), result)

    def test_uptime_handles_missing_or_invalid_timestamp(self) -> None:
        for value in (None, "", "n/a", "invalid"):
            self.assertEqual(formateaza_uptime(value), "Uptime indisponibil")


class NoLmStudioTests(unittest.TestCase):
    """Aplicația este exclusiv despre Ollama — fără nicio urmă de LM Studio.

    LM Studio a fost eliminat complet din proiect. Testul blochează
    reintroducerea lui prin cod sau prin documentație.
    """

    EXCLUDE = {"venv", "build", "dist", ".git", ".continue", "__pycache__"}

    #: Termeni interziși în surse și documentație.
    TERMENI_INTERZISI = ("lm studio", "lmstudio", "lm_studio", ".gguf")

    def test_nicio_sursa_nu_mai_mentioneaza_lm_studio(self) -> None:
        from pathlib import Path

        radacina = Path(__file__).resolve().parent.parent
        # Acest fișier conține termenii interziși prin definiție, deci e exclus.
        acest_fisier = Path(__file__).resolve()
        gasiri: list[str] = []
        for cale in sorted(radacina.rglob("*")):
            if not cale.is_file():
                continue
            if cale.resolve() == acest_fisier:
                continue
            if any(part in self.EXCLUDE for part in cale.parts):
                continue
            if cale.suffix.lower() not in (".py", ".md", ".desktop", ".spec", ".sh", ".txt"):
                continue
            try:
                continut = cale.read_text(encoding="utf-8", errors="ignore").lower()
            except OSError:
                continue
            for termen in self.TERMENI_INTERZISI:
                if termen in continut:
                    gasiri.append(f"{cale.relative_to(radacina)}: {termen}")

        self.assertEqual(gasiri, [], "referințe LM Studio rămase:\n" + "\n".join(gasiri))

    def test_modulul_lmstudio_nu_mai_exista(self) -> None:
        import importlib.util

        self.assertIsNone(importlib.util.find_spec("core.lmstudio"))


class SettingsLocationTests(unittest.TestCase):
    """Setările stau în `~/.config/ollama-control/`, nu lângă executabil."""

    def test_setarile_sunt_in_directorul_xdg(self) -> None:
        self.assertEqual(settings_config.CONFIG_DIR.name, "ollama-control")
        self.assertEqual(settings_config.SETTINGS_PATH.parent, settings_config.CONFIG_DIR)

    def test_directorul_de_configurare_se_creeaza_la_salvare(self) -> None:
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as temporar:
            director = Path(temporar) / "ollama-control"
            cale = director / "settings.json"
            original_dir = settings_config.CONFIG_DIR
            original_path = settings_config.SETTINGS_PATH
            try:
                settings_config.CONFIG_DIR = director
                settings_config.SETTINGS_PATH = cale
                settings_config.salveaza_setari()
                self.assertTrue(cale.exists())
            finally:
                settings_config.CONFIG_DIR = original_dir
                settings_config.SETTINGS_PATH = original_path


class ModelsPathTests(unittest.TestCase):
    """Calea modelelor se detectează din starea reală a serverului."""

    def test_manifestul_e_gasit_dupa_nume_sau_tag(self) -> None:
        import tempfile
        from pathlib import Path

        from services.ollama_paths import _manifest_pentru

        with tempfile.TemporaryDirectory() as temporar:
            director = Path(temporar)
            baza = director / "manifests" / "registry.ollama.ai" / "library"
            (baza / "qwen3").mkdir(parents=True)
            (baza / "qwen3" / "8b").write_text("x")
            (baza / "llama3").mkdir(parents=True)
            (baza / "llama3" / "latest").write_text("x")

            self.assertIsNotNone(_manifest_pentru(director, "qwen3:8b"))
            self.assertIsNotNone(_manifest_pentru(director, "llama3:latest"))
            self.assertIsNotNone(_manifest_pentru(director, "llama3"))
            self.assertIsNone(_manifest_pentru(director, "inexistent:1b"))

    def test_directorul_de_modele_este_intotdeauna_ales(self) -> None:
        from services.ollama_paths import get_models_directory

        cale = get_models_directory()
        self.assertTrue(str(cale))
        self.assertTrue(cale.is_absolute())

    def test_info_inclusa_caile_si_numarul_de_modele(self) -> None:
        from services.ollama_paths import get_models_directory_info

        info = get_models_directory_info()
        for cheie in ("path", "exists", "model_count"):
            self.assertIn(cheie, info)
        self.assertIsInstance(info["path"], str)
        self.assertIsInstance(info["exists"], bool)
        self.assertIsInstance(info["model_count"], int)


class LoadProgressTests(unittest.TestCase):
    """Progresul de încărcare se calculează din memoria runner-ului."""

    def test_rss_se_citeste_din_proc(self) -> None:
        import os

        from services.ollama_progress import _rss_bytes

        pid = os.getpid()
        valoare = _rss_bytes(pid)
        self.assertGreater(valoare, 0, "RSS-ul propriului proces trebuie să fie lizibil")

    def test_rss_pentru_pid_inexistent_este_zero(self) -> None:
        from services.ollama_progress import _rss_bytes

        self.assertEqual(_rss_bytes(999999999), 0)

    def test_procentul_este_cuplat_la_99(self) -> None:
        from pathlib import Path

        from services.ollama_progress import LoadProgressMonitor

        monitor = LoadProgressMonitor(model_size_bytes=1000, models_directory=Path("/tmp"))
        monitor.peak_bytes = monitor.baseline_bytes + 5000
        procent = monitor.sample()
        self.assertLessEqual(procent, 99)
        self.assertGreaterEqual(procent, 0)

    def test_dimensiunea_blobului_se_determina_dupa_digest(self) -> None:
        import tempfile
        from pathlib import Path

        from services.ollama_progress import _dimensiune_model

        with tempfile.TemporaryDirectory() as temporar:
            director = Path(temporar)
            (director / "blobs").mkdir()
            blob = director / "blobs" / "sha256-abc123"
            blob.write_bytes(b"x" * 4096)

            self.assertEqual(_dimensiune_model(director, "sha256-abc123"), 4096)
            self.assertEqual(_dimensiune_model(director, "sha256-lipsa"), 0)
            self.assertEqual(_dimensiune_model(director, None), 0)

    def test_monitorul_se_oprește_la_stop_event(self) -> None:
        import threading
        from pathlib import Path

        from services.ollama_progress import monitor_load_progress

        stop = threading.Event()
        stop.set()
        called: list[int] = []

        monitor_load_progress(
            model_size_bytes=1024,
            models_directory=Path("/tmp"),
            on_progress=called.append,
            stop_event=stop,
            interval=0.01,
        )
        self.assertEqual(called, [])


class OllamaApiTests(unittest.TestCase):
    """Clientul HTTP pentru Ollama trebuie să fie robust la erori."""

    def test_host_respecta_variabila_de_mediu(self) -> None:
        import os

        from services import ollama_api

        original = os.environ.get("OLLAMA_HOST")
        try:
            os.environ["OLLAMA_HOST"] = "127.0.0.1:9999"
            self.assertEqual(ollama_api._host(), "http://127.0.0.1:9999")

            os.environ["OLLAMA_HOST"] = "http://192.168.1.5:11434"
            self.assertEqual(ollama_api._host(), "http://192.168.1.5:11434")
        finally:
            if original is None:
                os.environ.pop("OLLAMA_HOST", None)
            else:
                os.environ["OLLAMA_HOST"] = original

    def test_load_model_rapoarta_eroare_cand_serverul_nu_exista(self) -> None:
        import os

        from services import ollama_api

        original = os.environ.get("OLLAMA_HOST")
        try:
            # Port închis: serverul nu răspunde.
            os.environ["OLLAMA_HOST"] = "127.0.0.1:9"
            succes, mesaj = ollama_api.load_model("qwen3:8b", timeout=5.0)
            self.assertFalse(succes)
            self.assertIsNotNone(mesaj)
        finally:
            if original is None:
                os.environ.pop("OLLAMA_HOST", None)
            else:
                os.environ["OLLAMA_HOST"] = original

    def test_modele_incarcate_returneaza_lista(self) -> None:
        from services import ollama_api

        modele = ollama_api.modele_incarcate()
        self.assertIsInstance(modele, list)


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
