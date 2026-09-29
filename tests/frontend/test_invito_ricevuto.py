"""P47: invito a partita ricevuto nella home (components/InviteDialog.js).

La home si apre in Chrome o Edge senza finestra (tests/browser.py) con l'utente di
prova collegato al tempo reale; il test crea l'invito sul server vero
(app/realtime/invites.py) e lo fa arrivare alla pagina con invite:received, come
farebbe invite:send di un amico. Controlla: chi invita, modalità e punti (il nome
entra come testo, mai come HTML), il conto alla rovescia, "Accetta" e l'attesa di chi
ha invitato, l'annullamento, l'errore del server mostrato nella finestra, Esc.
Se né Chrome né Edge sono installati i controlli nel browser si saltano.
"""

import re

import pytest

from app import create_app
from app.extensions import socketio
from app.realtime.events import user_channel
from app.realtime.invites import invites
from app.realtime.room import Player
from tests.browser import TEST_COOKIE, Browser, FakeUser, find_browser, running_server

ME = 7
FRIEND = Player(44, "<b>Giulia</b>")  # un nome con dell'HTML: deve restare testo
DIALOG = "document.querySelector('[data-invite-dialog]')"


@pytest.fixture(scope="module")
def server():
    with running_server(create_app("testing"), FakeUser("Mario", ME)) as url:
        yield url


@pytest.fixture(scope="module")
def browser(server, tmp_path_factory):
    b = Browser(find_browser(), tmp_path_factory.mktemp("chrome"))
    b.send("Network.setCookie", name=TEST_COOKIE[0], value=TEST_COOKIE[1], url=server)
    yield b
    b.close()


@pytest.fixture
def home(browser, server):
    """La home aperta e collegata al tempo reale (è arrivato home:status vero: 1 online)."""
    browser.open(f"{server}/", 390, 844,
                 "document.querySelector('[data-online-count]')?.textContent === '1'", timeout=60)
    yield browser
    invites.cancel_all_of(ME)


def _receive(mode="2v2", target_score=300):
    invite = invites.send(FRIEND, Player(ME, "Mario"), mode, target_score)
    socketio.emit("invite:received", invites.data(invite), to=user_channel(ME))
    return invite


def test_invito_ricevuto_con_chi_invita_e_conto_alla_rovescia(home):
    invite = _receive()
    home.wait_js(f"{DIALOG}?.open", "finestra dell'invito")
    facts = home.js(f"""(() => {{ const d = {DIALOG};
      return {{id: d.dataset.inviteDialog, text: d.textContent, bold: d.querySelector('b') !== null,
               seconds: d.querySelector('[data-invite-seconds]').textContent,
               accept: !d.querySelector('[data-invite-accept]').hidden}}; }})()""")
    assert facts["id"] == invite.invite_id
    assert "<b>Giulia</b> ti invita a una partita 2v2 tra amici, a 300 punti." in facts["text"]
    assert facts["bold"] is False
    assert re.fullmatch(r"0:5\d|1:00", facts["seconds"])
    assert facts["accept"] is True


def test_accetta_poi_aspetta_chi_ha_invitato_e_l_annullamento(home):
    invite = _receive("1v1", 150)
    home.wait_js(f"{DIALOG}?.open", "finestra dell'invito")
    home.js(f"{DIALOG}.querySelector('[data-invite-accept]').click()")
    home.wait_js(f"{DIALOG}.dataset.inviteStatus === 'accepted'", "invito accettato")
    assert invites.get(invite.invite_id).status == "accepted"
    note = home.js(f"{DIALOG}.querySelector('[data-invite-note]').textContent")
    assert note == "Hai accettato: aspettiamo che <b>Giulia</b> avvii la partita…"
    assert home.js(f"{DIALOG}.querySelector('[data-invite-accept]').hidden") is True

    invites.cancel(invite.invite_id, FRIEND.user_id)  # chi ha invitato chiude la carta
    home.wait_js(f"{DIALOG}.dataset.inviteStatus === 'cancelled'", "annullamento")
    assert "ha annullato l'invito" in home.js(f"{DIALOG}.querySelector('[data-invite-note]').textContent")
    home.js(f"{DIALOG}.querySelector('.icon-btn').click()")  # la X chiude subito
    home.wait_js(f"!{DIALOG}", "chiusura della finestra")


def test_errore_del_server_nella_finestra(home):
    invite = _receive()
    home.wait_js(f"{DIALOG}?.open", "finestra dell'invito")
    invites.cancel(invite.invite_id, FRIEND.user_id)  # annullato, ma la pagina non lo sa ancora
    home.js(f"{DIALOG}.querySelector('[data-invite-accept]').click()")
    home.wait_js(f"{DIALOG}?.querySelector('[data-invite-note]').textContent !== ''", "risposta del server")
    # L'annullamento arriva comunque con invite:update: la finestra lo mostra
    home.wait_js(f"{DIALOG}.dataset.inviteStatus === 'cancelled'", "annullamento")


def test_esc_rifiuta(home):
    invite = _receive()
    home.wait_js(f"{DIALOG}?.open", "finestra dell'invito")
    home.send("Input.dispatchKeyEvent", type="keyDown", key="Escape", code="Escape", windowsVirtualKeyCode=27)
    home.send("Input.dispatchKeyEvent", type="keyUp", key="Escape", code="Escape", windowsVirtualKeyCode=27)
    home.wait_js(f"!{DIALOG}", "chiusura con Esc")
    assert invites.get(invite.invite_id).status == "declined"
