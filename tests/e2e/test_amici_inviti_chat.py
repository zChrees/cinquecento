"""P31: amici, chat e inviti a partita, come li usano due o quattro persone vere.

- Richiesta di amicizia e accettazione con le rotte HTTP, avvisi friends:changed e
  friends:presence, chat (anche con testo che sembra HTML: si salva così com'è),
  blocco che chiude la chat.
- Invito 1v1: partita intera che non conta per il rating (D36); intanto l'amico
  risulta "in partita".
- Invito 2v2: la coppia entra in coda con il compagno, due singoli completano il
  tavolo; chi abbandona fa perdere la squadra, ma il rating scende solo a lui (D13).
"""

from tests.e2e.helpers import (
    check_result,
    play_to_the_end,
    request_id,
    sit,
    stats_after,
    wait_game_start,
)


def befriend(sender, receiver, sender_tab, receiver_tab):
    """sender manda la richiesta, receiver accetta: tutti e due ricevono l'avviso."""
    answer = sender.api("POST", "/friends/requests", {"request_id": request_id(), "username": receiver.username})
    assert answer["ok"] is True, answer
    assert answer["data"]["user_id"] == receiver.id
    receiver_tab.wait_for("friends:changed", lambda data: data["reason"] == "request_received")
    requests_in = receiver.api("GET", "/friends/")["data"]["requests_in"]
    assert [item["user_id"] for item in requests_in] == [sender.id]
    # La stessa richiesta ha la stessa ora nella risposta e nelle liste di tutti e due
    requests_out = sender.api("GET", "/friends/")["data"]["requests_out"]
    assert requests_out == [answer["data"]]
    assert requests_in[0]["sent_at"] == answer["data"]["sent_at"]
    assert receiver.api("POST", f"/friends/requests/{sender.id}/accept") == {"ok": True}
    sender_tab.wait_for("friends:changed", lambda data: data["reason"] == "request_accepted")


def friend_entry(user, friend_id):
    friends = user.api("GET", "/friends/")["data"]["friends"]
    return next((item for item in friends if item["user_id"] == friend_id), None)


def invite(host, guest, host_tab, guest_tab, mode):
    """host invita guest, guest accetta, host preme Gioca: restituisce la risposta di invite:start."""
    sent = host_tab.call("invite:send", {"request_id": request_id(), "user_id": guest.id,
                                         "mode": mode, "target_score": 150})
    assert sent["ok"] is True, sent
    invite_id = sent["data"]["invite_id"]
    assert sent["data"]["status"] == "pending"
    received = guest_tab.wait_for("invite:received", lambda data: data["invite_id"] == invite_id)
    assert received["from"]["user_id"] == host.id and received["mode"] == mode
    assert guest_tab.call("invite:accept", {"invite_id": invite_id}) == {"ok": True}
    host_tab.wait_for("invite:update", lambda data: data == {"invite_id": invite_id, "status": "accepted"})
    started = host_tab.call("invite:start", {"invite_id": invite_id})
    assert started["ok"] is True, started
    for tab in (host_tab, guest_tab):
        tab.wait_for("invite:update", lambda data: data == {"invite_id": invite_id, "status": "started"})
    return started


# --- Amicizia, presenza, chat, blocco -------------------------------------------------


def test_amicizia_chat_e_blocco(users):
    anna, bruno = users(2)
    tab_anna, tab_bruno = anna.tab(), bruno.tab()
    befriend(anna, bruno, tab_anna, tab_bruno)
    assert friend_entry(anna, bruno.id)["presence"] == "online"

    # Bruno chiude la scheda e la riapre: Anna lo vede uscire e tornare
    tab_bruno.close()
    tab_anna.wait_for("friends:presence", lambda data: data == {"user_id": bruno.id, "presence": "offline"})
    assert friend_entry(anna, bruno.id)["presence"] == "offline"
    mark = tab_anna.mark()
    tab_bruno = bruno.tab()
    tab_anna.wait_for("friends:presence", lambda data: data == {"user_id": bruno.id, "presence": "online"},
                      since=mark)

    # Chat: il testo arriva così com'è, anche se sembra HTML; lo stesso request_id non fa doppioni
    text = "<script>alert('ciao')</script> Ciao Bruno!"
    first = {"request_id": request_id(), "user_id": bruno.id, "text": text}
    sent = tab_anna.call("chat:send", first)
    assert sent["ok"] is True, sent
    message = sent["data"]["message"]
    assert message["text"] == text and message["from_user_id"] == anna.id and message["to_user_id"] == bruno.id
    assert tab_anna.call("chat:send", first) == sent
    assert tab_bruno.wait_for("chat:message") == {"message": message}
    # Subito dopo un altro messaggio: al massimo 1 al secondo
    too_fast = tab_anna.call("chat:send", {"request_id": request_id(), "user_id": bruno.id, "text": "Ci sei?"})
    assert too_fast["ok"] is False and too_fast["error"]["code"] == "too_fast"
    assert too_fast["error"]["retry_after"] >= 1

    assert bruno.api("GET", "/friends/")["data"]["counters"]["unread_messages"] == 1
    history = tab_bruno.call("chat:history", {"user_id": anna.id, "before_id": None})
    assert history["ok"] is True
    assert history["data"]["messages"] == [message]
    assert history["data"]["can_write"] is True and history["data"]["has_more"] is False
    assert bruno.api("GET", "/friends/")["data"]["counters"]["unread_messages"] == 0

    # Bruno blocca Anna: l'amicizia finisce e nessuno dei due può più scrivere
    assert bruno.api("POST", "/friends/blocks", {"request_id": request_id(), "user_id": anna.id}) == {"ok": True}
    tab_anna.wait_for("friends:changed", lambda data: data["reason"] == "friend_removed")
    assert friend_entry(anna, bruno.id) is None
    # Scrive Bruno, che non ha ancora scritto (Anna sarebbe fermata dal limite di 1 al secondo)
    blocked = tab_bruno.call("chat:send", {"request_id": request_id(), "user_id": anna.id, "text": "Ciao"})
    assert blocked["ok"] is False and blocked["error"]["code"] == "blocked"
    history = tab_anna.call("chat:history", {"user_id": bruno.id, "before_id": None})
    assert history["data"]["messages"] == [message]  # la conversazione resta visibile (D24)
    assert history["data"]["can_write"] is False


