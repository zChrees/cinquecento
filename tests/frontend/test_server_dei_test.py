"""P124: il server dei test (running_server di tests/browser.py) non lascia schede online.

Spegnendo il server dei test, le schede ancora collegate non passano dallo scollegamento
(connection_events.py), quindi restavano in presence.py per il resto del giro: la home
del file di test successivo mostrava "2 online" invece di 1 e test_suoni_menu.py falliva
quando girava dopo test_rifinitura.py. Ora running_server, allo spegnimento, toglie le
schede collegate mentre era acceso, e lascia quelle che c'erano già prima.

Non serve il browser: le schede si segnano direttamente in presence.py, come farebbe lo
scollegamento. Non serve MySQL.
"""

from app import create_app
from app.realtime.presence import presence
from tests.browser import FakeUser, running_server


def test_spegnendo_il_server_le_sue_schede_non_restano_online():
    presence.add(901, "scheda-di-prima")   # una scheda che c'era già prima del server
    try:
        with running_server(create_app("testing"), FakeUser("Mario", 902)):
            presence.add(902, "scheda-del-server")
            presence.add(903, "altra-scheda-del-server")
            presence.add(901, "seconda-scheda-di-prima-utente")
            assert {901, 902, 903} <= set(presence.online_users())
        assert presence.tabs_of(902) == [] and presence.tabs_of(903) == []
        assert presence.tabs_of(901) == ["scheda-di-prima"]
    finally:
        for user_id in (901, 902, 903):
            for sid in presence.tabs_of(user_id):
                presence.remove(user_id, sid)
