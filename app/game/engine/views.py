"""Vista di un giocatore (P15): solo quello che quel posto può vedere.

Mai le carte in mano agli altri, l'ordine o il contenuto del mazzo, le carte già
prese nella mano in corso (docs/CONTRATTO-SOCKET.md, 3.3): di quelle si vedono solo i punti (P67).
Unica eccezione (D46, P92): nel 2v2, con la briscola fissata e il mazzo finito, le carte del
compagno (partner_hand), mai quelle degli avversari.

Il motore non sa nulla della stanza: la vista che produce ha i campi di gioco del
contratto, e la stanza (P24, P25) aggiunge i suoi. ROOM_FIELDS li elenca.

Cosa contiene:
    MODES                    il nome della modalità dal numero di giocatori, per esempio MODES[4] = "2v2"
    ROOM_FIELDS, ...         i campi che aggiunge la stanza (li usano i test e room.py)
    card_to_dict(card)       una carta nella forma del contratto, per esempio {"suit": "coppe", "rank": 1}
    player_view(game, seat)  la vista di un posto: un dizionario pronto da mandare al browser

Una "vista" è un dizionario Python (chiave -> valore, come un oggetto JSON): la stanza
lo manda al browser con l'evento game:state, e Flask-SocketIO lo trasforma in JSON.

DA DOVE ARRIVANO I DATI: la stanza (app/realtime/room.py) chiama player_view per ogni
giocatore dopo ogni mossa, con la partita in corso (self.game) e il posto di quel
giocatore; la CPU legge la sua vista come un giocatore vero (cpu.py).
"""

from app.game.engine.cards import Card
from app.game.engine.errors import EngineError
from app.game.engine.game import game_legal_actions, hand_result, partner_cards_visible
from app.game.engine.rules import MARIANNA, RuleSet
from app.game.engine.state import (
    TEAMS,
    GameState,
    HandResult,
    HandState,
    LaidDown,
    LastTrick,
    team_of,
)
from app.game.engine.trick import winning_position

# MODES: il nome della modalità dal numero di giocatori
MODES = {2: "1v1", 4: "2v2"}

# Campi che aggiunge la stanza: in cima alla vista, per ogni giocatore, nel turno.
# "advice" (P92) c'è solo nel 2v2: il consiglio del compagno, che il motore non conosce
ROOM_FIELDS = ("game_id", "version", "rated", "advice")
ROOM_PLAYER_FIELDS = ("user_id", "username", "avatar", "rating", "cpu", "connected", "reconnect_seconds_left")
ROOM_TURN_FIELDS = ("seconds_total", "seconds_left")


def card_to_dict(card: Card) -> dict:
    """Una carta nella forma del contratto.

    In parole semplici:
        card_to_dict(card)
        card: una carta del motore, per esempio Card(Suit.COPPE, Rank.ACE).
        Restituisce {"suit": "coppe", "rank": 1}: il seme come testo e il valore come
        numero, la forma che il browser riconosce (contratto, 3.3).
    """
    return {"suit": card.suit.value, "rank": card.rank.value}


def _cards_to_dicts(cards) -> list[dict]:
    """Un elenco di carte nella forma del contratto.

    In parole semplici:
        _cards_to_dicts(cards)
        Chiama card_to_dict per ogni carta, nello stesso ordine; per esempio
        [{"suit": "coppe", "rank": 1}, {"suit": "spade", "rank": 3}].
    """
    result = []
    for card in cards:
        result.append(card_to_dict(card))
    return result


