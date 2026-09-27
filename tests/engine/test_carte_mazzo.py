"""P10: carte, mazzo e parametri delle regole.

Comando (finché P6 non aggiunge il runner): python -m pytest tests/engine
"""

import ast
import random
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from app.game.engine import deck as deck_module
from app.game.engine.cards import Card, Rank, Suit
from app.game.engine.deck import full_deck, shuffled_deck
from app.game.engine.errors import EngineError, InvalidMoveError
from app.game.engine.rules import MARIANNA, RuleSet
from config import load_config

ENGINE_DIR = Path(__file__).resolve().parents[2] / "app" / "game" / "engine"


def test_mazzo_ha_40_carte_tutte_diverse():
    cards = full_deck()
    assert len(cards) == 40
    assert len(set(cards)) == 40
    assert len({card.code for card in cards}) == 40


def test_dieci_carte_per_seme():
    cards = full_deck()
    for suit in Suit:
        assert sum(1 for card in cards if card.suit == suit) == 10


def test_somma_dei_punti_120():
    assert sum(card.points for card in full_deck()) == 120


@pytest.mark.parametrize(
    ("rank", "points"),
    [
        (Rank.ACE, 11),
        (Rank.THREE, 10),
        (Rank.KING, 4),
        (Rank.KNIGHT, 3),
        (Rank.JACK, 2),
        (Rank.SEVEN, 0),
        (Rank.SIX, 0),
        (Rank.FIVE, 0),
        (Rank.FOUR, 0),
        (Rank.TWO, 0),
    ],
)
def test_punti_per_valore(rank, points):
    assert Card(Suit.COPPE, rank).points == points


@pytest.mark.parametrize("suit", list(Suit))
def test_ordine_di_forza(suit):
    expected = [Rank.ACE, Rank.THREE, Rank.KING, Rank.KNIGHT, Rank.JACK,
                Rank.SEVEN, Rank.SIX, Rank.FIVE, Rank.FOUR, Rank.TWO]
    cards = [Card(suit, rank) for rank in Rank]
    by_strength = sorted(cards, key=lambda card: card.strength, reverse=True)
    assert [card.rank for card in by_strength] == expected
    assert len({card.strength for card in cards}) == 10


def test_codice_e_nome_della_carta():
    card = Card(Suit.DENARI, Rank.ACE)
    assert card.code == "denari-1"
    assert str(card) == "Asso di denari"
    assert str(Card(Suit.BASTONI, Rank.KNIGHT)) == "Cavallo di bastoni"


def test_codice_andata_e_ritorno():
    for card in full_deck():
        assert Card.from_code(card.code) == card


@pytest.mark.parametrize(
    "code",
    ["", "denari", "denari-", "denari-0", "denari-11", "oro-1", "Denari-1", "denari-1-2", "denari-uno",
     "denari-01", "denari- 1", " denari-1", "denari-1 ", "denari-+1", None, 7, ["denari-1"]],
)
def test_codice_sconosciuto_rifiutato(code):
    with pytest.raises(InvalidMoveError, match="Carta non valida"):
        Card.from_code(code)


def test_errore_di_mossa_e_errore_del_motore():
    assert issubclass(InvalidMoveError, EngineError)


def test_carta_immutabile():
    card = Card(Suit.SPADE, Rank.KING)
    with pytest.raises(FrozenInstanceError):
        card.rank = Rank.ACE


def test_mescolamento_con_seme_fisso_sempre_uguale():
    assert shuffled_deck(random.Random(42)) == shuffled_deck(random.Random(42))
    assert shuffled_deck(random.Random(42)) != shuffled_deck(random.Random(43))


def test_mescolamento_non_perde_carte():
    cards = shuffled_deck(random.Random(7))
    assert len(cards) == 40
    assert set(cards) == set(full_deck())
    assert cards != full_deck()


def test_mescolamento_di_default_usa_systemrandom(monkeypatch):
    used = []

    class FakeSystemRandom(random.Random):
        def __init__(self):
            used.append(True)
            super().__init__(0)

    monkeypatch.setattr(deck_module.secrets, "SystemRandom", FakeSystemRandom)
    cards = shuffled_deck()
    assert used == [True]
    assert set(cards) == set(full_deck())


def test_parametri_della_variante():
    assert MARIANNA == RuleSet()
    assert MARIANNA.player_counts == (2, 4)
    assert MARIANNA.hand_size == 5
    assert MARIANNA.must_follow_suit is False
    assert MARIANNA.sing_40_points == 40
    assert MARIANNA.sing_20_points == 20
    assert MARIANNA.min_hand_to_sing_after_deck == 3
    assert MARIANNA.last_trick_bonus == 0
    assert MARIANNA.target_scores == (150, 300, 500)


def test_parametri_immutabili():
    with pytest.raises(FrozenInstanceError):
        MARIANNA.hand_size = 6


def test_punteggi_uguali_a_config():
    assert MARIANNA.target_scores == load_config("testing", environ={}).TARGET_SCORES


def test_motore_non_importa_flask_ne_database():
    forbidden = ("flask", "flask_socketio", "flask_login", "flask_sqlalchemy", "sqlalchemy", "pymysql", "config")
    for path in ENGINE_DIR.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            for name in names:
                root = name.split(".")[0]
                assert root not in forbidden, f"{path.name} importa {name}"
                if root == "app":
                    assert name.startswith("app.game.engine"), f"{path.name} importa {name}"
