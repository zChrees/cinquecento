"""Aiuti della suite e2e (P31): utenti veri, schede Socket.IO e partite giocate fino in fondo.

Si importano con `from tests.e2e.helpers import ...` (come tests/browser.py).
"""

import re
import threading
import time
import uuid

import requests
import socketio as sio_client
import websocket

PASSWORD = "Password-di-prova-1"
WAIT = 5  # secondi massimi per aspettare un evento (si aspetta l'evento, non un tempo fisso)
CSRF_FIELD = re.compile(r'name="csrf_token" type="hidden" value="([^"]+)"')
CSRF_META = re.compile(r'<meta name="csrf-token" content="([^"]+)">')
USER_ID = re.compile(r'<body data-user-id="(\d+)"')

# Come nella suite sockets: il server di sviluppo (Werkzeug) non risponde alla chiusura
# ordinata del websocket, e websocket-client la aspetterebbe fino a 3 secondi per client.
_ws_close = websocket.WebSocket.close


def _quick_close(self, status=websocket.STATUS_NORMAL, reason=b"", timeout=0.1):
    return _ws_close(self, status, reason, timeout)


websocket.WebSocket.close = _quick_close


def request_id():
    return uuid.uuid4().hex


# --- Utenti e schede ------------------------------------------------------------------


class Tab:
    """Una scheda del browser: una connessione Socket.IO che raccoglie tutti gli eventi."""

    def __init__(self, url, cookie):
        self.events = []  # (nome, dati) nell'ordine di arrivo
        self._cond = threading.Condition()
        self.client = sio_client.Client(reconnection=False)
        self.client.on("*", self._receive)
        self.client.connect(url, headers={"Cookie": cookie}, transports=["websocket"], wait_timeout=WAIT)

    def _receive(self, event, data=None):
        with self._cond:
            self.events.append((event, data))
            self._cond.notify_all()

    def call(self, event, data=None):
        if data is None:
            return self.client.call(event, timeout=WAIT)
        return self.client.call(event, data, timeout=WAIT)

    def call_patiently(self, event, data):
        """Come call, ma se il server risponde too_fast (limite degli eventi, P32) aspetta
        i secondi che dice e riprova: così gioca chi clicca più veloce di una persona."""
        for _ in range(10):
            answer = self.call(event, data)
            if answer.get("ok") or answer["error"]["code"] != "too_fast":
                return answer
            time.sleep(answer["error"]["retry_after"])  # il server dice quanto aspettare
        raise AssertionError(f"{event}: sempre too_fast")

    def received(self, event):
        with self._cond:
            return [data for name, data in self.events if name == event]

    def mark(self):
        """Il punto attuale dell'elenco degli eventi: con wait_for(..., since=mark) si guarda solo dopo."""
        with self._cond:
            return len(self.events)

    def wait_for(self, event, match=lambda _data: True, timeout=WAIT, since=0):
        """Il primo evento `event` (già arrivato o in arrivo, dopo `since`) per cui `match(dati)` è vero."""
        def found():
            return next((data for name, data in self.events[since:] if name == event and match(data)), None)

        with self._cond:
            self._cond.wait_for(lambda: found() is not None, timeout)
            data = found()
            arrived = [item for name, item in self.events[since:] if name == event][-5:]
        assert data is not None, f"nessun evento {event} adatto in {timeout} secondi (arrivati: {arrived})"
        return data

    def state(self, version):
        """La vista di gioco con quella version (aspetta che arrivi)."""
        return self.wait_for("game:state", lambda view: view["version"] == version)

    def latest_state(self):
        views = self.received("game:state")
        return max(views, key=lambda view: view["version"]) if views else None

    def close(self):
        if self.client.connected:
            self.client.disconnect()


class User:
    """Un utente vero: si registra dal modulo come farebbe il browser, e resta con il login."""

    def __init__(self, url, username):
        self.url = url
        self.username = username
        self.session = requests.Session()
        page = self.session.get(f"{url}/auth/register", timeout=WAIT).text
        response = self.session.post(f"{url}/auth/register", data={
            "csrf_token": CSRF_FIELD.search(page)[1], "username": username,
            "email": f"{username.lower()}@esempio.it", "password": PASSWORD, "confirm": PASSWORD,
        }, allow_redirects=False, timeout=WAIT)
        assert response.status_code == 302, f"registrazione di {username} non riuscita"
        home = self.session.get(f"{url}/", timeout=WAIT).text  # dopo la registrazione si entra subito
        self.id = int(USER_ID.search(home)[1])
        self._csrf = CSRF_META.search(home)[1]
        self.tabs = []

    @property
    def cookie(self):
        return "; ".join(f"{k}={v}" for k, v in self.session.cookies.items())

    def tab(self):
        new = Tab(self.url, self.cookie)
        self.tabs.append(new)
        return new

    def api(self, method, path, body=None):
        """Richiesta JSON come quelle della pagina (codice CSRF nell'intestazione X-CSRFToken)."""
        response = self.session.request(method, f"{self.url}{path}", json=body,
                                        headers={"X-CSRFToken": self._csrf}, timeout=WAIT)
        return response.json()

    def close(self):
        for tab in self.tabs:
            tab.close()


