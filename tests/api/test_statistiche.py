"""P30: pannello statistiche con i dati veri (GET /stats/me, contratto 2.1).

Controlla il "Fatto quando" di SCALETTA.md (P30): dopo partite simulate note, le
cifre coincidono con quelle attese; un utente vede solo le proprie statistiche; il
pannello si legge bene a 360 px. Le partite si salvano con match_service.save_match
(P26), come a fine partita: così anche il rating è calcolato davvero (P27).

Serve MySQL con scripts/setup_db.sql già lanciato: si usa SOLO il database dei
test, che all'inizio viene svuotato e ricreato con migrate.py; prima di ogni prova
le tabelle si svuotano. Il controllo nel browser (Chrome o Edge senza finestra,
tests/browser.py) si salta se nessuno dei due è installato.
Comando: python tests/esegui_tutti.py api
"""

import importlib.util
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import sqlalchemy as sa

from app import create_app
from app.extensions import db
from app.services import auth_service, match_service, stats_service
from app.services.auth_service import LoginLimiter
from app.services.match_service import MatchRecord, PlayerRecord
from tests.browser import TEST_COOKIE, Browser, FakeUser, find_browser, running_server

BASE_DIR = Path(__file__).resolve().parents[2]
PASSWORD = "Password-di-prova-30"
TABLES = ("messaggi", "blocchi", "amicizie", "mosse_partita", "giocatori_partita", "partite", "rating", "utenti")
START = datetime(2026, 9, 28, 18, 0, 0, tzinfo=UTC).replace(tzinfo=None)  # UTC, come nel database


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


class Player:
    """Un utente con la sua sessione: registrato e con il login fatto."""

    def __init__(self, app, username):
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

    def stats(self):
        response = self.client.get("/stats/me")
        body = response.get_json()
        assert response.status_code == 200 and body["ok"] is True, body
        return body["data"]


@pytest.fixture
def players(app):
    return {name: Player(app, name) for name in ("Mario", "Turi", "Luca", "Rosa")}


def _save(app, mode, players, winner_team, *, rated=True, abandoned=(), number=0):
    """Salva una partita finita come fa la stanza (P26): players nell'ordine dei posti."""
    started = START + timedelta(minutes=10 * number)
    reason = "abbandono" if abandoned else "punteggio"
    record = MatchRecord(
        mode=mode, target_score=150, rated=rated,
        started_at=started, ended_at=started + timedelta(minutes=8),
        reason=reason, winner_team=winner_team, scores=(150, 90),
        players=tuple(PlayerRecord(seat, player.id, player in abandoned) for seat, player in enumerate(players)),
        moves=(),
    )
    with app.app_context():
        match_service.save_match(record)


def _rating_in_db(app, player, mode):
    with app.app_context():
        value = db.session.execute(
            sa.text("SELECT valore FROM rating WHERE utente_id = :u AND modalita = :m"),
            {"u": player.id, "m": mode},
        ).scalar()
    return None if value is None else float(value)


# --- Risposte del server ------------------------------------------------------------


def test_senza_login_not_logged_in(app):
    response = app.test_client().get("/stats/me")
    assert response.status_code == 401
    assert response.get_json() == {"ok": False, "error": {"code": "not_logged_in", "message": "Accedi per continuare."}}


def test_utente_nuovo(players):
    assert players["Mario"].stats() == {
        "games": 0, "wins": 0, "losses": 0, "draws": 0, "win_rate": None,
        "ratings": {
            "1v1": {"value": 1500, "games": 0, "provisional": True},
            "2v2": {"value": 1500, "games": 0, "provisional": True},
        },
    }


def test_cifre_dopo_partite_note(app, players):
    mario, turi, luca, rosa = (players[n] for n in ("Mario", "Turi", "Luca", "Rosa"))
    # 1v1 che contano: Mario vince 2, perde 1, pareggia 1
    _save(app, "1v1", (mario, turi), 0, number=1)
    _save(app, "1v1", (turi, mario), 1, number=2)
    _save(app, "1v1", (mario, turi), 1, number=3)
    _save(app, "1v1", (mario, turi), None, number=4)
    # 1v1 contro un amico: non conta per il rating (D36), ma è una partita vinta
    _save(app, "1v1", (mario, turi), 0, rated=False, number=5)
    # 2v2: Mario (posto 0) e Luca (posto 2) contro Turi e Rosa; Luca abbandona:
    # perde tutta la squadra, ma il rating di Mario non cambia (D13) e la partita
    # non conta tra le sue partite per il rating (scelta di P30)
    _save(app, "2v2", (mario, turi, luca, rosa), 1, abandoned=(luca,), number=6)

    stats = mario.stats()
    assert {key: stats[key] for key in ("games", "wins", "losses", "draws", "win_rate")} == {
        "games": 6, "wins": 3, "losses": 2, "draws": 1, "win_rate": 50,
    }
    value_1v1 = _rating_in_db(app, mario, "1v1")
    assert stats["ratings"]["1v1"] == {"value": int(value_1v1 + 0.5), "games": 4, "provisional": True}
    assert _rating_in_db(app, mario, "2v2") is None
    assert stats["ratings"]["2v2"] == {"value": 1500, "games": 0, "provisional": True}

    # Chi ha abbandonato: la partita conta, e il suo rating 2v2 è sceso
    luca_stats = luca.stats()
    assert luca_stats["games"] == 1 and luca_stats["losses"] == 1 and luca_stats["win_rate"] == 0
    assert luca_stats["ratings"]["2v2"]["games"] == 1
    assert luca_stats["ratings"]["2v2"]["value"] < 1500

    # Ognuno vede solo le proprie: Turi ha i risultati rovesciati
    turi_stats = turi.stats()
    assert {key: turi_stats[key] for key in ("games", "wins", "losses", "draws", "win_rate")} == {
        "games": 6, "wins": 2, "losses": 3, "draws": 1, "win_rate": 33,
    }
    assert turi_stats["ratings"]["1v1"]["games"] == 4
    assert turi_stats["ratings"]["2v2"]["games"] == 1
    assert stats != turi_stats


