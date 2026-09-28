"""P5: migrate.py crea le tabelle, i modelli le rispecchiano e il database fa rispettare le sue regole.

Serve MySQL 8.0 acceso, con scripts/setup_db.sql già lanciato e l'utente del .env
(DB_USER, DB_PASSWORD). Si usa SOLO il database dei test (DB_NAME_TEST, che finisce
con _test): all'inizio viene svuotato e ricreato con migrate.py.
Le prove sui dati girano dentro una transazione annullata alla fine: non lasciano righe.
Comando (finché P6 non aggiunge il runner): python -m pytest tests/db
"""

import importlib.util
from pathlib import Path

import pytest
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

import app.models  # noqa: F401  (registra tutti i modelli in db.metadata)
from app.extensions import db
from config import load_config

BASE_DIR = Path(__file__).resolve().parents[2]
MIGRATIONS_DIR = BASE_DIR / "migrations"
TABLES = {
    "utenti", "rating", "partite", "giocatori_partita", "mosse_partita",
    "amicizie", "blocchi", "messaggi", "versione_schema",
}

# Codici di errore di MySQL che le regole devono dare
DUPLICATE = 1062        # riga doppia su una chiave unica
CHECK_FAILED = 3819     # CHECK non rispettato
TOO_LONG = 1406         # testo più lungo della colonna
NO_DEFAULT = 1364       # colonna obbligatoria non scritta
NULL_NOT_ALLOWED = 1048 # colonna obbligatoria vuota


