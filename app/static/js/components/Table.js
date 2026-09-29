/**
 * Il tavolo di gioco (P21), costruito tutto dalla vista (contratto 3.3).
 *
 * Tu sei sempre in basso; gli altri si dispongono nell'ordine dei posti, verso
 * destra (D11): nel 1v1 l'avversario in alto; nel 2v2 a destra chi gioca dopo di
 * te, in alto il compagno, a sinistra chi gioca prima di te. Le loro carte coperte
 * (P70) sono ventagli agganciati al bordo dello schermo dal loro lato, per metà
 * fuori; quello in alto sta dietro la barra con "Esci" e il punteggio.
 *
 *   [Esci]        Punteggio
 *              (giocatore in alto)
 *   (sinistra)  presa · mazzo  (destra)
 *   [briscola]     (tu)      [Frasi]
 *   pulsanti Canta · la tua mano
 *
 * La pagina non calcola regole: le carte giocabili sono legal.play e i canti
 * legal.sing (entrambi vuoti quando non è il tuo turno).
 *
 * I momenti del tavolo (P57) arrivano in `moments`, già decisi da pages/game.js,
 * che sa quando cominciano e quando finiscono: la presa appena chiusa, il
 * riepilogo di fine mano e le carte del canto (D15). Qui si disegnano soltanto.
 * Allo stesso modo le frasi del tavolo (P56) arrivano in `phrases`: pulsante sopra
 * la mano a destra (P71), elenco che si apre verso l'alto e fumetti accanto a chi
 * ha parlato. Sopra la mano a sinistra il seme della briscola (P71), che resta anche
 * a mazzo finito, quando sparisce il seme sopra il mazzo.
 * Stile in css/components/table.css, trick.css, hand-summary.css e css/pages/game.css.
 */

import { el, icon } from '../utils/dom.js';
import { Card } from './Card.js';
import { EdgeHand, Hand } from './Hand.js';
import { HandSummary } from './HandSummary.js';
import { Scoreboard } from './Scoreboard.js';
import { SingButtons } from './SingButtons.js';
import { PhraseBubble, PhrasesButton, PhrasesMenu } from './TablePhrases.js';
import { Timer } from './Timer.js';
import { DeckAndTrump, LastTrick, Trick } from './Trick.js';

const IMG_BASE = new URL('../../img/cards-bg/', import.meta.url).href;
const POSITIONS = {
  2: ['bottom', 'top'],
  4: ['bottom', 'right', 'top', 'left'],
};

function positionFn(view) {
  const n = view.players.length;
  const names = POSITIONS[n];
  return (seat) => names[(seat - view.you.seat + n) % n];
}

/** I canti di un giocatore, come icone fisse accanto al nome (D15). */
function SingBadges(view, seat) {
  const sings = view.sings.filter((sing) => sing.seat === seat);
  if (!sings.length) return null;
  return el('div', { class: 'seat__sings' }, sings.map((sing) =>
    el('span', {
      class: `sing-badge sing-badge--${sing.suit}`,
      data: { singSeat: seat, suit: sing.suit },
      attrs: { title: `Ha cantato ${sing.points} a ${sing.suit}`, 'aria-label': `Ha cantato ${sing.points} a ${sing.suit}` },
    }, [
      el('img', { attrs: { src: `${IMG_BASE}asso-${sing.suit}-figura.webp`, alt: '' } }),
      el('span', { text: sing.points, attrs: { 'aria-hidden': 'true' } }),
    ]),
  ));
}

/**
 * Re e Cavallo appena cantati (game:sang, D15), accanto a chi ha cantato, verso il
 * centro del tavolo; spariscono dopo show_seconds (lo decide pages/game.js).
 */
function SangCards(sang, position) {
  return el('div', {
    class: `sang sang--${position}`,
    data: { sangSeat: sang.seat, suit: sang.suit, points: sang.points },
    attrs: { 'aria-hidden': 'true' }, // lo annuncia già la riga di stato
  }, [
    el('div', { class: 'sang__cards' }, sang.cards.map((card) => Card(card))),
    el('span', { class: 'sang__points', text: `Canta ${sang.points}` }),
  ]);
}

