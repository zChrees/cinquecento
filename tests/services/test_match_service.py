"""P26: salvataggio delle partite finite (match_service e la chiamata in room.py).

Partite simulate con la stanza vera (app/realtime/room.py, senza client): si gioca
fino alla fine o si abbandona, poi si controlla cosa c'è nel database. Serve MySQL
con scripts/setup_db.sql già lanciato: si usa SOLO il database dei test, che
all'inizio viene svuotato e ricreato con migrate.py.
Comando: python tests/esegui_tutti.py services
"""

import importlib.util
import json
import random
import threading
import time
from pathlib import Path

import pytest
import sqlalchemy as sa

from app import create_app
from app.extensions import db
from app.game.engine.cards import Card, Rank, Suit
from app.realtime import room as room_module
from app.realtime.room import Player, Room
from app.repositories import match_repo
from app.services import auth_service, match_service
from app.services.match_service import MatchRecord, MoveRecord, PlayerRecord

BASE_DIR = Path(__file__).resolve().parents[2]
PASSWORD = "Password-di-prova-26"
NAMES = ("Primo", "Secondo", "Terzo", "Quarto")
WAIT = 5


def _load_migrate():
    spec = importlib.util.spec_from_file_location("migrate", BASE_DIR / "scripts" / "migrate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def app():
    app = create_app("testing")
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
        app.user_ids = {n: auth_service.register(n, f"{n.lower()}@esempio.it", PASSWORD).id for n in NAMES}
    return app


@pytest.fixture(autouse=True)
def clean(app, monkeypatch):
    # Timer lunghi: nessuna mossa automatica né abbandono se non li chiede la prova
    monkeypatch.setattr(room_module, "TURN_SECONDS", 3600)
    monkeypatch.setattr(room_module, "RECONNECT_SECONDS", 3600)
    with app.app_context():
        db.session.execute(sa.text("DELETE FROM partite"))  # giocatori e mosse spariscono con la partita
        db.session.commit()
    yield


def new_room(app, mode="1v1", rated=True, seed=1, in_app=True):
    names = NAMES[: 2 if mode == "1v1" else 4]
    players = [Player(user_id=app.user_ids[n], username=n) for n in names]
    room = Room(f"prova-{seed}-{mode}")
    if in_app:
        with app.app_context():
            room.start(players, 150, rated=rated, rng=random.Random(seed))
    else:
        room.start(players, 150, rated=rated, rng=random.Random(seed))
    return room


def card_of(data):
    return Card(Suit(data["suit"]), Rank(data["rank"]))


def play_moves(room, limit=10_000):
    """Gioca fino alla fine (o per `limit` mosse): canta se può, altrimenti la prima carta ammessa.
    Restituisce le mosse fatte, nella forma in cui si salvano."""
    done = []
    while not room.finished and len(done) < limit:
        seat = room.game.hand.turn_seat
        legal = room.view_for(seat)["legal"]
        if legal["sing"]:
            room.sing(seat, Suit(legal["sing"][0]))
            done.append(("canta", seat, {"seme": legal["sing"][0]}))
        else:
            card = legal["play"][0]
            room.play(seat, card_of(card))
            done.append(("gioca_carta", seat, {"seme": card["suit"], "valore": card["rank"]}))
    return done


def rows(app, sql, **params):
    with app.app_context():
        return [dict(r._mapping) for r in db.session.execute(sa.text(sql), params)]


def matches(app):
    return rows(app, "SELECT * FROM partite ORDER BY id")


def players_of(app, match_id):
    return rows(app, "SELECT * FROM giocatori_partita WHERE partita_id = :m ORDER BY posto", m=match_id)


def moves_of(app, match_id):
    return rows(app, "SELECT * FROM mosse_partita WHERE partita_id = :m ORDER BY numero", m=match_id)


def details(move):
    value = move["dettagli"]
    return json.loads(value) if isinstance(value, str) else value


# --- Il "Fatto quando" di P26 ---


@pytest.mark.parametrize(("mode", "seed"), [("1v1", 1), ("1v1", 2), ("2v2", 3)])
def test_partita_intera_salvata_con_giocatori_e_mosse_in_ordine(app, mode, seed):
    room = new_room(app, mode, seed=seed)
    played = play_moves(room)
    assert room.finished

    (match,) = matches(app)
    winner = room.game.result.winner_team
    assert (match["modalita"], match["punti_per_vincere"], match["conta_per_rating"]) == (mode, 150, 1)
    assert (match["motivo_fine"], match["squadra_vincente"]) == ("punteggio", winner)
    assert (match["punti_squadra_0"], match["punti_squadra_1"]) == tuple(room.game.scores)
    assert max(room.game.scores) >= 150
    assert match["finita_il"] >= match["iniziata_il"]

    saved_players = players_of(app, match["id"])
    assert [(p["posto"], p["squadra"], p["utente_id"]) for p in saved_players] == [
        (seat, seat % 2, player.user_id) for seat, player in enumerate(room.players)
    ]
    for p in saved_players:
        expected = "pareggio" if winner is None else ("vittoria" if p["squadra"] == winner else "sconfitta")
        assert (p["risultato"], p["ha_abbandonato"]) == (expected, 0)

    saved = moves_of(app, match["id"])
    assert [m["numero"] for m in saved] == list(range(1, len(played) + 1))
    assert [(m["tipo"], m["posto"]) for m in saved] == [(kind, seat) for kind, seat, _ in played]
    for move, (kind, _seat, expected) in zip(saved, played, strict=True):
        got = details(move)
        if kind == "gioca_carta":
            assert got == expected
        else:
            assert got["seme"] == expected["seme"] and got["punti"] in (40, 20)
    hands = [m["mano"] for m in saved]
    assert hands == sorted(hands) and hands[0] == 1 and hands[-1] == room.game.hand_number
    times = [m["creata_il"] for m in saved]
    assert times == sorted(times)


def test_il_primo_canto_di_ogni_mano_vale_40(app):
    found = False
    for seed in range(1, 8):
        room = new_room(app, seed=seed)
        play_moves(room)
        (match,) = matches(app)
        by_hand = {}
        for move in moves_of(app, match["id"]):
            if move["tipo"] == "canta":
                by_hand.setdefault(move["mano"], []).append(details(move)["punti"])
        for points in by_hand.values():
            found = True
            assert points[0] == 40 and all(p == 20 for p in points[1:])
        with app.app_context():
            db.session.execute(sa.text("DELETE FROM partite"))
            db.session.commit()
    assert found, "nessun canto nelle partite di prova"


def test_errore_a_meta_salvataggio_non_lascia_dati(app, monkeypatch, caplog):
    def broken(_match_id, _moves):
        raise RuntimeError("errore di prova a metà salvataggio")

    monkeypatch.setattr(match_repo, "add_moves", broken)
    room = new_room(app)
    play_moves(room)
    assert room.finished  # i giocatori vedono comunque il risultato
    assert "Salvataggio della partita della stanza" in caplog.text
    for table in ("partite", "giocatori_partita", "mosse_partita"):
        assert rows(app, f"SELECT COUNT(*) AS n FROM {table}")[0]["n"] == 0, table


def test_errore_su_un_giocatore_non_lascia_la_partita(app):
    record = MatchRecord(
        mode="1v1", target_score=150, rated=True, started_at=room_module.utc_now(),
        ended_at=room_module.utc_now(), reason="punteggio", winner_team=0, scores=(150, 20),
        players=(PlayerRecord(0, app.user_ids["Primo"]), PlayerRecord(1, 999_999)),  # utente inesistente
        moves=(),
    )
    with app.app_context(), pytest.raises(sa.exc.IntegrityError):
        match_service.save_match(record)
    assert matches(app) == []


# --- Abbandono, mossa automatica, rating ---


def test_abbandono_con_esci(app):
    room = new_room(app)
    played = play_moves(room, limit=7)
    thread = threading.Thread(target=room.abandon, args=(1,))  # fuori da Flask, come un timer
    thread.start()
    thread.join(WAIT)

    (match,) = matches(app)
    assert (match["motivo_fine"], match["squadra_vincente"]) == ("abbandono", 0)
    assert [(p["risultato"], p["ha_abbandonato"]) for p in players_of(app, match["id"])] == [
        ("vittoria", 0), ("sconfitta", 1)
    ]
    saved = moves_of(app, match["id"])
    assert len(saved) == len(played) + 1
    assert (saved[-1]["tipo"], saved[-1]["posto"], details(saved[-1])) == ("abbandono", 1, {"motivo": "esci"})


def test_abbandono_nel_2v2_perde_la_squadra(app):
    room = new_room(app, "2v2", seed=4)
    room.abandon(2)
    (match,) = matches(app)
    assert match["squadra_vincente"] == 1
    assert [(p["posto"], p["risultato"], p["ha_abbandonato"]) for p in players_of(app, match["id"])] == [
        (0, "sconfitta", 0), (1, "vittoria", 0), (2, "sconfitta", 1), (3, "vittoria", 0)
    ]


def test_non_rientrato_in_tempo(app):
    room = new_room(app)
    room.reconnect_seconds = 0.05
    room.join(0, "scheda-di-prova")
    room.disconnect("scheda-di-prova")
    deadline = time.monotonic() + WAIT
    while not matches(app) and time.monotonic() < deadline:
        time.sleep(0.05)  # il salvataggio arriva dal timer del rientro, in un altro thread
    (match,) = matches(app)
    last = moves_of(app, match["id"])[-1]
    assert (last["tipo"], last["posto"], details(last)) == ("abbandono", 0, {"motivo": "tempo_scaduto"})


def test_mossa_automatica_salvata(app):
    room = new_room(app)
    seat = room.game.hand.turn_seat
    room._turn_expired(room._turn_token)  # il tempo del turno è scaduto
    room.abandon(seat)
    (match,) = matches(app)
    first = moves_of(app, match["id"])[0]
    assert (first["tipo"], first["posto"]) == ("mossa_automatica", seat)
    assert set(details(first)) == {"seme", "valore"}


def test_partita_contro_un_amico_non_conta_per_il_rating(app):
    room = new_room(app, rated=False)
    play_moves(room)
    assert matches(app)[0]["conta_per_rating"] == 0


# --- Una volta sola, e solo con Flask ---


def test_si_salva_una_volta_sola(app):
    room = new_room(app)
    play_moves(room)
    room._save()
    assert room.abandon(0) is False  # già finita: niente abbandono
    assert len(matches(app)) == 1


def test_senza_applicazione_flask_non_si_salva(app, caplog):
    room = new_room(app, in_app=False)
    room.abandon(0)
    assert matches(app) == []
    assert "non salvata: nessuna applicazione Flask" in caplog.text


def test_dati_non_validi_rifiutati_prima_di_scrivere(app):
    base = {
        "mode": "1v1", "target_score": 150, "rated": True, "started_at": room_module.utc_now(),
        "ended_at": room_module.utc_now(), "reason": "punteggio", "winner_team": 0, "scores": (150, 20),
        "players": (PlayerRecord(0, app.user_ids["Primo"]), PlayerRecord(1, app.user_ids["Secondo"])),
        "moves": (MoveRecord(1, 0, "gioca_carta", {"seme": "coppe", "valore": 1}, room_module.utc_now()),),
    }
    wrong = [
        {"mode": "3v3"}, {"reason": "noia"}, {"winner_team": 2}, {"scores": (150,)},
        {"players": (PlayerRecord(0, app.user_ids["Primo"]),)},
        {"moves": (MoveRecord(1, 0, "bara", {}, room_module.utc_now()),)},
    ]
    with app.app_context():
        for change in wrong:
            with pytest.raises(ValueError):
                match_service.save_match(MatchRecord(**{**base, **change}))
        assert matches(app) == []
        match_service.save_match(MatchRecord(**base))
    assert len(matches(app)) == 1


def test_log_senza_nomi(app, caplog):
    caplog.set_level("DEBUG")
    room = new_room(app)
    play_moves(room)
    assert "Partita salvata" in caplog.text
    assert not any(name in caplog.text for name in NAMES)
