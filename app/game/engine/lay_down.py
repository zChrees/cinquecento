""""Cala le carte" (P84, D45; regola in docs/REGOLE-GIOCO.md, "Calare le carte").

A mazzo finito, all'inizio di una presa, chi deve aprire può calare se la sua squadra
ha un modo di giocare che vince **tutte** le prese rimaste, qualunque cosa facciano gli
avversari ("giocando bene"). Il server conosce le carte di tutti, quindi il calcolo è
esatto: si provano le mosse una presa alla volta, e una situazione già vista non si
ricalcola.

Condizioni (D45): briscola fissata, oppure senza briscola al massimo 2 carte a testa;
chi apre ha già cantato tutti i semi che poteva; nessun avversario può ancora cantare.
Calando, il compagno (2v2) canta da sé ogni seme che potrebbe cantare adesso.

Cosa contiene:
    Hands                                     il tipo delle mani usato nel calcolo
    can_lay_down(state, seat)                 si può calare adesso? per esempio True
    partner_sings(state, seat)                i canti che il server fa per il compagno
    team_wins_all(hands, leader, team, trump) la squadra vince tutte le prese rimaste?

DA DOVE ARRIVANO I DATI: game.py chiama can_lay_down per le mosse legali (legal.lay_down)
e, quando arriva un'azione di calata, sia can_lay_down sia partner_sings; la CPU
(cpu.py) legge legal.lay_down dalla sua vista. team_wins_all la chiama can_lay_down
(e la provano i test).
"""

# lru_cache: un decoratore che fa "ricordare" a una funzione le ultime risposte (lru
# = "least recently used": quando sono troppe, dimentica quella usata meno di recente).
# Se la funzione si chiama di nuovo con gli stessi parametri, restituisce la risposta
# ricordata senza rifare il calcolo. Funziona solo con parametri che non si possono
# cambiare (lo stato è immutabile, P13).
from functools import lru_cache

from app.game.engine.cards import Card, Suit
from app.game.engine.rules import MARIANNA, RuleSet
from app.game.engine.singing import Sing, sing, singable_suits
from app.game.engine.state import HandState, team_of

# Hands: le carte di ogni posto, ognuna come frozenset (un insieme che non si cambia).
# È un "alias di tipo": un nome corto, usato solo per scrivere i tipi dei parametri
Hands = tuple[frozenset[Card], ...]


# Lo stesso stato si controlla più volte (vista, mossa, viste di nuovo): il calcolo nel 2v2
# può arrivare a circa 0,1 s, quindi si ricordano le ultime risposte (256)
@lru_cache(maxsize=256)
def can_lay_down(state: HandState, seat: int, rules: RuleSet = MARIANNA) -> bool:
    """Il posto `seat` può calare le carte adesso?

    In parole semplici:
        can_lay_down(state, seat)
        state: lo stato della mano. Arriva da game.py (legal_actions e la calata).
        seat:  il posto che vuole calare.
        rules: facoltativo, se manca vale MARIANNA.

        Controlla le condizioni di D45 dalla più veloce alla più lenta e si ferma
        alla prima che non va; per ultima, la ricerca di team_wins_all.
        Restituisce True o False.
    """
    # 1. solo chi è di turno, a inizio presa (nessuna carta sul tavolo), a mazzo finito
    if state.finished or seat != state.turn_seat or len(state.trick) > 0 or len(state.deck) > 0:
        return False

    # 2. senza briscola si cala solo con al massimo 2 carte a testa
    if state.trump is None:
        for hand in state.hands:
            if len(hand) > rules.lay_down_max_cards_without_trump:
                return False

    team = team_of(seat)
    # 3. chi apre canta prima tutti i suoi semi; un avversario che può ancora cantare lo impedisce
    if len(_singable(state, seat, rules)) > 0:
        return False
    for other in range(state.num_players):
        if team_of(other) != team and len(_singable(state, other, rules)) > 0:
            return False

    # 4. la ricerca vera: le mani come insiemi, e team_wins_all prova tutte le strade
    hands = []
    for hand in state.hands:
        hands.append(frozenset(hand))
    return team_wins_all(tuple(hands), seat, team, state.trump)