/** Un giocatore al tavolo: avatar (con l'anello del tempo se tocca a lui), nome, stato. */
function Seat(view, player, position, sang = null, phrase = null) {
  const isTurn = view.turn !== null && view.turn.seat === player.seat;
  const isMe = player.seat === view.you.seat;
  const partner = view.mode === '2v2' && !isMe && player.team === view.players[view.you.seat].team;

  const notes = [];
  if (partner) notes.push('compagno');
  if (!player.connected) {
    const left = player.reconnect_seconds_left;
    notes.push(left === null ? 'scollegato' : `scollegato · ${Math.ceil(left)} s`);
  }

  const avatar = el('span', { class: 'seat__avatar' }, [
    el('span', { class: 'avatar', text: player.username.slice(0, 1).toUpperCase(), attrs: { 'aria-hidden': 'true' } }),
    isTurn ? Timer(view.turn) : null,
    phrase ? PhraseBubble(player.username, phrase, position) : null,
  ]);
  const label = el('div', { class: 'seat__label' }, [
    el('span', { class: 'seat__name', text: isMe ? `${player.username} (tu)` : player.username }),
    notes.length ? el('span', { class: 'seat__note', text: notes.join(' · ') }) : null,
  ]);

  return el('section', {
    class: `seat seat--${position}${isTurn ? ' seat--turn' : ''}${player.connected ? '' : ' seat--offline'}`,
    data: { seat: player.seat, position, team: player.team, turn: isTurn ? 'yes' : 'no' },
    attrs: { 'aria-label': `${player.username}${isTurn ? ', di turno' : ''}` },
  }, [
    avatar,
    label,
    SingBadges(view, player.seat),
    sang ? SangCards(sang, position) : null,
  ]);
}

/**
 * Riquadro di fine partita (result della vista). Se la partita è finita a punti,
 * sotto c'è il riepilogo dell'ultima mano (P57); dopo un abbandono no, perché
 * last_hand sarebbe quello di una mano precedente.
 */
function Result(view) {
  const myTeam = view.players[view.you.seat].team;
  const { winner_team: winner, reason } = view.result;
  let title = 'Pareggio';
  if (winner !== null) title = winner === myTeam ? 'Hai vinto!' : 'Hai perso';
  const text = reason === 'abandon' ? 'La partita è finita per abbandono.' : 'La partita è finita.';
  const summary = reason === 'score' && view.last_hand && view.last_hand.hand_number === view.hand_number
    ? HandSummary(view, view.last_hand)
    : null;
  return el('div', { class: 'table__result panel', data: { result: reason }, attrs: { role: 'status' } }, [
    el('h2', { text: title }),
    el('p', { text }),
    summary,
    el('a', { class: 'btn btn--primary', text: 'Torna alla home', attrs: { href: '/' } }),
  ]);
}

/** Il seme della briscola sopra la mano, a sinistra (P71); niente prima del canto del 40. */
function TrumpBadge(trump) {
  if (!trump) return null;
  return el('span', {
    class: 'trump-badge',
    data: { trumpBadge: trump },
    attrs: { role: 'img', 'aria-label': `Briscola: ${trump}`, title: `Briscola: ${trump}` },
  }, [el('img', { attrs: { src: `${IMG_BASE}asso-${trump}-figura.webp`, alt: '' } })]);
}

/** "Prendi tu", "Prende Turi". */
function winnerText(view, seat) {
  if (seat === view.you.seat) return 'Prendi tu';
  return `Prende ${view.players[seat]?.username ?? 'un giocatore'}`;
}

