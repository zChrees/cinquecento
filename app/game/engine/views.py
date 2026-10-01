"""Vista di un giocatore (P15): solo quello che quel posto può vedere.

Mai le carte in mano agli altri, l'ordine o il contenuto del mazzo, le carte già
prese nella mano in corso (docs/CONTRATTO-SOCKET.md, 3.3): di quelle si vedono solo i punti (P67).

Il motore non sa nulla della stanza: la vista che produce ha i campi di gioco del
contratto, e la stanza (P24, P25) aggiunge i suoi. ROOM_FIELDS li elenca.
"""

from app.game.engine.cards import Card
from app.game.engine.errors import EngineError
from app.game.engine.game import game_legal_actions, hand_result
from app.game.engine.rules import MARIANNA, RuleSet
from app.game.engine.state import (
    TEAMS,
    GameState,
    HandResult,
    HandState,
    LastTrick,
    team_of,
)
from app.game.engine.trick import winning_position

MODES = {2: "1v1", 4: "2v2"}

# Campi che aggiunge la stanza: in cima alla vista, per ogni giocatore, nel turno
ROOM_FIELDS = ("game_id", "version", "rated")
ROOM_PLAYER_FIELDS = ("user_id", "username", "avatar", "rating", "connected", "reconnect_seconds_left")
ROOM_TURN_FIELDS = ("seconds_total", "seconds_left")


def card_to_dict(card: Card) -> dict:
    return {"suit": card.suit.value, "rank": card.rank.value}


def player_view(game: GameState, seat: int, rules: RuleSet = MARIANNA) -> dict:
    if isinstance(seat, bool) or not isinstance(seat, int) or not 0 <= seat < game.num_players:
        raise EngineError("Posto non valido.")
    hand = game.hand
    legal = game_legal_actions(game, seat, rules)
    return {
        "mode": MODES[game.num_players],
        "target_score": game.target_score,
        "status": "finished" if game.finished else "playing",
        "hand_number": game.hand_number,
        "dealer_seat": game.dealer_seat,
        "you": {"seat": seat},
        "players": [
            {"seat": other, "team": team_of(other), "cards_in_hand": len(hand.hands[other])}
            for other in range(game.num_players)
        ],
        "hand": [card_to_dict(card) for card in hand.hands[seat]],
        "trick": _trick(hand),
        "last_trick": None if hand.last_trick is None else _last_trick(hand.last_trick),
        "trump": None if hand.trump is None else hand.trump.value,
        "deck_count": len(hand.deck),
        "sings": [{"seat": done.seat, "suit": done.suit.value, "points": done.points} for done in hand.sings],
        "scores": _scores(game.scores),
        "hand_points": _hand_points(hand, rules),
        "last_hand": _last_hand(game),
        "turn": None if game.finished else {"seat": hand.turn_seat},
        "legal": {
            "play": [card_to_dict(card) for card in legal.play],
            "sing": [suit.value for suit in legal.sing],
        },
        "result": (
            None
            if game.result is None
            else {
                "reason": "score",
                "winner_team": game.result.winner_team,
                "abandoned_seats": [],
                "scores": _scores(game.scores),
            }
        ),
    }


def _plays(plays) -> list[dict]:
    return [{"seat": play.seat, "card": card_to_dict(play.card)} for play in plays]


def _trick(hand: HandState) -> dict:
    # Chi sta vincendo la presa in corso (P75), con la stessa regola di chi la prende; null senza carte
    winning = None
    if hand.trick:
        winning = hand.trick[winning_position([play.card for play in hand.trick], hand.trump)].seat
    return {"leader_seat": hand.leader_seat, "cards": _plays(hand.trick), "winning_seat": winning}


def _last_trick(last: LastTrick) -> dict:
    return {"winner_seat": last.winner_seat, "cards": _plays(last.plays)}


def _scores(scores: tuple[int, ...]) -> list[dict]:
    return [{"team": team, "total": scores[team]} for team in range(TEAMS)]


def _hand_points(hand: HandState, rules: RuleSet) -> list[dict]:
    """Punti della mano in corso di tutte e due le squadre (P67, D44): carte prese più canti.

    Le carte prese restano nascoste, si vede solo quanto valgono. A mano finita (fine
    partita) sono i punti del riepilogo, bonus dell'ultima presa compreso.
    """
    if hand.finished:
        return _scores(hand_result(hand, rules).totals)
    points = [sum(card.points for card in taken) for taken in hand.captured]
    for done in hand.sings:
        points[team_of(done.seat)] += done.points
    return _scores(tuple(points))


def _last_hand(game: GameState) -> dict | None:
    done: HandResult | None = game.last_hand
    if done is None:
        return None
    # A partita finita la mano in corso è proprio l'ultima finita; durante la partita è quella prima
    number = game.hand_number if game.finished else game.hand_number - 1
    return {
        "hand_number": number,
        "teams": [
            {
                "team": team,
                "card_points": done.card_points[team],
                "sing_points": done.sing_points[team],
                "hand_total": done.totals[team],
            }
            for team in range(TEAMS)
        ],
        # Carte già giocate e viste da tutti: la pagina le mostra prima del riepilogo (P58)
        "last_trick": _last_trick(done.last_trick),
    }
