"""P18: backup e ripristino del database (scripts/backup.py e scripts/ripristina.py).

Serve MySQL 8.0 acceso, con scripts/setup_db.sql già lanciato e i programmi mysqldump
e mysql (nel PATH o nella cartella di MySQL 8.0). Si usa SOLO il database dei test
(DB_NAME_TEST, che finisce con _test): all'inizio viene svuotato e ricreato con
migrate.py. I backup delle prove vanno in cartelle temporanee, mai in backups/.
Comando: python tests/esegui_tutti.py db
"""

import gzip
import importlib.util
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

import pytest
import sqlalchemy as sa

from config import TestingConfig, load_config

BASE_DIR = Path(__file__).resolve().parents[2]
TABLES = (
    "utenti", "rating", "partite", "giocatori_partita", "mosse_partita",
    "amicizie", "blocchi", "messaggi", "versione_schema",
)
CHAT_TEXT = "Amunì! 🃏 \"virgolette\" 'apici' \\ barra; -- non è un commento"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, BASE_DIR / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


migrate = _load("migrate")
ripristina = _load("ripristina")
backup = ripristina.backup
BackupError = backup.BackupError


@pytest.fixture(scope="module")
def url():
    if (BASE_DIR / "PRODUZIONE").exists():
        pytest.exit("Trovato il file PRODUZIONE: i test non partono in un'installazione vera.")
    url = load_config("testing").SQLALCHEMY_DATABASE_URI
    assert url.database.endswith("_test"), "i test usano solo un database che finisce con _test"
    try:
        backup.find_program("mysqldump")
        backup.find_program("mysql")
    except BackupError as exc:
        pytest.fail(str(exc), pytrace=False)
    return url


@pytest.fixture(scope="module")
def engine(url):
    engine = sa.create_engine(url)
    try:
        with engine.begin() as conn:
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
    migrate.migrate(url, report=lambda _msg: None)
    yield engine
    engine.dispose()


@pytest.fixture
def seeded(engine):
    """Dati di prova in tutte le tabelle (versione_schema la riempie migrate.py)."""
    statements = [
        (
            "INSERT INTO utenti (id, nome_utente, email, hash_password, avatar) VALUES "
            "(1, 'Toto', 'totò@esempio.it', 'scrypt:uno', 'coppe'), "
            "(2, 'Nina', 'nina@esempio.it', 'scrypt:due', NULL), "
            "(3, 'Peppi_3', 'peppi@esempio.it', 'scrypt:tre', 'denari')"
        ),
        (
            "INSERT INTO rating VALUES (1, '1v1', 1512.25, 290.5, 0.0599, '2026-09-28 10:00:00'), "
            "(2, '1v1', 1487.75, 290.5, 0.06, '2026-09-28 10:00:00')"
        ),
        (
            "INSERT INTO partite VALUES (1, '1v1', 300, TRUE, '2026-09-28 09:00:00', "
            "'2026-09-28 09:20:00', 'punteggio', 0, 310, 180)"
        ),
        "INSERT INTO giocatori_partita VALUES (1, 0, 0, 1, 'vittoria', FALSE), (1, 1, 1, 2, 'sconfitta', FALSE)",
        (
            "INSERT INTO mosse_partita VALUES (1, 1, 1, 0, 'canta', "
            "'{\"seme\": \"coppe\", \"punti\": 40, \"nota\": \"Càlati juncu\"}', '2026-09-28 09:01:02.345')"
        ),
        (
            "INSERT INTO amicizie (richiedente_id, destinatario_id, stato, richiesta_il, risposta_il) "
            "VALUES (1, 2, 'accettata', '2026-09-27 18:00:00', '2026-09-27 18:05:00')"
        ),
        "INSERT INTO blocchi VALUES (3, 1, '2026-09-28 08:00:00')",
        (
            "INSERT INTO messaggi (mittente_id, destinatario_id, testo, inviato_il) "
            "VALUES (1, 2, :testo, '2026-09-28 11:00:00.500')"
        ),
    ]
    with engine.begin() as conn:
        _clear(conn)
        for statement in statements:
            conn.execute(sa.text(statement), {"testo": CHAT_TEXT} if ":testo" in statement else {})
    yield engine
    with engine.begin() as conn:
        _clear(conn)


def _clear(conn):
    conn.execute(sa.text("SET FOREIGN_KEY_CHECKS = 0"))
    for table in TABLES:
        if table != "versione_schema":
            conn.execute(sa.text(f"DELETE FROM `{table}`"))
    conn.execute(sa.text("SET FOREIGN_KEY_CHECKS = 1"))


