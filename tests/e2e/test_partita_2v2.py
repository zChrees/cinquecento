"""P31: quattro utenti nuovi entrano da soli nella coda 2v2 e giocano fino a 150.

La coda forma le squadre (D17), i compagni stanno uno di fronte all'altro (posti 0 e 2,
1 e 3), nessuno vede le carte degli altri, nemmeno del compagno, e la partita conta
per il rating 2v2 di tutti e quattro.
"""

from tests.e2e.helpers import (
    check_result,
    play_to_the_end,
    request_id,
    sit,
    stats_after,
    wait_game_start,
)


def test_coda_2v2_e_partita_intera(users):
    players = users(4)
    tabs = [user.tab() for user in players]
    for tab in tabs:
        status = tab.call("queue:join", {"request_id": request_id(), "mode": "2v2", "target_score": 150})
        assert status["ok"] is True, status
        assert status["data"]["mode"] == "2v2" and status["data"]["partner"] is None

    game_id = wait_game_start(tabs)
    seats, version = sit(tabs, game_id)
    first = seats[0].state(version)
    assert first["mode"] == "2v2" and first["rated"] is True
    assert [(p["seat"], p["team"]) for p in first["players"]] == [(0, 0), (1, 1), (2, 0), (3, 1)]
    assert {p["username"] for p in first["players"]} == {user.username for user in players}

    views = play_to_the_end(game_id, seats, version)
    result = check_result(views, 150)

    teams = {p["username"]: p["team"] for p in views[0]["players"]}
    for user in players:
        stats_after(user, result, teams[user.username], "2v2", rated=True)
    # I due compagni hanno lo stesso esito
    by_team = {}
    for user in players:
        by_team.setdefault(teams[user.username], []).append(user.api("GET", "/stats/me")["data"]["wins"])
    assert all(len(set(wins)) == 1 for wins in by_team.values())
