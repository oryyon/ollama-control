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

        # API-ul e sursa primară; aici testăm calea de rezervă (CLI-ul).
        with patch.object(ollama_info, "modele_incarcate_detaliat", return_value=None):
            with patch.object(ollama_info.subprocess, "run", return_value=result):
                modele = obtine_modelele_activate()

        self.assertEqual(
            modele,
            [
                "phi4-mini-reasoning:latest",
                "qwen2.5-coder:3b",
            ],
        )

    def test_modelele_activate_uses_api_first(self) -> None:
        """API-ul HTTP e sursa primară: răspunde instant, CLI-ul poate bloca.

        Regresie: cu serverul ocupat, `ollama ps` expira după 3 s, iar
        aplicația raporta „Model activ: indisponibil” deși modelul era
        încărcat corect (fereastra Modele Ollama îl arăta ca „Activ”).
        """
        from services.ollama_info import obtine_modelele_activate

        with patch.object(
            ollama_info,
            "modele_incarcate_detaliat",
            return_value=["lfm3-audio:latest", "qwen2.5-coder:3b"],
        ):
            with patch.object(ollama_info.subprocess, "run") as mock_run:
                modele = obtine_modelele_activate()

        self.assertEqual(modele, ["lfm3-audio:latest", "qwen2.5-coder:3b"])
        mock_run.assert_not_called()

    def test_model_activ_se_afiseaza_chiar_daca_serviciul_este_activating(self) -> None:
        """Starea systemd nu ascunde modelul: serverul e sursa de adevăr.

        Regresie: cu serviciul în „activating”, aplicația afișa
        „Indisponibil” la MODEL ACTIV, deși modelul era încărcat.
        """
        from services.ollama_info import obtine_model_activ

        with patch.object(
            ollama_info, "modele_incarcate_detaliat", return_value=["lfm3-audio:latest"]
        ):
            for stare in ("activating", "inactive", "active"):
                text = obtine_model_activ(stare)
                self.assertIn("lfm3-audio:latest", text, f"stare={stare}")

    def test_server_neaccesibil_este_diferit_de_fara_model(self) -> None:
        """Server inaccesibil → „Server indisponibil”; server gol → „Neîncărcat”."""
        from services.ollama_info import obtine_model_activ

        with patch.object(ollama_info, "modele_incarcate_detaliat", return_value=None):
            with patch.object(ollama_info.subprocess, "run", side_effect=OSError("boom")):
                with patch.object(ollama_info.subprocess, "run", side_effect=OSError("boom")):
                    text = obtine_model_activ("active")
        self.assertIn("indisponibil", text.lower())

        with patch.object(ollama_info, "modele_incarcate_detaliat", return_value=[]):
            text = obtine_model_activ("active")
        self.assertIn("neîncărcat", text.lower())

    def test_textele_pentru_model_sunt_diferite(self) -> None:
        """Cele două stări trebuie să aibă texte distincte și clare.

        „Server indisponibil” înseamnă că serverul nu răspunde (serviciu
        oprit), iar „Neîncărcat” că serverul merge, dar nu are model în
        memorie. Textul ambiguu „Indisponibil” lăsa utilizatorul să
        creadă că lipsește modelul, când de fapt serverul era oprit.
        """
        from services.ollama_info import (MODEL_NEINCARCAT, SERVER_INDISPONIBIL,
                                           este_fara_model, este_necunoscut)

        self.assertNotEqual(MODEL_NEINCARCAT, SERVER_INDISPONIBIL)
        self.assertTrue(este_fara_model(MODEL_NEINCARCAT))
        self.assertTrue(este_fara_model(SERVER_INDISPONIBIL))
        self.assertTrue(este_necunoscut(MODEL_NEINCARCAT))
        self.assertTrue(este_necunoscut(SERVER_INDISPONIBIL))

    def test_comparatiile_sunt_ignorate_cazul(self) -> None:
        """„Indisponibil” și „indisponibil” trebuie recunoscute identic.

        Regresie: verificările din interfață comparau cu „Indisponibil”
        (I mare), iar valoarea reală era „indisponibil” (mic) — condiția
        nu se îndeplinea niciodată, iar butonul de copiere copia literal
        textul afișat.
        """
        from services.ollama_info import (SERVER_INDISPONIBIL, este_fara_model,
                                           este_necunoscut)

        for varianta in (SERVER_INDISPONIBIL, SERVER_INDISPONIBIL.lower(),
                         SERVER_INDISPONIBIL.upper()):
            self.assertTrue(este_fara_model(varianta), varianta)
            self.assertTrue(este_necunoscut(varianta), varianta)

        self.assertTrue(este_fara_model("Indisponibil"))
        self.assertTrue(este_fara_model("indisponibil"))
        self.assertTrue(este_fara_model(""))

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

        with patch.object(ollama_info, "modele_incarcate_detaliat", return_value=None):
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