def snapshot(engine):
    """Tutte le righe di tutte le tabelle, in un ordine stabile."""
    with engine.connect() as conn:
        return {
            table: sorted((tuple(row) for row in conn.execute(sa.text(f"SELECT * FROM `{table}`"))), key=repr)
            for table in TABLES
        }


def change_everything(engine):
    with engine.begin() as conn:
        conn.execute(sa.text("DELETE FROM utenti WHERE id = 3"))
        conn.execute(sa.text("UPDATE rating SET valore = 1600 WHERE utente_id = 1"))
        conn.execute(sa.text("DELETE FROM partite"))
        conn.execute(sa.text(
            "INSERT INTO messaggi (mittente_id, destinatario_id, testo, inviato_il) "
            "VALUES (2, 1, 'nuovo', '2026-09-28 12:00:00')"
        ))
        conn.execute(sa.text("DELETE FROM versione_schema"))


# Il "Fatto quando" di P18


def test_backup_modifica_ripristino_dati_identici(url, seeded, tmp_path):
    before = snapshot(seeded)
    assert all(before[table] for table in TABLES), "ogni tabella deve avere dati di prova"

    path = backup.backup(url, tmp_path)
    change_everything(seeded)
    assert snapshot(seeded) != before

    ripristina.restore(url, path, url.database)
    assert snapshot(seeded) == before


def test_file_compresso_con_database_data_e_ora_nel_nome(url, seeded, tmp_path):
    when = datetime(2026, 9, 28, 21, 30, 5).astimezone()
    path = backup.backup(url, tmp_path, now=when)
    assert path == tmp_path / f"{url.database}_2026-09-28_213005.sql.gz"
    with gzip.open(path, "rb") as source:
        text = source.read().decode("utf-8")
    assert text.startswith("-- MySQL dump")
    assert "CREATE DATABASE" not in text and "USE `" not in text  # si può ricaricare in un altro database
    assert list(tmp_path.iterdir()) == [path]


