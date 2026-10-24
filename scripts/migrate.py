"""Applica al database del file .env le migrazioni mancanti: python scripts/migrate.py

Le migrazioni sono i file migrations/NNN_nome.sql, applicati in ordine di numero.
Quelle già applicate sono registrate nella tabella versione_schema (creata da
001_init.sql): rilanciato, lo script non rifà niente.

Attenzione: in MySQL i comandi che creano o cambiano tabelle non si possono
annullare in blocco. Se un file si ferma a metà, le istruzioni già eseguite
restano, il file NON viene registrato e lo script dice quale istruzione è fallita.
Le funzioni sono importabili (i test le usano su cinquecento_test).

Cosa contiene:
    MigrationError                 l'errore di una migrazione che non si può applicare
    find_migrations()              [(1, .../001_init.sql), ...]: i file, in ordine di numero
    split_statements("A; B;")      ["A", "B"]: le istruzioni di un file SQL
    migrate(url)                   applica le migrazioni mancanti; restituisce i nomi dei file
    _migrate(raw, migrations, report)   il lavoro di migrate, su un collegamento già aperto
    _first_line(istruzione)        la prima riga di un'istruzione, accorciata, per i messaggi
    main()                         il programma: python scripts/migrate.py

DA DOVE ARRIVANO I DATI: i file di migrations/; l'indirizzo del database da
load_config (config.py e .env). I test chiamano le funzioni con cinquecento_test e
cartelle di migrazioni finte.
"""

import re
import sys
from pathlib import Path

import pymysql
import sqlalchemy as sa

# BASE_DIR: la cartella del progetto (questo file sta in scripts/). La si aggiunge ai
# percorsi di Python, così "from config import ..." funziona anche lanciando lo script.
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

MIGRATIONS_DIR = BASE_DIR / "migrations"
VERSION_TABLE = "versione_schema"
# Il nome di un file di migrazione: tre cifre, un trattino basso, lettere minuscole,
# numeri e _, per esempio 001_init.sql (le tre cifre sono il gruppo 1)
FILE_NAME = re.compile(r"^(\d{3})_[a-z0-9_]+\.sql$")


class MigrationError(Exception):
    """Una migrazione non si può applicare: il messaggio dice cosa fare.

    In parole semplici:
        raise MigrationError("Due migrazioni con lo stesso numero 002: ...")
        main la prende, stampa il messaggio ed esce con 1. È un'eccezione con un
        nome suo ("eredita" da Exception).
    """


def find_migrations(directory=MIGRATIONS_DIR):
    """Restituisce [(versione, percorso)] in ordine; rifiuta nomi sbagliati e numeri doppi.

    In parole semplici:
        find_migrations(directory)
        directory: facoltativo, la cartella dei file .sql (se manca: migrations/;
                   i test ne passano una finta).
        Per esempio [(1, Path(".../001_init.sql"))]. Un file con un nome che non
        rispetta FILE_NAME, o due file con lo stesso numero, fermano tutto con
        MigrationError.
    """
    # found: numero → percorso, per esempio {1: Path(".../001_init.sql")}
    found = {}
    for path in sorted(Path(directory).glob("*.sql")):
        match = FILE_NAME.match(path.name)
        if not match:
            raise MigrationError(
                f'Nome di migrazione non valido: "{path.name}". '
                "Usa tre cifre, un trattino basso e lettere minuscole, per esempio 002_amici.sql."
            )
        version = int(match[1])
        if version in found:
            # {version:03d}: il numero scritto con tre cifre, per esempio 002
            raise MigrationError(
                f"Due migrazioni con lo stesso numero {version:03d}: "
                f"{found[version].name} e {path.name}."
            )
        found[version] = path
    # sorted di found.items(): le coppie (numero, percorso) in ordine di numero
    return sorted(found.items())