def partner_sings(state: HandState, seat: int, rules: RuleSet = MARIANNA) -> tuple[Sing, ...]:
    """I canti che il compagno di chi cala avrebbe fatto al suo turno (D45): uno per seme possibile.

    In parole semplici:
        partner_sings(state, seat)
        state: lo stato della mano prima della calata. Arriva da _apply_lay_down di game.py.
        seat:  il posto di chi cala.
        rules: facoltativo, se manca vale MARIANNA.

        Per il compagno (nel 1v1 non c'è, e il ciclo non trova nessuno) prova ogni
        seme che potrebbe cantare e lo canta con sing di singing.py: il primo canto
        della mano vale 40, gli altri 20, come se lo avesse fatto lui.
        Restituisce: la tupla dei canti aggiunti, per esempio (Sing(2, Suit.SPADE, 20),),
        oppure () se non ce ne sono.
    """
    # sings: i canti della mano fin qui, più quelli aggiunti man mano (contano per i punti: 40 o 20)
    sings = list(state.sings)
    added = []
    for partner in range(state.num_players):
        # si salta chi cala e chi è dell'altra squadra: resta solo il compagno
        if partner == seat or team_of(partner) != team_of(seat):
            continue
        for suit in _singable(state, partner, rules):
            done = sing(suit, seat=partner, hand=state.hands[partner], sings=sings,
                        played_cards=state.played_cards, deck_count=len(state.deck), is_turn=True,
                        first_trick=state.last_trick is None, rules=rules)
            sings.append(done)
            added.append(done)
    return tuple(added)


def _card_code(card: Card) -> str:
    """Il codice di una carta, per ordinare le carte sempre allo stesso modo.

    In parole semplici:
        _card_code(card)
        Per esempio "coppe-10". La usa sorted in team_wins_all come "chiave" (key):
        sorted ordina le carte confrontando i loro codici.
    """
    return card.code