# --- Partite --------------------------------------------------------------------------


def wait_game_start(tabs):
    """Tutti ricevono game:start con la stessa partita; restituisce il game_id."""
    starts = [tab.wait_for("game:start") for tab in tabs]
    assert all(start == starts[0] for start in starts), starts
    assert starts[0]["url"] == f"/game/{starts[0]['game_id']}"
    return starts[0]["game_id"]


def sit(tabs, game_id):
    """Ogni scheda entra al tavolo; restituisce le schede nell'ordine dei posti e la version attuale."""
    for tab in tabs:
        assert tab.call("game:join", {"game_id": game_id}) == {"ok": True}
    views = [tab.wait_for("game:state") for tab in tabs]
    by_seat = sorted(zip(views, tabs, strict=True), key=lambda pair: pair[0]["you"]["seat"])
    assert [view["you"]["seat"] for view, _tab in by_seat] == list(range(len(tabs)))
    seats = [tab for _view, tab in by_seat]
    # L'ultima a entrare ha ricevuto la vista più recente: gli altri la ricevono subito dopo
    version = max(tab.latest_state()["version"] for tab in seats)
    return seats, version


def card_key(card):
    return (card["suit"], card["rank"])


def cards_in(value):
    """Ogni carta ({"suit", "rank"}) che compare in un punto qualsiasi della vista."""
    if isinstance(value, dict):
        if set(value) == {"suit", "rank"}:
            yield card_key(value)
        else:
            for item in value.values():
                yield from cards_in(item)
    elif isinstance(value, list):
        for item in value:
            yield from cards_in(item)


def check_private(views):
    """Nessuna vista contiene carte in mano agli altri (le mani vengono dalle loro viste).

    `last_hand` parla della mano prima, con il mazzo mescolato di nuovo: le sue carte
    (già giocate davanti a tutti) possono essere adesso in mano a un altro, e si
    controllano a parte: solo le carte di una presa, una per giocatore.
    """
    hands = [{card_key(card) for card in view["hand"]} for view in views]
    for seat, view in enumerate(views):
        others = set().union(*(hand for other, hand in enumerate(hands) if other != seat))
        current = {key: value for key, value in view.items() if key != "last_hand"}
        assert not set(cards_in(current)) & others, f"il posto {seat} vede carte altrui"
        assert view["players"][seat]["cards_in_hand"] == len(view["hand"])
        if view["last_hand"] is not None:
            assert len(list(cards_in(view["last_hand"]))) == len(views)
    for seat, hand in enumerate(hands):
        for other in range(seat + 1, len(hands)):
            assert not hand & hands[other]


def play_to_the_end(game_id, seats, version):
    """Gioca fino alla fine: chi è di turno canta se può, altrimenti gioca la prima carta ammessa.

    A ogni vista controlla che nessuno veda carte altrui; restituisce le viste finali.
    """
    for _ in range(2000):
        views = [seat.state(version) for seat in seats]
        check_private(views)
        if views[0]["status"] == "finished":
            return views
        turn = views[0]["turn"]["seat"]
        view = views[turn]
        assert all(v["legal"] == {"play": [], "sing": []} for i, v in enumerate(views) if i != turn)
        if view["legal"]["sing"]:
            answer = seats[turn].call_patiently("game:sing", {"game_id": game_id, "version": version,
                                                             "suit": view["legal"]["sing"][0]})
        else:
            answer = seats[turn].call_patiently("game:play_card", {"game_id": game_id, "version": version,
                                                                  "card": view["legal"]["play"][0]})
        assert answer == {"ok": True}, answer
        version += 1
    raise AssertionError("la partita non finisce")


def check_result(views, target_score):
    result = views[0]["result"]
    assert all(view["result"] == result for view in views)
    assert result["reason"] == "score" and result["abandoned_seats"] == []
    totals = [score["total"] for score in result["scores"]]
    assert max(totals) >= target_score
    expected = None if totals[0] == totals[1] else totals.index(max(totals))
    assert result["winner_team"] == expected
    return result


def outcome(result, team):
    """"win", "loss" o "draw" per la squadra `team`."""
    if result["winner_team"] is None:
        return "draw"
    return "win" if result["winner_team"] == team else "loss"


def stats_after(user, result, team, mode, rated):
    """Le statistiche di `user` dopo la sua prima partita: una partita, con l'esito giusto."""
    answer = user.api("GET", "/stats/me")
    assert answer["ok"] is True, answer
    stats = answer["data"]
    counts = {"win": 0, "loss": 0, "draw": 0}
    counts[outcome(result, team)] = 1
    assert stats["games"] == 1
    assert (stats["wins"], stats["losses"], stats["draws"]) == (counts["win"], counts["loss"], counts["draw"])
    assert stats["ratings"][mode]["games"] == (1 if rated else 0)
    other = "2v2" if mode == "1v1" else "1v1"
    assert stats["ratings"][other] == {"value": 1500, "games": 0, "provisional": True}
    return stats
