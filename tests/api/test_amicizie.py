"""P45: amicizie e blocchi, via HTTP come le chiamerà la pagina (contratto 2.2).

Serve MySQL con scripts/setup_db.sql già lanciato: si usa SOLO il database dei
test, che all'inizio viene svuotato e ricreato con migrate.py; prima di ogni prova
le tabelle si svuotano. Comando: python tests/esegui_tutti.py api
"""

import importlib.util
import json
import re
import threading
import uuid
from pathlib import Path

import pytest
import sqlalchemy as sa

from app import create_app
from app.extensions import db
from app.services import auth_service, friend_service
from app.services.auth_service import LoginLimiter

BASE_DIR = Path(__file__).resolve().parents[2]
EXAMPLE = json.loads((BASE_DIR / "app" / "static" / "dev" / "amici_esempio.json").read_text(encoding="utf-8"))
PASSWORD = "Password-di-prova-45"
TABLES = ("messaggi", "blocchi", "amicizie", "mosse_partita", "giocatori_partita", "partite", "rating", "utenti")
ISO_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")


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


@pytest.fixture(autouse=True)
def clean(app, monkeypatch):
    with app.app_context():
        for table in TABLES:
            db.session.execute(sa.text(f"DELETE FROM {table}"))
        db.session.commit()
    monkeypatch.setattr(auth_service, "limiter", LoginLimiter())
    monkeypatch.setattr(friend_service, "recent", friend_service.RecentRequests())
    app.config["FRIENDS_MAX"] = 100


class Player:
    """Un utente con la sua sessione: registrato e con il login fatto."""

    def __init__(self, app, username):
        self.app = app
        self.username = username
        self.client = app.test_client()
        response = self.client.post("/auth/register", data={
            "username": username, "email": f"{username.lower()}@esempio.it",
            "password": PASSWORD, "confirm": PASSWORD,
        })
        assert response.status_code == 302, "registrazione non riuscita"
        with app.app_context():
            self.id = db.session.execute(
                sa.text("SELECT id FROM utenti WHERE nome_utente = :u"), {"u": username}
            ).scalar()

    def call(self, method, url, payload=None):
        response = self.client.open(url, method=method, json=payload)
        return response.status_code, response.get_json()

    def overview(self):
        status, body = self.call("GET", "/friends/")
        assert status == 200 and body["ok"] is True
        return body["data"]

    def request(self, username, request_id=None):
        return self.call("POST", "/friends/requests", {"request_id": request_id or str(uuid.uuid4()), "username": username})

    def accept(self, other):
        return self.call("POST", f"/friends/requests/{other.id}/accept")

    def decline(self, other):
        return self.call("POST", f"/friends/requests/{other.id}/decline")

    def cancel(self, other):
        return self.call("DELETE", f"/friends/requests/{other.id}")

    def remove(self, other):
        return self.call("DELETE", f"/friends/{other.id}")

    def block(self, user_id, request_id=None):
        return self.call("POST", "/friends/blocks", {"request_id": request_id or str(uuid.uuid4()), "user_id": user_id})

    def unblock(self, other):
        return self.call("DELETE", f"/friends/blocks/{other.id}")


@pytest.fixture
def mario(app):
    return Player(app, "Mario")


@pytest.fixture
def nina(app):
    return Player(app, "Nina")


@pytest.fixture
def toto(app):
    return Player(app, "Toto")


def ids(items):
    return [item["user_id"] for item in items]


def assert_error(result, status, code):
    got_status, body = result
    assert (got_status, body["ok"], body["error"]["code"]) == (status, False, code), body
    assert body["error"]["message"]


def befriend(a, b):
    assert a.request(b.username)[0] == 200
    assert b.accept(a)[0] == 200


def rows(app, table):
    with app.app_context():
        return db.session.execute(sa.text(f"SELECT COUNT(*) FROM {table}")).scalar()


# Il "Fatto quando" di P45