/**
 * @param {object} view la vista di gioco
 * @param {object} handlers
 * @param {function} handlers.onPlay carta toccata ({suit, rank})
 * @param {function} handlers.onSing seme da cantare
 * @param {function} handlers.onLeave pulsante "Esci"
 * @param {string} [status] messaggio sotto la mano (es. risposta del server)
 * @param {object} [moments] momenti del tavolo da mostrare adesso (P57)
 * @param {object|null} [moments.lastTrick] la presa appena chiusa (last_trick)
 * @param {number} [moments.lastTrickFor] P70: millisecondi da quando la presa chiusa si vede
 * @param {object} [moments.thrown] P70: carta ("coppe-10") → millisecondi dal lancio, per le carte in volo
 * @param {object} [moments.drawnSeats] P70: posto di un avversario → millisecondi dalla sua pescata
 * @param {object} [moments.drawnCards] P70: carta pescata da te ("coppe-10") → millisecondi dalla pescata
 * @param {object|null} [moments.deal] P70, distribuzione a inizio mano: { shuffled: ms dalla
 *   mescolata o null, mine: carta → ms dalla partenza, seats: posto → [ms per carta] }
 * @param {object|null} [moments.summary] il riepilogo di fine mano (last_hand)
 * @param {function} [moments.onCloseSummary] pulsante "Ok" del riepilogo
 * @param {object} [moments.sang] posto → evento game:sang da mostrare
 * @param {object|null} [phrases] frasi del tavolo (P56); null finché l'elenco non arriva
 * @param {Array} phrases.list l'elenco di game:phrases ({code, text})
 * @param {boolean} phrases.open l'elenco è aperto
 * @param {boolean} phrases.disabled pulsante e frasi spenti
 * @param {function} phrases.onToggle apre o chiude l'elenco
 * @param {function} phrases.onPick frase scelta (code)
 * @param {object} phrases.bubbles posto → testo del fumetto da mostrare
 * @returns {HTMLElement}
 */
export function Table(view, { onPlay, onSing, onLeave }, status = '', moments = {}, phrases = null) {
  const {
    lastTrick = null, lastTrickFor = 0, thrown = {}, drawnSeats = {}, drawnCards = {},
    deal = null, summary = null, onCloseSummary = null, sang = {},
  } = moments;
  const bubbles = phrases ? phrases.bubbles : {};
  const positionOf = positionFn(view);
  const me = view.players.find((player) => player.seat === view.you.seat);
  const others = view.players.filter((player) => player.seat !== view.you.seat);

  const topbar = el('header', { class: 'table__top' }, [
    el('button', {
      class: 'btn btn--ghost btn--small table__leave',
      data: { leave: '' },
      attrs: { type: 'button' },
      on: { click: onLeave },
    }, [icon('logout'), 'Esci']),
    Scoreboard(view),
  ]);

  const board = el('div', { class: `table__board table__board--${view.mode}` }, [
    ...others.map((player) =>
      Seat(view, player, positionOf(player.seat), sang[player.seat], bubbles[player.seat])),
    el('div', { class: 'table__center' }, [
      lastTrick
        ? LastTrick(lastTrick, positionOf, winnerText(view, lastTrick.winner_seat), { shownFor: lastTrickFor, thrown })
        : Trick(view.trick, positionOf, thrown),
      DeckAndTrump(view.deck_count, view.trump, deal ? deal.shuffled : null),
    ]),
    summary ? HandSummary(view, summary, { onClose: onCloseSummary }) : null,
  ]);

  // Sopra la mano: la briscola a sinistra, tu al centro, le frasi a destra (P71)
  const meRow = el('div', { class: 'table__me' }, [
    TrumpBadge(view.trump),
    Seat(view, me, 'bottom', sang[me.seat], bubbles[me.seat]),
    phrases ? PhrasesButton(phrases) : null,
    phrases && phrases.open ? PhrasesMenu(phrases.list, phrases) : null,
  ]);
  const mine = el('div', { class: 'table__mine' }, [
    meRow,
    SingButtons(view.legal.sing, view.sings, onSing),
    Hand(view.hand, { playable: view.legal.play, onPlay, drawn: drawnCards, dealt: deal ? deal.mine : {} }),
    el('p', { class: 'table__status', text: status, data: { tableStatus: '' }, attrs: { role: 'status', 'aria-live': 'polite' } }),
  ]);

  // P70: le carte coperte degli altri, a ventaglio dal bordo dello schermo dal loro lato
  const edgeHands = others.map((player) =>
    EdgeHand(player.cards_in_hand, positionOf(player.seat), drawnSeats[player.seat] ?? null,
      deal ? deal.seats[player.seat] ?? null : null));

  // A fine partita il riquadro arriva dopo che si è vista l'ultima presa
  const result = view.result && !lastTrick ? Result(view) : null;
  return el('div', {
    class: 'table__inner',
    data: { mode: view.mode, version: view.version, status: view.status },
  }, [...edgeHands, topbar, board, mine, result]);
}
