"""P17: impostazioni: avatar e cancellazione dell'account.

Dal passo 6 della migrazione la pagina /profile/settings la disegna la SPA e i dati
passano dalle rotte JSON /api/profile/ (app/blueprints/profile/api.py).

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
from tests import accounts
from tests.spa import needs_spa

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
    response = accounts.register(client, username, email, PASSWORD)
    assert accounts.ok(response), "registrazione non riuscita"
    client.get("/api/auth/session")  # legge (e così consuma) il messaggio "Benvenuto", come la home React


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


# Pagina (dal passo 6 della migrazione la disegna la SPA)


def test_pagina_solo_con_il_login(client):
    response = client.get("/profile/settings")
    assert response.status_code == 302
    assert response.location.startswith("/auth/login")


def test_pagina_della_spa_con_il_login(client):
    needs_spa()
    register(client)
    response = client.get("/profile/settings")
    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert '<div id="root">' in page  # la SPA: la pagina la disegna React
    assert "profile.js" not in page
    assert not (BASE_DIR / "app" / "templates" / "profile" / "settings.html").exists()
    assert not (BASE_DIR / "app" / "static" / "js" / "pages" / "profile.js").exists()


def test_elenco_degli_avatar(client):
    register(client)
    body = client.get("/api/profile/avatars").get_json()
    assert body["ok"] is True
    assert body["data"]["avatars"] == [{"code": code, "name": name} for code, name in avatars.AVATARS.items()]


# Avatar


def save_avatar(client, value, raw=None):
    """POST /api/profile/avatar con {"avatar": value} (o il corpo `raw`, se c'è)."""
    return client.post("/api/profile/avatar", json={"avatar": value} if raw is None else raw)


def test_avatar_scelto_viene_salvato(app, client):
    register(client)
    response = save_avatar(client, "re_denari")
    assert accounts.ok(response) and response.get_json()["data"] == {"redirect": "/profile/settings"}
    assert flashes(client) == ["Avatar salvato."]
    assert scalar(app, "SELECT avatar FROM utenti WHERE nome_utente = 'Mario'") == "re_denari"
    session = client.get("/api/auth/session").get_json()["data"]
    assert session["user"]["avatar"] == "re_denari"  # la navbar della SPA lo legge da qui


def test_iniziale_toglie_l_avatar(app, client):
    register(client)
    save_avatar(client, "coppe")
    save_avatar(client, "")
    assert scalar(app, "SELECT avatar FROM utenti WHERE nome_utente = 'Mario'") is None


@pytest.mark.parametrize("value", ["drago", "Coppe", "coppe ", "x" * 40, "<b>coppe</b>", 3, None, ["coppe"]])
def test_avatar_fuori_elenco_rifiutato(app, client, value):
    register(client)
    save_avatar(client, "spade")
    client.get("/api/auth/session")  # consuma il messaggio "Avatar salvato"
    response = save_avatar(client, value)
    assert response.status_code == 400
    error = response.get_json()["error"]
    assert error["code"] == "invalid_data" and error["message"] == AVATAR_INVALID
    assert error["fields"] == {"avatar": [AVATAR_INVALID]}
    assert flashes(client) == []
    assert scalar(app, "SELECT avatar FROM utenti WHERE nome_utente = 'Mario'") == "spade"


@pytest.mark.parametrize("raw", [{}, [], "coppe"])
def test_avatar_mancante_o_corpo_sbagliato_rifiutato(app, client, raw):
    register(client)
    response = save_avatar(client, None, raw=raw)
    assert response.status_code == 400 and response.get_json()["error"]["message"] == AVATAR_INVALID
    assert scalar(app, "SELECT avatar FROM utenti WHERE nome_utente = 'Mario'") is None


def test_rotte_solo_con_il_login(client):
    for method, path, body in (("get", "/api/profile/avatars", None),
                               ("post", "/api/profile/avatar", {"avatar": "coppe"}),
                               ("post", "/api/profile/delete", {"password": PASSWORD})):
        response = getattr(client, method)(path, json=body)
        assert response.status_code == 401, path
        assert response.get_json()["error"]["code"] == "not_logged_in", path


def test_rotte_vecchie_tolte(client):
    register(client)
    assert client.post("/profile/avatar", data={"avatar": "coppe"}).status_code in (404, 405)
    assert client.post("/profile/delete", data={"password": PASSWORD}).status_code in (404, 405)


def test_senza_codice_csrf_rifiutate(app):
    app.config["WTF_CSRF_ENABLED"] = True
    try:
        client = app.test_client()
        assert client.post("/api/profile/avatar", json={"avatar": "coppe"}).status_code == 400
        assert client.post("/api/profile/delete", json={"password": PASSWORD}).status_code == 400
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


def delete(client, password):
    """POST /api/profile/delete con {"password": password} (senza il campo se None)."""
    return client.post("/api/profile/delete", json={} if password is None else {"password": password})


def test_cancellazione_con_la_password_giusta(app, client):
    other = app.test_client()
    register(other, "Nina")
    register(client)
    mario, nina = _game_and_friends(app)

    response = delete(client, PASSWORD)
    assert accounts.ok(response) and response.get_json()["data"] == {"redirect": "/"}
    assert not logged_in(client)
    assert any("Account cancellato" in message for message in flashes(client))

    # L'utente non esiste più e il login fallisce
    assert user_id(app, "Mario") is None
    login = accounts.login(client, "Mario", PASSWORD)
    assert login.status_code == 403 and LOGIN_FAILED in accounts.messages(login)

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
    response = delete(client, password)
    assert response.status_code == 400
    error = response.get_json()["error"]
    assert error["code"] == "invalid_data" and error["message"] == message
    assert error["fields"] == {"password": [message]}
    assert user_id(app, "Mario") is not None
    assert logged_in(client)


def test_password_che_non_e_un_testo_rifiutata(app, client):
    register(client)
    response = delete(client, 12345)
    assert response.status_code == 400 and response.get_json()["error"]["message"] == DELETE_NO_PASSWORD
    assert user_id(app, "Mario") is not None


def test_troppe_password_sbagliate_bloccano(app, client):
    register(client)
    attempts = app.config["LOGIN_MAX_ATTEMPTS"]
    answers = [delete(client, "Password-sbagliata") for _ in range(attempts)]
    assert answers[-1].status_code == 403
    assert answers[-1].get_json()["error"] == {"code": "not_allowed", "message": LOGIN_LOCKED}
    # Bloccato: anche con la password giusta non si cancella
    response = delete(client, PASSWORD)
    assert response.status_code == 403 and response.get_json()["error"]["message"] == LOGIN_LOCKED
    assert user_id(app, "Mario") is not None


def test_con_una_partita_in_corso_non_si_cancella(app, client, monkeypatch):
    register(client)
    mario = user_id(app, "Mario")
    monkeypatch.setattr(auth_service, "find_room_of_user", lambda uid: object() if uid == mario else None)
    response = delete(client, PASSWORD)
    assert response.status_code == 403
    assert response.get_json()["error"] == {"code": "not_allowed", "message": DELETE_IN_GAME}
    assert user_id(app, "Mario") == mario
    assert logged_in(client)


def test_cancellazione_solo_con_post(client):
    register(client)
    assert client.get("/api/profile/delete").status_code == 405


def test_password_mai_nei_log(client, caplog):
    caplog.set_level("DEBUG")
    register(client)
    delete(client, "Password-sbagliata")
    delete(client, PASSWORD)
    assert "Account cancellato" in caplog.text
    for secret in (PASSWORD, "Password-sbagliata", "Mario", "mario@esempio.it"):
        assert secret not in caplog.text
