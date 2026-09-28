"""Chat tra amici (P48; D24, D25, D26; contratto 5.4).

Con il server vero e client simulati:
- un messaggio arriva solo al destinatario (e alle altre schede di chi scrive);
- a chi non è amico il messaggio si rifiuta; troppo lungo, vuoto o troppo frequente
  si rifiuta con un avviso; `<script>` si salva e si restituisce così com'è;
- la cronologia arriva in ordine, a blocchi di 50, con before_id; aprire la chat e
  chat:read segnano come letti;
- dopo la fine dell'amicizia o un blocco la cronologia si legge ma non si scrive, e
  la risposta dice perché (cannot_write);
- lo stesso request_id non salva due volte.
"""

import threading
import uuid

import pytest
import sqlalchemy as sa

from app.extensions import db
from app.repositories import chat_repo
from app.services import chat_service, friend_service

WAIT = 5


class Events:
    def __init__(self, client, event):
        self.items = []
        self._cond = threading.Condition()

        def receive(data):
            with self._cond:
                self.items.append(data)
                self._cond.notify_all()

        client.on(event, receive)

    def wait_for(self, test=lambda _: True, timeout=WAIT):
        with self._cond:
            found = self._cond.wait_for(lambda: any(test(item) for item in self.items), timeout)
        assert found, f"evento atteso non arrivato; ricevuti: {self.items}"
        return next(item for item in self.items if test(item))


@pytest.fixture
def ids(server):
    return server["user_ids"]


@pytest.fixture
def app(server):
    return server["app"]


@pytest.fixture(autouse=True)
def no_rate_limit(app):
    """Il limite di 1 messaggio al secondo si prova a parte: qui si scrive di seguito."""
    saved = app.config["CHAT_MIN_INTERVAL_SECONDS"]
    app.config["CHAT_MIN_INTERVAL_SECONDS"] = 0
    yield
    app.config["CHAT_MIN_INTERVAL_SECONDS"] = saved


@pytest.fixture
def friends(app, ids):
    """friends("Primo", "Secondo") li rende amici; alla fine amicizie e messaggi di prova si tolgono."""
    made = []

    def _make(a, b):
        with app.app_context():
            friend_service.send_request(ids[a], uuid.uuid4().hex, b)
            friend_service.accept_request(ids[b], ids[a])
        made.append((a, b))

    yield _make
    with app.app_context():
        for a, b in made:
            friend_service.remove_friend(ids[a], ids[b])
        db.session.execute(sa.text("DELETE FROM messaggi"))
        db.session.commit()


def _send(client, user_id, text, request_id=None):
    return client.call("chat:send", {"request_id": request_id or uuid.uuid4().hex, "user_id": user_id,
                                     "text": text}, timeout=WAIT)


def _history(client, user_id, before_id=None):
    return client.call("chat:history", {"user_id": user_id, "before_id": before_id}, timeout=WAIT)


def test_il_messaggio_arriva_solo_al_destinatario(connect, ids, friends):
    friends("Primo", "Secondo")
    primo, primo_altra_scheda = connect("Primo"), connect("Primo")
    secondo, terzo = connect("Secondo"), connect("Terzo")
    to_secondo, to_terzo = Events(secondo, "chat:message"), Events(terzo, "chat:message")
    to_primo, to_primo_altra = Events(primo, "chat:message"), Events(primo_altra_scheda, "chat:message")

    answer = _send(primo, ids["Secondo"], "Ciao, na partita?")
    assert answer["ok"] is True
    message = answer["data"]["message"]
    assert message["from_user_id"] == ids["Primo"] and message["to_user_id"] == ids["Secondo"]
    assert message["text"] == "Ciao, na partita?" and message["sent_at"].endswith("Z")

    assert to_secondo.wait_for()["message"] == message
    assert to_primo_altra.wait_for()["message"] == message  # l'altra scheda di chi scrive
    assert to_terzo.items == []
    assert to_primo.items == []  # la scheda che l'ha mandato lo ha nella risposta


def test_a_chi_non_e_amico_si_rifiuta(connect, ids):
    answer = _send(connect("Primo"), ids["Terzo"], "Ciao")
    assert answer["ok"] is False and answer["error"]["code"] == "not_friends"


@pytest.mark.parametrize("text", ["", "   ", "\n\t", "x" * 1001, None, 5])
def test_testo_non_valido(connect, ids, friends, text):
    friends("Primo", "Secondo")
    answer = _send(connect("Primo"), ids["Secondo"], text)
    assert answer["ok"] is False and answer["error"]["code"] == "invalid_data"


def test_mille_caratteri_si_possono_mandare(connect, ids, friends):
    friends("Primo", "Secondo")
    assert _send(connect("Primo"), ids["Secondo"], "x" * 1000)["ok"] is True


def test_troppo_frequente(connect, ids, friends, app):
    friends("Primo", "Secondo")
    app.config["CHAT_MIN_INTERVAL_SECONDS"] = 1
    chat_service.rate_limit.give_back(ids["Primo"])  # i messaggi delle prove precedenti non contano
    primo = connect("Primo")
    assert _send(primo, ids["Secondo"], "uno")["ok"] is True
    answer = _send(primo, ids["Secondo"], "due")
    assert answer["ok"] is False and answer["error"]["code"] == "too_fast"
    assert answer["error"]["retry_after"] == 1


def test_script_salvato_e_restituito_come_testo(connect, ids, friends):
    friends("Primo", "Secondo")
    text = '<script>alert("x")</script> & <b>ciao</b>'
    primo, secondo = connect("Primo"), connect("Secondo")
    assert _send(primo, ids["Secondo"], text)["data"]["message"]["text"] == text
    assert _history(secondo, ids["Primo"])["data"]["messages"][0]["text"] == text