def test_richiesta_poi_accettazione_poi_amici(mario, nina):
    status, body = mario.request("Nina")
    assert status == 200 and body["ok"] is True
    sent = body["data"]
    assert (sent["user_id"], sent["username"], sent["avatar"]) == (nina.id, "Nina", None)
    assert ISO_UTC.match(sent["sent_at"])

    assert ids(mario.overview()["requests_out"]) == [nina.id]
    incoming = nina.overview()
    assert ids(incoming["requests_in"]) == [mario.id]
    assert incoming["counters"]["requests_in"] == 1
    assert ISO_UTC.match(incoming["requests_in"][0]["sent_at"])

    assert nina.accept(mario) == (200, {"ok": True})
    for me, other in ((mario, nina), (nina, mario)):
        data = me.overview()
        assert ids(data["friends"]) == [other.id]
        assert data["requests_in"] == [] and data["requests_out"] == []
        assert data["counters"]["requests_in"] == 0


def test_richiesta_a_se_stessi_rifiutata(mario):
    assert_error(mario.request("Mario"), 400, "invalid_data")


def test_richiesta_doppia_rifiutata(app, mario, nina):
    mario.request("Nina")
    assert_error(mario.request("Nina"), 409, "already_exists")
    assert rows(app, "amicizie") == 1


def test_richiesta_a_chi_te_ne_ha_gia_mandata_una(app, mario, nina):
    nina.request("Mario")
    assert_error(mario.request("Nina"), 409, "request_from_them")
    assert mario.overview()["friends"] == []  # l'amicizia non parte da sola (P8)
    assert rows(app, "amicizie") == 1


def test_richiesta_a_chi_e_gia_amico(mario, nina):
    befriend(mario, nina)
    assert_error(mario.request("Nina"), 409, "already_exists")
    assert_error(nina.request("Mario"), 409, "already_exists")


def test_rimuovere_un_amico_lo_toglie_a_entrambi(mario, nina):
    befriend(mario, nina)
    assert nina.remove(mario) == (200, {"ok": True})
    assert mario.overview()["friends"] == [] and nina.overview()["friends"] == []
    assert nina.remove(mario) == (200, {"ok": True})  # seconda volta: ok senza fare niente
    assert mario.request("Nina")[0] == 200  # si può richiedere di nuovo


def test_utente_bloccato_non_puo_mandare_richieste(mario, nina):
    assert nina.block(mario.id)[0] == 200
    blocked = mario.request("Nina")
    unknown = mario.request("Nessuno")
    assert_error(blocked, 404, "not_found")
    assert blocked[1] == unknown[1]  # chi ti ha bloccato risulta inesistente (P8)


def test_limite_di_amici(app, mario, nina, toto):
    app.config["FRIENDS_MAX"] = 1
    befriend(mario, nina)
    assert_error(mario.request("Toto"), 409, "limit_reached")   # Mario è al limite
    assert_error(toto.request("Mario"), 409, "limit_reached")   # l'altro è al limite
    app.config["FRIENDS_MAX"] = 2
    toto.request("Mario")
    app.config["FRIENDS_MAX"] = 1
    assert_error(mario.accept(toto), 409, "limit_reached")      # anche accettando
    assert ids(mario.overview()["friends"]) == [nina.id]


def test_limite_di_d26_in_config(app):
    assert app.config["FRIENDS_MAX"] == 100


# Richieste: rifiutare, annullare, accettare


def test_username_esatto_con_le_maiuscole(mario, nina):
    assert_error(mario.request("nina"), 404, "not_found")
    assert_error(mario.request("NINA"), 404, "not_found")
    assert mario.request("Nina")[0] == 200


@pytest.mark.parametrize("written", [" Nina", "Nina ", "  Nina  ", "\tNina\n"])
def test_spazi_prima_o_dopo_il_nome_trovano_l_utente(mario, nina, written):
    """P63: dal telefono capita di scrivere il nome con uno spazio in più; uno username
    non ha mai spazi (D7), quindi il server li toglie prima di cercarlo."""
    status, body = mario.request(written)
    assert status == 200 and body["data"]["username"] == "Nina"
    assert [r["username"] for r in mario.overview()["requests_out"]] == ["Nina"]