def player_view(game: GameState, seat: int, rules: RuleSet = MARIANNA) -> dict:
    """La vista di un posto: tutto quello che quel giocatore può vedere della partita.

    In parole semplici:
        player_view(game, seat)
        game:  la partita in corso (GameState). Arriva dalla stanza (self.game).
        seat:  il posto del giocatore, da 0 a num_players - 1.
        rules: facoltativo, se manca vale MARIANNA.

        Restituisce un dizionario con i campi di gioco del contratto (3.3), per esempio
        {"mode": "1v1", "target_score": 300, "status": "playing", "hand": [...], ...}.
        Le carte degli altri non ci sono mai: di loro c'è solo quante ne hanno
        (cards_in_hand), tranne il compagno nel caso di D46 (partner_hand).
    """
    # In Python True e False sono anche numeri (1 e 0): un posto True si rifiuta a parte
    if isinstance(seat, bool) or not isinstance(seat, int) or seat < 0 or seat >= game.num_players:
        raise EngineError("Posto non valido.")
    hand = game.hand
    legal = game_legal_actions(game, seat, rules)

    # I campi che dipendono da un "se", decisi prima di costruire la vista

    # status: "finished" a partita finita, altrimenti "playing"
    if game.finished:
        status = "finished"
    else:
        status = "playing"

    # players: per ogni posto, la squadra e QUANTE carte ha (mai quali)
    players = []
    for other in range(game.num_players):
        players.append({"seat": other, "team": team_of(other), "cards_in_hand": len(hand.hands[other])})

    # last_trick: l'ultima presa chiusa, oppure None se non se n'è chiusa nessuna
    if hand.last_trick is None:
        last_trick = None
    else:
        last_trick = _last_trick(hand.last_trick)

    # trump: il seme di briscola come testo, oppure None (carte franche)
    if hand.trump is None:
        trump = None
    else:
        trump = hand.trump.value

    # turn: chi è di turno, None a partita finita
    if game.finished:
        turn = None
    else:
        turn = {"seat": hand.turn_seat}

    # legal_sing: i semi che si possono cantare, come testi
    legal_sing = []
    for suit in legal.sing:
        legal_sing.append(suit.value)

    # result: il risultato della partita, None mentre si gioca
    if game.result is None:
        result = None
    else:
        result = {
            "reason": "score",
            "winner_team": game.result.winner_team,
            "abandoned_seats": [],
            "scores": _scores(game.scores),
        }

    view = {
        "mode": MODES[game.num_players],
        "target_score": game.target_score,
        "status": status,
        "hand_number": game.hand_number,
        "dealer_seat": game.dealer_seat,
        "you": {"seat": seat},
        "players": players,
        "hand": _cards_to_dicts(hand.hands[seat]),
        "trick": _trick(hand),
        "last_trick": last_trick,
        "trump": trump,
        "deck_count": len(hand.deck),
        "sings": _sings(hand.sings),
        "scores": _scores(game.scores),
        "hand_points": _hand_points(hand, rules),
        "last_hand": _last_hand(game),
        "turn": turn,
        "legal": {
            "play": _cards_to_dicts(legal.play),
            "sing": legal_sing,
            "lay_down": legal.lay_down,
        },
        "result": result,
    }
    if game.num_players == 4:
        # D46: le carte del compagno, e solo le sue, quando ci sono briscola e mazzo finito; nel 1v1 il campo non c'è.
        # Il compagno è due posti più avanti: (seat + 2) % 4, per esempio 3 per il posto 1
        partner = hand.hands[(seat + 2) % 4]
        if partner_cards_visible(hand):
            view["partner_hand"] = _cards_to_dicts(partner)
        else:
            view["partner_hand"] = None
    return view


def _plays(plays) -> list[dict]:
    """Le carte giocate in una presa, nella forma del contratto.

    In parole semplici:
        _plays(plays)
        plays: le giocate (TrickPlay di state.py), nell'ordine di gioco.
        Restituisce per esempio [{"seat": 0, "card": {"suit": "coppe", "rank": 1}}, ...].
    """
    result = []
    for play in plays:
        result.append({"seat": play.seat, "card": card_to_dict(play.card)})
    return result


def _sings(sings) -> list[dict]:
    """I canti della mano, nella forma del contratto.

    In parole semplici:
        _sings(sings)
        sings: i canti (Sing di singing.py), in ordine.
        Restituisce per esempio [{"seat": 1, "suit": "spade", "points": 40}].
    """
    result = []
    for done in sings:
        result.append({"seat": done.seat, "suit": done.suit.value, "points": done.points})
    return result


def _trick(hand: HandState) -> dict:
    """La presa in corso: chi l'ha aperta, le carte e chi la sta vincendo.

    In parole semplici:
        _trick(hand)
        hand: lo stato della mano.
        Restituisce per esempio {"leader_seat": 0, "cards": [...], "winning_seat": 1}.
    """
    # Chi sta vincendo la presa in corso (P75), con la stessa regola di chi la prende; null senza carte
    winning = None
    if len(hand.trick) > 0:
        trick_cards = []
        for play in hand.trick:
            trick_cards.append(play.card)
        # winning_position dà la posizione nella presa: con hand.trick[...] si passa al posto
        winning = hand.trick[winning_position(trick_cards, hand.trump)].seat
    return {"leader_seat": hand.leader_seat, "cards": _plays(hand.trick), "winning_seat": winning}


