"""P6: lancia le suite di test una dopo l'altra, senza mai toccare dati veri.

Uso, dalla cartella del progetto e dentro la .venv:
    python tests/esegui_tutti.py              tutte le suite
    python tests/esegui_tutti.py engine db    solo quelle indicate

Ogni suite è una cartella di tests/ (runner, engine, db, api, services, sockets,
frontend, e2e, più quelle nuove in ordine alfabetico). Prima di partire il runner
si rifiuta se trova il file PRODUZIONE, se il database dei test non finisce con
_test o se la porta 5099 è occupata. Ogni suite ha un tempo massimo: se lo supera
viene fermata e segnata FAIL. I file protetti (.env.example, migrations/*.sql,
app/static/dev/*.json) si copiano fuori dal progetto all'inizio e, dopo ogni suite,
quelli cambiati si ripristinano. Alla fine il database dei test si svuota, le copie
e i file temporanei si cancellano e si stampa il riepilogo.

Esce con 0 se tutte le suite sono PASS, 1 se almeno una è FAIL, 2 se non parte.
"""

import hashlib
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

SUITES = ("runner", "engine", "db", "api", "services", "sockets", "frontend", "e2e")
PROTECTED = (".env.example", "migrations/*.sql", "app/static/dev/*.json")
TEST_PORT = 5099
SUITE_TIMEOUT = 240  # secondi per suite (29/09/2026: la suite frontend da sola ne dura circa 110)

# Conteggi nell'ultima riga di pytest, per esempio "3 failed, 655 passed in 12.34s"
COUNTS = re.compile(r"(\d+) (passed|failed|errors?|skipped|xfailed|xpassed)")


class RunnerError(Exception):
    """Il runner si ferma con questo messaggio: non è un test fallito, è un rifiuto."""


@dataclass
class SuiteResult:
    name: str
    passed: bool
    seconds: float
    detail: str
    output: str = ""
    passed_tests: int = 0
    restored: list = field(default_factory=list)


# --- Controlli prima di partire ---


def check_not_production(base_dir):
    if (base_dir / "PRODUZIONE").exists():
        raise RunnerError("trovato il file PRODUZIONE: questa è un'installazione vera, i test non partono.")


def check_test_database(environ=None):
    """Configurazione dei test; si rifiuta se il database non finisce con _test."""
    from config import ConfigError, load_config

    try:
        config = load_config("testing", environ=environ)
    except ConfigError as exc:
        raise RunnerError(str(exc)) from None
    if not config.DB_NAME.endswith("_test"):
        raise RunnerError(f'il database dei test "{config.DB_NAME}" non finisce con "_test".')
    return config


def check_port_free(port, host="127.0.0.1"):
    busy = RunnerError(
        f"la porta {port} è occupata: forse è acceso un server (il tuo o uno dei test "
        "rimasto aperto). Chiudilo e rilancia."
    )
    with socket.socket() as probe:
        probe.settimeout(1)
        if probe.connect_ex((host, port)) == 0:
            raise busy
    with socket.socket() as probe:
        try:
            probe.bind((host, port))
        except OSError:
            raise busy from None


def select_suites(base_dir, names=None):
    """Le suite da eseguire, nell'ordine: prima quelle di SUITES, poi le altre in ordine alfabetico.

    Una suite è una cartella di tests/ con almeno un file test_*.py.
    """
    tests_dir = base_dir / "tests"
    found = [
        d.name for d in tests_dir.iterdir()
        if d.is_dir() and not d.name.startswith(("_", ".")) and any(d.rglob("test_*.py"))
    ]
    ordered = [s for s in SUITES if s in found] + sorted(s for s in found if s not in SUITES)
    if not ordered:
        raise RunnerError(f"nessuna suite trovata in {tests_dir}.")
    if not names:
        return ordered
    unknown = [n for n in names if n not in ordered]
    if unknown:
        raise RunnerError(
            f"suite sconosciuta: {', '.join(unknown)}. Suite disponibili: {', '.join(ordered)}."
        )
    return [s for s in ordered if s in names]


