"""P27: aggiornamento del rating a fine partita, nella stessa transazione del salvataggio.

Si salvano partite finte con match_service.save_match (come fa la stanza a fine
partita) e si controlla la tabella rating. Serve MySQL con scripts/setup_db.sql già
lanciato: si usa SOLO il database dei test, che all'inizio viene svuotato e ricreato
con migrate.py. Comando: python tests/esegui_tutti.py services
"""

import importlib.util
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import sqlalchemy as sa

from app import create_app
from app.extensions import db
from app.repositories import rating_repo
from app.services import auth_service, glicko2, match_service
from app.services.match_service import MatchRecord, PlayerRecord

BASE_DIR = Path(__file__).resolve().parents[2]
PASSWORD = "Password-di-prova-27"
NAMES = ("Anna", "Bruno", "Carla", "Dario")
NEW = glicko2.Rating(1500, 350, 0.06)
TAU = 0.5
ENDED = datetime(2026, 9, 28, 20, 0, 0, tzinfo=UTC).replace(tzinfo=None)  # UTC, come nel database


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
def clean(app):
    with app.app_context():
        db.session.execute(sa.text("DELETE FROM partite"))
        db.session.execute(sa.text("DELETE FROM rating"))
        db.session.commit()


def save(app, names, winner=0, rated=True, reason="punteggio", abandoned=None, target=150, ended=ENDED):
    """Salva una partita finta: `names` nell'ordine dei posti (2 per il 1v1, 4 per il 2v2)."""
    mode = "1v1" if len(names) == 2 else "2v2"
    record = MatchRecord(
        mode=mode, target_score=target, rated=rated, started_at=ended - timedelta(minutes=20),
        ended_at=ended, reason=reason, winner_team=winner, scores=(target, 40) if winner == 0 else (40, target),
        players=tuple(PlayerRecord(seat, app.user_ids[n], abandoned=seat == abandoned) for seat, n in enumerate(names)),
        moves=(),
    )
    with app.app_context():
        return match_service.save_match(record)


def ratings(app, mode=None):
    """{nome: (valore, deviazione, volatilità, modalità, aggiornato_il)}."""
    names = {uid: name for name, uid in app.user_ids.items()}
    sql = "SELECT * FROM rating" + (" WHERE modalita = :m" if mode else "")
    with app.app_context():
        found = db.session.execute(sa.text(sql), {"m": mode}).mappings().all()
    return {names[r["utente_id"]]: r for r in found}


def as_rating(row):
    return glicko2.Rating(row["valore"], row["deviazione"], row["volatilita"])


def assert_same(row, expected):
    assert row["valore"] == pytest.approx(expected.value)
    assert row["deviazione"] == pytest.approx(expected.deviation)
    assert row["volatilita"] == pytest.approx(expected.volatility)


# --- 1v1 ---


def test_prima_partita_1v1_crea_il_rating(app):
    save(app, ["Anna", "Bruno"], winner=0)
    found = ratings(app)
    assert set(found) == {"Anna", "Bruno"}
    assert_same(found["Anna"], glicko2.update(NEW, [glicko2.Result(NEW, 1)], TAU))
    assert_same(found["Bruno"], glicko2.update(NEW, [glicko2.Result(NEW, 0)], TAU))
    assert found["Anna"]["valore"] > 1500 > found["Bruno"]["valore"]
    assert all(r["modalita"] == "1v1" and r["aggiornato_il"] == ENDED for r in found.values())


def test_la_seconda_partita_parte_dal_rating_salvato(app):
    save(app, ["Anna", "Bruno"], winner=0)
    first = ratings(app)
    save(app, ["Anna", "Bruno"], winner=1, ended=ENDED + timedelta(hours=1))
    second = ratings(app)
    anna, bruno = as_rating(first["Anna"]), as_rating(first["Bruno"])
    assert_same(second["Anna"], glicko2.update(anna, [glicko2.Result(bruno, 0)], TAU))
    assert_same(second["Bruno"], glicko2.update(bruno, [glicko2.Result(anna, 1)], TAU))
    assert second["Anna"]["aggiornato_il"] == ENDED + timedelta(hours=1)


def test_pareggio_vale_mezzo_punto(app):
    save(app, ["Anna", "Bruno"], winner=None)
    found = ratings(app)
    assert found["Anna"]["valore"] == pytest.approx(1500)
    assert found["Bruno"]["valore"] == pytest.approx(1500)
    assert found["Anna"]["deviazione"] < 350


def test_1v1_contro_un_amico_non_cambia_il_rating(app):
    save(app, ["Anna", "Bruno"], winner=0, rated=False)
    assert ratings(app) == {}


def test_stesso_rating_a_150_300_e_500(app):
    results = []
    for target in (150, 300, 500):
        save(app, ["Anna", "Bruno"], winner=0, target=target)
        results.append(round(ratings(app)["Anna"]["valore"], 9))
        with app.app_context():
            db.session.execute(sa.text("DELETE FROM rating"))
            db.session.commit()
    assert len(set(results)) == 1


