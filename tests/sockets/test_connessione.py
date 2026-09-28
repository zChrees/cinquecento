"""P23: collegamento in tempo reale con client simulati contro il server vero.

- Senza login la connessione è rifiutata con `not_logged_in` (contratto 1.4).
- Due utenti nella stessa stanza ricevono gli eventi della stanza; chi è fuori no.
- Le risposte hanno sempre la forma del contratto (1.2), anche con un errore imprevisto.
"""

from types import SimpleNamespace

import pytest
import socketio as sio_client

from app.realtime import events
from app.realtime.events import EventError, error, handler, ok

WAIT = 5


def test_senza_login_connessione_rifiutata(server):
    client = sio_client.Client(reconnection=False)
    reasons = []
    client.on("connect_error", reasons.append)
    with pytest.raises(sio_client.exceptions.ConnectionError):
        client.connect(server["url"], transports=["websocket"], wait_timeout=WAIT)
    assert reasons == [{"message": "not_logged_in"}]
    assert not client.connected


@pytest.mark.parametrize("transports", [("websocket",), ("polling",)])
def test_con_login_si_collega(connect, transports):
    client = connect("Primo", transports=transports)
    assert client.connected


def test_due_utenti_nella_stessa_stanza_ricevono_gli_eventi(connect, room, inbox, server):
    primo, secondo, terzo = connect("Primo"), connect("Secondo"), connect("Terzo")
    heard = {name: inbox(c, "test:shouted") for name, c in (("Primo", primo), ("Secondo", secondo), ("Terzo", terzo))}
    ping_terzo = inbox(terzo, "test:ping")

    assert primo.call("test:join", {"room_id": room.id}, timeout=WAIT) == ok()
    assert secondo.call("test:join", {"room_id": room.id}, timeout=WAIT) == ok()
    assert room.members == {server["user_ids"]["Primo"], server["user_ids"]["Secondo"]}

    assert primo.call("test:shout", {"room_id": room.id, "text": "Amunì!"}, timeout=WAIT) == ok()
    assert heard["Primo"].wait() and heard["Secondo"].wait()
    assert heard["Primo"].items == heard["Secondo"].items == [{"text": "Amunì!"}]

    # Terzo è fuori dalla stanza: sulla sua connessione gli eventi arrivano in ordine,
    # quindi se il ping (mandato dopo) è arrivato, il messaggio della stanza non arriverà più.
    primo.call("test:ping_user", {"user_id": server["user_ids"]["Terzo"]}, timeout=WAIT)
    assert ping_terzo.wait()
    assert heard["Terzo"].items == []


def test_tutte_le_schede_dello_stesso_utente_ricevono(connect, inbox, server):
    scheda_1, scheda_2, altro = connect("Primo"), connect("Primo"), connect("Secondo")
    pings = [inbox(c, "test:ping") for c in (scheda_1, scheda_2, altro)]
    altro.call("test:ping_user", {"user_id": server["user_ids"]["Primo"]}, timeout=WAIT)
    assert pings[0].wait() and pings[1].wait()
    assert len(pings[0].items) == len(pings[1].items) == 1
    # Secondo non l'ha ricevuto: un ping mandato dopo a lui arriva, ed è il solo
    altro.call("test:ping_user", {"user_id": server["user_ids"]["Secondo"]}, timeout=WAIT)
    assert pings[2].wait()
    assert len(pings[2].items) == 1


def test_stanza_inesistente_risposta_not_found(connect):
    client = connect("Primo")
    answer = client.call("test:join", {"room_id": "non-esiste"}, timeout=WAIT)
    assert answer == {"ok": False, "error": {"code": "not_found", "message": "Non esiste o non esiste più."}}


def test_errore_imprevisto_diventa_server_error(connect):
    answer = connect("Primo").call("test:fail", {}, timeout=WAIT)
    assert answer["ok"] is False
    assert answer["error"]["code"] == "server_error"
    assert "errore di prova" not in answer["error"]["message"]  # il dettaglio va solo nel log


# --- Forma delle risposte (senza server) ---


def test_forma_delle_risposte(monkeypatch):
    # Fuori da una connessione: il decoratore (P32) legge utente, scheda e limite da qui
    monkeypatch.setattr(events, "current_user", SimpleNamespace(is_authenticated=True))
    monkeypatch.setattr(events, "request", SimpleNamespace(sid="scheda-di-prova"))
    monkeypatch.setattr(events, "current_app", SimpleNamespace(config={"EVENT_BURST": 5, "EVENT_RATE_PER_SECOND": 1}))
    assert ok() == {"ok": True}
    assert ok({"a": 1}) == {"ok": True, "data": {"a": 1}}
    assert error("too_fast", retry_after=2.5) == {
        "ok": False, "error": {"code": "too_fast", "message": "Troppo veloce: aspetta un momento.", "retry_after": 2.5},
    }

    @handler
    def rejected():
        raise EventError("not_your_turn")

    assert rejected() == {"ok": False, "error": {"code": "not_your_turn", "message": "Non è il tuo turno."}}


def test_codice_di_errore_fuori_contratto_rifiutato():
    with pytest.raises(ValueError, match="sconosciuto"):
        EventError("codice_inventato")