def _load_migrate():
    spec = importlib.util.spec_from_file_location("migrate", BASE_DIR / "scripts" / "migrate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


migrate = _load_migrate()


@pytest.fixture(scope="module")
def engine():
    if (BASE_DIR / "PRODUZIONE").exists():
        pytest.exit("Trovato il file PRODUZIONE: i test non partono in un'installazione vera.")
    config = load_config("testing")
    url = config.SQLALCHEMY_DATABASE_URI
    assert url.database.endswith("_test"), "i test usano solo un database che finisce con _test"

    engine = sa.create_engine(url)
    try:
        with engine.connect() as conn:
            tables = conn.execute(sa.text(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = DATABASE()"
            )).scalars().all()
            conn.execute(sa.text("SET FOREIGN_KEY_CHECKS = 0"))
            for table in tables:
                conn.execute(sa.text(f"DROP TABLE `{table}`"))
            conn.execute(sa.text("SET FOREIGN_KEY_CHECKS = 1"))
    except sa.exc.OperationalError as exc:
        code = exc.orig.args[0] if exc.orig is not None and exc.orig.args else "?"
        pytest.fail(
            f"Non riesco a usare il database {url.database} (errore MySQL {code}): "
            "MySQL è acceso? scripts/setup_db.sql è stato lanciato? "
            "DB_USER e DB_PASSWORD nel .env sono giusti?",
            pytrace=False,
        )
    yield engine
    engine.dispose()


@pytest.fixture(scope="module")
def migrated(engine):
    """Il database dei test, vuoto, dopo il primo giro di migrate.py."""
    applied = migrate.migrate(engine.url, report=lambda _msg: None)
    return applied


@pytest.fixture
def conn(engine, migrated):
    """Connessione in una transazione che si annulla alla fine del test."""
    with engine.connect() as connection:
        transaction = connection.begin()
        yield connection
        transaction.rollback()


def run(conn, sql, **params):
    return conn.execute(sa.text(sql), params)


def rejected(conn, sql, codes, **params):
    """Esegue `sql` e controlla che MySQL lo rifiuti con uno dei codici `codes`."""
    with pytest.raises(sa.exc.DBAPIError) as info, conn.begin_nested():
        run(conn, sql, **params)
    code = info.value.orig.args[0]
    assert code in codes, f"MySQL ha rifiutato con il codice {code}, atteso uno tra {codes}"


def add_user(conn, name, email=None):
    result = run(
        conn,
        "INSERT INTO utenti (nome_utente, email, hash_password) VALUES (:n, :e, 'hash')",
        n=name, e=email or f"{name}@prova.it",
    )
    return result.lastrowid


def add_match(conn, omit=None, **overrides):
    """Inserisce una partita finita; `omit` è una colonna da non scrivere affatto."""
    values = {
        "modalita": "1v1", "punti_per_vincere": 500, "conta_per_rating": True,
        "iniziata_il": "2026-09-28 10:00:00", "finita_il": "2026-09-28 10:30:00",
        "motivo_fine": "punteggio", "squadra_vincente": 0,
        "punti_squadra_0": 512, "punti_squadra_1": 340,
    }
    values.update(overrides)
    values.pop(omit, None)
    columns = ", ".join(values)
    marks = ", ".join(f":{c}" for c in values)
    return run(conn, f"INSERT INTO partite ({columns}) VALUES ({marks})", **values).lastrowid


def add_player(conn, match_id, seat, user_id, team=None):
    run(
        conn,
        "INSERT INTO giocatori_partita (partita_id, posto, squadra, utente_id, risultato) "
        "VALUES (:p, :s, :t, :u, 'vittoria')",
        p=match_id, s=seat, t=seat % 2 if team is None else team, u=user_id,
    )


def count(conn, sql, **params):
    return run(conn, sql, **params).scalar()


# ---------------------------------------------------------------------
# migrate.py
# ---------------------------------------------------------------------

def test_database_vuoto_crea_tutte_le_tabelle(engine, migrated):
    assert migrated == ["001_init.sql"]
    with engine.connect() as c:
        tables = set(c.execute(sa.text(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = DATABASE()"
        )).scalars())
        versions = c.execute(sa.text("SELECT versione, nome_file FROM versione_schema")).all()
    assert tables == TABLES
    assert versions == [(1, "001_init.sql")]


def test_rilanciato_non_fa_niente(engine, migrated):
    messages = []
    assert migrate.migrate(engine.url, report=messages.append) == []
    assert messages == [f"Database {engine.url.database}: niente da applicare (ultima migrazione: 001)."]


def test_tutte_le_tabelle_in_innodb_e_utf8mb4(engine, migrated):
    with engine.connect() as c:
        rows = c.execute(sa.text(
            "SELECT table_name, engine, table_collation FROM information_schema.tables "
            "WHERE table_schema = DATABASE()"
        )).all()
    for name, table_engine, collation in rows:
        assert table_engine == "InnoDB", name
        assert collation == "utf8mb4_0900_ai_ci", name


def test_mysql_in_modalita_rigorosa(engine):
    """Senza STRICT_TRANS_TABLES MySQL taglierebbe in silenzio i testi troppo lunghi."""
    with engine.connect() as c:
        mode = c.execute(sa.text("SELECT @@SESSION.sql_mode")).scalar()
    assert "STRICT_TRANS_TABLES" in mode.split(","), (
        f"sql_mode di MySQL senza STRICT_TRANS_TABLES ({mode}): rimettilo nel my.ini "
        "(è il valore predefinito di MySQL 8.0)"
    )


def test_file_fermo_a_meta_non_viene_registrato(engine, migrated, tmp_path):
    (tmp_path / "001_init.sql").write_bytes((MIGRATIONS_DIR / "001_init.sql").read_bytes())
    (tmp_path / "002_rotta.sql").write_text(
        "CREATE TABLE prova_rotta (id INT);\nSELEC 1;\n", encoding="utf-8"
    )
    try:
        with pytest.raises(migrate.MigrationError, match=r"002_rotta\.sql, istruzione 2 di 2"):
            migrate.migrate(engine.url, directory=tmp_path, report=lambda _msg: None)
        with engine.connect() as c:
            versions = c.execute(sa.text("SELECT versione FROM versione_schema")).scalars().all()
        assert versions == [1]
    finally:
        with engine.connect() as c:
            c.execute(sa.text("DROP TABLE IF EXISTS prova_rotta"))


def test_tabelle_senza_versione_schema_rifiutate(engine, migrated):
    with engine.connect() as c:
        c.execute(sa.text("RENAME TABLE versione_schema TO versione_schema_prova"))
    try:
        with pytest.raises(migrate.MigrationError, match="contiene già delle tabelle"):
            migrate.migrate(engine.url, report=lambda _msg: None)
    finally:
        with engine.connect() as c:
            c.execute(sa.text("RENAME TABLE versione_schema_prova TO versione_schema"))


def test_migrazione_applicata_ma_file_diverso_rifiutata(engine, migrated, tmp_path):
    (tmp_path / "001_altro.sql").write_text("SELECT 1;", encoding="utf-8")
    with pytest.raises(migrate.MigrationError, match="risulta applicata 001_init.sql"):
        migrate.migrate(engine.url, directory=tmp_path, report=lambda _msg: None)


@pytest.mark.parametrize("name", ["1_init.sql", "001-init.sql", "001_Init.sql", "init.sql"])
def test_nome_di_migrazione_sbagliato_rifiutato(tmp_path, name):
    (tmp_path / name).write_text("SELECT 1;", encoding="utf-8")
    with pytest.raises(migrate.MigrationError, match="Nome di migrazione non valido"):
        migrate.find_migrations(tmp_path)


def test_due_migrazioni_con_lo_stesso_numero_rifiutate(tmp_path):
    (tmp_path / "002_a.sql").write_text("SELECT 1;", encoding="utf-8")
    (tmp_path / "002_b.sql").write_text("SELECT 1;", encoding="utf-8")
    with pytest.raises(migrate.MigrationError, match="stesso numero 002"):
        migrate.find_migrations(tmp_path)


def test_istruzioni_divise_al_punto_e_virgola():
    sql = (
        "-- commento; con punto e virgola\n"
        "CREATE TABLE a (x VARCHAR(5) DEFAULT 'a;b'); # altro; commento\n"
        "/* blocco;\n di commento */ INSERT INTO a VALUES ('it''s;'), (\"x;\\\"y\");\n"
        "SELECT 1"
    )
    assert migrate.split_statements(sql) == [
        "CREATE TABLE a (x VARCHAR(5) DEFAULT 'a;b')",
        "INSERT INTO a VALUES ('it''s;'), (\"x;\\\"y\")",
        "SELECT 1",
    ]


def test_001_ha_una_istruzione_per_tabella():
    statements = migrate.split_statements((MIGRATIONS_DIR / "001_init.sql").read_text(encoding="utf-8"))
    assert len(statements) == len(TABLES)
    assert all(s.startswith("CREATE TABLE") for s in statements)


# ---------------------------------------------------------------------
# I modelli Python rispecchiano le tabelle
# ---------------------------------------------------------------------

def _model_type(column):
    text = column.type.compile(dialect=mysql.dialect()).lower()
    text = text.split(" character set ")[0].replace("integer", "int").replace("bool", "tinyint(1)")
    return text.replace("', '", "','")


def test_modelli_uguali_alle_tabelle(engine, migrated):
    tables = db.metadata.tables
    assert set(tables) == TABLES - {"versione_schema"}
    with engine.connect() as c:
        for name, table in tables.items():
            rows = c.execute(sa.text(
                "SELECT column_name, column_type, is_nullable, column_key, collation_name "
                "FROM information_schema.columns WHERE table_schema = DATABASE() AND table_name = :t"
            ), {"t": name}).all()
            in_db = {r[0]: (r[1], r[2] == "YES") for r in rows}
            in_model = {col.name: (_model_type(col), col.nullable) for col in table.columns}
            assert in_model == in_db, name
            db_pk = {r[0] for r in rows if r[3] == "PRI"}
            assert {col.name for col in table.primary_key} == db_pk, name
            # Dove il modello indica una collation (testo esatto), è la stessa della tabella
            db_collation = {r[0]: r[4] for r in rows}
            for col in table.columns:
                collation = getattr(col.type, "collation", None)
                if collation:
                    assert db_collation[col.name] == collation, (name, col.name)


def test_nome_utente_distingue_le_maiuscole_anche_nel_modello():
    column = db.metadata.tables["utenti"].c.nome_utente
    assert column.type.collation == "utf8mb4_0900_as_cs"


# ---------------------------------------------------------------------
# Regole del database
# ---------------------------------------------------------------------

def test_account_cancellato_toglie_i_suoi_dati_ma_non_le_partite(conn):
    """D6: rating, amicizie, blocchi e messaggi spariscono; la partita resta con utente vuoto."""
    tot = add_user(conn, "Toto")
    nina = add_user(conn, "Nina")
    run(conn, "INSERT INTO rating VALUES (:u, '1v1', 1500, 350, 0.06, '2026-09-28 10:30:00')", u=tot)
    run(conn, "INSERT INTO amicizie (richiedente_id, destinatario_id) VALUES (:a, :b)", a=tot, b=nina)
    run(conn, "INSERT INTO blocchi (bloccante_id, bloccato_id) VALUES (:a, :b)", a=nina, b=tot)
    for sender, recipient in ((tot, nina), (nina, tot)):
        run(
            conn,
            "INSERT INTO messaggi (mittente_id, destinatario_id, testo, inviato_il) "
            "VALUES (:a, :b, 'ciao', '2026-09-28 10:00:00.123')",
            a=sender, b=recipient,
        )
    match_id = add_match(conn)
    add_player(conn, match_id, 0, tot)
    add_player(conn, match_id, 1, nina)
    run(
        conn,
        "INSERT INTO mosse_partita VALUES (:p, 1, 1, 0, 'gioca_carta', '{\"seme\": \"coppe\"}', "
        "'2026-09-28 10:01:00.500')",
        p=match_id,
    )

    run(conn, "DELETE FROM utenti WHERE id = :u", u=tot)

    assert count(conn, "SELECT COUNT(*) FROM rating WHERE utente_id = :u", u=tot) == 0
    assert count(conn, "SELECT COUNT(*) FROM amicizie") == 0
    assert count(conn, "SELECT COUNT(*) FROM blocchi") == 0
    assert count(conn, "SELECT COUNT(*) FROM messaggi") == 0
    players = run(
        conn, "SELECT posto, utente_id FROM giocatori_partita WHERE partita_id = :p ORDER BY posto",
        p=match_id,
    ).all()
    assert players == [(0, None), (1, nina)]
    assert count(conn, "SELECT COUNT(*) FROM partite WHERE id = :p", p=match_id) == 1
    assert count(conn, "SELECT COUNT(*) FROM mosse_partita WHERE partita_id = :p", p=match_id) == 1


@pytest.mark.parametrize(
    "name",
    ["ab", "a" * 21, "Nicolò", "mario rossi", "mario-rossi", "", "mario!"],
    ids=["corto", "lungo", "accento", "spazio", "trattino", "vuoto", "simbolo"],
)
def test_nome_utente_non_valido_rifiutato(conn, name):
    rejected(
        conn,
        "INSERT INTO utenti (nome_utente, email, hash_password) VALUES (:n, 'x@prova.it', 'h')",
        {CHECK_FAILED, TOO_LONG},
        n=name,
    )


@pytest.mark.parametrize("name", ["abc", "a" * 20, "Mario_99", "___"])
def test_nome_utente_valido_accettato(conn, name):
    add_user(conn, name, email="x@prova.it")


def test_mario_e_mario_minuscolo_sono_due_utenti(conn):
    """D7: il nome utente distingue le maiuscole."""
    add_user(conn, "Mario", email="uno@prova.it")
    add_user(conn, "mario", email="due@prova.it")
    rejected(
        conn,
        "INSERT INTO utenti (nome_utente, email, hash_password) VALUES ('Mario', 'tre@prova.it', 'h')",
        {DUPLICATE},
    )


def test_email_uguale_a_parte_le_maiuscole_rifiutata(conn):
    add_user(conn, "Mario", email="Mario@Prova.it")
    rejected(
        conn,
        "INSERT INTO utenti (nome_utente, email, hash_password) VALUES ('Luigi', 'mario@prova.it', 'h')",
        {DUPLICATE},
    )


def test_stesso_utente_due_volte_nella_stessa_partita_rifiutato(conn):
    mario = add_user(conn, "Mario")
    match_id = add_match(conn)
    add_player(conn, match_id, 0, mario)
    rejected(
        conn,
        "INSERT INTO giocatori_partita (partita_id, posto, squadra, utente_id, risultato) "
        "VALUES (:p, 1, 1, :u, 'sconfitta')",
        {DUPLICATE},
        p=match_id, u=mario,
    )


def test_due_utenti_eliminati_nella_stessa_partita_ammessi(conn):
    """I posti con utente vuoto (account cancellati) non contano come doppioni."""
    match_id = add_match(conn)
    add_player(conn, match_id, 0, None)
    add_player(conn, match_id, 1, None)


def test_seconda_amicizia_tra_gli_stessi_utenti_rifiutata(conn):
    tot = add_user(conn, "Toto")
    nina = add_user(conn, "Nina")
    run(conn, "INSERT INTO amicizie (richiedente_id, destinatario_id) VALUES (:a, :b)", a=tot, b=nina)
    for a, b in ((tot, nina), (nina, tot)):
        rejected(
            conn,
            "INSERT INTO amicizie (richiedente_id, destinatario_id) VALUES (:a, :b)",
            {DUPLICATE},
            a=a, b=b,
        )


@pytest.mark.parametrize("points", [0, 100, 200, 499, 501, 1000])
def test_punteggio_per_vincere_diverso_da_150_300_500_rifiutato(conn, points):
    with pytest.raises(sa.exc.DBAPIError) as info, conn.begin_nested():
        add_match(conn, punti_per_vincere=points)
    assert info.value.orig.args[0] == CHECK_FAILED


@pytest.mark.parametrize("points", [150, 300, 500])
def test_punteggio_per_vincere_ammesso(conn, points):
    add_match(conn, punti_per_vincere=points)


@pytest.mark.parametrize("column", ["finita_il", "motivo_fine"])
def test_partita_senza_fine_rifiutata(conn, column):
    """Le partite si salvano solo a fine partita: data e motivo di fine sono obbligatori."""
    for kwargs, code in (({column: None}, NULL_NOT_ALLOWED), ({"omit": column}, NO_DEFAULT)):
        with pytest.raises(sa.exc.DBAPIError) as info, conn.begin_nested():
            add_match(conn, **kwargs)
        assert info.value.orig.args[0] == code, kwargs


LIST_COLUMNS = [
    ("partite", "modalita", ["1v1", "2v2"], ["1V1", "3v3", ""]),
    ("partite", "motivo_fine", ["punteggio", "abbandono"], ["Punteggio", "resa", "punteggiò", "punteggio "]),
    ("giocatori_partita", "risultato", ["vittoria", "sconfitta", "pareggio"], ["Vittoria", "vinta", ""]),
    ("rating", "modalita", ["1v1", "2v2"], ["2V2", "1v2"]),
]


def _insert_with(conn, table, column, value, omit=False):
    """Scrive una riga valida di `table`, con `column` = `value` (o senza `column`)."""
    if table == "partite":
        return add_match(conn, omit=column if omit else None, **({} if omit else {column: value}))
    user = add_user(conn, "Toto")
    if table == "rating":
        columns = {"utente_id": user, "modalita": value, "valore": 1500, "deviazione": 350,
                   "volatilita": 0.06, "aggiornato_il": "2026-09-28 10:30:00"}
    else:
        columns = {"partita_id": add_match(conn), "posto": 0, "squadra": 0,
                   "utente_id": user, "risultato": value}
    if omit:
        del columns[column]
    names = ", ".join(columns)
    marks = ", ".join(f":{c}" for c in columns)
    return run(conn, f"INSERT INTO {table} ({names}) VALUES ({marks})", **columns)


@pytest.mark.parametrize(("table", "column", "_good", "_bad"), LIST_COLUMNS, ids=lambda v: str(v))
def test_colonna_a_elenco_dimenticata_rifiutata(conn, table, column, _good, _bad):
    """Un ENUM avrebbe messo in silenzio il primo valore (es. 'vittoria'): qui MySQL rifiuta."""
    with pytest.raises(sa.exc.DBAPIError) as info, conn.begin_nested():
        _insert_with(conn, table, column, None, omit=True)
    assert info.value.orig.args[0] == NO_DEFAULT


@pytest.mark.parametrize(("table", "column", "good", "bad"), LIST_COLUMNS, ids=lambda v: str(v))
def test_colonna_a_elenco_accetta_solo_i_valori_esatti(conn, table, column, good, bad):
    for value in good:
        with conn.begin_nested() as savepoint:
            _insert_with(conn, table, column, value)
            savepoint.rollback()
    for value in bad:
        with pytest.raises(sa.exc.DBAPIError) as info, conn.begin_nested():
            _insert_with(conn, table, column, value)
        assert info.value.orig.args[0] == CHECK_FAILED, value


def test_partita_che_finisce_prima_di_iniziare_rifiutata(conn):
    with pytest.raises(sa.exc.DBAPIError) as info, conn.begin_nested():
        add_match(conn, finita_il="2026-09-28 09:00:00")
    assert info.value.orig.args[0] == CHECK_FAILED


def _message(conn, text):
    tot = add_user(conn, "Toto")
    nina = add_user(conn, "Nina")
    return run(
        conn,
        "INSERT INTO messaggi (mittente_id, destinatario_id, testo, inviato_il) "
        "VALUES (:a, :b, :t, '2026-09-28 10:00:00')",
        a=tot, b=nina, t=text,
    )


def test_messaggio_di_1000_caratteri_accettato_anche_con_accenti_ed_emoji(conn):
    _message(conn, "è" * 500 + "\U0001f0cf" * 500)
    assert count(conn, "SELECT CHAR_LENGTH(testo) FROM messaggi") == 1000


def test_messaggio_di_1001_caratteri_rifiutato(conn):
    with pytest.raises(sa.exc.DBAPIError) as info, conn.begin_nested():
        _message(conn, "a" * 1001)
    assert info.value.orig.args[0] == TOO_LONG