def test_abbandono_1v1_chi_esce_perde(app):
    save(app, ["Anna", "Bruno"], winner=1, reason="abbandono", abandoned=0)
    found = ratings(app)
    assert found["Anna"]["valore"] < 1500 < found["Bruno"]["valore"]


# --- 2v2 ---


def test_2v2_la_squadra_avversaria_come_un_solo_avversario(app):
    # Prima un 1v1: il suo rating non deve entrare nel 2v2 (rating separati)
    save(app, ["Anna", "Bruno"], winner=0)
    save(app, ["Anna", "Bruno", "Carla", "Dario"], winner=0)  # squadra 0: Anna e Carla
    found = ratings(app, "2v2")
    assert set(found) == set(NAMES)
    opponent = glicko2.team_opponent([NEW, NEW])
    for name, score in (("Anna", 1), ("Carla", 1), ("Bruno", 0), ("Dario", 0)):
        assert_same(found[name], glicko2.update(NEW, [glicko2.Result(opponent, score)], TAU))
    # Il 1v1 non è cambiato con il 2v2: rating separati
    one = ratings(app, "1v1")
    assert set(one) == {"Anna", "Bruno"}
    assert_same(one["Anna"], glicko2.update(NEW, [glicko2.Result(NEW, 1)], TAU))


def test_2v2_con_rating_diversi(app):
    save(app, ["Anna", "Bruno", "Carla", "Dario"], winner=0)
    before = {n: as_rating(r) for n, r in ratings(app, "2v2").items()}
    save(app, ["Anna", "Carla", "Bruno", "Dario"], winner=1, ended=ENDED + timedelta(hours=1))
    # squadra 0 = Anna e Bruno (posti 0 e 2), squadra 1 = Carla e Dario (posti 1 e 3): vince la 1
    after = ratings(app, "2v2")
    teams = {"Anna": 0, "Bruno": 0, "Carla": 1, "Dario": 1}
    for name, team in teams.items():
        opponents = [before[n] for n, t in teams.items() if t != team]
        expected = glicko2.update(before[name], [glicko2.Result(glicko2.team_opponent(opponents), float(team == 1))],
                                  TAU)
        assert_same(after[name], expected)


def test_abbandono_2v2_scende_solo_chi_ha_abbandonato(app):
    save(app, ["Anna", "Bruno", "Carla", "Dario"], winner=0)
    before = ratings(app, "2v2")
    # Bruno (posto 1, squadra 1) abbandona: perde la squadra 1, ma Dario resta com'era (D13)
    save(app, ["Anna", "Bruno", "Carla", "Dario"], winner=0, reason="abbandono", abandoned=1,
         ended=ENDED + timedelta(hours=1))
    after = ratings(app, "2v2")
    assert after["Bruno"]["valore"] < before["Bruno"]["valore"]
    assert after["Dario"]["valore"] == before["Dario"]["valore"]
    assert after["Dario"]["aggiornato_il"] == before["Dario"]["aggiornato_il"]
    assert after["Anna"]["valore"] > before["Anna"]["valore"]
    assert after["Carla"]["valore"] > before["Carla"]["valore"]


def test_compagno_di_chi_abbandona_alla_prima_partita_non_ha_riga(app):
    save(app, ["Anna", "Bruno", "Carla", "Dario"], winner=0, reason="abbandono", abandoned=1)
    assert set(ratings(app, "2v2")) == {"Anna", "Bruno", "Carla"}


def test_2v2_con_un_amico_come_compagno_conta(app):
    save(app, ["Anna", "Bruno", "Carla", "Dario"], winner=0, rated=True)
    assert len(ratings(app, "2v2")) == 4


# --- Stessa transazione del salvataggio ---


def test_se_il_rating_fallisce_non_si_salva_nemmeno_la_partita(app, monkeypatch):
    def broken(*_args, **_kwargs):
        raise RuntimeError("errore di prova nel rating")

    monkeypatch.setattr(rating_repo, "add", broken)
    with pytest.raises(RuntimeError):
        save(app, ["Anna", "Bruno"], winner=0)
    with app.app_context():
        for table in ("partite", "giocatori_partita", "rating"):
            assert db.session.execute(sa.text(f"SELECT COUNT(*) FROM {table}")).scalar() == 0, table


def test_se_la_partita_fallisce_il_rating_non_cambia(app):
    save(app, ["Anna", "Bruno"], winner=0)
    before = ratings(app)
    record = MatchRecord(
        mode="1v1", target_score=150, rated=True, started_at=ENDED, ended_at=ENDED, reason="punteggio",
        winner_team=0, scores=(150, 40),
        players=(PlayerRecord(0, app.user_ids["Anna"]), PlayerRecord(1, 999_999)),  # utente inesistente
        moves=(),
    )
    with app.app_context(), pytest.raises(sa.exc.IntegrityError):
        match_service.save_match(record)
    assert ratings(app) == before
