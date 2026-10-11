""""Cala le carte" (P84, D45; regola in docs/REGOLE-GIOCO.md, "Calare le carte").

A mazzo finito, all'inizio di una presa, chi deve aprire può calare se la sua squadra
ha un modo di giocare che vince **tutte** le prese rimaste, qualunque cosa facciano gli
avversari ("giocando bene"). Il server conosce le carte di tutti, quindi il calcolo è
esatto: si provano le mosse una presa alla volta, e una situazione già vista non si
ricalcola.

Condizioni (D45): briscola fissata, oppure senza briscola al massimo 2 carte a testa;
chi apre ha già cantato tutti i semi che poteva; nessun avversario può ancora cantare.
Calando, il compagno (2v2) canta da sé ogni seme che potrebbe cantare adesso.
"""

from functools import lru_cache

from app.game.engine.cards import Card, Suit
from app.game.engine.rules import MARIANNA, RuleSet
from app.game.engine.singing import Sing, sing, singable_suits
from app.game.engine.state import HandState, team_of

Hands = tuple[frozenset[Card], ...]


# Lo stesso stato si controlla più volte (vista, mossa, viste di nuovo): il calcolo nel 2v2
# può arrivare a circa 0,1 s, quindi si ricordano le ultime risposte
@lru_cache(maxsize=256)
def can_lay_down(state: HandState, seat: int, rules: RuleSet = MARIANNA) -> bool:
    if state.finished or seat != state.turn_seat or state.trick or state.deck:
        return False
    if state.trump is None and any(len(hand) > rules.lay_down_max_cards_without_trump for hand in state.hands):
        return False
    team = team_of(seat)
    # Chi apre canta prima tutti i suoi semi; un avversario che può ancora cantare lo impedisce
    if _singable(state, seat, rules):
        return False
    if any(_singable(state, other, rules) for other in range(state.num_players) if team_of(other) != team):
        return False
    hands = tuple(frozenset(hand) for hand in state.hands)
    return team_wins_all(hands, seat, team, state.trump)


def partner_sings(state: HandState, seat: int, rules: RuleSet = MARIANNA) -> tuple[Sing, ...]:
    """I canti che il compagno di chi cala avrebbe fatto al suo turno (D45): uno per seme possibile."""
    sings = list(state.sings)
    added = []
    for partner in range(state.num_players):
        if partner == seat or team_of(partner) != team_of(seat):
            continue
        for suit in _singable(state, partner, rules):
            done = sing(suit, seat=partner, hand=state.hands[partner], sings=sings,
                        played_cards=state.played_cards, deck_count=len(state.deck), is_turn=True,
                        first_trick=state.last_trick is None, rules=rules)
            sings.append(done)
            added.append(done)
    return tuple(added)


def team_wins_all(hands: Hands, leader: int, team: int, trump: Suit | None) -> bool:
    """La squadra vince tutte le prese rimaste, giocando bene, se la prima la apre `leader`?

    Nelle scelte della squadra basta una carta che funzioni; in quelle degli avversari
    devono funzionare tutte. Per andare veloce (nel 2v2 sono milioni di strade) ogni mano
    è un numero con un bit per carta, e la forza nella presa è un numero calcolato una
    volta: la regola è quella di trick.py (briscola, poi seme di uscita, poi forza), e un
    test confronta il risultato con partite giocate davvero con il motore.
    """
    players = len(hands)
    cards = sorted({card for hand in hands for card in hand}, key=lambda card: card.code)
    suits = [list(Suit).index(card.suit) for card in cards]
    # Le carte più forti hanno i bit più bassi: provarle per prime chiude prima le strade
    order = sorted(range(len(cards)), key=lambda i: (cards[i].suit == trump, cards[i].strength), reverse=True)
    cards = [cards[i] for i in order]
    suits = [suits[i] for i in order]
    is_trump = [card.suit == trump for card in cards]
    strength = [card.strength for card in cards]
    bit = {card: 1 << index for index, card in enumerate(cards)}
    masks = tuple(sum(bit[card] for card in hand) for hand in hands)
    on_team = [team_of(seat) == team for seat in range(players)]
    known: dict[tuple[tuple[int, ...], int], bool] = {}

    def power(index: int, lead: int) -> int:
        # Come (seme == briscola, seme == uscita, forza) di trick.py, in un solo numero
        return is_trump[index] * 32 + (suits[index] == lead) * 16 + strength[index]

    def from_lead(masks: tuple[int, ...], leader: int) -> bool:
        if not masks[leader]:
            return True
        key = (masks, leader)
        if key not in known:
            known[key] = in_trick(masks, leader, 0, -1, -1, -1)
        return known[key]

    def in_trick(masks, leader, step, lead, best, best_seat) -> bool:
        if step == players:
            return on_team[best_seat] and from_lead(masks, best_seat)
        seat = (leader + step) % players
        mine, wanted = masks[seat], on_team[seat]
        if step:
            # La carta più forte che la squadra può ancora mettere in questa presa, dopo di lui
            later = max((strongest(masks[(leader + after) % players], lead)
                         for after in range(step + 1, players) if on_team[(leader + after) % players]),
                        default=-1)
            if not on_team[best_seat] and max(later, strongest(mine, lead) if wanted else -1) <= best:
                return False  # vince un avversario e nessuno della squadra lo batte più
            if not wanted and strongest(mine, lead) > max(best, later):
                return False  # l'avversario prende la presa e nessuno gliela toglie
        while mine:
            low = mine & -mine
            mine ^= low
            index = low.bit_length() - 1
            card_lead = suits[index] if step == 0 else lead
            mine_power = power(index, card_lead)
            if step == 0 or mine_power > best:
                new_best, new_seat = mine_power, seat
            else:
                new_best, new_seat = best, best_seat
            rest = tuple(mask ^ low if other == seat else mask for other, mask in enumerate(masks))
            if in_trick(rest, leader, step + 1, card_lead, new_best, new_seat) == wanted:
                return wanted  # la squadra ha trovato la carta giusta, o l'avversario quella che rompe
        return not wanted

    def strongest(mask: int, lead: int) -> int:
        top = -1
        while mask:
            low = mask & -mask
            mask ^= low
            top = max(top, power(low.bit_length() - 1, lead))
        return top

    return from_lead(masks, leader)


def _singable(state: HandState, seat: int, rules: RuleSet) -> list[Suit]:
    return singable_suits(hand=state.hands[seat], sings=state.sings, played_cards=state.played_cards,
                          deck_count=len(state.deck), is_turn=True, first_trick=state.last_trick is None,
                          rules=rules)