class OllamaUpdateTests(unittest.TestCase):
    """Compararea versiunilor Ollama și actualizarea."""

    def test_comparatia_versiunilor(self) -> None:
        from services.ollama_update import este_versiune_mai_noua

        self.assertTrue(este_versiune_mai_noua("0.40.17", "0.30.6"))
        self.assertTrue(este_versiune_mai_noua("1.0.0", "0.99.99"))
        self.assertTrue(este_versiune_mai_noua("0.40.1", "0.40"))
        self.assertFalse(este_versiune_mai_noua("0.30.6", "0.40.17"))
        self.assertFalse(este_versiune_mai_noua("0.40.0", "0.40.0"))
        self.assertFalse(este_versiune_mai_noua("0.40", "0.40.1"))
        self.assertFalse(este_versiune_mai_noua("", "1.0.0"))
        self.assertFalse(este_versiune_mai_noua("1.0.0", ""))

    def test_versiunea_instalata_este_un_numar(self) -> None:
        from services.ollama_update import get_installed_version

        versiune = get_installed_version()
        self.assertIsInstance(versiune, str)
        if versiune:
            self.assertRegex(versiune, r"^\d+\.\d+")

    def test_check_for_update_returneaza_structura_completa(self) -> None:
        from services.ollama_update import check_for_update

        info = check_for_update()
        for cheie in ("installed", "latest", "update_available", "error"):
            self.assertIn(cheie, info)
        self.assertIsInstance(info["update_available"], bool)

    def test_arhitectura_detectata_e_una_suportata(self) -> None:
        from services.ollama_update import _arhitectura

        arhitectura = _arhitectura()
        self.assertIn(arhitectura, ("amd64", "arm64"))

    def test_scriptul_de_instalare_opreste_serviciul(self) -> None:
        from pathlib import Path

        from services.ollama_update import _script_instalare

        script = _script_instalare(Path("/tmp/extras"), "0.40.17")
        self.assertIn("systemctl stop ollama", script)
        self.assertIn("systemctl start ollama", script)
        self.assertIn("/usr/local/bin/ollama", script)
        self.assertIn("/usr/local/lib/ollama", script)
        self.assertIn("0.40.17", script)