def test_backup_non_riuscito_non_lascia_file(url, tmp_path):
    wrong = url.set(database="inesistente_p18_test")
    with pytest.raises(BackupError, match="mysqldump non è riuscito"):
        backup.backup(wrong, tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_stesso_secondo_non_sovrascrive(url, seeded, tmp_path):
    when = datetime(2026, 9, 28, 21, 30, 5).astimezone()
    backup.backup(url, tmp_path, now=when)
    with pytest.raises(BackupError, match="Esiste già"):
        backup.backup(url, tmp_path, now=when)


# Password e file di opzioni


def test_password_mai_sulla_riga_di_comando_e_file_di_opzioni_cancellato(url, seeded, tmp_path, monkeypatch):
    commands = []
    real_popen = subprocess.Popen

    def recording_popen(command, *args, **kwargs):
        commands.append(list(command))
        return real_popen(command, *args, **kwargs)

    monkeypatch.setattr(subprocess, "Popen", recording_popen)
    path = backup.backup(url, tmp_path)
    ripristina.restore(url, path, url.database)

    assert len(commands) == 2
    options = [arg.split("=", 1)[1] for command in commands for arg in command if arg.startswith("--defaults-extra-file=")]
    assert len(options) == 2
    assert all(not Path(option).exists() for option in options)
    if url.password:
        leaked = any(url.password in arg for command in commands for arg in command)
        assert not leaked, "la password compare sulla riga di comando"


def test_password_mai_stampata(url, seeded, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(TestingConfig, "BACKUP_DIR", tmp_path)
    assert backup.main([]) == 0
    (path,) = tmp_path.iterdir()
    assert ripristina.main([str(path), url.database], ask=_never_ask) == 0
    assert backup.main([]) in (0, 1)  # anche un secondo backup nello stesso secondo non stampa la password
    out = capsys.readouterr()
    if url.password:
        leaked = url.password in out.out + out.err
        assert not leaked, "la password compare nei messaggi"
    assert "Backup salvato:" in out.out and "Ripristino completato:" in out.out


def test_file_di_opzioni_con_caratteri_speciali(url):
    tricky = url.set(password='a"b\\c#d e')
    with backup.options_file(tricky) as path:
        text = Path(path).read_text(encoding="utf-8")
        assert 'password="a\\"b\\\\c#d e"' in text
    assert not Path(path).exists()


# Pulizia dei backup vecchi


def test_si_cancellano_solo_i_backup_piu_vecchi_del_limite(tmp_path):
    now = datetime(2026, 9, 28, 12, 0, 0).astimezone()

    def name(database, days):
        return f"{database}_{(now - timedelta(days=days)).strftime(backup.TIME_FORMAT)}.sql.gz"

    old = [name("cinquecento_dev", 20), name("cinquecento_dev", 15), name("cinquecento_demo", 30)]
    kept = [
        name("cinquecento_dev", 13), name("cinquecento_dev", 0),
        "appunti.txt", "copia_a_mano.sql.gz", "cinquecento_2020-13-45_000000.sql.gz",
        name("cinquecento_dev", 40) + ".parziale",
    ]
    for file_name in old + kept:
        (tmp_path / file_name).write_bytes(b"x")

    removed = backup.remove_old_backups(tmp_path, 14, now=now)
    assert sorted(p.name for p in removed) == sorted(old)
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted(kept)


def test_giorni_di_conservazione_da_config():
    assert load_config("testing").BACKUP_RETENTION_DAYS == 14  # provvisorio, D10


# Ripristino: conferma e controlli


def _never_ask(_prompt):
    raise AssertionError("per un database di test non si chiede conferma")


def _fake_backup(tmp_path):
    path = tmp_path / "cinquecento_dev_2026-09-28_120000.sql.gz"
    with gzip.open(path, "wb") as out:
        out.write(b"-- MySQL dump 10.13\n")
    return path


@pytest.mark.parametrize("answer", ["", "no", "CINQUECENTO_DEV", "cinquecento"])
def test_database_non_di_test_senza_conferma_non_si_tocca(tmp_path, monkeypatch, capsys, answer):
    calls = []
    monkeypatch.setattr(ripristina, "restore", lambda *args: calls.append(args))
    path = _fake_backup(tmp_path)
    assert ripristina.main([str(path), "cinquecento_dev"], ask=lambda _prompt: answer) == 1
    assert calls == []
    assert "Ripristino annullato" in capsys.readouterr().out


def test_database_non_di_test_con_conferma(tmp_path, monkeypatch):
    calls = []
    prompts = []
    monkeypatch.setattr(ripristina, "restore", lambda *args: calls.append(args))
    path = _fake_backup(tmp_path)

    def ask(prompt):
        prompts.append(prompt)
        return " cinquecento_dev "

    assert ripristina.main([str(path), "cinquecento_dev"], ask=ask) == 0
    assert len(prompts) == 1 and "cinquecento_dev" in prompts[0]
    assert len(calls) == 1 and calls[0][2] == "cinquecento_dev"


def test_conferma_interrotta_non_tocca_niente(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(ripristina, "restore", lambda *args: calls.append(args))

    def interrupted(_prompt):
        raise EOFError

    assert ripristina.main([str(_fake_backup(tmp_path)), "cinquecento_dev"], ask=interrupted) == 1
    assert calls == []


@pytest.mark.parametrize("kind", ["mancante", "estensione", "non_compresso", "troncato", "non_backup"])
def test_file_non_valido_rifiutato_senza_toccare_il_database(url, seeded, tmp_path, kind):
    before = snapshot(seeded)
    good = backup.backup(url, tmp_path / "buoni")
    path = tmp_path / "prova.sql.gz"
    if kind == "mancante":
        path = tmp_path / "non_esiste.sql.gz"
    elif kind == "estensione":
        path = tmp_path / "prova.sql"
        path.write_bytes(gzip.decompress(good.read_bytes()))
    elif kind == "non_compresso":
        path.write_bytes(b"-- MySQL dump\nDROP TABLE utenti;\n")
    elif kind == "troncato":
        data = good.read_bytes()
        path.write_bytes(data[: len(data) // 2])
    else:
        path.write_bytes(gzip.compress(b"DROP TABLE utenti;\n"))

    with pytest.raises(BackupError):
        ripristina.restore(url, path, url.database)
    assert snapshot(seeded) == before


def test_errore_di_mysql_nel_ripristino(url, seeded, tmp_path):
    path = backup.backup(url, tmp_path)
    with pytest.raises(BackupError, match="mysql si è fermato"):
        ripristina.restore(url, path, "inesistente_p18_test")


@pytest.mark.parametrize("name", ["", "--help", "a;b", "cinque cento", "x" * 65])
def test_nome_del_database_non_valido(url, tmp_path, name):
    with pytest.raises(BackupError, match="Nome del database non valido"):
        ripristina.restore(url, _fake_backup(tmp_path), name)


def test_uso_sbagliato(capsys):
    assert backup.main(["troppo"]) == 2
    assert ripristina.main(["solo_il_file.sql.gz"]) == 2
    assert "Uso:" in capsys.readouterr().err
