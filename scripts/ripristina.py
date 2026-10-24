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

Cosa contiene:
    check_backup_file("backups/x.sql.gz")   controlla il file; restituisce il percorso
    restore(url, file, "cinquecento_test")  carica il backup nel database
    _feed(source, sink)                     passa il backup a mysql a pezzi
    main()                                  il programma: python scripts/ripristina.py <file> <database>

DA DOVE ARRIVANO I DATI: il file e il nome del database dalla riga di comando;
utente e password di MySQL da load_config (config.py e .env); i controlli comuni
(BackupError, check_database_name, find_program, options_file, program_errors) da
scripts/backup.py.
"""

import gzip
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

# SCRIPTS_DIR: la cartella di questo file. La si aggiunge ai percorsi di Python, così
# "import backup" trova scripts/backup.py anche lanciando lo script.
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
DUMP_HEADER = b"-- MySQL dump"  # b"...": byte, non testo (come un array di char in C)
CHUNK = 1 << 16  # 65536 byte (64 KB) alla volta: 1 spostato di 16 bit a sinistra, 2 alla 16


def check_backup_file(backup_file):
    """Il file esiste, è un .sql.gz intero e comincia come un backup di mysqldump.

    In parole semplici:
        check_backup_file(backup_file)
        backup_file: il percorso scritto sulla riga di comando, per esempio
                     "backups/cinquecento_dev_2026-09-28_213000.sql.gz"
        Lo legge tutto, decomprimendolo, prima di toccare il database: un file
        tagliato o rovinato si rifiuta subito con BackupError, e così anche un file
        che non comincia con "-- MySQL dump".

        Restituisce: il percorso come Path.
    """
    path = Path(backup_file)
    if not path.is_file():
        raise BackupError(f"Non trovo il file {path}.")
    if not path.name.endswith(backup.BACKUP_SUFFIX):
        raise BackupError(f"{path.name} non è un backup: serve un file {backup.BACKUP_SUFFIX} fatto da backup.py.")
    try:
        # with: il file si chiude da solo alla fine del blocco
        with gzip.open(path, "rb") as source:
            header = source.read(len(DUMP_HEADER))
            # Legge il resto a pezzi, solo per controllare che sia intero; un pezzo
            # vuoto vuol dire fine del file
            chunk = source.read(CHUNK)
            while chunk:
                chunk = source.read(CHUNK)
    except (OSError, EOFError, zlib.error) as exc:
        raise BackupError(f"Il file {path.name} è rovinato o incompleto: non lo carico.") from exc
    if header != DUMP_HEADER:
        raise BackupError(f"{path.name} non è un backup di MySQL: non lo carico.")
    return path


def restore(url, backup_file, database):
    """Carica `backup_file` nel database `database` con l'utente di `url`.

    In parole semplici:
        restore(url, backup_file, database)
        url:         l'indirizzo del database del .env (serve per utente, password,
                     host e porta; il nome del database è quello di `database`)
        backup_file: il file .sql.gz, controllato con check_backup_file
        database:    il database in cui caricarlo, per esempio "cinquecento_test"
        Avvia mysql e gli passa il backup decompresso, a pezzi. Se mysql si ferma
        con un errore lancia BackupError con il suo messaggio.
    """
    check_database_name(database)
    path = check_backup_file(backup_file)
    program = find_program("mysql")

    # Un with con due oggetti separati da una virgola è come due with uno dentro
    # l'altro (lo chiede ruff, SIM117): si aprono in ordine e si chiudono al contrario.
    # errors: un file temporaneo per i messaggi d'errore di mysql
    with options_file(url) as options, tempfile.TemporaryFile() as errors:
        command = [program, f"--defaults-extra-file={options}", database]
        try:
            # Popen avvia mysql; stdin=PIPE: si può scrivergli il backup
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
    """Passa a mysql il backup decompresso, a pezzi di CHUNK byte.

    In parole semplici:
        _feed(source, sink)
        source: il backup aperto con gzip (si legge già decompresso)
        sink:   l'ingresso di mysql (process.stdin)
        Alla fine chiude sink, così mysql sa che il backup è finito.
    """
    # Se mysql si ferma per un errore, scrivergli ancora dà OSError: il motivo lo dice mysql.
    try:
        chunk = source.read(CHUNK)
        while chunk:
            sink.write(chunk)
            chunk = source.read(CHUNK)
    except OSError:
        pass
    finally:
        # Anche la chiusura può dare OSError (mysql già fermo): si ignora
        try:
            sink.close()
        except OSError:
            pass


def main(argv=None, ask=input):
    """Il programma: python scripts/ripristina.py <file .sql.gz> <database>.

    In parole semplici:
        main(argv, ask)
        argv: facoltativo, gli argomenti al posto di quelli della riga di comando
              (lo passano i test); se manca: sys.argv[1:].
        ask:  facoltativo, la funzione che fa la domanda di conferma (se manca:
              input, che legge dalla tastiera; i test passano una funzione che
              risponde da sola).
        Con un database che non finisce con _test chiede di scriverne il nome: una
        risposta diversa (o Ctrl+C) annulla senza toccare niente.
        Restituisce il codice di uscita: 0 tutto bene, 1 errore o annullato,
        2 argomenti sbagliati.
    """
    # Import qui dentro: config.py (che legge il .env) si carica quando parte il
    # programma, non quando un test importa questo file
    from config import ConfigError, load_config

    args = argv
    if args is None:
        args = sys.argv[1:]
    if len(args) != 2:
        print("Uso: python scripts/ripristina.py <file .sql.gz> <database>", file=sys.stderr)
        return 2
    backup_file = args[0]
    database = args[1]
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


# Solo lanciando il file (python scripts/ripristina.py ...), non importandolo; sys.exit
# esce con il codice restituito da main
if __name__ == "__main__":
    sys.exit(main())