class UpdateDialogLayoutTests(unittest.TestCase):
    """Dialogul de actualizare trebuie să arate butonul de acțiune.

    Butonul poate fi creat corect și totuși să nu fie afișat, dacă nu este
    adăugat în ierarhia de widget-uri. Verificăm deci pachetarea lui.
    """

    def test_butonul_de_actualizare_este_pachetat(self) -> None:
        import ast
        from pathlib import Path

        radacina = Path(__file__).resolve().parent.parent
        sursa = (radacina / "ui" / "ollama_update_dialog.py").read_text(encoding="utf-8")
        arbore = ast.parse(sursa)

        apeluri: list[str] = []
        for nod in ast.walk(arbore):
            if not isinstance(nod, ast.Call):
                continue
            functie = nod.func
            if not isinstance(functie, ast.Attribute):
                continue
            if functie.attr == "pack" and isinstance(functie.value, ast.Attribute):
                if functie.value.attr == "actualizeaza_button":
                    apeluri.append("pack")

        self.assertIn(
            "pack",
            apeluri,
            "Butonul de actualizare nu este adăugat în ierarhia de widget-uri, "
            "deci nu va fi vizibil.",
        )

    def test_dialogul_are_eticheta_de_verificare(self) -> None:
        import ast
        from pathlib import Path

        radacina = Path(__file__).resolve().parent.parent
        sursa = (radacina / "ui" / "ollama_update_dialog.py").read_text(encoding="utf-8")
        self.assertIn("verificare_label", sursa)


class CopyModelButtonTests(unittest.TestCase):
    """Butonul de copiere a numelui modelului activ trebuie să fie afișat."""

    @staticmethod
    def _este_pachetat(sursa: str, nume: str) -> bool:
        """Verifică dacă obiectul `nume` primește un apel `pack()`.

        Obiectul poate fi o variabilă locală (`buton`) sau un atribut
        (`self.buton`), așa că tratăm ambele forme.
        """
        import ast

        arbore = ast.parse(sursa)
        for nod in ast.walk(arbore):
            if not isinstance(nod, ast.Call):
                continue
            functie = nod.func
            if not isinstance(functie, ast.Attribute) or functie.attr != "pack":
                continue

            obiect = functie.value
            if isinstance(obiect, ast.Name) and obiect.id == nume:
                return True
            if isinstance(obiect, ast.Attribute) and obiect.attr == nume:
                return True

        return False

    def test_butonul_de_copiere_este_pachetat(self) -> None:
        from pathlib import Path

        radacina = Path(__file__).resolve().parent.parent
        sursa = (radacina / "ui" / "meta_section.py").read_text(encoding="utf-8")

        self.assertTrue(
            self._este_pachetat(sursa, "copy_button"),
            "Butonul de copiere nu este adăugat în ierarhia de widget-uri, "
            "deci nu va fi vizibil.",
        )

    def test_sectiunea_meta_expune_butonul_de_copiere(self) -> None:
        from pathlib import Path

        radacina = Path(__file__).resolve().parent.parent
        sursa = (radacina / "ui" / "meta_section.py").read_text(encoding="utf-8")
        self.assertIn('"copy_button": copy_button', sursa)

    def test_folosirea_clipboardului_este_cu_management_de_erori(self) -> None:
        from pathlib import Path

        radacina = Path(__file__).resolve().parent.parent
        sursa = (radacina / "ui" / "main_window.py").read_text(encoding="utf-8")
        self.assertIn("clipboard_clear", sursa)
        self.assertIn("clipboard_append", sursa)


class OnlineModelsTests(unittest.TestCase):
    """Butonul care trimite la catalogul de modele de pe ollama.com."""

    def test_adresa_cataloguei_este_corecta(self) -> None:
        from ui.model_window import ONLINE_MODELS_URL

        self.assertEqual(ONLINE_MODELS_URL, "https://ollama.com/search")

    def test_butoanul_de_modele_online_este_pachetat(self) -> None:
        from pathlib import Path

        radacina = Path(__file__).resolve().parent.parent
        sursa = (radacina / "ui" / "model_window.py").read_text(encoding="utf-8")

        self.assertTrue(
            CopyModelButtonTests._este_pachetat(sursa, "online_button"),
            "Butonul de modele online nu este vizibil.",
        )

    def test_butoanul_de_descarcare_este_pachetat(self) -> None:
        from pathlib import Path

        radacina = Path(__file__).resolve().parent.parent
        sursa = (radacina / "ui" / "model_window.py").read_text(encoding="utf-8")

        self.assertTrue(
            CopyModelButtonTests._este_pachetat(sursa, "download_button"),
            "Butonul de descărcare a modelului nu este vizibil.",
        )