def test_cronologia_in_ordine_a_blocchi_di_50(connect, ids, friends, app):
    friends("Primo", "Secondo")
    with app.app_context():
        for n in range(55):
            sender, recipient = (ids["Primo"], ids["Secondo"]) if n % 2 == 0 else (ids["Secondo"], ids["Primo"])
            chat_repo.add(sender, recipient, f"messaggio {n}", chat_repo.utc_now())
        db.session.commit()
    primo = connect("Primo")
    last = _history(primo, ids["Secondo"])["data"]
    assert [m["text"] for m in last["messages"]] == [f"messaggio {n}" for n in range(5, 55)]
    assert last["has_more"] is True and last["can_write"] is True and last["cannot_write"] is None
    older = _history(primo, ids["Secondo"], before_id=last["messages"][0]["id"])["data"]
    assert [m["text"] for m in older["messages"]] == [f"messaggio {n}" for n in range(5)]
    assert older["has_more"] is False


def test_aprire_la_chat_e_chat_read_segnano_come_letti(connect, ids, friends, app):
    friends("Primo", "Secondo")
    primo, secondo = connect("Primo"), connect("Secondo")
    for text in ("uno", "due"):
        assert _send(primo, ids["Secondo"], text)["ok"]

    def unread():
        with app.app_context():
            return friend_service.overview(ids["Secondo"])["counters"]["unread_messages"]

    assert unread() == 2
    assert _history(secondo, ids["Primo"])["ok"]
    assert unread() == 0
    assert _send(primo, ids["Secondo"], "tre")["ok"]
    assert unread() == 1
    assert secondo.call("chat:read", {"user_id": ids["Primo"]}, timeout=WAIT) == {"ok": True}
    assert unread() == 0


def test_amicizia_finita_si_legge_ma_non_si_scrive(connect, ids, friends, app):
    friends("Primo", "Secondo")
    primo = connect("Primo")
    assert _send(primo, ids["Secondo"], "ciao")["ok"]
    with app.app_context():
        friend_service.remove_friend(ids["Secondo"], ids["Primo"])
    data = _history(primo, ids["Secondo"])["data"]
    assert [m["text"] for m in data["messages"]] == ["ciao"]
    assert data["can_write"] is False and data["cannot_write"] == "not_friends"
    answer = _send(primo, ids["Secondo"], "ci sei?")
    assert answer["ok"] is False and answer["error"]["code"] == "not_friends"


def test_dopo_un_blocco_tutti_e_due_vedono_bloccato(connect, ids, friends, app):
    friends("Primo", "Secondo")
    primo, secondo = connect("Primo"), connect("Secondo")
    assert _send(secondo, ids["Primo"], "ciao")["ok"]
    with app.app_context():
        friend_service.block(ids["Primo"], uuid.uuid4().hex, ids["Secondo"])
    try:
        for client, other in ((secondo, "Primo"), (primo, "Secondo")):
            data = _history(client, ids[other])["data"]
            assert [m["text"] for m in data["messages"]] == ["ciao"]  # si legge ancora (D24)
            assert data["can_write"] is False and data["cannot_write"] == "blocked"
            answer = _send(client, ids[other], "ehi")
            assert answer["ok"] is False and answer["error"]["code"] == "blocked"
    finally:
        with app.app_context():
            friend_service.unblock(ids["Primo"], ids["Secondo"])


def test_stesso_request_id_un_solo_messaggio(connect, ids, friends, app):
    friends("Primo", "Secondo")
    primo, secondo = connect("Primo"), connect("Secondo")
    received = Events(secondo, "chat:message")
    request_id = uuid.uuid4().hex
    first = _send(primo, ids["Secondo"], "una volta", request_id)
    assert _send(primo, ids["Secondo"], "una volta", request_id) == first
    received.wait_for()
    assert len(received.items) == 1
    assert len(_history(primo, ids["Secondo"])["data"]["messages"]) == 1


def test_limite_senza_database():
    clock = [100.0]
    limit = chat_service.RateLimit(lambda: clock[0])
    limit.take(1, 1)
    with pytest.raises(Exception) as exc:
        limit.take(1, 1)
    assert exc.value.code == "too_fast" and exc.value.extra["retry_after"] == 1
    limit.take(2, 1)  # un altro utente non è limitato
    clock[0] += 1
    limit.take(1, 1)
    limit.give_back(1)
    limit.take(1, 1)  # un messaggio non salvato non conta


@pytest.mark.parametrize("event, data, code", [
    ("chat:send", None, "invalid_data"),
    ("chat:send", {"user_id": 2, "text": "ciao"}, "invalid_data"),
    ("chat:history", {"user_id": "2", "before_id": None}, "invalid_data"),
    ("chat:history", {"user_id": 2, "before_id": 0}, "invalid_data"),
    ("chat:history", {"user_id": 2, "before_id": True}, "invalid_data"),
    ("chat:history", {"user_id": 999999, "before_id": None}, "not_found"),
    ("chat:read", [], "invalid_data"),
])
def test_dati_non_validi(connect, event, data, code):
    answer = connect("Primo").call(event, data, timeout=WAIT)
    assert answer["ok"] is False and answer["error"]["code"] == code


def test_a_se_stessi(connect, ids):
    answer = _send(connect("Primo"), ids["Primo"], "ciao")
    assert answer["ok"] is False and answer["error"]["code"] == "invalid_data"
