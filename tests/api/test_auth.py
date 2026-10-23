"""P16: registrazione, login e logout.

Dal passo 4 della migrazione le pagine /auth/login e /auth/register sono della SPA e i
dati vanno alle rotte JSON /api/auth/ (app/blueprints/auth/api.py): i controlli sono
quelli di prima, sulle risposte JSON. L'aspetto delle pagine lo controlla
tests/frontend/test_pagine_accesso.py.

Serve MySQL con scripts/setup_db.sql già lanciato: si usa SOLO il database dei
test, che all'inizio viene svuotato e ricreato con migrate.py; prima di ogni prova
la tabella utenti si svuota. Comando: python tests/esegui_tutti.py api
"""

import importlib.util
from pathlib import Path

import pytest
import sqlalchemy as sa
from flask_login import login_required

from app import create_app
from app.extensions import db
from app.models.user import User
from app.services import auth_service
from app.services.auth_service import (
    EMAIL_TAKEN,
    LOGIN_FAILED,
    LOGIN_LOCKED,
    USERNAME_TAKEN,
    LoginLimiter,
)
from tests import accounts

BASE_DIR = Path(__file__).resolve().parents[2]
PASSWORD = "Password-di-prova-1"


def _load_migrate():
    spec = importlib.util.spec_from_file_location("migrate", BASE_DIR / "scripts" / "migrate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _make_app(csrf):
    app = create_app("testing")
    app.config["WTF_CSRF_ENABLED"] = csrf

    @app.route("/_prova/protetta")
    @login_required
    def protected():
        return "pagina protetta"

    return app


@pytest.fixture(scope="module")
def app():
    app = _make_app(csrf=False)
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
        db.session.execute(sa.text("DELETE FROM utenti"))
        db.session.commit()
    monkeypatch.setattr(auth_service, "limiter", LoginLimiter())
    return app.test_client()


def register(client, username="Mario", email="mario@esempio.it", password=PASSWORD, confirm=None):
    return accounts.register(client, username, email, password, confirm)


def login(client, username="Mario", password=PASSWORD, next_url=""):
    return accounts.login(client, username, password, next_url)


def redirect_of(response):
    """Dove manda la risposta di un login o di una registrazione riusciti."""
    assert accounts.ok(response), response.get_json()
    return response.get_json()["data"]["redirect"]


def logged_in(client):
    with client.session_transaction() as session:
        return "_user_id" in session


def users(app):
    with app.app_context():
        return db.session.scalars(sa.select(User)).all()


def page_text(response):
    """I messaggi di errore della risposta JSON (error.message e quelli dei campi)."""
    return accounts.messages(response)


# --- Registrazione ---


def test_registrazione_ok_entra_e_torna_alla_home(app, client):
    response = register(client)
    assert redirect_of(response) == "/"
    assert logged_in(client)
    # Il messaggio la home React lo legge da GET /api/auth/session (dal lotto 9b-1)
    flashes = client.get("/api/auth/session").get_json()["data"]["flashes"]
    assert [flash["message"] for flash in flashes] == ["Benvenuto, Mario!"]
    [user] = users(app)
    assert (user.username, user.email) == ("Mario", "mario@esempio.it")


def test_password_mai_in_chiaro_nel_database(app, client):
    register(client)
    with app.app_context():
        stored = db.session.execute(sa.text("SELECT hash_password FROM utenti")).scalar()
    assert PASSWORD not in stored
    assert stored.startswith("scrypt:")


def test_username_duplicato_rifiutato(app, client):
    register(client)
    client.post("/api/auth/logout")
    response = register(client, email="altro@esempio.it")
    assert response.status_code == 400
    assert response.get_json()["error"]["fields"] == {"username": [USERNAME_TAKEN]}
    assert len(users(app)) == 1


def test_username_con_maiuscole_diverse_accettato(app, client):
    register(client)
    client.post("/api/auth/logout")
    assert accounts.ok(register(client, username="mario", email="altro@esempio.it"))
    assert sorted(u.username for u in users(app)) == ["Mario", "mario"]


def test_email_duplicata_rifiutata_anche_con_maiuscole(app, client):
    register(client)
    client.post("/api/auth/logout")
    response = register(client, username="Luigi", email="Mario@Esempio.it")
    assert response.get_json()["error"]["fields"] == {"email": [EMAIL_TAKEN]}
    assert len(users(app)) == 1


@pytest.mark.parametrize(("fields", "message"), [
    ({"username": "ab"}, "da 3 a 20 caratteri"),
    ({"username": "a" * 21}, "da 3 a 20 caratteri"),
    ({"username": "mario rossi"}, "solo lettere, numeri e _"),
    ({"username": "màrio"}, "solo lettere, numeri e _"),
    # P137 (R1 di REVIEW.md): in Python "$" vale anche prima di un a-capo finale, e
    # "Mario\n" nelle pagine si vedrebbe come "Mario"
    ({"username": "Mario\n"}, "solo lettere, numeri e _"),
    ({"email": "non-una-email"}, "email valida"),
    ({"email": "mario@esempio.it\n"}, "email valida"),
    ({"password": "corta1"}, "almeno 8 caratteri"),
    ({"confirm": "Un-altra-password"}, "non coincidono"),
])
def test_dati_non_validi_rifiutati_con_messaggio(app, client, fields, message):
    response = register(client, **fields)
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_data"
    assert message in page_text(response)
    assert users(app) == []
    assert not logged_in(client)


# --- Regole della password (P61, D8) ---

NO_UPPER = "almeno una lettera maiuscola"
NO_NUMBER = "almeno un numero"
NO_SYMBOL = "almeno un simbolo"


@pytest.mark.parametrize(("password", "missing"), [
    ("password-di-prova-1", {NO_UPPER}),
    ("Password-di-prova", {NO_NUMBER}),
    ("Passworddiprova1", {NO_SYMBOL}),
    ("Password di prova 1", {NO_SYMBOL}),       # lo spazio non è un simbolo
    ("passworddiprova", {NO_UPPER, NO_NUMBER, NO_SYMBOL}),
    ("PASSWORD1234", {NO_SYMBOL}),
])
def test_password_senza_una_regola_rifiutata_con_un_messaggio_per_regola(app, client, password, missing):
    text = page_text(register(client, password=password))
    for rule in (NO_UPPER, NO_NUMBER, NO_SYMBOL):
        assert (f"La password deve contenere {rule}" in text) == (rule in missing), rule
    assert users(app) == []
    assert not logged_in(client)


def test_password_corta_senza_regole_dice_tutto_quello_che_manca(app, client):
    text = page_text(register(client, password="corta"))
    assert "almeno 8 caratteri" in text
    for rule in (NO_UPPER, NO_NUMBER, NO_SYMBOL):
        assert f"La password deve contenere {rule}" in text
    assert users(app) == []


@pytest.mark.parametrize("password", [
    "Password-di-prova-1",
    "Àbcdefg1!",            # maiuscola accentata
    "Abcdefg1€",            # qualunque segno vale come simbolo
    "abcdefG9.",
    "Aa1_Aa1_",             # esattamente 8 caratteri
])
def test_password_con_tutte_le_regole_accettata(app, client, password):
    response = register(client, password=password)
    assert accounts.ok(response)
    assert len(users(app)) == 1


def test_account_con_una_password_vecchia_entra_ancora(app, client):
    """Le regole valgono solo per le password nuove: il login non le controlla."""
    with app.app_context():
        auth_service.register("Vecchio", "vecchio@esempio.it", "semplice")
    response = login(client, username="Vecchio", password="semplice")
    assert accounts.ok(response)
    assert logged_in(client)


# --- Login e logout ---


def test_login_ok(client):
    register(client)
    client.post("/api/auth/logout")
    assert not logged_in(client)
    response = login(client)
    assert redirect_of(response) == "/"
    assert logged_in(client)


def test_password_sbagliata_e_utente_inesistente_stesso_messaggio(client):
    register(client)
    client.post("/api/auth/logout")
    response = login(client, password="Sbagliata-123")
    assert response.status_code == 403 and response.get_json()["error"]["code"] == "not_allowed"
    wrong_password = page_text(response)
    unknown_user = page_text(login(client, username="Nessuno"))
    assert LOGIN_FAILED in wrong_password
    assert LOGIN_FAILED in unknown_user
    assert not logged_in(client)


def test_username_con_maiuscole_diverse_non_entra(client):
    register(client)
    client.post("/api/auth/logout")
    assert LOGIN_FAILED in page_text(login(client, username="mario"))


def test_dopo_il_logout_le_pagine_protette_rimandano_al_login(client):
    register(client)
    assert client.get("/_prova/protetta").get_data(as_text=True) == "pagina protetta"
    response = client.post("/api/auth/logout")
    assert response.status_code == 200
    response = client.get("/_prova/protetta")
    assert response.status_code == 302
    assert response.location.startswith("/auth/login?next=")


def test_dopo_il_login_si_torna_alla_pagina_chiesta(client):
    register(client)
    client.post("/api/auth/logout")
    assert redirect_of(login(client, next_url="/_prova/protetta")) == "/_prova/protetta"


@pytest.mark.parametrize("target", ["//sito-esterno.it", "https://sito-esterno.it", "/\\sito-esterno.it"])
def test_dopo_il_login_mai_verso_un_altro_sito(client, target):
    register(client)
    client.post("/api/auth/logout")
    assert redirect_of(login(client, next_url=target)) == "/"


def test_logout_solo_con_post(client):
    register(client)
    assert client.get("/api/auth/logout").status_code == 405
    assert logged_in(client)


# Lotto 9c: il logout è una rotta JSON sotto /api/, come le altre della SPA
def test_logout_risponde_in_json_e_toglie_il_login(client):
    register(client)
    response = client.post("/api/auth/logout", json={})
    assert response.status_code == 200
    assert response.get_json() == {"ok": True, "data": {"redirect": "/"}}
    assert not logged_in(client)


def test_logout_senza_login_non_e_un_errore(client):
    response = client.post("/api/auth/logout", json={})
    assert response.get_json() == {"ok": True, "data": {"redirect": "/"}}


def test_il_vecchio_logout_non_esiste_piu(client):
    register(client)
    assert client.post("/auth/logout").status_code == 404
    assert logged_in(client)


def test_chi_ha_gia_fatto_il_login_torna_alla_home(client):
    register(client)
    assert client.get("/auth/login").location == "/"
    assert client.get("/auth/register").location == "/"


def test_sessione_con_id_non_valido_non_entra(app):
    with app.app_context():
        assert auth_service.load_user("abc") is None
        assert auth_service.load_user("999999") is None


# --- Troppi tentativi ---


def test_dopo_5_errori_si_aspetta_anche_con_la_password_giusta(app, client, monkeypatch):
    now = [1000.0]
    monkeypatch.setattr(auth_service, "limiter", LoginLimiter(clock=lambda: now[0]))
    register(client)
    client.post("/api/auth/logout")
    attempts = app.config["LOGIN_MAX_ATTEMPTS"]
    for _ in range(attempts - 1):
        assert LOGIN_FAILED in page_text(login(client, password="Sbagliata-123"))
    assert LOGIN_LOCKED in page_text(login(client, password="Sbagliata-123"))
    assert LOGIN_LOCKED in page_text(login(client))
    assert not logged_in(client)

    now[0] += app.config["LOGIN_LOCK_SECONDS"]
    assert accounts.ok(login(client))
    assert logged_in(client)


def test_login_riuscito_azzera_gli_errori(app, client):
    register(client)
    client.post("/api/auth/logout")
    attempts = app.config["LOGIN_MAX_ATTEMPTS"]
    for _ in range(attempts - 1):
        login(client, password="Sbagliata-123")
    assert accounts.ok(login(client))
    client.post("/api/auth/logout")
    for _ in range(attempts - 1):
        assert LOGIN_FAILED in page_text(login(client, password="Sbagliata-123"))


def test_il_blocco_vale_solo_per_quello_username(client):
    register(client)
    client.post("/api/auth/logout")
    for _ in range(10):
        login(client, username="Altro", password="Sbagliata-123")
    assert accounts.ok(login(client))


def test_errori_vecchi_dimenticati():
    now = [0.0]
    limiter = LoginLimiter(clock=lambda: now[0])
    for _ in range(4):
        assert not limiter.record_failure("Mario", 5, 300)
    now[0] += 300
    assert not limiter.record_failure("Mario", 5, 300)  # riparte da 1
    assert not limiter.is_locked("Mario")


def test_username_inventati_non_restano_in_memoria():
    now = [0.0]
    limiter = LoginLimiter(clock=lambda: now[0])
    for i in range(LoginLimiter.SWEEP_SIZE):
        limiter.record_failure(f"finto{i}", 5, 300)
    now[0] += 301
    limiter.record_failure("Mario", 5, 300)
    assert list(limiter._entries) == ["Mario"]


# --- Login con nome utente o email (P96) ---


def test_si_entra_con_l_email(client):
    register(client)
    client.post("/api/auth/logout")
    assert accounts.ok(login(client, username="mario@esempio.it"))
    assert logged_in(client)


def test_l_email_non_distingue_le_maiuscole(client):
    # Come alla registrazione (D7): "Mario@Esempio.it" è la stessa email di "mario@esempio.it"
    register(client)
    client.post("/api/auth/logout")
    assert accounts.ok(login(client, username="Mario@Esempio.IT"))


def test_email_sbagliata_o_inesistente_stesso_messaggio(client):
    register(client)
    client.post("/api/auth/logout")
    assert LOGIN_FAILED in page_text(login(client, username="mario@esempio.it", password="Sbagliata-123"))
    assert LOGIN_FAILED in page_text(login(client, username="nessuno@esempio.it"))
    assert not logged_in(client)


def test_campo_vuoto_chiede_nome_utente_o_email(client):
    # La scritta "Nome utente o email" della pagina la controlla test_pagine_accesso.py
    response = login(client, username="")
    assert response.get_json()["error"]["fields"]["username"] == ["Scrivi il tuo nome utente o la tua email."]


def test_il_blocco_vale_per_l_account_con_username_e_con_email(app, client, monkeypatch):
    """Alternando username ed email non si hanno più tentativi: il conto è dell'account."""
    now = [1000.0]
    monkeypatch.setattr(auth_service, "limiter", LoginLimiter(clock=lambda: now[0]))
    register(client)
    client.post("/api/auth/logout")
    attempts = app.config["LOGIN_MAX_ATTEMPTS"]
    for attempt in range(attempts - 1):
        name = "Mario" if attempt % 2 else "MARIO@esempio.it"
        assert LOGIN_FAILED in page_text(login(client, username=name, password="Sbagliata-123"))
    assert LOGIN_LOCKED in page_text(login(client, username="mario@esempio.it", password="Sbagliata-123"))
    assert LOGIN_LOCKED in page_text(login(client))  # bloccato anche con lo username e la password giusta
    assert LOGIN_LOCKED in page_text(login(client, username="mario@esempio.it"))
    now[0] += app.config["LOGIN_LOCK_SECONDS"]
    assert accounts.ok(login(client, username="mario@esempio.it"))


def test_campo_troppo_lungo_rifiutato(client):
    assert "Al massimo 254 caratteri." in page_text(login(client, username="a" * 250 + "@x.it"))


# --- CSRF e log ---


def test_richieste_senza_codice_csrf_rifiutate():
    client = _make_app(csrf=True).test_client()
    assert client.get("/api/auth/session").get_json()["data"]["csrf_token"]
    for url in ("/api/auth/login", "/api/auth/register", "/api/auth/logout"):
        response = client.post(url, json={"username": "Mario", "password": PASSWORD})
        assert response.status_code == 400, url
        assert response.get_json()["error"]["code"] == "invalid_data", url  # in JSON, per la SPA
    # Con il codice nell'intestazione passa (e qui risponde con l'errore delle credenziali)
    assert login(client).status_code == 403


# --- Rotte JSON della SPA (passo 4 della migrazione) ---


def test_le_pagine_di_prima_non_accettano_piu_moduli(client):
    assert client.post("/auth/login", data={"username": "Mario", "password": PASSWORD}).status_code == 405
    assert client.post("/auth/register", data={"username": "Mario"}).status_code == 405


def test_le_pagine_sono_quelle_della_spa(client):
    for url in ("/auth/login", "/auth/register"):
        response = client.get(url)
        assert response.status_code == 200, url
        assert '<div id="root">' in response.get_data(as_text=True), url
        response.close()


@pytest.mark.parametrize("body", [
    {"username": 5, "password": PASSWORD},
    {"username": ["Mario"], "password": PASSWORD},
    {"username": "Mario", "password": None},
    ["Mario", PASSWORD],
])
def test_dati_del_tipo_sbagliato_rifiutati(client, body):
    response = client.post("/api/auth/login", json=body)
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_data"
    assert not logged_in(client)


def test_sessione_dice_chi_e_collegato_e_consuma_i_messaggi(client):
    data = client.get("/api/auth/session").get_json()["data"]
    assert data["user"] is None and data["flashes"] == []
    register(client)
    data = client.get("/api/auth/session").get_json()["data"]
    assert data["user"]["username"] == "Mario" and data["user"]["avatar"] is None
    assert data["flashes"] == [{"kind": "success", "message": "Benvenuto, Mario!"}]
    # Letti una volta: la seconda richiesta non li ha più
    assert client.get("/api/auth/session").get_json()["data"]["flashes"] == []
    assert client.get("/api/auth/session").headers["Cache-Control"] == "no-store"


def test_il_messaggio_di_flask_login_arriva_alla_spa(client):
    # Una pagina protetta rimanda all'accesso con "Accedi per continuare." (app/extensions.py):
    # la pagina React lo legge dalla sessione e lo mostra in basso
    assert client.get("/_prova/protetta").location.startswith("/auth/login?next=")
    flashes = client.get("/api/auth/session").get_json()["data"]["flashes"]
    assert flashes == [{"kind": "info", "message": "Accedi per continuare."}]


def test_chi_ha_gia_il_login_e_rimandato_alla_home(client):
    register(client)
    assert redirect_of(login(client, username="Altro", password="qualunque")) == "/"
    assert redirect_of(register(client, username="Luigi", email="luigi@esempio.it")) == "/"
    assert len(users(client.application)) == 1


def test_password_mai_nei_log(client, caplog):
    caplog.set_level("DEBUG")
    register(client)
    client.post("/api/auth/logout")
    for _ in range(6):
        login(client, password="Sbagliata-123")
    assert "Login bloccato" in caplog.text
    assert PASSWORD not in caplog.text
    assert "Sbagliata-123" not in caplog.text