class PullProgressTests(unittest.TestCase):
    """Progresul descărcării este agregat pe toate blob-urile."""

    def test_agregarea_tine_cont_de_fiecare_blob(self) -> None:
        """Serverul raportează progres per blob; suma dă procentul real."""
        total_pe_blob: dict[str, int] = {}
        descarcat_pe_blob: dict[str, int] = {}

        evenimente = [
            {"digest": "sha256:a", "total": 1000, "completed": 100},
            {"digest": "sha256:a", "total": 1000, "completed": 900},
            {"digest": "sha256:b", "total": 100, "completed": 50},
            {"digest": "sha256:b", "total": 100, "completed": 100},
        ]

        for eveniment in evenimente:
            digest = eveniment["digest"]
            total_pe_blob[digest] = eveniment["total"]
            descarcat_pe_blob[digest] = eveniment["completed"]

        descarcat = sum(descarcat_pe_blob.values())
        total = sum(total_pe_blob.values())

        # Ultimul blob (mic) nu trebuie să strivească procentul global.
        self.assertEqual(descarcat, 1000)
        self.assertEqual(total, 1100)
        self.assertEqual(int(descarcat * 100 / total), 90)

    def test_pull_model_rapoarta_eroare_cand_serverul_nu_exista(self) -> None:
        import os

        from services import ollama_api

        original = os.environ.get("OLLAMA_HOST")
        try:
            os.environ["OLLAMA_HOST"] = "127.0.0.1:9"
            succes, mesaj = ollama_api.pull_model("qwen3:8b", timeout=5.0)
            self.assertFalse(succes)
            self.assertIsNotNone(mesaj)
        finally:
            if original is None:
                os.environ.pop("OLLAMA_HOST", None)
            else:
                os.environ["OLLAMA_HOST"] = original


class ContextMenuTests(unittest.TestCase):
    """Meniul contextual trebuie legat pe widget-ul de text real."""

    def test_se_gaseste_widgetul_de_text_intern(self) -> None:
        from ui.context_menu import _widget_texte

        class Fals:
            _entry = "nu-sunt-un-entry"

        camp = Fals()
        # Fără un Entry intern, se folosește chiar obiectul dat.
        self.assertIs(_widget_texte(camp), camp)

    def test_meniul_contextual_e_legat_pe_campul_de_text(self) -> None:
        from pathlib import Path

        radacina = Path(__file__).resolve().parent.parent
        sursa = (radacina / "ui" / "context_menu.py").read_text(encoding="utf-8")
        self.assertIn('tinta.bind("<Button-3>"', sursa)
        self.assertIn('tinta.bind("<Button-2>"', sursa)
        self.assertIn("<<Paste>>", sursa)

    def test_meniul_contextual_e_aplicat_in_campurile_de_text(self) -> None:
        from pathlib import Path

        radacina = Path(__file__).resolve().parent.parent
        for fisier in ("ui/pull_model_dialog.py", "ui/model_list.py"):
            sursa = (radacina / fisier).read_text(encoding="utf-8")
            self.assertIn(
                "ataseaza_meniu_contextual",
                sursa,
                f"{fisier} nu are meniu contextual.",
            )