def test_invito_con_chi_non_e_amico_rifiutato(users):
    anna, bruno = users(2)
    tab_anna, _tab_bruno = anna.tab(), bruno.tab()
    answer = tab_anna.call("invite:send", {"request_id": request_id(), "user_id": bruno.id,
                                           "mode": "1v1", "target_score": 150})
    assert answer["ok"] is False and answer["error"]["code"] == "not_friends"


# --- Inviti a partita -----------------------------------------------------------------


def test_invito_1v1_partita_intera_senza_rating(users):
    anna, bruno = users(2)
    tab_anna, tab_bruno = anna.tab(), bruno.tab()
    befriend(anna, bruno, tab_anna, tab_bruno)

    started = invite(anna, bruno, tab_anna, tab_bruno, "1v1")
    assert started == {"ok": True}
    game_id = wait_game_start([tab_anna, tab_bruno])
    tab_anna.wait_for("friends:presence", lambda data: data == {"user_id": bruno.id, "presence": "in_game"})
    assert friend_entry(anna, bruno.id)["presence"] == "in_game"

    seats, version = sit([tab_anna, tab_bruno], game_id)
    assert seats[0].state(version)["rated"] is False
    mark = tab_anna.mark()
    views = play_to_the_end(game_id, seats, version)
    result = check_result(views, 150)

    teams = {p["username"]: p["team"] for p in views[0]["players"]}
    for user in (anna, bruno):
        stats = stats_after(user, result, teams[user.username], "1v1", rated=False)
        assert stats["ratings"]["1v1"]["value"] == 1500
    # A partita finita Bruno torna "online" per Anna
    tab_anna.wait_for("friends:presence", lambda data: data == {"user_id": bruno.id, "presence": "online"},
                      since=mark)


def test_invito_2v2_coppia_in_coda_e_abbandono(users):
    anna, bruno, carlo, dora = users(4)
    tab_anna, tab_bruno, tab_carlo, tab_dora = (user.tab() for user in (anna, bruno, carlo, dora))
    befriend(anna, bruno, tab_anna, tab_bruno)

    started = invite(anna, bruno, tab_anna, tab_bruno, "2v2")
    # Nel 2v2 la coppia entra in coda: la risposta è lo stato della coda, con il compagno
    assert started["data"]["mode"] == "2v2" and started["data"]["partner"]["user_id"] == bruno.id
    status = tab_bruno.wait_for("queue:status")
    assert status["partner"]["user_id"] == anna.id

    for tab in (tab_carlo, tab_dora):
        joined = tab.call("queue:join", {"request_id": request_id(), "mode": "2v2", "target_score": 150})
        assert joined["ok"] is True, joined
    tabs = [tab_anna, tab_bruno, tab_carlo, tab_dora]
    game_id = wait_game_start(tabs)
    seats, version = sit(tabs, game_id)
    view = seats[0].state(version)
    teams = {p["username"]: p["team"] for p in view["players"]}
    assert view["rated"] is True
    assert teams[anna.username] == teams[bruno.username] != teams[carlo.username] == teams[dora.username]

    # Anna esce dal tavolo: la partita finisce subito, e la sua squadra perde (D13)
    marks = [tab.mark() for tab in tabs]
    assert tab_anna.call("game:leave", {"game_id": game_id}) == {"ok": True}
    anna_seat = next(p["seat"] for p in view["players"] if p["username"] == anna.username)
    final = [tab.wait_for("game:state", lambda state: state["status"] == "finished") for tab in tabs]
    result = final[0]["result"]
    assert all(state["result"] == result for state in final)
    assert result["reason"] == "abandon" and result["abandoned_seats"] == [anna_seat]
    assert result["winner_team"] == teams[carlo.username]

    # Rating: scende ad Anna, sale agli avversari; Bruno resta com'era (D13, P30)
    for tab, mark in zip(tabs, marks, strict=True):
        tab.wait_for("home:status", lambda status: status["resume"] is None, since=mark)
    stats = {user.username: user.api("GET", "/stats/me")["data"] for user in (anna, bruno, carlo, dora)}
    assert stats[anna.username]["losses"] == 1 and stats[anna.username]["ratings"]["2v2"]["games"] == 1
    assert stats[anna.username]["ratings"]["2v2"]["value"] < 1500
    assert stats[bruno.username]["losses"] == 1
    assert stats[bruno.username]["ratings"]["2v2"] == {"value": 1500, "games": 0, "provisional": True}
    for name in (carlo.username, dora.username):
        assert stats[name]["wins"] == 1 and stats[name]["ratings"]["2v2"]["games"] == 1
        assert stats[name]["ratings"]["2v2"]["value"] > 1500