def test_spazio_in_mezzo_al_nome_resta_un_utente_che_non_c_e(mario, nina):
    status, body = mario.request("Ni na")
    assert_error((status, body), 404, "not_found")
    assert body["error"]["message"] == "Nessun utente con questo username."


def test_nome_di_soli_spazi_rifiutato(app, mario):
    status, body = mario.request("   ")
    assert (status, body["error"]["code"]) == (400, "invalid_data")
    assert rows(app, "amicizie") == 0


def test_rifiutare_cancella_la_richiesta(app, mario, nina):
    mario.request("Nina")
    assert nina.decline(mario) == (200, {"ok": True})
    assert nina.overview()["requests_in"] == [] and mario.overview()["requests_out"] == []
    assert nina.decline(mario) == (200, {"ok": True})  # seconda volta: ok
    assert rows(app, "amicizie") == 0
    assert mario.request("Nina")[0] == 200  # si potrà rimandare


def test_annullare_una_richiesta_mandata(mario, nina):
    mario.request("Nina")
    assert mario.cancel(nina) == (200, {"ok": True})
    assert nina.overview()["requests_in"] == []
    assert mario.cancel(nina) == (200, {"ok": True})


def test_non_si_annulla_ne_si_rifiuta_la_richiesta_sbagliata(app, mario, nina):
    mario.request("Nina")
    mario.decline(nina)  # Mario non ha ricevuto niente da Nina
    nina.cancel(mario)   # Nina non ha mandato niente a Mario
    assert ids(nina.overview()["requests_in"]) == [mario.id]


def test_accettare(mario, nina):
    assert_error(nina.accept(mario), 404, "not_found")  # nessuna richiesta
    mario.request("Nina")
    assert_error(mario.accept(nina), 404, "not_found")  # la propria richiesta non si accetta
    assert nina.accept(mario) == (200, {"ok": True})
    assert nina.accept(mario) == (200, {"ok": True})  # seconda volta: ok


# Blocchi (D23)


def test_il_blocco_toglie_l_amicizia(mario, nina):
    befriend(mario, nina)
    assert mario.block(nina.id) == (200, {"ok": True})
    assert mario.overview()["friends"] == [] and nina.overview()["friends"] == []
    assert [(u["user_id"], u["username"], u["avatar"]) for u in mario.overview()["blocked"]] == [(nina.id, "Nina", None)]
    assert nina.overview()["blocked"] == []


@pytest.mark.parametrize("who_asked", ["blocker", "blocked"])
def test_il_blocco_toglie_le_richieste(app, mario, nina, who_asked):
    (mario if who_asked == "blocker" else nina).request("Nina" if who_asked == "blocker" else "Mario")
    mario.block(nina.id)
    assert rows(app, "amicizie") == 0


def test_chi_ha_bloccato_non_puo_mandare_richieste_finche_non_sblocca(mario, nina):
    mario.block(nina.id)
    assert_error(mario.request("Nina"), 403, "blocked")
    assert mario.unblock(nina) == (200, {"ok": True})
    assert mario.overview()["blocked"] == []
    assert mario.unblock(nina) == (200, {"ok": True})  # seconda volta: ok
    assert mario.request("Nina")[0] == 200


def test_bloccare(app, mario, nina):
    assert_error(mario.block(mario.id), 400, "invalid_data")
    assert_error(mario.block(999_999), 404, "not_found")
    assert mario.block(nina.id)[0] == 200
    assert mario.block(nina.id)[0] == 200  # già bloccato: ok, nessun doppione
    assert rows(app, "blocchi") == 1
    assert nina.block(mario.id)[0] == 200  # si può bloccare anche chi ti ha bloccato
    assert rows(app, "blocchi") == 2


# request_id (contratto 1.3)


def test_stesso_request_id_stessa_risposta(app, mario, nina):
    first = mario.request("Nina", request_id="tentativo-1")
    again = mario.request("Nina", request_id="tentativo-1")
    assert first == again and first[0] == 200
    assert rows(app, "amicizie") == 1
    assert_error(mario.request("Nina", request_id="tentativo-2"), 409, "already_exists")


