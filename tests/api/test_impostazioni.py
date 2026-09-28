"""P17: impostazioni: avatar e cancellazione dell'account.

Serve MySQL con scripts/setup_db.sql già lanciato: si usa SOLO il database dei
test, che all'inizio viene svuotato e ricreato con migrate.py; prima di ogni prova
le tabelle si svuotano. Comando: python tests/esegui_tutti.py api
"""

import importlib.util
import re
from pathlib import Path

import pytest
import sqlalchemy as sa

from app import create_app
from app.extensions import db
from app.services import auth_service, avatars
from app.services.auth_service import (
    AVATAR_INVALID,
    DELETE_IN_GAME,
    DELETE_NO_PASSWORD,
    DELETE_WRONG_PASSWORD,
    LOGIN_FAILED,
    LOGIN_LOCKED,
    LoginLimiter,
)

BASE_DIR = Path(__file__).resolve().parents[2]
PASSWORD = "Password-di-prova-17"
TABLES = ("messaggi", "blocchi", "amicizie", "mosse_partita", "giocatori_partita", "partite", "rating", "utenti")


def _load_migrate():
    spec = importlib.util.spec_from_file_location("migrate", BASE_DIR / "scripts" / "migrate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def app():
    app = create_app("testing")
    app.config["WTF_CSRF_ENABLED"] = False
    with app.app_context():
        url = db.engine.url
        assert url.database.endswith("_test"), "i test usano solo un database che finisce con _test"
        try:
            with db.engine.begin() as conn:
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
        _load_migrate().migrate(url, report=lambda _msg: None)
    return app


@pytest.fixture
def client(app, monkeypatch):
    with app.app_context():
        for table in TABLES:
            db.session.execute(sa.text(f"DELETE FROM {table}"))
        db.session.commit()
    monkeypatch.setattr(auth_service, "limiter", LoginLimiter())
    return app.test_client()


def register(client, username="Mario", email=None):
    email = email or f"{username.lower()}@esempio.it"
    response = client.post("/auth/register", data={
        "username": username, "email": email, "password": PASSWORD, "confirm": PASSWORD,
    })
    assert response.status_code == 302, "registrazione non riuscita"
    client.get("/")  # mostra (e così consuma) il messaggio "Benvenuto"


def logged_in(client):
    with client.session_transaction() as session:
        return "_user_id" in session


def flashes(client):
    with client.session_transaction() as session:
        return [message for _category, message in session.get("_flashes", [])]


def scalar(app, sql, **params):
    with app.app_context():
        return db.session.execute(sa.text(sql), params).scalar()


def user_id(app, username):
    return scalar(app, "SELECT id FROM utenti WHERE nome_utente = :u", u=username)


# Elenco degli avatar (D29)


def test_dodici_avatar_con_codici_validi():
    assert len(avatars.AVATARS) == 12
    for code, name in avatars.AVATARS.items():
        assert re.fullmatch(r"[a-z_]{1,30}", code), code
        assert name
    semi = {"coppe", "denari", "spade", "bastoni"}
    assert semi <= set(avatars.AVATARS)


@pytest.mark.parametrize("value", [None, "", "Coppe", "drago", "coppe ", 3, ["coppe"]])
def test_is_valid_rifiuta_i_valori_fuori_elenco(value):
    assert not avatars.is_valid(value)


# Pagina


def test_pagina_solo_con_il_login(client):
    response = client.get("/profile/settings")
    assert response.status_code == 302
    assert response.location.startswith("/auth/login")


def test_pagina_mostra_tutti_gli_avatar_e_la_cancellazione(client):
    register(client)
    page = client.get("/profile/settings").get_data(as_text=True)
    for code, name in avatars.AVATARS.items():
        assert f'data-avatar="{code}"' in page
        assert name in page
    assert 'data-avatar=""' in page and "Iniziale" in page
    assert re.search(r'value=""\s+checked', page), "senza avatar è scelta l'iniziale"
    assert "data-delete-form" in page and "data-delete-open" in page
    assert page.count("js/pages/profile.js") == 1


def test_template_estende_base_senza_stile_ne_script_scritti_dentro():
    source = (BASE_DIR / "app" / "templates" / "profile" / "settings.html").read_text(encoding="utf-8")
    assert source.lstrip().startswith('{% extends "base.html" %}')
    assert "<style" not in source
    assert re.findall(r"<script[^>]*>", source) == [
        '<script type="module" src="{{ url_for(\'static\', filename=\'js/pages/profile.js\') }}">'
    ]


def test_script_della_pagina_avvia_la_navbar_e_usa_la_finestra_nella_pagina():
    source = (BASE_DIR / "app" / "static" / "js" / "pages" / "profile.js").read_text(encoding="utf-8")
    assert "initLayout()" in source
    assert "openModal" in source
    for forbidden in ("alert(", "confirm(", "prompt(", "innerHTML"):
        assert forbidden not in source


# Avatar


def test_avatar_scelto_viene_salvato(app, client):
    register(client)
    response = client.post("/profile/avatar", data={"avatar": "re_denari"})
    assert response.status_code == 302 and response.location == "/profile/settings"
    assert flashes(client) == ["Avatar salvato."]
    assert scalar(app, "SELECT avatar FROM utenti WHERE nome_utente = 'Mario'") == "re_denari"
    page = client.get("/profile/settings").get_data(as_text=True)
    assert re.search(r'value="re_denari"\s+checked', page)
    assert 'data-avatar="re_denari"' in client.get("/").get_data(as_text=True)  # <body data-avatar>


def test_iniziale_toglie_l_avatar(app, client):
    register(client)
    client.post("/profile/avatar", data={"avatar": "coppe"})
    client.post("/profile/avatar", data={"avatar": ""})
    assert scalar(app, "SELECT avatar FROM utenti WHERE nome_utente = 'Mario'") is None


@pytest.mark.parametrize("value", ["drago", "Coppe", "coppe ", "x" * 40, "<b>coppe</b>"])
def test_avatar_fuori_elenco_rifiutato(app, client, value):
    register(client)
    client.post("/profile/avatar", data={"avatar": "spade"})
    client.get("/profile/settings")  # consuma il messaggio "Avatar salvato"
    response = client.post("/profile/avatar", data={"avatar": value})
    assert response.status_code == 302
    assert flashes(client) == [AVATAR_INVALID]
    assert scalar(app, "SELECT avatar FROM utenti WHERE nome_utente = 'Mario'") == "spade"


def test_avatar_mancante_rifiutato(app, client):
    register(client)
    client.post("/profile/avatar", data={})
    assert AVATAR_INVALID in flashes(client)
    assert scalar(app, "SELECT avatar FROM utenti WHERE nome_utente = 'Mario'") is None


def test_avatar_solo_con_il_login(app, client):
    response = client.post("/profile/avatar", data={"avatar": "coppe"})
    assert response.status_code == 302 and response.location.startswith("/auth/login")


def test_moduli_senza_codice_csrf_rifiutati(app):
    app.config["WTF_CSRF_ENABLED"] = True
    try:
        client = app.test_client()
        assert client.post("/profile/avatar", data={"avatar": "coppe"}).status_code == 400
        assert client.post("/profile/delete", data={"password": PASSWORD}).status_code == 400
    finally:
        app.config["WTF_CSRF_ENABLED"] = False


# Cancellazione dell'account


def _game_and_friends(app):
    """Mario e Nina: una partita, rating, amicizia, blocco e messaggi."""
    mario, nina = user_id(app, "Mario"), user_id(app, "Nina")
    with app.app_context():
        for sql in (
            (
                "INSERT INTO partite VALUES (1, '1v1', 300, TRUE, '2026-09-28 09:00:00', "
                "'2026-09-28 09:20:00', 'punteggio', 0, 310, 180)"
            ),
            (
                f"INSERT INTO giocatori_partita VALUES (1, 0, 0, {mario}, 'vittoria', FALSE), "
                f"(1, 1, 1, {nina}, 'sconfitta', FALSE)"
            ),
            (
                f"INSERT INTO rating VALUES ({mario}, '1v1', 1512, 290, 0.06, '2026-09-28 09:20:00'), "
                f"({nina}, '1v1', 1488, 290, 0.06, '2026-09-28 09:20:00')"
            ),
            f"INSERT INTO amicizie (richiedente_id, destinatario_id, stato) VALUES ({mario}, {nina}, 'accettata')",
            f"INSERT INTO blocchi (bloccante_id, bloccato_id) VALUES ({nina}, {mario})",
            (
                f"INSERT INTO messaggi (mittente_id, destinatario_id, testo, inviato_il) VALUES "
                f"({mario}, {nina}, 'ciao', '2026-09-28 10:00:00'), ({nina}, {mario}, 'ciao!', '2026-09-28 10:01:00')"
            ),
        ):
            db.session.execute(sa.text(sql))
        db.session.commit()
    return mario, nina


def test_cancellazione_con_la_password_giusta(app, client):
    other = app.test_client()
    register(other, "Nina")
    register(client)
    mario, nina = _game_and_friends(app)

    response = client.post("/profile/delete", data={"password": PASSWORD})
    assert response.status_code == 302 and response.location == "/"
    assert not logged_in(client)
    assert any("Account cancellato" in message for message in flashes(client))

    # L'utente non esiste più e il login fallisce
    assert user_id(app, "Mario") is None
    login = client.post("/auth/login", data={"username": "Mario", "password": PASSWORD})
    assert login.status_code == 200 and LOGIN_FAILED in login.get_data(as_text=True)

    # D6: la partita resta, con "utente eliminato"; rating, amicizie, blocchi e messaggi spariscono
    assert scalar(app, "SELECT COUNT(*) FROM partite") == 1
    assert scalar(app, "SELECT COUNT(*) FROM giocatori_partita WHERE partita_id = 1") == 2
    assert scalar(app, "SELECT COUNT(*) FROM giocatori_partita WHERE posto = 0 AND utente_id IS NULL") == 1
    assert scalar(app, "SELECT utente_id FROM giocatori_partita WHERE posto = 1") == nina
    assert scalar(app, "SELECT COUNT(*) FROM rating WHERE utente_id = :m", m=mario) == 0
    assert scalar(app, "SELECT COUNT(*) FROM rating WHERE utente_id = :n", n=nina) == 1
    for table in ("amicizie", "blocchi", "messaggi"):
        assert scalar(app, f"SELECT COUNT(*) FROM {table}") == 0, table
    assert user_id(app, "Nina") == nina


@pytest.mark.parametrize(("password", "message"), [
    ("", DELETE_NO_PASSWORD),
    (None, DELETE_NO_PASSWORD),
    ("Password-sbagliata", DELETE_WRONG_PASSWORD),
])
def test_senza_la_password_giusta_l_account_resta(app, client, password, message):
    register(client)
    data = {} if password is None else {"password": password}
    response = client.post("/profile/delete", data=data)
    assert response.status_code == 302 and response.location == "/profile/settings"
    assert message in flashes(client)
    assert user_id(app, "Mario") is not None
    assert logged_in(client)


def test_troppe_password_sbagliate_bloccano(app, client):
    register(client)
    attempts = app.config["LOGIN_MAX_ATTEMPTS"]
    for _ in range(attempts):
        client.post("/profile/delete", data={"password": "Password-sbagliata"})
    assert LOGIN_LOCKED in flashes(client)
    client.get("/profile/settings")  # consuma i messaggi precedenti
    client.post("/profile/delete", data={"password": PASSWORD})
    assert flashes(client) == [LOGIN_LOCKED]
    assert user_id(app, "Mario") is not None


def test_con_una_partita_in_corso_non_si_cancella(app, client, monkeypatch):
    register(client)
    mario = user_id(app, "Mario")
    monkeypatch.setattr(auth_service, "find_room_of_user", lambda uid: object() if uid == mario else None)
    client.post("/profile/delete", data={"password": PASSWORD})
    assert flashes(client) == [DELETE_IN_GAME]
    assert user_id(app, "Mario") == mario
    assert logged_in(client)


def test_cancellazione_solo_con_post_e_con_il_login(client):
    assert client.post("/profile/delete", data={"password": PASSWORD}).location.startswith("/auth/login")
    register(client)
    assert client.get("/profile/delete").status_code == 405


def test_password_mai_nei_log(client, caplog):
    caplog.set_level("DEBUG")
    register(client)
    client.post("/profile/delete", data={"password": "Password-sbagliata"})
    client.post("/profile/delete", data={"password": PASSWORD})
    assert "Account cancellato" in caplog.text
    for secret in (PASSWORD, "Password-sbagliata", "Mario", "mario@esempio.it"):
        assert secret not in caplog.text