def test_provvisorio_finisce_dopo_dieci_partite(app, players):
    mario, turi = players["Mario"], players["Turi"]
    for number in range(9):
        _save(app, "1v1", (mario, turi), 0, number=number)
    assert mario.stats()["ratings"]["1v1"]["provisional"] is True
    _save(app, "1v1", (mario, turi), 0, number=9)
    rating = mario.stats()["ratings"]["1v1"]
    assert rating["games"] == 10 and rating["provisional"] is False
    assert rating["value"] > 1500
    assert mario.stats()["win_rate"] == 100


def test_utente_cancellato_non_conta(app, players):
    mario, turi = players["Mario"], players["Turi"]
    _save(app, "1v1", (mario, turi), 0)
    with app.app_context():
        db.session.execute(sa.text("DELETE FROM utenti WHERE id = :u"), {"u": turi.id})
        db.session.commit()
    stats = mario.stats()
    assert stats["games"] == 1 and stats["wins"] == 1


@pytest.mark.parametrize(("wins", "games", "expected"), [
    (0, 0, None), (0, 5, 0), (1, 3, 33), (2, 3, 67), (1, 8, 13), (3, 8, 38), (5, 5, 100),
])
def test_percentuale_arrotondata(wins, games, expected):
    assert stats_service.win_rate(wins, games) == expected


def test_forma_uguale_all_esempio_del_contratto(players):
    example = json.loads((BASE_DIR / "app" / "static" / "dev" / "statistiche_esempio.json").read_text(encoding="utf-8"))
    example.pop("_nota")
    stats = players["Mario"].stats()
    assert stats.keys() == example.keys()
    assert stats["ratings"].keys() == example["ratings"].keys()
    for mode in stats["ratings"]:
        assert stats["ratings"][mode].keys() == example["ratings"][mode].keys()


# --- Il pannello nel browser ----------------------------------------------------------


def test_pannello_a_360_px_con_i_dati_veri(app, players, tmp_path):
    mario, turi = players["Mario"], players["Turi"]
    _save(app, "1v1", (mario, turi), 0, number=1)
    _save(app, "1v1", (mario, turi), 1, number=2)
    _save(app, "1v1", (mario, turi), 0, number=3)
    expected = mario.stats()

    with running_server(app, FakeUser("Mario", mario.id)) as url:
        browser = Browser(find_browser(), tmp_path / "chrome")
        try:
            browser.send("Network.setCookie", name=TEST_COOKIE[0], value=TEST_COOKIE[1], url=url)
            browser.open(f"{url}/", 360, 640, "document.querySelector('[data-open-stats]') !== null")
            browser.click("[data-open-stats]")
            browser.wait_js("document.querySelector('[data-stats-body] .stats-grid') !== null", "statistiche")
            shown = browser.js("""Object.fromEntries([...document.querySelectorAll('[data-stats-body] [data-stat]')]
              .map((s) => [s.dataset.stat, s.querySelector('dd').textContent]))""")
            box = browser.js("""(() => {
              const b = document.querySelector('#stats').getBoundingClientRect();
              return { l: b.left, t: b.top, r: b.right, b: b.bottom, w: innerWidth, h: innerHeight,
                       sw: document.scrollingElement.scrollWidth };
            })()""")
        finally:
            browser.close()

    rating_1v1 = expected["ratings"]["1v1"]["value"]
    assert shown == {
        "Partite": "3", "Vinte": "2", "Perse": "1", "Vittorie": "67%",
        "Rating 1v1": f"{rating_1v1}provvisorio", "Rating 2v2": "1500provvisorio",
    }
    assert box["l"] >= 0 and box["t"] >= 0 and box["r"] <= box["w"] and box["b"] <= box["h"], box
    assert box["sw"] <= box["w"], "la pagina scorre in orizzontale"