def split_statements(sql):
    """Divide un file SQL nelle sue istruzioni, al punto e virgola.

    Ignora i commenti (-- ..., # ..., /* ... */) e i punti e virgola dentro
    le stringhe tra apici. Non gestisce DELIMITER (niente procedure o trigger).

    In parole semplici:
        split_statements(sql)
        Per esempio split_statements("CREATE TABLE a (x INT); -- nota\\nINSERT INTO a VALUES (1);")
        = ["CREATE TABLE a (x INT)", "INSERT INTO a VALUES (1)"].
        Legge il testo un carattere alla volta, con l'indice i (come un ciclo sui
        caratteri di una stringa in C), e raccoglie i pezzi dell'istruzione in
        corso in current; a ogni ; l'istruzione è finita.
    """
    # statements: le istruzioni finite; current: i pezzi di quella in corso
    statements = []
    current = []
    i = 0
    n = len(sql)
    while i < n:
        ch = sql[i]
        if ch in "'\"`":
            # Un testo tra apici (o un nome tra `): si copia intero fino all'apice di
            # chiusura; dentro gli apici, \ salta anche il carattere dopo (per esempio \')
            end = i + 1
            while end < n and sql[end] != ch:
                if sql[end] == "\\" and ch != "`":
                    end += 2
                else:
                    end += 1
            current.append(sql[i : end + 1])
            i = end + 1
        elif sql.startswith("--", i) or ch == "#":
            # Commento fino alla fine della riga (l'a-capo resta)
            end = sql.find("\n", i)
            if end == -1:
                i = n
            else:
                i = end
        elif sql.startswith("/*", i):
            # Commento fino a */
            end = sql.find("*/", i + 2)
            if end == -1:
                i = n
            else:
                i = end + 2
        elif ch == ";":
            statements.append("".join(current).strip())
            current = []
            i += 1
        else:
            current.append(ch)
            i += 1
    statements.append("".join(current).strip())

    # Si tengono solo le istruzioni non vuote (per esempio dopo l'ultimo ;)
    result = []
    for statement in statements:
        if statement:
            result.append(statement)
    return result


def migrate(url, directory=MIGRATIONS_DIR, report=print):
    """Applica le migrazioni mancanti al database di `url`; restituisce i file applicati.

    In parole semplici:
        migrate(url, directory, report)
        url:       l'indirizzo del database (SQLALCHEMY_DATABASE_URI di load_config)
        directory: facoltativo, la cartella delle migrazioni (se manca: migrations/)
        report:    facoltativo, la funzione che riceve i messaggi da mostrare (se
                   manca: print; i test passano una funzione che li raccoglie). In C
                   sarebbe un puntatore a funzione.
        Restituisce per esempio ["002_amici.sql"], oppure [] se non c'era niente da
        applicare.
    """
    migrations = find_migrations(directory)
    engine = sa.create_engine(url)
    # Due try/finally uno dentro l'altro: finally si esegue sempre, anche dopo un
    # errore, e chiude prima il collegamento e poi il motore di SQLAlchemy.
    try:
        # raw_connection: il collegamento di PyMySQL, senza i servizi di SQLAlchemy
        raw = engine.raw_connection()
        try:
            return _migrate(raw, migrations, report)
        finally:
            raw.close()
    finally:
        engine.dispose()


def _migrate(raw, migrations, report):
    """Il lavoro di migrate, su un collegamento già aperto.

    In parole semplici:
        _migrate(raw, migrations, report)
        raw:        il collegamento a MySQL (aperto da migrate)
        migrations: l'elenco di find_migrations, per esempio [(1, Path(...))]
        report:     la funzione per i messaggi (print o quella dei test)
        1. controlla che sia scelto un database;
        2. legge le migrazioni già applicate da versione_schema (un database con
           tabelle ma senza versione_schema si rifiuta);
        3. controlla che quelle applicate ci siano ancora nella cartella, con lo
           stesso nome, e che le nuove abbiano numeri più alti;
        4. esegue le mancanti, un'istruzione alla volta, e registra ogni file.

        Restituisce: i nomi dei file applicati.
    """
    # cursor: l'oggetto con cui si mandano le istruzioni e si leggono le righe
    cursor = raw.cursor()
    cursor.execute("SELECT DATABASE()")
    database = cursor.fetchone()[0]
    if not database:
        raise MigrationError("Nessun database scelto: controlla DB_NAME nel file .env.")

    cursor.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = DATABASE()"
    )
    # tables: i nomi delle tabelle del database, in un insieme (set: senza doppioni)
    tables = set()
    for row in cursor.fetchall():
        tables.add(row[0])
    # applied: numero → nome del file delle migrazioni già applicate, per esempio {1: "001_init.sql"}
    applied = {}
    if VERSION_TABLE in tables:
        cursor.execute(f"SELECT versione, nome_file FROM {VERSION_TABLE}")
        # dict di un elenco di coppie (numero, nome): numero → nome
        applied = dict(cursor.fetchall())
    elif tables:
        raise MigrationError(
            f"Il database {database} contiene già delle tabelle, ma non {VERSION_TABLE}: "
            "forse una migrazione precedente si è fermata a metà. "
            "Se è un database di sviluppo, svuotalo e rilancia lo script."
        )

    # files: numero → nome del file nella cartella, per esempio {1: "001_init.sql"}
    files = {}
    for migration in migrations:
        files[migration[0]] = migration[1].name
    for version, name in sorted(applied.items()):
        if files.get(version) != name:
            raise MigrationError(
                f"Nel database {database} risulta applicata {name}, ma in migrations/ "
                "non c'è un file con quel numero e quel nome: aggiorna il codice (git pull)."
            )

    # pending: le migrazioni ancora da applicare, nello stesso ordine
    pending = []
    for migration in migrations:
        if migration[0] not in applied:
            pending.append(migration)
    if pending and applied and pending[0][0] < max(applied):
        raise MigrationError(
            f"{pending[0][1].name} ha un numero più basso dell'ultima migrazione applicata "
            f"({max(applied):03d}): le migrazioni nuove vanno numerate dopo."
        )

    done = []
    for migration in pending:
        version = migration[0]
        path = migration[1]
        statements = split_statements(path.read_text(encoding="utf-8"))
        for index in range(len(statements)):
            statement = statements[index]
            # number: il numero dell'istruzione per i messaggi, da 1
            number = index + 1
            try:
                cursor.execute(statement)
            except pymysql.MySQLError as exc:
                # from None: nel messaggio resta solo il nostro testo (con quello di MySQL)
                raise MigrationError(
                    f"{path.name}, istruzione {number} di {len(statements)} "
                    f"({_first_line(statement)}): {exc}. Le istruzioni precedenti restano "
                    "applicate e il file non è stato registrato."
                ) from None
        cursor.execute(
            f"INSERT INTO {VERSION_TABLE} (versione, nome_file) VALUES (%s, %s)",
            (version, path.name),
        )
        raw.commit()
        report(f"Database {database}: applicata {path.name}")
        done.append(path.name)

    if not done:
        last = "nessuna"
        if applied:
            last = f"{max(applied):03d}"
        report(f"Database {database}: niente da applicare (ultima migrazione: {last}).")
    return done