class LoadingStateTests(unittest.TestCase):
    """Starea de încărcare a modelului trebuie eliberată corect.

    Fereastra principală nu mai are o bară de progres; încărcarea se
    urmărește în fereastra „Modele Ollama". Aici rămâne doar starea,
    ca eticheta modelului să nu flutureze.
    """

    def test_fereastra_principala_nu_mai_are_bara_de_loading(self) -> None:
        from pathlib import Path

        radacina = Path(__file__).resolve().parent.parent
        sursa = (radacina / "ui" / "buttons_section.py").read_text(encoding="utf-8")
        self.assertNotIn("loading_model_frame", sursa)
        self.assertNotIn("loading_model_bar", sursa)

    def test_starea_se_elibereaza_la_serviciu_pretit(self) -> None:
        import inspect

        from core import state_manager

        sursa = inspect.getsource(state_manager.programeaza_actualizare_info_ollama)
        self.assertIn("finalizeaza_incarcare_model", sursa)

    def test_exista_o_plasa_de_siguranta_pentru_timpul_de_asteptare(self) -> None:
        import time

        from core.state_manager import MODEL_LOAD_BAR_TIMEOUT_SECONDS, _incarcare_expirata
        from core.app_state import AppState

        self.assertGreater(MODEL_LOAD_BAR_TIMEOUT_SECONDS, 0)

        stare = AppState()
        # Fără încărcare în curs, nu expiră.
        self.assertFalse(_incarcare_expirata(stare))

        # Referința de timp se calculează din ceasul curent: un moment
        # fixat (ex.: 1.0) ar face testul dependent de vechimea mașinii —
        # pe un runner proaspăt, `time.monotonic()` este încă mic.
        acum = time.monotonic()

        stare.model_incarcare_in_curs = True
        stare.model_incarcare_inceput = acum - MODEL_LOAD_BAR_TIMEOUT_SECONDS - 1
        self.assertTrue(_incarcare_expirata(stare))

        stare.model_incarcare_inceput = acum
        self.assertFalse(_incarcare_expirata(stare))

        stare.model_incarcare_inceput = 10**12
        self.assertFalse(_incarcare_expirata(stare))

    def test_marcheaza_si_finalizeaza_gestioneaza_doar_starea(self) -> None:
        from core.app_state import AppState
        from ui.main_window import finalizeaza_incarcare_model, marcheaza_incarcare_model

        stare = AppState()
        marcheaza_incarcare_model(stare)
        self.assertTrue(stare.model_incarcare_in_curs)
        self.assertGreater(stare.model_incarcare_inceput, 0)

        finalizeaza_incarcare_model(stare)
        self.assertFalse(stare.model_incarcare_in_curs)
        self.assertEqual(stare.model_incarcare_inceput, 0.0)


class ManifestLayoutTests(unittest.TestCase):
    """Manifestele se caută atât în formatul vechi, cât și în cel nou."""

    def test_se_cauta_in_ambele_formate(self) -> None:
        import tempfile
        from pathlib import Path

        from services.ollama_paths import _manifest_pentru

        with tempfile.TemporaryDirectory() as temporar:
            director = Path(temporar)

            vechi = director / "manifests" / "registry.ollama.ai" / "library" / "qwen3" / "8b"
            vechi.parent.mkdir(parents=True)
            vechi.write_text("x")

            nou = director / "manifests-v2" / "ollama.com" / "library" / "bonsai-2" / "9b"
            nou.parent.mkdir(parents=True)
            nou.write_text("x")

            self.assertIsNotNone(_manifest_pentru(director, "qwen3:8b"))
            self.assertIsNotNone(_manifest_pentru(director, "bonsai-2:9b"))
            self.assertIsNone(_manifest_pentru(director, "inexistent:1b"))


