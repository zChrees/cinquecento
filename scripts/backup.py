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

Cosa contiene:
    BackupError                      l'errore di un backup o di un ripristino
    check_database_name("x_test")    rifiuta un nome di database non valido
    find_program("mysqldump")        il percorso del programma, per esempio "C:\\...\\mysqldump.exe"
    options_file(url)                il file di opzioni temporaneo (con with)
    _quote('a"b')                    '"a\\"b"': un valore tra virgolette per quel file
    program_errors(stream)           il messaggio d'errore di mysqldump o mysql
    backup(url, cartella)            fa il backup; restituisce il percorso del file
    remove_old_backups(cartella, 14) cancella i backup vecchi; restituisce quali
    _shown(percorso)                 il percorso da mostrare, se si può relativo al progetto
    main()                           il programma: python scripts/backup.py

DA DOVE ARRIVANO I DATI: l'indirizzo del database, BACKUP_DIR e
BACKUP_RETENTION_DAYS da load_config (config.py e .env). scripts/ripristina.py usa
BackupError, check_database_name, find_program, options_file e program_errors; il
backup pianificato (scripts/pianifica_backup.ps1, P38) lancia questo script.
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

# BASE_DIR: la cartella del progetto (questo file sta in scripts/). La si aggiunge ai
# percorsi di Python, così "from config import ..." funziona anche lanciando lo script.
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# r"...": testo "grezzo", dove \ resta un carattere normale (comodo per i percorsi di Windows)
WINDOWS_BIN = Path(r"C:\Program Files\MySQL\MySQL Server 8.0\bin")
DATABASE_NAME = re.compile(r"^[A-Za-z0-9_]{1,64}$")
BACKUP_SUFFIX = ".sql.gz"
# Il nome di un backup: database, trattino basso, data e ora, .sql.gz; (?P<nome>...) dà
# un nome a un pezzo, che poi si legge con match["database"] e match["when"]
BACKUP_NAME = re.compile(r"^(?P<database>[A-Za-z0-9_]+)_(?P<when>\d{4}-\d{2}-\d{2}_\d{6})\.sql\.gz$")
TIME_FORMAT = "%Y-%m-%d_%H%M%S"
DUMP_OPTIONS = (
    "--single-transaction",       # copia coerente senza bloccare le tabelle (InnoDB)
    "--no-tablespaces",           # senza, mysqldump chiede il permesso PROCESS, che l'utente del progetto non ha
    "--set-gtid-purged=OFF",      # il backup si può ricaricare anche in un altro database
    "--skip-dump-date",           # due backup degli stessi dati sono identici
)


class BackupError(Exception):
    """Backup o ripristino non riuscito: il messaggio dice cosa fare.

    In parole semplici:
        raise BackupError("Non trovo mysqldump: installa MySQL 8.0 ...")
        main (qui e in ripristina.py) la prende, stampa il messaggio ed esce con 1.
        È un'eccezione con un nome suo ("eredita" da Exception).
    """


def check_database_name(name):
    """Rifiuta un nome di database che non sia fatto di lettere, numeri e _.

    In parole semplici:
        check_database_name(name)
        Con "cinquecento_test" non dice niente; con "x; DROP" o con un valore che
        non è un testo (per esempio None) lancia BackupError. Il nome finisce
        sulla riga di comando di mysqldump e mysql: così non può contenere altro.
    """
    if not isinstance(name, str) or not DATABASE_NAME.fullmatch(name):
        raise BackupError(f'Nome del database non valido: "{name}" (solo lettere, numeri e _).')


def find_program(name):
    """Percorso di un programma di MySQL (mysqldump, mysql): prima il PATH, poi la cartella di MySQL 8.0.

    In parole semplici:
        find_program(name)
        Per esempio find_program("mysqldump") =
        "C:\\Program Files\\MySQL\\MySQL Server 8.0\\bin\\mysqldump.exe".
        Se non lo trova lancia BackupError con cosa fare.
    """
    # shutil.which: cerca il programma nelle cartelle del PATH; None se non c'è
    found = shutil.which(name)
    if found:
        return found
    candidate = WINDOWS_BIN / f"{name}.exe"
    if candidate.is_file():
        return str(candidate)
    raise BackupError(
        f"Non trovo {name}: installa MySQL 8.0 oppure aggiungi al PATH la sua cartella bin."
    )


# @contextmanager è un "decoratore": trasforma la funzione qui sotto in una che si usa
# con with ("with options_file(url) as path: ..."). Il codice fino a yield gira
# all'inizio del with, yield dà il valore (path) al blocco with, e il finally gira alla
# fine del blocco, anche dopo un errore: così il file con la password si cancella sempre.
@contextmanager
def options_file(url):
    """File di opzioni temporaneo con utente, password, host e porta; cancellato alla fine.

    In parole semplici:
        with options_file(url) as path:
            ... mysqldump --defaults-extra-file=path ...
        url: l'indirizzo del database (utente, password, host, porta). Il file è come
        [client]
        user="cinquecento"
        host="127.0.0.1"
        port=3306
        default-character-set=utf8mb4
        password="..."
        e sta nella cartella temporanea di Windows, con un nome come cinquecento-abc123.cnf.
    """
    username = url.username
    if not username:
        username = ""
    host = url.host
    if not host:
        host = "127.0.0.1"
    port = url.port
    if not port:
        port = 3306
    lines = [
        "[client]",
        f"user={_quote(username)}",
        f"host={_quote(host)}",
        f"port={port}",
        "default-character-set=utf8mb4",
    ]
    if url.password:
        lines.append(f"password={_quote(url.password)}")
    # mkstemp: crea il file e restituisce due cose, il "descrittore" (fd, il numero con
    # cui il sistema lo conosce, come in C) e il percorso
    created = tempfile.mkstemp(prefix="cinquecento-", suffix=".cnf")
    fd = created[0]
    path = created[1]
    try:
        # with: il file si chiude da solo alla fine del blocco
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            out.write("\n".join(lines) + "\n")
        yield path
    finally:
        Path(path).unlink(missing_ok=True)


