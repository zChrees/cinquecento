"""P31: due utenti nuovi si registrano, entrano nella coda 1v1 e giocano fino a 150.

Tutto dall'esterno: la coda li abbina (rating 1500 tutti e due), la partita si gioca
con le mosse ammesse della vista, nessuno vede carte altrui, a fine partita la home
non propone più il rientro e le statistiche contano la partita (con il rating).
"""

from tests.e2e.helpers import (
    check_result,
    play_to_the_end,
    request_id,
    sit,
    stats_after,
    wait_game_start,
)


def test_coda_1v1_e_partita_intera(users):
    primo, secondo = users(2)
    tabs = [primo.tab(), secondo.tab()]
    for tab in tabs:
        status = tab.call("queue:join", {"request_id": request_id(), "mode": "1v1", "target_score": 150})
        assert status["ok"] is True, status
        assert status["data"]["mode"] == "1v1" and status["data"]["target_score"] == 150
        assert status["data"]["partner"] is None

    game_id = wait_game_start(tabs)
    # La home lo sa: chi apre un'altra scheda vede "rientra in partita"
    resume = primo.tab().wait_for("home:status")["resume"]
    assert resume == {"game_id": game_id, "url": f"/game/{game_id}", "mode": "1v1", "target_score": 150}

    seats, version = sit(tabs, game_id)
    first = seats[0].state(version)
    assert first["mode"] == "1v1" and first["rated"] is True and first["target_score"] == 150
    assert {p["username"] for p in first["players"]} == {primo.username, secondo.username}

    marks = [tab.mark() for tab in tabs]
    views = play_to_the_end(game_id, seats, version)
    result = check_result(views, 150)

    # A partita finita: niente più rientro nella home, e le mosse si rifiutano
    for tab, mark in zip(tabs, marks, strict=True):
        tab.wait_for("home:status", lambda status: status["resume"] is None, since=mark)
    answer = seats[0].call("game:play_card", {"game_id": game_id, "version": views[0]["version"],
                                              "card": {"suit": "denari", "rank": 1}})
    assert answer["ok"] is False

    # Statistiche: una partita, che conta per il rating 1v1
    by_name = {p["username"]: p["team"] for p in views[0]["players"]}
    for user in (primo, secondo):
        stats = stats_after(user, result, by_name[user.username], "1v1", rated=True)
        value = stats["ratings"]["1v1"]["value"]
        if result["winner_team"] is None:
            assert value == 1500
        elif result["winner_team"] == by_name[user.username]:
            assert value > 1500
        else:
            assert value < 1500