def test_stesso_request_id_anche_per_gli_errori(mario):
    first = mario.request("Nessuno", request_id="tentativo-x")
    assert_error(first, 404, "not_found")
    assert mario.request("Nessuno", request_id="tentativo-x") == first


def test_request_id_di_utenti_diversi_non_si_mescolano(mario, nina, toto):
    assert mario.request("Toto", request_id="stesso")[0] == 200
    assert nina.request("Toto", request_id="stesso")[0] == 200
    assert sorted(ids(toto.overview()["requests_in"])) == sorted([mario.id, nina.id])


def test_blocco_con_request_id(app, mario, nina):
    assert mario.block(nina.id, request_id="b-1") == mario.block(nina.id, request_id="b-1")
    assert rows(app, "blocchi") == 1


def test_request_id_scade_dopo_il_tempo():
    now = [0.0]
    recent = friend_service.RecentRequests(seconds=600, clock=lambda: now[0])
    calls = []
    assert recent.run(1, "request", "r", lambda: calls.append(1) or "prima") == "prima"
    assert recent.run(1, "request", "r", lambda: calls.append(2) or "seconda") == "prima"
    now[0] = 601
    assert recent.run(1, "request", "r", lambda: calls.append(3) or "terza") == "terza"
    assert calls == [1, 3]


# Richieste contemporanee (doppio clic, due schede)