def _quote(value):
    """Un valore tra virgolette per il file di opzioni di MySQL.

    In parole semplici:
        _quote(value)
        Per esempio _quote('pa"ss') = '"pa\\"ss"'. Nei file di opzioni di MySQL un
        valore tra virgolette accetta \\\\ e \\" come caratteri: per questo \\ e "
        si raddoppiano con una \\ davanti.
    """
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def program_errors(stream):
    """Messaggio d'errore di mysqldump o mysql, letto dal file temporaneo.

    In parole semplici:
        program_errors(stream)
        stream è il file temporaneo dove il programma ha scritto i suoi errori.
        seek(0) torna all'inizio del file per leggerlo tutto. Se è vuoto il
        messaggio è "nessun dettaglio".
    """
    stream.seek(0)
    text = stream.read().decode("utf-8", errors="replace").strip()
    if not text:
        return "nessun dettaglio"
    return text


def backup(url, backup_dir, now=None):
    """Salva il database di `url` in `backup_dir` e restituisce il percorso del file.

    In parole semplici:
        backup(url, backup_dir, now)
        url:        l'indirizzo del database (con dentro il nome, url.database)
        backup_dir: la cartella dei backup, per esempio backups/
        now:        facoltativo, l'ora da scrivere nel nome (i test la fissano); se
                    manca è l'ora di adesso, nel fuso orario del PC
        Per esempio restituisce backups/cinquecento_dev_2026-09-28_213000.sql.gz.
        mysqldump scrive il database come testo SQL; qui lo si comprime (gzip) in
        un file .parziale, che prende il nome vero solo se tutto è andato bene.
    """
    database = url.database
    check_database_name(database)
    backup_dir = Path(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    if now is None:
        now = datetime.now().astimezone()
    when = now.strftime(TIME_FORMAT)
    target = backup_dir / f"{database}_{when}{BACKUP_SUFFIX}"
    if target.exists():
        raise BackupError(f"Esiste già {target.name}: riprova tra un secondo.")
    partial = target.with_name(target.name + ".parziale")
    program = find_program("mysqldump")

    # Un with con due oggetti separati da una virgola è come due with uno dentro
    # l'altro (lo chiede ruff, SIM117): si aprono in ordine e si chiudono al contrario.
    # errors: un file temporaneo per i messaggi d'errore di mysqldump
    with options_file(url) as options, tempfile.TemporaryFile() as errors:
        # command: il programma e i suoi argomenti, uno per elemento
        command = [program, f"--defaults-extra-file={options}"]
        command.extend(DUMP_OPTIONS)
        command.append(database)
        try:
            # Popen avvia mysqldump; quello che scrive (stdout) si copia nel file
            # compresso a pezzi, senza tenere tutto in memoria. La \ in fondo alla
            # riga dice che il with continua sulla riga dopo.
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
    """Cancella i backup più vecchi di `days` giorni e restituisce l'elenco dei file cancellati.

    In parole semplici:
        remove_old_backups(backup_dir, days, now)
        backup_dir: la cartella dei backup
        days:       quanti giorni tenerli, per esempio 14 (BACKUP_RETENTION_DAYS)
        now:        facoltativo, l'ora da cui contare (i test la fissano); se manca
                    è adesso
        Guarda solo i file con il nome di BACKUP_NAME e legge la data dal nome: un
        file che non ha quella forma, o con una data impossibile, non si tocca.
    """
    if now is None:
        now = datetime.now().astimezone()
    limit = now - timedelta(days=days)
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
    """Il percorso da mostrare: relativo al progetto se si può, altrimenti intero.

    In parole semplici:
        _shown(path)
        Per esempio "backups\\cinquecento_dev_2026-09-28_213000.sql.gz" per un file
        dentro il progetto. relative_to lancia ValueError se il file è fuori dal
        progetto: allora si mostra il percorso intero.
    """
    try:
        return str(Path(path).relative_to(BASE_DIR))
    except ValueError:
        return str(path)


def main(argv=None):
    """Il programma: python scripts/backup.py (senza argomenti).

    In parole semplici:
        main(argv)
        argv: facoltativo, gli argomenti al posto di quelli della riga di comando
              (lo passano i test); se manca: sys.argv[1:].
        Fa il backup, cancella quelli vecchi e stampa il file salvato con la sua
        misura in KB. Restituisce il codice di uscita: 0 tutto bene, 1 errore,
        2 argomenti sbagliati.
    """
    # Import qui dentro: config.py (che legge il .env) si carica quando parte il
    # programma, non quando un test importa questo file
    from config import ConfigError, load_config

    args = argv
    if args is None:
        args = sys.argv[1:]
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
    # size_kb: la misura del file in KB, almeno 1 (un file piccolo non dice "0 KB")
    size_kb = max(1, round(path.stat().st_size / 1024))
    print(f"Backup salvato: {_shown(path)} ({size_kb} KB)")
    if removed:
        print(f"Cancellati {len(removed)} backup più vecchi di {config.BACKUP_RETENTION_DAYS} giorni.")
    return 0


# Solo lanciando il file (python scripts/backup.py), non importandolo; sys.exit esce
# con il codice restituito da main
if __name__ == "__main__":
    sys.exit(main())