# --- File protetti ---


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ProtectedFiles:
    """Copia dei file protetti fatta all'inizio, fuori dal progetto, con il loro hash."""

    def __init__(self, base_dir, backup_dir, patterns=PROTECTED):
        self.base_dir = base_dir
        self.backup_dir = backup_dir
        self.patterns = patterns
        self.hashes = {}
        for path in self._current():
            rel = path.relative_to(base_dir).as_posix()
            copy = backup_dir / rel
            copy.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, copy)
            self.hashes[rel] = _sha256(path)

    def _current(self):
        found = set()
        for pattern in self.patterns:
            found.update(p for p in self.base_dir.glob(pattern) if p.is_file())
        return sorted(found)

    def restore_changed(self):
        """Ripristina i file protetti modificati o cancellati; restituisce cosa è successo.

        Un file nuovo che corrisponde a un modello protetto non si cancella (potrebbe
        essere lavoro vero, per esempio una migrazione in scrittura): si segnala soltanto.
        """
        notes = []
        for rel, digest in self.hashes.items():
            path = self.base_dir / rel
            if path.is_file() and _sha256(path) == digest:
                continue
            what = "modificato" if path.exists() else "cancellato"
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.backup_dir / rel, path)
            if _sha256(path) != digest:
                raise RunnerError(
                    f"non riesco a ripristinare {rel}: la copia buona è in {self.backup_dir / rel}."
                )
            notes.append(f"{rel} {what} durante i test: ripristinato")
        for path in self._current():
            rel = path.relative_to(self.base_dir).as_posix()
            if rel not in self.hashes:
                notes.append(f"{rel} creato durante i test: non cancellato, controllalo")
        return notes


# --- Esecuzione di una suite ---


def _process_group():
    if os.name == "nt":
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    return {"start_new_session": True}


def _kill_tree(process):
    """Ferma la suite e i processi che ha avviato (per esempio un server di test)."""
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)], capture_output=True, check=False)
    else:
        import signal

        os.killpg(process.pid, signal.SIGKILL)


def run_suite(base_dir, name, timeout, temp_dir):
    temp_dir.mkdir(parents=True, exist_ok=True)  # pytest crea --basetemp, ma non la cartella che lo contiene
    command = [
        sys.executable, "-m", "pytest", f"tests/{name}", "-q",
        "-p", "no:cacheprovider", f"--basetemp={temp_dir / name}",
    ]
    env = {**os.environ, "APP_ENV": "testing", "PYTHONIOENCODING": "utf-8"}
    start = time.monotonic()
    process = subprocess.Popen(
        command, cwd=base_dir, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **_process_group(),
    )
    timed_out = False
    try:
        raw, _ = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        _kill_tree(process)
        try:
            raw, _ = process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            raw = b""
    except BaseException:
        _kill_tree(process)
        raise
    seconds = time.monotonic() - start
    output = raw.decode("utf-8", errors="replace")

    counts = {}
    for number, kind in COUNTS.findall(output.strip().splitlines()[-1] if output.strip() else ""):
        counts[kind.rstrip("s") if kind.startswith("error") else kind] = int(number)
    passed_tests = counts.get("passed", 0)

    if timed_out:
        return SuiteResult(name, False, seconds, f"tempo massimo superato ({timeout} s): suite fermata",
                           output, passed_tests)
    if process.returncode == 5:
        return SuiteResult(name, False, seconds, "nessun test trovato", output)
    parts = [f"{passed_tests} PASS"]
    parts += [f"{counts[k]} {label}" for k, label in
              (("failed", "falliti"), ("error", "errori"), ("skipped", "saltati")) if counts.get(k)]
    if process.returncode not in (0, 1) and not counts:
        parts = [f"pytest si è fermato (codice {process.returncode})"]
    return SuiteResult(name, process.returncode == 0, seconds, ", ".join(parts), output, passed_tests)


# --- Database dei test ---


