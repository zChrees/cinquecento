"""Ripristino di un backup: python scripts/ripristina.py <file> <database>

Ricarica nel database indicato un backup fatto da backup.py (file .sql.gz). Ogni
tabella del backup sostituisce quella con lo stesso nome, con tutti i suoi dati; le
tabelle che nel backup non ci sono restano come sono.
Se il database non è di test (il nome non finisce con _test) chiede di scriverne il
nome per confermare: così un errore di battitura non sovrascrive dati veri.
Prima di toccare il database controlla che il file sia intero e sia un backup di
MySQL; il caricamento lo fa mysql, il programma di MySQL, con l'utente del file .env,
che deve poter scrivere in quel database. La password non si stampa mai.
Le funzioni sono importabili (i test le usano su cinquecento_test).
"""

import contextlib
import gzip
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

# scripts/backup.py, importabile dopo aver aggiunto la cartella al percorso
import backup
from backup import (
    BackupError,
    check_database_name,
    find_program,
    options_file,
    program_errors,
)

TEST_SUFFIX = "_test"
DUMP_HEADER = b"-- MySQL dump"
CHUNK = 1 << 16


def check_backup_file(backup_file):
    """Il file esiste, è un .sql.gz intero e comincia come un backup di mysqldump."""
    path = Path(backup_file)
    if not path.is_file():
        raise BackupError(f"Non trovo il file {path}.")
    if not path.name.endswith(backup.BACKUP_SUFFIX):
        raise BackupError(f"{path.name} non è un backup: serve un file {backup.BACKUP_SUFFIX} fatto da backup.py.")
    try:
        with gzip.open(path, "rb") as source:
            header = source.read(len(DUMP_HEADER))
            while source.read(CHUNK):
                pass
    except (OSError, EOFError, zlib.error) as exc:
        raise BackupError(f"Il file {path.name} è rovinato o incompleto: non lo carico.") from exc
    if header != DUMP_HEADER:
        raise BackupError(f"{path.name} non è un backup di MySQL: non lo carico.")
    return path


def restore(url, backup_file, database):
    """Carica `backup_file` nel database `database` con l'utente di `url`."""
    check_database_name(database)
    path = check_backup_file(backup_file)
    program = find_program("mysql")

    with options_file(url) as options, tempfile.TemporaryFile() as errors:
        command = [program, f"--defaults-extra-file={options}", database]
        try:
            with gzip.open(path, "rb") as source, subprocess.Popen(
                command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=errors
            ) as process:
                _feed(source, process.stdin)
                code = process.wait()
        except OSError as exc:
            raise BackupError(f"Non riesco ad avviare mysql: {exc.strerror}.") from exc
        if code != 0:
            raise BackupError(f"mysql si è fermato: {program_errors(errors)}")


def _feed(source, sink):
    # Se mysql si ferma per un errore, scrivergli ancora dà OSError: il motivo lo dice mysql.
    try:
        while chunk := source.read(CHUNK):
            sink.write(chunk)
    except OSError:
        pass
    finally:
        with contextlib.suppress(OSError):
            sink.close()


def main(argv=None, ask=input):
    from config import ConfigError, load_config

    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2:
        print("Uso: python scripts/ripristina.py <file .sql.gz> <database>", file=sys.stderr)
        return 2
    backup_file, database = args
    try:
        check_database_name(database)
        path = check_backup_file(backup_file)
        if not database.endswith(TEST_SUFFIX):
            print(f'Attenzione: "{database}" non è un database di test. Le sue tabelle '
                  f"verranno sostituite con quelle del backup {path.name}.")
            try:
                answer = ask(f"Per confermare scrivi il nome del database ({database}): ")
            except (EOFError, KeyboardInterrupt):
                answer = ""
            if answer.strip() != database:
                print("Ripristino annullato: il database non è stato toccato.")
                return 1
        config = load_config()
        restore(config.SQLALCHEMY_DATABASE_URI, path, database)
    except (ConfigError, BackupError) as exc:
        print(f"Ripristino non riuscito: {exc}", file=sys.stderr)
        return 1
    print(f"Ripristino completato: {path.name} caricato in {database}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
