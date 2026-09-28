"""Applica al database del file .env le migrazioni mancanti: python scripts/migrate.py

Le migrazioni sono i file migrations/NNN_nome.sql, applicati in ordine di numero.
Quelle già applicate sono registrate nella tabella versione_schema (creata da
001_init.sql): rilanciato, lo script non rifà niente.

Attenzione: in MySQL i comandi che creano o cambiano tabelle non si possono
annullare in blocco. Se un file si ferma a metà, le istruzioni già eseguite
restano, il file NON viene registrato e lo script dice quale istruzione è fallita.
Le funzioni sono importabili (i test le usano su cinquecento_test).
"""

import re
import sys
from pathlib import Path

import pymysql
import sqlalchemy as sa

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

MIGRATIONS_DIR = BASE_DIR / "migrations"
VERSION_TABLE = "versione_schema"
FILE_NAME = re.compile(r"^(\d{3})_[a-z0-9_]+\.sql$")


class MigrationError(Exception):
    """Una migrazione non si può applicare: il messaggio dice cosa fare."""


def find_migrations(directory=MIGRATIONS_DIR):
    """Restituisce [(versione, percorso)] in ordine; rifiuta nomi sbagliati e numeri doppi."""
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
            raise MigrationError(
                f"Due migrazioni con lo stesso numero {version:03d}: "
                f"{found[version].name} e {path.name}."
            )
        found[version] = path
    return sorted(found.items())


def split_statements(sql):
    """Divide un file SQL nelle sue istruzioni, al punto e virgola.

    Ignora i commenti (-- ..., # ..., /* ... */) e i punti e virgola dentro
    le stringhe tra apici. Non gestisce DELIMITER (niente procedure o trigger).
    """
    statements, current = [], []
    i, n = 0, len(sql)
    while i < n:
        ch = sql[i]
        if ch in "'\"`":
            end = i + 1
            while end < n and sql[end] != ch:
                end += 2 if sql[end] == "\\" and ch != "`" else 1
            current.append(sql[i : end + 1])
            i = end + 1
        elif sql.startswith("--", i) or ch == "#":
            end = sql.find("\n", i)
            i = n if end == -1 else end
        elif sql.startswith("/*", i):
            end = sql.find("*/", i + 2)
            i = n if end == -1 else end + 2
        elif ch == ";":
            statements.append("".join(current).strip())
            current = []
            i += 1
        else:
            current.append(ch)
            i += 1
    statements.append("".join(current).strip())
    return [s for s in statements if s]


def migrate(url, directory=MIGRATIONS_DIR, report=print):
    """Applica le migrazioni mancanti al database di `url`; restituisce i file applicati."""
    migrations = find_migrations(directory)
    engine = sa.create_engine(url)
    try:
        raw = engine.raw_connection()
        try:
            return _migrate(raw, migrations, report)
        finally:
            raw.close()
    finally:
        engine.dispose()


def _migrate(raw, migrations, report):
    cursor = raw.cursor()
    cursor.execute("SELECT DATABASE()")
    database = cursor.fetchone()[0]
    if not database:
        raise MigrationError("Nessun database scelto: controlla DB_NAME nel file .env.")

    cursor.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = DATABASE()"
    )
    tables = {row[0] for row in cursor.fetchall()}
    applied = {}
    if VERSION_TABLE in tables:
        cursor.execute(f"SELECT versione, nome_file FROM {VERSION_TABLE}")
        applied = dict(cursor.fetchall())
    elif tables:
        raise MigrationError(
            f"Il database {database} contiene già delle tabelle, ma non {VERSION_TABLE}: "
            "forse una migrazione precedente si è fermata a metà. "
            "Se è un database di sviluppo, svuotalo e rilancia lo script."
        )

    files = {version: path.name for version, path in migrations}
    for version, name in sorted(applied.items()):
        if files.get(version) != name:
            raise MigrationError(
                f"Nel database {database} risulta applicata {name}, ma in migrations/ "
                "non c'è un file con quel numero e quel nome: aggiorna il codice (git pull)."
            )

    pending = [(v, p) for v, p in migrations if v not in applied]
    if pending and applied and pending[0][0] < max(applied):
        raise MigrationError(
            f"{pending[0][1].name} ha un numero più basso dell'ultima migrazione applicata "
            f"({max(applied):03d}): le migrazioni nuove vanno numerate dopo."
        )

    done = []
    for version, path in pending:
        statements = split_statements(path.read_text(encoding="utf-8"))
        for number, statement in enumerate(statements, start=1):
            try:
                cursor.execute(statement)
            except pymysql.MySQLError as exc:
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
        last = f"{max(applied):03d}" if applied else "nessuna"
        report(f"Database {database}: niente da applicare (ultima migrazione: {last}).")
    return done


def _first_line(statement):
    line = statement.splitlines()[0].strip()
    return line if len(line) <= 60 else line[:57] + "..."


def main(argv=None):
    from config import ConfigError, load_config

    args = sys.argv[1:] if argv is None else argv
    if args:
        print("Uso: python scripts/migrate.py (senza argomenti: usa il database del .env)", file=sys.stderr)
        return 2
    try:
        config = load_config()
        migrate(config.SQLALCHEMY_DATABASE_URI)
    except (ConfigError, MigrationError) as exc:
        print(f"Migrazione annullata: {exc}", file=sys.stderr)
        return 1
    except sa.exc.OperationalError as exc:
        code = exc.orig.args[0] if exc.orig is not None and exc.orig.args else "?"
        print(
            f"Migrazione annullata: non riesco a collegarmi a MySQL (errore MySQL {code}). "
            "Controlla che MySQL sia avviato, che scripts/setup_db.sql sia stato lanciato "
            "e che DB_USER, DB_PASSWORD e DB_NAME nel file .env siano giusti.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
