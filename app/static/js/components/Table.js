/**
 * Il tavolo di gioco (P21), costruito tutto dalla vista (contratto 3.3).
 *
 * Tu sei sempre in basso; gli altri si dispongono nell'ordine dei posti, verso
 * destra (D11): nel 1v1 l'avversario in alto; nel 2v2 a destra chi gioca dopo di
 * te, in alto il compagno, a sinistra chi gioca prima di te.
 *
 *   [Esci]        Punteggio
 *              (giocatore in alto)
 *   (sinistra)  presa · mazzo  (destra)
 *   (tu) pulsanti Canta · la tua mano
 *
 * La pagina non calcola regole: le carte giocabili sono legal.play e i canti
 * legal.sing (entrambi vuoti quando non è il tuo turno).
 * Stile in css/components/table.css e css/pages/game.css.
 */

import { el, icon } from '../utils/dom.js';
import { Hand, HiddenHand } from './Hand.js';
import { Scoreboard } from './Scoreboard.js';
import { SingButtons } from './SingButtons.js';
import { Timer } from './Timer.js';
import { DeckAndTrump, Trick } from './Trick.js';

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

/** Un giocatore al tavolo: avatar (con l'anello del tempo se tocca a lui), nome, stato. */
function Seat(view, player, position) {
  const isTurn = view.turn !== null && view.turn.seat === player.seat;
  const isMe = player.seat === view.you.seat;
  const partner = view.mode === '2v2' && !isMe && player.team === view.players[view.you.seat].team;

  const notes = [];
  if (partner) notes.push('compagno');
  if (player.seat === view.dealer_seat) notes.push('mazziere');
  if (!player.connected) {
    const left = player.reconnect_seconds_left;
    notes.push(left === null ? 'scollegato' : `scollegato · ${Math.ceil(left)} s`);
  }

  const avatar = el('span', { class: 'seat__avatar' }, [
    el('span', { class: 'avatar', text: player.username.slice(0, 1).toUpperCase(), attrs: { 'aria-hidden': 'true' } }),
    isTurn ? Timer(view.turn) : null,
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
    isMe ? null : HiddenHand(player.cards_in_hand),
  ]);
}

/** Riquadro di fine partita (result della vista). */
function Result(view) {
  const myTeam = view.players[view.you.seat].team;
  const { winner_team: winner, reason } = view.result;
  let title = 'Pareggio';
  if (winner !== null) title = winner === myTeam ? 'Hai vinto!' : 'Hai perso';
  const text = reason === 'abandon' ? 'La partita è finita per abbandono.' : 'La partita è finita.';
  return el('div', { class: 'table__result panel', data: { result: reason }, attrs: { role: 'status' } }, [
    el('h2', { text: title }),
    el('p', { text }),
    el('a', { class: 'btn btn--primary', text: 'Torna alla home', attrs: { href: '/' } }),
  ]);
}

/**
 * @param {object} view la vista di gioco
 * @param {object} handlers
 * @param {function} handlers.onPlay carta toccata ({suit, rank})
 * @param {function} handlers.onSing seme da cantare
 * @param {function} handlers.onLeave pulsante "Esci"
 * @param {string} [status] messaggio sotto la mano (es. risposta del server)
 * @returns {HTMLElement}
 */
export function Table(view, { onPlay, onSing, onLeave }, status = '') {
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
    ...others.map((player) => Seat(view, player, positionOf(player.seat))),
    el('div', { class: 'table__center' }, [
      Trick(view.trick, positionOf),
      DeckAndTrump(view.deck_count, view.trump),
    ]),
  ]);

  const mine = el('div', { class: 'table__mine' }, [
    Seat(view, me, 'bottom'),
    SingButtons(view.legal.sing, view.sings, onSing),
    Hand(view.hand, { playable: view.legal.play, onPlay }),
    el('p', { class: 'table__status', text: status, data: { tableStatus: '' }, attrs: { role: 'status', 'aria-live': 'polite' } }),
  ]);

  return el('div', {
    class: 'table__inner',
    data: { mode: view.mode, version: view.version, status: view.status },
  }, [topbar, board, mine, view.result ? Result(view) : null]);
}