def team_wins_all(hands: Hands, leader: int, team: int, trump: Suit | None) -> bool:
    """La squadra vince tutte le prese rimaste, giocando bene, se la prima la apre `leader`?

    Nelle scelte della squadra basta una carta che funzioni; in quelle degli avversari
    devono funzionare tutte. Per andare veloce (nel 2v2 sono milioni di strade) ogni mano
    è un numero con un bit per carta, e la forza nella presa è un numero calcolato una
    volta: la regola è quella di trick.py (briscola, poi seme di uscita, poi forza), e un
    test confronta il risultato con partite giocate davvero con il motore.

    In parole semplici:
        team_wins_all(hands, leader, team, trump)
        hands:  le carte rimaste a ogni posto, come frozenset. Arriva da can_lay_down.
        leader: il posto che apre la prima presa (chi vuole calare).
        team:   la squadra di chi vuole calare, 0 o 1.
        trump:  il seme di briscola, oppure None.

        Come funziona: è una ricerca "in profondità" (come un albero di tutte le
        partite possibili), con le funzioni interne qui sotto che si chiamano a
        vicenda. Ogni carta ha un numero da 0 a n-1, e la mano di un posto è un
        numero intero in cui il bit i vale 1 se il posto ha la carta i (una
        "maschera di bit", come in C: 0b101 = le carte 0 e 2).

        Restituisce: True se la squadra vince tutte le prese qualunque cosa facciano
        gli avversari, altrimenti False.
    """
    players = len(hands)

    # cards: tutte le carte ancora in mano, senza ripetizioni (un insieme), poi
    # ordinate per codice, così l'ordine è sempre lo stesso
    all_cards = set()
    for hand in hands:
        for card in hand:
            all_cards.add(card)
    cards = sorted(all_cards, key=_card_code)

    # suits: per ogni carta, il numero del suo seme (0 = denari, 1 = coppe, ...)
    suit_list = list(Suit)
    suits = []
    for card in cards:
        suits.append(suit_list.index(card.suit))

    def strong_first(i: int) -> tuple[bool, int]:
        """La chiave per ordinare le carte: prima le briscole, poi la forza.

        In parole semplici:
            strong_first(i)
            i: la posizione di una carta in cards. Per esempio (True, 10) per l'Asso
            di briscola. Con reverse=True, sorted mette prima le più forti.
        """
        return (cards[i].suit == trump, cards[i].strength)

    # Le carte più forti hanno i bit più bassi: provarle per prime chiude prima le strade.
    # order: le posizioni delle carte, dalla più forte alla più debole. sorted tiene
    # nello stesso ordine di prima le carte con la stessa chiave, anche con reverse=True
    order = sorted(range(len(cards)), key=strong_first, reverse=True)
    sorted_cards = []
    sorted_suits = []
    for i in order:
        sorted_cards.append(cards[i])
        sorted_suits.append(suits[i])
    cards = sorted_cards
    suits = sorted_suits

    # is_trump e strength: per ogni carta (nella posizione nuova), se è di briscola e
    # la sua forza; liste semplici, più veloci da leggere che chiedere alla carta
    is_trump = []
    strength = []
    for card in cards:
        is_trump.append(card.suit == trump)
        strength.append(card.strength)

    # bit: per ogni carta, il suo bit; 1 << index è 2 elevato a index (1, 2, 4, 8, ...)
    bit = {}
    for index in range(len(cards)):
        bit[cards[index]] = 1 << index

    # masks: la mano di ogni posto come numero, la somma dei bit delle sue carte
    masks_list = []
    for hand in hands:
        mask = 0
        for card in hand:
            mask = mask + bit[card]
        masks_list.append(mask)
    masks = tuple(masks_list)

    # on_team: per ogni posto, True se è della squadra che vuole calare
    on_team = []
    for seat in range(players):
        on_team.append(team_of(seat) == team)

    # known: le situazioni già calcolate, (maschere, chi apre) -> risposta. Nel 2v2 la
    # stessa situazione si raggiunge da tante strade: così si calcola una volta sola
    known: dict[tuple[tuple[int, ...], int], bool] = {}

    def power(index: int, lead: int) -> int:
        """La forza della carta `index` in una presa aperta con il seme `lead`.

        In parole semplici:
            power(index, lead)
            Come (seme == briscola, seme == uscita, forza) di trick.py, in un solo
            numero: una briscola vale 32 in più, una carta del seme di uscita 16 in più,
            poi la forza (da 1 a 10). True e False contano come 1 e 0. Per esempio
            l'Asso di briscola vale 32 + 0 + 10 = 42 se si è aperto con un altro seme.
        """
        return is_trump[index] * 32 + (suits[index] == lead) * 16 + strength[index]

    def from_lead(masks: tuple[int, ...], leader: int) -> bool:
        """La squadra vince tutto da qui, se la presa la apre `leader`?

        In parole semplici:
            from_lead(masks, leader)
            masks:  le mani di tutti come numeri.
            leader: chi apre la presa.
            Se chi apre non ha più carte, la mano è finita e la squadra ha vinto tutto
            (True). Altrimenti guarda in known e, se non c'è, lo calcola con in_trick.
        """
        if masks[leader] == 0:
            return True
        key = (masks, leader)
        if key not in known:
            known[key] = in_trick(masks, leader, 0, -1, -1, -1)
        return known[key]

    def in_trick(masks, leader, step, lead, best, best_seat) -> bool:
        """Dentro una presa: prova le carte di chi deve giocare adesso.

        In parole semplici:
            in_trick(masks, leader, step, lead, best, best_seat)
            masks:     le mani di tutti come numeri.
            leader:    chi ha aperto la presa.
            step:      quante carte sono già state giocate nella presa (0 = si apre).
            lead:      il seme di uscita (-1 finché nessuno ha giocato).
            best:      la forza (power) della carta che vince per ora (-1 all'inizio).
            best_seat: il posto di chi vince per ora (-1 all'inizio).

            Se la squadra deve scegliere ("wanted" True), basta UNA carta che porti
            a vincere tutto; se sceglie un avversario, TUTTE le sue carte devono
            portare a vincere tutto. Restituisce True o False.
        """
        # Presa completa: la squadra deve averla vinta, e poi vincere tutto il resto
        if step == players:
            return on_team[best_seat] and from_lead(masks, best_seat)

        # seat: chi gioca adesso; mine: le sue carte; wanted: True se è della squadra
        seat = (leader + step) % players
        mine = masks[seat]
        wanted = on_team[seat]

        # Due "tagli" per non provare strade già perse (solo dopo la prima carta)
        if step > 0:
            # later: la carta più forte che la squadra può ancora mettere in questa
            # presa, dopo di lui; -1 se dopo di lui non gioca nessuno della squadra
            later = -1
            for after in range(step + 1, players):
                other = (leader + after) % players
                if on_team[other]:
                    later = max(later, strongest(masks[other], lead))
            # mine_top: la sua carta più forte, se è della squadra; -1 se è un avversario
            mine_top = -1
            if wanted:
                mine_top = strongest(mine, lead)
            if not on_team[best_seat] and max(later, mine_top) <= best:
                return False  # vince un avversario e nessuno della squadra lo batte più
            if not wanted and strongest(mine, lead) > max(best, later):
                return False  # l'avversario prende la presa e nessuno gliela toglie

        # Si provano le sue carte una alla volta, dal bit più basso (la carta più forte)
        while mine != 0:
            # low: solo il bit più basso acceso di mine (un trucco dei bit, come in C:
            # x & -x); poi lo si spegne in mine con ^ (xor)
            low = mine & -mine
            mine = mine ^ low
            # index: il numero della carta, cioè la posizione di quel bit
            index = low.bit_length() - 1

            # card_lead: chi apre decide il seme di uscita con la sua carta
            if step == 0:
                card_lead = suits[index]
            else:
                card_lead = lead
            mine_power = power(index, card_lead)

            # new_best e new_seat: chi vince la presa dopo questa carta
            if step == 0 or mine_power > best:
                new_best = mine_power
                new_seat = seat
            else:
                new_best = best
                new_seat = best_seat

            # rest: le mani dopo aver giocato quella carta (tolta dalla sua mano)
            rest_list = []
            for other in range(players):
                if other == seat:
                    rest_list.append(masks[other] ^ low)
                else:
                    rest_list.append(masks[other])
            rest = tuple(rest_list)

            if in_trick(rest, leader, step + 1, card_lead, new_best, new_seat) == wanted:
                return wanted  # la squadra ha trovato la carta giusta, o l'avversario quella che rompe
        return not wanted

    def strongest(mask: int, lead: int) -> int:
        """La forza della carta più forte in una mano, con quel seme di uscita.

        In parole semplici:
            strongest(mask, lead)
            mask: le carte di un posto come numero. lead: il seme di uscita.
            Restituisce la forza più alta (power), oppure -1 se la mano è vuota.
        """
        top = -1
        while mask != 0:
            low = mask & -mask
            mask = mask ^ low
            top = max(top, power(low.bit_length() - 1, lead))
        return top

    return from_lead(masks, leader)


def _singable(state: HandState, seat: int, rules: RuleSet) -> list[Suit]:
    """I semi che quel posto potrebbe cantare adesso, se fosse di turno.

    In parole semplici:
        _singable(state, seat, rules)
        Chiama singable_suits di singing.py con i dati dello stato e is_turn True.
        La usano can_lay_down (chi apre e gli avversari) e partner_sings (il compagno).
    """
    return singable_suits(hand=state.hands[seat], sings=state.sings, played_cards=state.played_cards,
                          deck_count=len(state.deck), is_turn=True, first_trick=state.last_trick is None,
                          rules=rules)