def _together(*actions):
    barrier = threading.Barrier(len(actions))
    results = [None] * len(actions)

    def run(index, action):
        barrier.wait()
        results[index] = action()

    threads = [threading.Thread(target=run, args=(i, a)) for i, a in enumerate(actions)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    return results


def test_due_richieste_incrociate_contemporanee(app, mario, nina):
    for _ in range(5):
        results = _together(lambda: mario.request("Nina"), lambda: nina.request("Mario"))
        statuses = sorted(status for status, _body in results)
        assert statuses == [200, 409], results
        assert rows(app, "amicizie") == 1
        mario.cancel(nina)
        nina.cancel(mario)


def test_doppio_clic_con_lo_stesso_request_id(app, mario, nina):
    results = _together(*(lambda: mario.request("Nina", request_id="doppio") for _ in range(4)))
    assert all(result == results[0] for result in results) and results[0][0] == 200
    assert rows(app, "amicizie") == 1


def test_limite_con_accettazioni_contemporanee(app, mario, nina, toto):
    app.config["FRIENDS_MAX"] = 1
    nina.request("Mario")
    toto.request("Mario")
    results = _together(lambda: mario.accept(nina), lambda: mario.accept(toto))
    assert sorted(status for status, _body in results) == [200, 409]
    assert len(mario.overview()["friends"]) == 1


# Dati non validi


@pytest.mark.parametrize("payload", [
    None, [], "Nina", {"username": "Nina"}, {"request_id": "", "username": "Nina"},
    {"request_id": 5, "username": "Nina"}, {"request_id": "x" * 101, "username": "Nina"},
    {"request_id": "r"}, {"request_id": "r", "username": ""}, {"request_id": "r", "username": 7},
    {"request_id": "r", "username": "x" * 21},
])
def test_richiesta_con_dati_non_validi(app, mario, payload):
    status, body = mario.call("POST", "/friends/requests", payload)
    assert (status, body["error"]["code"]) == (400, "invalid_data")
    assert rows(app, "amicizie") == 0


@pytest.mark.parametrize("user_id", [None, "3", True, 0, -1, 1.5])
def test_blocco_con_dati_non_validi(app, mario, user_id):
    status, body = mario.call("POST", "/friends/blocks", {"request_id": "r", "user_id": user_id})
    assert (status, body["error"]["code"]) == (400, "invalid_data")
    assert rows(app, "blocchi") == 0


def test_indirizzo_sconosciuto_risponde_in_json(mario):
    assert_error(mario.call("POST", "/friends/requests/abc/accept"), 404, "not_found")


# Login e CSRF


@pytest.mark.parametrize(("method", "url"), [
    ("GET", "/friends/"), ("POST", "/friends/requests"), ("POST", "/friends/requests/1/accept"),
    ("POST", "/friends/requests/1/decline"), ("DELETE", "/friends/requests/1"), ("DELETE", "/friends/1"),
    ("POST", "/friends/blocks"), ("DELETE", "/friends/blocks/1"),
])
def test_senza_login_not_logged_in(app, method, url):
    response = app.test_client().open(url, method=method, json={"request_id": "r", "username": "Nina"})
    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "not_logged_in"


def test_modifiche_solo_con_il_codice_csrf(app, mario, nina):
    app.config["WTF_CSRF_ENABLED"] = True
    try:
        page = mario.client.get("/").get_data(as_text=True)
        token = re.search(r'name="csrf-token" content="([^"]+)"', page).group(1)
        payload = {"request_id": "c-1", "username": "Nina"}
        assert mario.client.post("/friends/requests", json=payload).status_code == 400
        response = mario.client.post("/friends/requests", json=payload, headers={"X-CSRFToken": token})
        assert response.status_code == 200
        assert mario.client.get("/friends/").status_code == 200  # la lettura non lo chiede
    finally:
        app.config["WTF_CSRF_ENABLED"] = False


# Lista: forma, presenza, messaggi non letti


def test_lista_con_la_forma_del_file_di_esempio(mario, nina, toto):
    befriend(mario, nina)
    toto.request("Mario")
    data = mario.overview()
    example = EXAMPLE["GET /friends/"]
    assert set(data) == set(example)
    assert set(data["friends"][0]) == set(example["friends"][0])
    assert set(data["requests_in"][0]) == set(example["requests_in"][0])
    assert set(data["counters"]) == set(example["counters"])
    toto.cancel(mario)
    nina.request("Toto")
    assert set(nina.overview()["requests_out"][0]) == set(example["requests_out"][0])


def test_presenza_degli_amici(mario, nina, toto, monkeypatch):
    befriend(mario, nina)
    befriend(mario, toto)
    assert {f["presence"] for f in mario.overview()["friends"]} == {"offline"}
    monkeypatch.setattr(friend_service, "find_room_of_user", lambda uid: object() if uid == nina.id else None)
    # P47: "online" viene da presence.py (P44), non più dai canali di Socket.IO
    monkeypatch.setattr(friend_service.online_users, "is_online", lambda uid: uid in (nina.id, toto.id))
    friends = mario.overview()["friends"]
    assert [(f["username"], f["presence"]) for f in friends] == [("Toto", "online"), ("Nina", "in_game")]


def test_messaggi_non_letti(app, mario, nina, toto):
    befriend(mario, nina)
    with app.app_context():
        for sender, read in ((nina.id, None), (nina.id, None), (nina.id, "2026-09-28 10:05:00"), (toto.id, None)):
            db.session.execute(sa.text(
                "INSERT INTO messaggi (mittente_id, destinatario_id, testo, inviato_il, letto_il) "
                "VALUES (:s, :d, 'ciao', '2026-09-28 10:00:00', :r)"
            ), {"s": sender, "d": mario.id, "r": read})
        db.session.commit()
    data = mario.overview()
    assert [(f["user_id"], f["unread"]) for f in data["friends"]] == [(nina.id, 2)]
    assert data["counters"]["unread_messages"] == 3  # anche da chi non è più amico
    assert nina.overview()["counters"]["unread_messages"] == 0


def test_lista_ordinata_e_date_in_utc(app, mario, nina, toto):
    toto.request("Mario")
    nina.request("Mario")
    with app.app_context():
        db.session.execute(sa.text(
            "UPDATE amicizie SET richiesta_il = '2026-09-28 09:41:05' WHERE richiedente_id = :t"
        ), {"t": toto.id})
        db.session.commit()
    requests = mario.overview()["requests_in"]
    assert ids(requests) == [nina.id, toto.id]  # la più recente prima
    assert requests[1]["sent_at"] == "2026-09-28T09:41:05.000Z"


def test_log_senza_username(mario, nina, caplog):
    caplog.set_level("DEBUG")
    befriend(mario, nina)
    mario.block(nina.id)
    assert "Richiesta di amicizia" in caplog.text
    assert "Mario" not in caplog.text and "Nina" not in caplog.text