def _last_trick(last: LastTrick) -> dict:
    """L'ultima presa chiusa, nella forma del contratto.

    In parole semplici:
        _last_trick(last)
        Restituisce per esempio {"winner_seat": 1, "cards": [...]}.
    """
    return {"winner_seat": last.winner_seat, "cards": _plays(last.plays)}


def _scores(scores: tuple[int, ...]) -> list[dict]:
    """I punteggi delle squadre, nella forma del contratto.

    In parole semplici:
        _scores(scores)
        scores: una tupla con un numero per squadra, per esempio (120, 85).
        Restituisce [{"team": 0, "total": 120}, {"team": 1, "total": 85}].
    """
    result = []
    for team in range(TEAMS):
        result.append({"team": team, "total": scores[team]})
    return result


def _hand_points(hand: HandState, rules: RuleSet) -> list[dict]:
    """Punti della mano in corso di tutte e due le squadre (P67, D44): carte prese più canti.

    Le carte prese restano nascoste, si vede solo quanto valgono. A mano finita (fine
    partita) sono i punti del riepilogo, bonus dell'ultima presa compreso.

    In parole semplici:
        _hand_points(hand, rules)
        Lo stesso conto di hand_result di game.py, ma anche a mano non finita, e
        senza il bonus dell'ultima presa finché la mano non è finita (oggi è 0): se
        cambiano le regole dei punti vanno cambiati tutti e due (P72).
        Restituisce per esempio [{"team": 0, "total": 35}, {"team": 1, "total": 40}].
    """
    if hand.finished:
        return _scores(hand_result(hand, rules).totals)
    # points: per ogni squadra, i punti delle carte prese
    points = []
    for taken in hand.captured:
        total = 0
        for card in taken:
            total = total + card.points
        points.append(total)
    # più i canti, ognuno alla squadra di chi l'ha fatto
    for done in hand.sings:
        points[team_of(done.seat)] += done.points
    return _scores(tuple(points))


def _last_hand(game: GameState) -> dict | None:
    """Il riepilogo dell'ultima mano finita, oppure None nella prima mano.

    In parole semplici:
        _last_hand(game)
        Restituisce per esempio {"hand_number": 2, "teams": [...], "last_trick": {...},
        "laid_down": None}. La pagina lo mostra a fine mano (P57, P58).
    """
    # done: il risultato dell'ultima mano finita (HandResult di state.py), oppure None
    done: HandResult | None = game.last_hand
    if done is None:
        return None

    # A partita finita la mano in corso è proprio l'ultima finita; durante la partita è quella prima
    if game.finished:
        number = game.hand_number
    else:
        number = game.hand_number - 1

    # teams: i punti di ogni squadra in quella mano
    teams = []
    for team in range(TEAMS):
        teams.append({
            "team": team,
            "card_points": done.card_points[team],
            "sing_points": done.sing_points[team],
            "hand_total": done.totals[team],
        })

    # laid_down: le carte calate (P84), None se la mano è finita normalmente
    if done.laid_down is None:
        laid_down = None
    else:
        laid_down = _laid_down(done.laid_down)

    return {
        "hand_number": number,
        "teams": teams,
        # Carte già giocate e viste da tutti: la pagina le mostra prima del riepilogo (P58)
        "last_trick": _last_trick(done.last_trick),
        "laid_down": laid_down,
    }


def _laid_down(laid: LaidDown) -> dict:
    """Carte calate (P84): dopo la calata sono scoperte per tutti, comprese quelle degli avversari.

    In parole semplici:
        _laid_down(laid)
        Restituisce per esempio {"seat": 2, "hands": [{"seat": 0, "cards": [...]}, ...],
        "sings": [...]}.
    """
    hands = []
    for seat in range(len(laid.hands)):
        hands.append({"seat": seat, "cards": _cards_to_dicts(laid.hands[seat])})
    return {
        "seat": laid.seat,
        "hands": hands,
        "sings": _sings(laid.sings),
    }
