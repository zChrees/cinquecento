"""P6: il runner dei test si rifiuta quando deve, ferma le suite troppo lunghe,
ripristina i file protetti e stampa un riepilogo giusto.

Ogni prova lancia il runner vero su un progetto finto, creato in una cartella
temporanea con le sue suite: il progetto vero e MySQL non si toccano.
"""

import importlib.util
import os
import shutil
import socket
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parents[2]


def _load_runner():
    spec = importlib.util.spec_from_file_location("esegui_tutti", BASE_DIR / "tests" / "esegui_tutti.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runner = _load_runner()

# Righe da mettere in cima ai test finti: ROOT è la cartella del progetto finto.
HEADER = "from pathlib import Path\nROOT = Path(__file__).resolve().parents[2]\n\n"

PROTECTED_CONTENT = {
    ".env.example": "SECRET_KEY=\nDB_NAME=cinquecento_dev\n",
    "migrations/001_init.sql": "CREATE TABLE prova (id INT);\n",
    "app/static/dev/vista.json": '{"version": 1}\n',
}


def make_project(root, suites):
    """Progetto finto: i file protetti e una cartella tests/<nome> per ogni suite."""
    for rel, text in PROTECTED_CONTENT.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode())
    for name, source in suites.items():
        suite_dir = root / "tests" / name
        suite_dir.mkdir(parents=True)
        (suite_dir / "test_finto.py").write_text(HEADER + textwrap.dedent(source), encoding="utf-8")
    return root


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def project(tmp_path):
    return tmp_path / "progetto"


@pytest.fixture
def launch(tmp_path):
    """Lancia il runner su un progetto finto e raccoglie quello che stampa."""
    temp_root = tmp_path / "temporanei"
    temp_root.mkdir()

    def _launch(base_dir, names=None, **options):
        calls = []
        lines = []
        options.setdefault("environ", {})
        options.setdefault("port", free_port())

        def empty_db(config):
            calls.append(config.DB_NAME)
            return "svuotato (finto)"

        code = runner.run(base_dir, names, empty_db=empty_db, temp_root=temp_root,
                          out=lines.append, **options)
        return code, "\n".join(lines), calls

    _launch.temp_root = temp_root
    return _launch


PASSING = """
def test_uno():
    assert True
"""


# --- Rifiuti prima di partire ---


def test_produzione_presente_rifiuta(project, launch):
    make_project(project, {"alfa": "def test_scrive():\n    (ROOT / 'eseguito').write_text('si')\n"})
    (project / "PRODUZIONE").write_text("")
    code, output, calls = launch(project)
    assert code == 2
    assert "PRODUZIONE" in output
    assert not (project / "eseguito").exists()
    assert calls == []


def test_database_non_di_test_rifiuta(project, launch):
    make_project(project, {"alfa": PASSING})
    code, output, calls = launch(project, environ={"DB_NAME_TEST": "cinquecento_dev"})
    assert code == 2
    assert "_test" in output
    assert calls == []


def test_database_di_test_accettato():
    assert runner.check_test_database({}).DB_NAME == "cinquecento_test"


def test_porta_occupata_ferma(project, launch):
    make_project(project, {"alfa": "def test_scrive():\n    (ROOT / 'eseguito').write_text('si')\n"})
    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        server.listen()
        port = server.getsockname()[1]
        code, output, calls = launch(project, port=port)
    assert code == 2
    assert f"porta {port} è occupata" in output
    assert not (project / "eseguito").exists()
    assert calls == []


def test_suite_sconosciuta_rifiuta(project, launch):
    make_project(project, {"alfa": PASSING})
    code, output, _ = launch(project, ["zeta"])
    assert code == 2
    assert "suite sconosciuta: zeta" in output
    assert "alfa" in output


def test_ordine_e_scelta_delle_suite(project):
    make_project(project, {name: PASSING for name in ("zeta", "e2e", "engine", "runner", "db")})
    (project / "tests" / "vuota").mkdir()
    (project / "tests" / "__pycache__").mkdir()
    assert runner.select_suites(project) == ["runner", "engine", "db", "e2e", "zeta"]
    assert runner.select_suites(project, ["db", "engine"]) == ["engine", "db"]


# --- Durante le suite ---