def empty_test_database(config):
    """Cancella tutte le tabelle del database dei test; restituisce una riga per il riepilogo."""
    import pymysql
    import sqlalchemy as sa

    engine = sa.create_engine(config.SQLALCHEMY_DATABASE_URI, connect_args={"connect_timeout": 5})
    try:
        with engine.connect() as conn:
            current = conn.execute(sa.text("SELECT DATABASE()")).scalar()
            if not current or not current.endswith("_test"):
                return f"non svuotato: il database collegato ({current}) non è di test"
            tables = conn.execute(sa.text(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = DATABASE()"
            )).scalars().all()
            conn.execute(sa.text("SET FOREIGN_KEY_CHECKS = 0"))
            for table in tables:
                conn.execute(sa.text(f"DROP TABLE `{table}`"))
            conn.execute(sa.text("SET FOREIGN_KEY_CHECKS = 1"))
    except (sa.exc.SQLAlchemyError, pymysql.MySQLError) as exc:
        orig = getattr(exc, "orig", exc)
        code = orig.args[0] if getattr(orig, "args", None) else "?"
        return f"non svuotato: MySQL non raggiungibile (errore MySQL {code})"
    finally:
        engine.dispose()
    return f"svuotato ({len(tables)} tabelle cancellate)"


# --- Runner ---


def run(base_dir=BASE_DIR, names=None, *, port=TEST_PORT, timeout=SUITE_TIMEOUT, environ=None,
        empty_db=empty_test_database, temp_root=None, out=print):
    try:
        check_not_production(base_dir)
        config = check_test_database(environ)
        suites = select_suites(base_dir, names)
        check_port_free(port)
    except RunnerError as exc:
        out(f"Test non avviati: {exc}")
        return 2

    work_dir = Path(tempfile.mkdtemp(prefix="cinquecento-test-", dir=temp_root))
    keep_work_dir = False
    protected = None
    results = []
    started = time.monotonic()
    try:
        protected = ProtectedFiles(base_dir, work_dir / "protetti")
        out(f"File protetti copiati fuori dal progetto: {len(protected.hashes)}")
        for name in suites:
            out(f"\n=== Suite {name} ===")
            result = run_suite(base_dir, name, timeout, work_dir / "pytest")
            results.append(result)
            lines = result.output.strip().splitlines()
            out(result.output.rstrip() if not result.passed else (lines[-1] if lines else ""))
            out(f"{'PASS' if result.passed else 'FAIL'} {name}: {result.detail} ({result.seconds:.1f} s)")
            result.restored = protected.restore_changed()
            for note in result.restored:
                out(f"ATTENZIONE: {note}")
        db_note = empty_db(config)
    except RunnerError as exc:
        keep_work_dir = True
        out(f"\nRunner fermato: {exc}")
        return 1
    finally:
        if protected is not None and not keep_work_dir:
            try:
                protected.restore_changed()
            except RunnerError as exc:
                keep_work_dir = True
                out(f"\nRunner fermato: {exc}")
        if not keep_work_dir:
            shutil.rmtree(work_dir, ignore_errors=True)

    out(summary(results, db_note, time.monotonic() - started))
    return 0 if all(r.passed for r in results) else 1


def summary(results, db_note, seconds):
    width = max(len(r.name) for r in results)
    lines = ["", "=== Riepilogo ==="]
    for r in results:
        lines.append(f"  {'PASS' if r.passed else 'FAIL'}  {r.name:<{width}}  {r.seconds:6.1f} s  {r.detail}")
    restored = [f"{r.name}: {note}" for r in results for note in r.restored]
    failed = [r.name for r in results if not r.passed]
    lines += [
        (f"Controlli PASS: {sum(r.passed_tests for r in results)} in {len(results)} suite, "
         f"durata totale {seconds:.1f} s"),
        "File protetti: " + ("tutti intatti" if not restored else "; ".join(restored)),
        f"Database dei test: {db_note}",
        "TUTTO PASS" if not failed else f"FAIL: {', '.join(failed)}",
    ]
    return "\n".join(lines)


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    args = sys.argv[1:] if argv is None else argv
    if any(a.startswith("-") for a in args):
        print("Uso: python tests/esegui_tutti.py [suite ...]   (senza nomi: tutte le suite)")
        return 2
    return run(names=args)


if __name__ == "__main__":
    sys.exit(main())