def _first_line(statement):
    """La prima riga di un'istruzione, al massimo 60 caratteri, per i messaggi.

    In parole semplici:
        _first_line(statement)
        Per esempio _first_line("CREATE TABLE amici (\\n  ...") = "CREATE TABLE amici (".
        Una riga più lunga si taglia a 57 caratteri e finisce con "...".
    """
    line = statement.splitlines()[0].strip()
    if len(line) <= 60:
        return line
    return line[:57] + "..."


def main(argv=None):
    """Il programma: python scripts/migrate.py (senza argomenti).

    In parole semplici:
        main(argv)
        argv: facoltativo, gli argomenti al posto di quelli della riga di comando
              (lo passano i test); se manca: sys.argv[1:], cioè quelli dopo il nome
              dello script.
        Restituisce il codice di uscita: 0 tutto bene, 1 errore (configurazione,
        migrazione o MySQL che non risponde), 2 argomenti sbagliati.
    """
    # Import qui dentro: config.py (che legge il .env) si carica quando parte il
    # programma, non quando un test importa questo file
    from config import ConfigError, load_config

    args = argv
    if args is None:
        args = sys.argv[1:]
    if args:
        print("Uso: python scripts/migrate.py (senza argomenti: usa il database del .env)", file=sys.stderr)
        return 2
    try:
        config = load_config()
        migrate(config.SQLALCHEMY_DATABASE_URI)
    except (ConfigError, MigrationError) as exc:
        print(f"Migrazione annullata: {exc}", file=sys.stderr)
        return 1
    # engine.raw_connection() lancia l'errore di PyMySQL così com'è, non quello di SQLAlchemy.
    except (sa.exc.OperationalError, pymysql.err.OperationalError) as exc:
        # orig: l'errore di PyMySQL (dentro quello di SQLAlchemy, o l'errore stesso)
        orig = getattr(exc, "orig", exc)
        # code: il numero dell'errore di MySQL (per esempio 1045, accesso negato), "?" se manca
        code = "?"
        if orig is not None and orig.args:
            code = orig.args[0]
        print(
            f"Migrazione annullata: non riesco a collegarmi a MySQL (errore MySQL {code}). "
            "Controlla che MySQL sia avviato, che scripts/setup_db.sql sia stato lanciato "
            "e che DB_USER, DB_PASSWORD e DB_NAME nel file .env siano giusti.",
            file=sys.stderr,
        )
        return 1
    return 0


# Solo lanciando il file (python scripts/migrate.py), non importandolo; sys.exit esce
# con il codice restituito da main
if __name__ == "__main__":
    sys.exit(main())
