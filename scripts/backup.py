"""Backup del database del file .env: python scripts/backup.py

Salva una copia del database (DB_NAME) in backups/, compressa e con data e ora nel
nome (per esempio cinquecento_dev_2026-09-28_213000.sql.gz), poi cancella i backup
più vecchi di BACKUP_RETENTION_DAYS giorni (config.py, provvisorio: D10). Si
cancellano solo i file con questa forma del nome, mai altri file della cartella; l'età
si legge dal nome, non dalla data del file.
La copia la fa mysqldump, il programma di MySQL: si cerca nel PATH e poi nella
cartella dove lo installa MySQL 8.0 su Windows.
La password non passa mai sulla riga di comando (la vedrebbero gli altri programmi
del PC) e non si stampa: sta in un file di opzioni temporaneo, cancellato alla fine.
Un backup non riuscito non lascia file: la copia si scrive con il nome
".parziale" e prende il nome vero solo alla fine.
Per ricaricare un backup: python scripts/ripristina.py <file> <database>.
Le funzioni sono importabili (i test le usano su cinquecento_test).
"""

import gzip
import os
import re
import shutil
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

WINDOWS_BIN = Path(r"C:\Program Files\MySQL\MySQL Server 8.0\bin")
DATABASE_NAME = re.compile(r"^[A-Za-z0-9_]{1,64}$")
BACKUP_SUFFIX = ".sql.gz"
BACKUP_NAME = re.compile(r"^(?P<database>[A-Za-z0-9_]+)_(?P<when>\d{4}-\d{2}-\d{2}_\d{6})\.sql\.gz$")
TIME_FORMAT = "%Y-%m-%d_%H%M%S"
DUMP_OPTIONS = (
    "--single-transaction",       # copia coerente senza bloccare le tabelle (InnoDB)
    "--no-tablespaces",           # senza, mysqldump chiede il permesso PROCESS, che l'utente del progetto non ha
    "--set-gtid-purged=OFF",      # il backup si può ricaricare anche in un altro database
    "--skip-dump-date",           # due backup degli stessi dati sono identici
)


class BackupError(Exception):
    """Backup o ripristino non riuscito: il messaggio dice cosa fare."""


def check_database_name(name):
    if not isinstance(name, str) or not DATABASE_NAME.fullmatch(name):
        raise BackupError(f'Nome del database non valido: "{name}" (solo lettere, numeri e _).')


def find_program(name):
    """Percorso di un programma di MySQL (mysqldump, mysql): prima il PATH, poi la cartella di MySQL 8.0."""
    found = shutil.which(name)
    if found:
        return found
    candidate = WINDOWS_BIN / f"{name}.exe"
    if candidate.is_file():
        return str(candidate)
    raise BackupError(
        f"Non trovo {name}: installa MySQL 8.0 oppure aggiungi al PATH la sua cartella bin."
    )


@contextmanager
def options_file(url):
    """File di opzioni temporaneo con utente, password, host e porta; cancellato alla fine."""
    lines = [
        "[client]",
        f"user={_quote(url.username or '')}",
        f"host={_quote(url.host or '127.0.0.1')}",
        f"port={url.port or 3306}",
        "default-character-set=utf8mb4",
    ]
    if url.password:
        lines.append(f"password={_quote(url.password)}")
    fd, path = tempfile.mkstemp(prefix="cinquecento-", suffix=".cnf")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            out.write("\n".join(lines) + "\n")
        yield path
    finally:
        Path(path).unlink(missing_ok=True)


def _quote(value):
    # Nei file di opzioni di MySQL un valore tra virgolette accetta \\ e \" come caratteri.
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def program_errors(stream):
    """Messaggio d'errore di mysqldump o mysql, letto dal file temporaneo."""
    stream.seek(0)
    text = stream.read().decode("utf-8", errors="replace").strip()
    return text or "nessun dettaglio"


def backup(url, backup_dir, now=None):
    """Salva il database di `url` in `backup_dir` e restituisce il percorso del file."""
    database = url.database
    check_database_name(database)
    backup_dir = Path(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    when = (now or datetime.now().astimezone()).strftime(TIME_FORMAT)
    target = backup_dir / f"{database}_{when}{BACKUP_SUFFIX}"
    if target.exists():
        raise BackupError(f"Esiste già {target.name}: riprova tra un secondo.")
    partial = target.with_name(target.name + ".parziale")
    program = find_program("mysqldump")

    with options_file(url) as options, tempfile.TemporaryFile() as errors:
        command = [program, f"--defaults-extra-file={options}", *DUMP_OPTIONS, database]
        try:
            with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=errors) as process, \
                    gzip.open(partial, "wb") as out:
                shutil.copyfileobj(process.stdout, out)
                code = process.wait()
        except OSError as exc:
            partial.unlink(missing_ok=True)
            raise BackupError(f"Non riesco a scrivere il backup in {backup_dir}: {exc.strerror}.") from exc
        if code != 0:
            partial.unlink(missing_ok=True)
            raise BackupError(f"mysqldump non è riuscito: {program_errors(errors)}")
    partial.replace(target)
    return target


def remove_old_backups(backup_dir, days, now=None):
    """Cancella i backup più vecchi di `days` giorni e restituisce l'elenco dei file cancellati."""
    limit = (now or datetime.now().astimezone()) - timedelta(days=days)
    removed = []
    for path in sorted(Path(backup_dir).glob(f"*{BACKUP_SUFFIX}")):
        match = BACKUP_NAME.fullmatch(path.name)
        if not match or not path.is_file():
            continue
        try:
            when = datetime.strptime(match["when"], TIME_FORMAT).astimezone()  # ora locale, come nel nome
        except ValueError:
            continue
        if when < limit:
            path.unlink()
            removed.append(path)
    return removed


def _shown(path):
    try:
        return str(Path(path).relative_to(BASE_DIR))
    except ValueError:
        return str(path)


def main(argv=None):
    from config import ConfigError, load_config

    args = sys.argv[1:] if argv is None else argv
    if args:
        print("Uso: python scripts/backup.py (senza argomenti: usa il database del .env)", file=sys.stderr)
        return 2
    try:
        config = load_config()
        path = backup(config.SQLALCHEMY_DATABASE_URI, config.BACKUP_DIR)
        removed = remove_old_backups(config.BACKUP_DIR, config.BACKUP_RETENTION_DAYS)
    except (ConfigError, BackupError) as exc:
        print(f"Backup non riuscito: {exc}", file=sys.stderr)
        return 1
    size_kb = max(1, round(path.stat().st_size / 1024))
    print(f"Backup salvato: {_shown(path)} ({size_kb} KB)")
    if removed:
        print(f"Cancellati {len(removed)} backup più vecchi di {config.BACKUP_RETENTION_DAYS} giorni.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
