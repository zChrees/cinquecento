"""P27: il calcolo di Glicko-2 (app/services/glicko2.py), senza database.

Il riferimento è l'esempio numerico del documento di Mark Glickman,
"Example of the Glicko-2 system" (2013): un giocatore 1500 / 200 / 0,06 gioca contro
1400 / 30 (vince), 1550 / 100 (perde) e 1700 / 300 (perde), con tau 0,5, e arriva a
circa 1464,06 / 151,52 / 0,05999.
"""

import math

import pytest

from app.services.glicko2 import Rating, Result, team_opponent, update
from config import BaseConfig

TAU = 0.5
NEW = Rating(1500, 350, 0.06)


def test_esempio_del_documento_di_glickman():
    player = Rating(1500, 200, 0.06)
    results = [
        Result(Rating(1400, 30, 0.06), 1),
        Result(Rating(1550, 100, 0.06), 0),
        Result(Rating(1700, 300, 0.06), 0),
    ]
    after = update(player, results, TAU)
    assert after.value == pytest.approx(1464.06, abs=0.01)
    assert after.deviation == pytest.approx(151.52, abs=0.01)
    assert after.volatility == pytest.approx(0.05999, abs=0.00001)


def test_valori_di_config():
    assert (BaseConfig.RATING_INITIAL, BaseConfig.RATING_RD_INITIAL, BaseConfig.RATING_VOLATILITY_INITIAL) == (
        1500, 350, 0.06
    )
    assert BaseConfig.GLICKO_TAU == TAU


def test_senza_partite_cresce_solo_la_deviazione():
    player = Rating(1600, 100, 0.06)
    after = update(player, [], TAU)
    assert after.value == 1600 and after.volatility == 0.06
    assert after.deviation == pytest.approx(math.sqrt((100 / 173.7178) ** 2 + 0.06 ** 2) * 173.7178)


def test_vittoria_sale_sconfitta_scende_pareggio_fermo():
    win = update(NEW, [Result(NEW, 1)], TAU)
    loss = update(NEW, [Result(NEW, 0)], TAU)
    draw = update(NEW, [Result(NEW, 0.5)], TAU)
    assert win.value > 1500 > loss.value
    assert win.value - 1500 == pytest.approx(1500 - loss.value)  # simmetrico
    assert draw.value == pytest.approx(1500)
    for after in (win, loss, draw):
        assert after.deviation < 350  # dopo una partita il sistema è più sicuro


def test_battere_un_avversario_forte_vale_di_piu():
    weak = update(NEW, [Result(Rating(1300, 100, 0.06), 1)], TAU)
    strong = update(NEW, [Result(Rating(1800, 100, 0.06), 1)], TAU)
    assert strong.value - 1500 > weak.value - 1500 > 0


def test_un_giocatore_sicuro_si_muove_meno():
    unsure = update(Rating(1500, 350, 0.06), [Result(NEW, 1)], TAU)
    sure = update(Rating(1500, 60, 0.06), [Result(NEW, 1)], TAU)
    assert unsure.value - 1500 > sure.value - 1500 > 0


@pytest.mark.parametrize(("player", "opponent", "score"), [
    (Rating(1500, 350, 0.06), Rating(2800, 30, 0.06), 1),  # sorpresa enorme (ramo "delta grande" del passo 5)
    (Rating(2800, 30, 0.06), Rating(1000, 350, 0.06), 0),
    (Rating(100, 30, 0.2), Rating(3000, 30, 0.2), 0.5),
])
def test_casi_estremi_numeri_finiti(player, opponent, score):
    after = update(player, [Result(opponent, score)], TAU)
    for value in (after.value, after.deviation, after.volatility):
        assert math.isfinite(value)
    assert 0 < after.deviation < 400
    assert after.volatility > 0


def test_squadra_come_un_solo_avversario():
    team = team_opponent([Rating(1400, 100, 0.06), Rating(1600, 200, 0.08)])
    assert team.value == 1500
    assert team.deviation == pytest.approx(math.sqrt((100 ** 2 + 200 ** 2) / 2))
    assert team.volatility == pytest.approx(0.07)