class DuplicateCleanupTests(unittest.TestCase):
    """Curățarea copiilor de manifest din formatul vechi."""

    def _structura_test(self, director) -> None:
        """Creează o structură cu un model duplicat și unul doar în v2."""
        blob = director / "blobs" / "sha256-abc"
        blob.parent.mkdir(parents=True)
        blob.write_text("{}")

        baza_noua = director / "manifests-v2" / "ollama.com" / "library"
        baza_veche = director / "manifests" / "registry.ollama.ai" / "library"

        # Model duplicat: în ambele formate.
        for baza in (baza_noua, baza_veche):
            (baza / "duplicat").mkdir(parents=True)
        (baza_noua / "duplicat" / "latest").symlink_to(blob)
        (baza_veche / "duplicat" / "latest").write_text("{}")

        # Model doar în formatul nou.
        (baza_noua / "doar-nou").mkdir(parents=True)
        (baza_noua / "doar-nou" / "latest").symlink_to(blob)

        # Model doar în formatul vechi.
        (baza_veche / "doar-vechi").mkdir(parents=True)
        (baza_veche / "doar-vechi" / "latest").write_text("{}")

    def test_detecteaza_doar_modelele_duplicate(self) -> None:
        import tempfile
        from pathlib import Path

        from services.ollama_paths import find_duplicate_manifests

        with tempfile.TemporaryDirectory() as temporar:
            director = Path(temporar)
            self._structura_test(director)

            duplicate = find_duplicate_manifests(director)
            self.assertEqual(len(duplicate), 1)
            self.assertEqual(duplicate[0]["model"], "duplicat")
            self.assertEqual(duplicate[0]["tag"], "latest")

    def test_curatarea_sterge_copiile_si_pastreaza_ambele_formate(self) -> None:
        import shutil
        import subprocess
        import tempfile
        from pathlib import Path

        from services.ollama_paths import (_script_curatare,
                                           find_duplicate_manifests)

        with tempfile.TemporaryDirectory() as temporar:
            director = Path(temporar)
            self._structura_test(director)

            duplicate = find_duplicate_manifests(director)
            rezultat = subprocess.run(
                ["/bin/sh", "-c", _script_curatare(director, duplicate)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(rezultat.returncode, 0, rezultat.stderr)

            # Copia veche a modelului duplicat a dispărut.
            baza_veche = director / "manifests" / "registry.ollama.ai" / "library"
            self.assertFalse((baza_veche / "duplicat" / "latest").exists())

            # Formatul nou rămâne neatins.
            baza_noua = director / "manifests-v2" / "ollama.com" / "library"
            self.assertTrue((baza_noua / "duplicat" / "latest").is_symlink())
            self.assertTrue((baza_noua / "doar-nou" / "latest").is_symlink())

            # Modelul existent doar în formatul vechi nu a fost atins.
            self.assertTrue((baza_veche / "doar-vechi" / "latest").exists())

            # Blob-urile nu sunt atinse.
            self.assertTrue((director / "blobs" / "sha256-abc").exists())

            self.assertEqual(find_duplicate_manifests(director), [])

    def test_curatarea_e_ignorata_cand_nu_sunt_duplicate(self) -> None:
        import tempfile
        from pathlib import Path

        from services.ollama_paths import cleanup_duplicate_manifests

        with tempfile.TemporaryDirectory() as temporar:
            director = Path(temporar)
            succes, mesaj = cleanup_duplicate_manifests(director)
            self.assertTrue(succes)
            self.assertIn("Nu există", str(mesaj))


class ServiceStatusTests(unittest.TestCase):
    """Starea serviciului se citeste intr-un singur apel `systemctl show`."""

    def test_se_uses_un_singur_apel_systemctl(self) -> None:
        import inspect

        from services import systemd_service

        sursa = inspect.getsource(systemd_service.obtine_detalii_serviciu)
        self.assertIn(
            "ActiveState,SubState,ActiveEnterTimestamp",
            systemd_service._PROPRIETATI_SERVICIU,
        )
        # Niciun apel separat pentru fiecare proprietate.
        self.assertNotIn('"is-active"', sursa)

    def test_parseaza_proprietatile_sistemd(self) -> None:
        from unittest.mock import patch

        from services import systemd_service

        iesire = (
            "ActiveState=active\n"
            "SubState=running\n"
            "ActiveEnterTimestamp=Sun 2026-11-23 10:00:00 UTC\n"
        )
        with patch.object(systemd_service, "ruleaza_si_citeste", return_value=iesire):
            detalii = systemd_service.obtine_detalii_serviciu()

        self.assertEqual(detalii["active_state"], "active")
        self.assertEqual(detalii["sub_state"], "running")
        self.assertEqual(detalii["active_timestamp"], "Sun 2026-11-23 10:00:00 UTC")

    def test_iesire_goala_da_valori_implicite(self) -> None:
        from unittest.mock import patch

        from services import systemd_service

        with patch.object(systemd_service, "ruleaza_si_citeste", return_value=""):
            detalii = systemd_service.obtine_detalii_serviciu()

        self.assertEqual(detalii["active_state"], "necunoscut")
        self.assertEqual(detalii["sub_state"], "necunoscut")
        self.assertEqual(detalii["active_timestamp"], "")


class RefreshIntervalTests(unittest.TestCase):
    """Panoul trebuie sa se reimprospateze chiar si cu actualizarea rapida off."""

    def test_intervalul_lent_este_folosit_cand_rapidul_e_oprit(self) -> None:
        from core import state_manager

        original = settings_config.AUTO_REFRESH_MS
        try:
            settings_config.AUTO_REFRESH_MS = None
            self.assertEqual(state_manager._interval_refresh(), state_manager.SLOW_REFRESH_MS)

            settings_config.AUTO_REFRESH_MS = 5000
            self.assertEqual(state_manager._interval_refresh(), 5000)
        finally:
            settings_config.AUTO_REFRESH_MS = original

    def test_timerul_e_Programat_in_tot_always(self) -> None:
        """Si cu rapidul oprit, se programeaza o verificare lenta."""
        import inspect

        from core import state_manager

        sursa = inspect.getsource(state_manager.programeaza_auto_refresh)
        self.assertIn("_interval_refresh()", sursa)
        # Nu mai exista conditia care sa nu programeze nimic.
        self.assertNotIn("if refresh_ms is not None:", sursa)


class SettingsWindowLayoutTests(unittest.TestCase):
    """Fereastra de setări trebuie să-și măsoare înălțimea după conținut.

    Înălțimea fixă de 580 px tăia butoanele „Anulează” și „Salvează”
    imediat ce lista de modele recente avea trei intrări.
    """

    def test_inaltime_se_calculeaza_dupa_conținut(self) -> None:
        from ui.settings_window import calculeaza_inaltime

        # Conținut scurt: fereastra rămâne mică.
        self.assertEqual(calculeaza_inaltime(380, 1080), 420)

        # Conținut cu trei modele recente: fereastra se întinde exact cât trebuie.
        self.assertEqual(calculeaza_inaltime(598, 1080), 598)

        # Ecran mic: nu se depășește ecranul.
        self.assertEqual(calculeaza_inaltime(900, 600), 520)

    def test_inaltime_nu_taie_butoanele(self) -> None:
        """Înălțimea aleasă trebuie să acopere conținutul măsurat."""
        from ui.settings_window import calculeaza_inaltime

        for necesar in (380, 480, 562, 598, 640, 700):
            for ecran in (1080, 900, 768):
                self.assertGreaterEqual(
                    calculeaza_inaltime(necesar, ecran),
                    min(necesar, ecran - 80),
                )

    def test_fereastra_nu_mai_are_inaltime_fixa(self) -> None:
        """Nu mai există o înălțime fixă, care ar tăia butoanele."""
        from pathlib import Path

        radacina = Path(__file__).resolve().parent.parent
        sursa = (radacina / "ui" / "settings_window.py").read_text(encoding="utf-8")
        self.assertNotIn("420x580", sursa)
        self.assertIn("calculeaza_inaltime", sursa)

    def test_dimensionarea_se_aplica_dupa_crearea_widgeturilor(self) -> None:
        """Măsurarea trebuie să urmeze crearea tuturor widget-urilor."""
        import ast
        from pathlib import Path

        radacina = Path(__file__).resolve().parent.parent
        sursa = (radacina / "ui" / "settings_window.py").read_text(encoding="utf-8")
        arbore = ast.parse(sursa)

        for nod in ast.walk(arbore):
            if not isinstance(nod, ast.FunctionDef) or nod.name != "deschide_setari":
                continue

            linii_pack: list[int] = []
            linie_dimensionare: int | None = None
            linie_deiconify: int | None = None

            for sub in ast.walk(nod):
                if not isinstance(sub, ast.Call):
                    continue
                if isinstance(sub.func, ast.Attribute):
                    nume = sub.func.attr
                elif isinstance(sub.func, ast.Name):
                    nume = sub.func.id
                else:
                    continue

                if nume == "pack":
                    linii_pack.append(sub.lineno)
                elif nume == "_ajusteaza_dimensiunile":
                    linie_dimensionare = sub.lineno
                elif nume == "deiconify":
                    linie_deiconify = sub.lineno

            self.assertTrue(linii_pack, "Nu s-au găsit widget-uri împachetate.")
            self.assertIsNotNone(linie_dimensionare, "Fereastra nu este dimensionată.")
            self.assertIsNotNone(linie_deiconify, "Fereastra nu este făcută vizibilă.")
            assert linie_dimensionare is not None
            assert linie_deiconify is not None

            self.assertLess(
                max(linii_pack),
                linie_dimensionare,
                "Dimensionarea trebuie să urmeze după crearea widget-urilor.",
            )
            self.assertLess(
                linie_dimensionare,
                linie_deiconify,
                "Fereastra poate fi făcută vizibilă doar după dimensionare.",
            )
            return

        self.fail("Funcția deschide_setari nu a fost găsită.")

    def test_fereastra_ramane_ascunsa_pana_la_final(self) -> None:
        """Fereastra nu trebuie să „crească” în pași sub ochii utilizatorului.

        Fiecare widget adăugat unei ferestre vizibile forțează o redesenare,
        așa că utilizatorul vedea o succesiune de stări intermediare. Fereastra
        e ascunsă (`withdraw`) cât timp e construită și apare o singură dată
        (`deiconify`), după dimensionare.
        """
        import ast
        from pathlib import Path

        radacina = Path(__file__).resolve().parent.parent
        sursa = (radacina / "ui" / "settings_window.py").read_text(encoding="utf-8")
        arbore = ast.parse(sursa)

        for nod in ast.walk(arbore):
            if not isinstance(nod, ast.FunctionDef) or nod.name != "deschide_setari":
                continue

            apeluri: list[str] = []
            for sub in ast.walk(nod):
                if not isinstance(sub, ast.Call):
                    continue
                if isinstance(sub.func, ast.Name):
                    apeluri.append(sub.func.id)
                elif isinstance(sub.func, ast.Attribute):
                    apeluri.append(sub.func.attr)

            self.assertIn("withdraw", apeluri, "Fereastra trebuie ascunsă în timpul construcției.")
            self.assertIn("deiconify", apeluri, "Fereastra trebuie făcută vizibilă la final.")
            return

        self.fail("Funcția deschide_setari nu a fost găsită.")

    def test_geometria_se_aplica_inainte_de_afisare(self) -> None:
        """Dimensiunile trebuie fixate înainte ca fereastra să devină vizibilă.

        Altfel fereastra apare cu lățimea implicită (350 px) și se extinde
        abia după — un salt vizibil.
        """
        import ast
        from pathlib import Path

        radacina = Path(__file__).resolve().parent.parent
        sursa = (radacina / "ui" / "settings_window.py").read_text(encoding="utf-8")
        arbore = ast.parse(sursa)

        for nod in ast.walk(arbore):
            if not isinstance(nod, ast.FunctionDef) or nod.name != "_ajusteaza_dimensiunile":
                continue

            apeluri = [
                sub.func.attr
                for sub in ast.walk(nod)
                if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute)
            ]
            self.assertIn("update_idletasks", apeluri)
            self.assertIn("geometry", apeluri)
            return

        self.fail("Funcția _ajusteaza_dimensiunile nu a fost găsită.")


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