def test_suite_troppo_lunga_fermata_e_fail(project, launch):
    make_project(project, {
        "alfa": "import time\n\ndef test_lento():\n    time.sleep(600)\n",
        "beta": PASSING,
    })
    start = time.monotonic()
    code, output, _ = launch(project, timeout=3)
    assert time.monotonic() - start < 60
    assert code == 1
    assert "FAIL  alfa" in output
    assert "tempo massimo superato (3 s)" in output
    assert "PASS  beta" in output  # il runner prosegue con la suite dopo


def test_file_protetti_ripristinati_dopo_ogni_suite(project, launch):
    make_project(project, {
        "alfa": """
            def test_rovina_i_file_protetti():
                (ROOT / ".env.example").write_text("rotto")
                (ROOT / "migrations" / "001_init.sql").unlink()
                (ROOT / "app" / "static" / "dev" / "vista.json").write_text("{}")
                (ROOT / "migrations" / "002_nuova.sql").write_text("-- nuova")
        """,
        "beta": """
            def test_trova_i_file_originali():
                assert (ROOT / ".env.example").read_text() == "SECRET_KEY=\\nDB_NAME=cinquecento_dev\\n"
                assert (ROOT / "migrations" / "001_init.sql").exists()
                assert (ROOT / "app" / "static" / "dev" / "vista.json").read_text() == '{"version": 1}\\n'
        """,
    })
    code, output, _ = launch(project)
    assert code == 0, output
    for rel, text in PROTECTED_CONTENT.items():
        assert (project / rel).read_bytes() == text.encode()
    assert ".env.example modificato durante i test: ripristinato" in output
    assert "migrations/001_init.sql cancellato durante i test: ripristinato" in output
    assert "app/static/dev/vista.json modificato durante i test: ripristinato" in output
    # un file nuovo si segnala ma non si cancella: potrebbe essere lavoro vero
    assert "migrations/002_nuova.sql creato durante i test: non cancellato" in output
    assert (project / "migrations" / "002_nuova.sql").exists()


# --- Alla fine ---


def test_riepilogo_corretto(project, launch):
    make_project(project, {
        "alfa": PASSING + "\n\ndef test_due():\n    assert True\n",
        "beta": PASSING + "\n\ndef test_sbagliato():\n    assert 1 == 2\n",
    })
    code, output, calls = launch(project)
    assert code == 1
    summary = output.split("=== Riepilogo ===")[1]
    assert "PASS  alfa" in summary
    assert "2 PASS" in summary
    assert "FAIL  beta" in summary
    assert "1 PASS, 1 falliti" in summary
    assert "Controlli PASS: 3 in 2 suite" in summary
    assert "File protetti: tutti intatti" in summary
    assert "Database dei test: svuotato (finto)" in summary
    assert summary.rstrip().endswith("FAIL: beta")
    assert "assert 1 == 2" in output  # di una suite FAIL si vede l'uscita di pytest
    assert calls == ["cinquecento_test"]


def test_tutto_pass_e_temporanei_cancellati(project, launch):
    make_project(project, {"alfa": "def test_usa_tmp(tmp_path):\n    (tmp_path / 'f.txt').write_text('x')\n"})
    code, output, _ = launch(project, ["alfa"])
    assert code == 0, output
    assert output.rstrip().endswith("TUTTO PASS")
    assert list(launch.temp_root.iterdir()) == []
    assert not (project / ".pytest_cache").exists()


def test_database_non_raggiungibile_segnalato():
    config = runner.check_test_database({"DB_PORT": str(free_port())})
    note = runner.empty_test_database(config)
    assert note.startswith("non svuotato: MySQL non raggiungibile")


# --- conftest.py: gli stessi rifiuti valgono lanciando pytest a mano ---


@pytest.mark.parametrize("case", ["produzione", "database"])
def test_conftest_rifiuta_anche_senza_runner(project, case):
    make_project(project, {"alfa": PASSING})
    shutil.copy2(BASE_DIR / "tests" / "conftest.py", project / "tests" / "conftest.py")
    shutil.copy2(BASE_DIR / "config.py", project / "config.py")
    env = {k: v for k, v in os.environ.items() if not k.startswith("DB_")}
    if case == "produzione":
        (project / "PRODUZIONE").write_text("")
    else:
        env["DB_NAME_TEST"] = "cinquecento_dev"
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/alfa", "-q", "-p", "no:cacheprovider"],
        cwd=project, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace",
        check=False,
    )
    assert result.returncode == 2, result.stdout
    assert ("PRODUZIONE" if case == "produzione" else "_test") in result.stdout + result.stderr
