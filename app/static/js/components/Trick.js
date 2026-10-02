/**
 * Presa in corso al centro del tavolo (P21): ogni carta sta dal lato di chi l'ha
 * giocata (in basso la tua, poi destra, in alto e sinistra, come i posti).
 * Accanto, il mazzo coperto con le carte rimaste e sopra il seme della briscola
 * (P71). Stile in css/components/trick.css.
 * P57: LastTrick, la presa appena chiusa, per un momento.
 * P70: la carta appena giocata vola al suo posto (lancio); i tempi li decide
 * pages/game.js e qui diventano ritardi delle animazioni, così un ridisegno a metà
 * non le fa ripartire da capo.
 * P76: le carte stanno a croce senza coprirsi e la carta che sta vincendo (o che
 * ha preso, nella presa chiusa) è sollevata e bordata (trick__card--winner).
 */

import { el } from '../utils/dom.js';
import { Card, CardBack, cardName } from './Card.js';

const IMG_BASE = new URL('../../img/cards-bg/', import.meta.url).href;
// Dopo quanto le carte della presa chiusa scivolano via: come il ritardo di trick-away in trick.css
const AWAY_DELAY_MS = 1100;

/**
 * La carta dentro la presa. P70: se è appena stata giocata (`thrown` = millisecondi
 * dal lancio, lo decide pages/game.js) vola al suo posto; il ritardo negativo fa
 * ripartire l'animazione dal punto giusto quando il tavolo si ridisegna a metà volo.
 */
function ThrownCard(card, thrown) {
  const face = Card(card);
  if (thrown != null) {
    face.classList.add('card--thrown');
    face.dataset.thrown = '';
    face.style.animationDelay = `${-Math.round(thrown)}ms`;
  }
  return face;
}

/** Chiave di una carta per i lanci (P70): "coppe-10". */
export function throwKey(card) {
  return `${card.suit}-${card.rank}`;
}

/**
 * @param {object} trick il campo trick della vista ({leader_seat, cards: [{seat, card}]})
 * @param {function} positionOf posto → 'bottom' | 'right' | 'top' | 'left'
 * @param {object} [thrown] P70: throwKey(carta) → millisecondi dal lancio, per le carte in volo
 * @returns {HTMLElement}
 */
export function Trick(trick, positionOf, thrown = {}) {
  // P76: la carta che sta vincendo la presa la dice il server (trick.winning_seat, P75)
  const winning = trick.cards.find(({ seat }) => seat === trick.winning_seat);
  const cards = trick.cards.map(({ seat, card }) =>
    el('div', {
      class: `trick__card trick__card--${positionOf(seat)}${seat === trick.winning_seat ? ' trick__card--winner' : ''}`,
      data: { trickSeat: seat, ...(seat === trick.winning_seat ? { winning: '' } : {}) },
    }, [ThrownCard(card, thrown[throwKey(card)])]),
  );
  const label = trick.cards.length
    ? `Presa in corso: ${trick.cards.map(({ card }) => cardName(card)).join(', ')}`
      + (winning ? `. Sta vincendo: ${cardName(winning.card)}` : '')
    : 'Presa in corso: nessuna carta';
  return el('div', { class: 'trick', data: { trick: '', count: trick.cards.length }, attrs: { role: 'group', 'aria-label': label } }, cards);
}

/**
 * La presa appena chiusa (P57, last_trick della vista), mostrata per un momento al
 * posto della presa vuota: le carte restano dove sono state giocate, quella di chi
 * ha preso è in risalto, e alla fine scivolano verso di lui (con "riduci
 * movimento" spariscono e basta). Quando e per quanto la decide pages/game.js.
 *
 * @param {object} lastTrick il campo last_trick ({winner_seat, cards: [{seat, card}]})
 * @param {function} positionOf posto → 'bottom' | 'right' | 'top' | 'left'
 * @param {string} winnerText es. "Prende Turi" oppure "Prendi tu"
 * @param {object} [timing] P70, per non far ripartire le animazioni a ogni ridisegno
 * @param {number} [timing.shownFor] millisecondi da quando la presa chiusa si vede
 * @param {object} [timing.thrown] throwKey(carta) → millisecondi dal lancio (la carta che l'ha chiusa)
 * @returns {HTMLElement}
 */
export function LastTrick(lastTrick, positionOf, winnerText, { shownFor = 0, thrown = {} } = {}) {
  const winner = lastTrick.winner_seat;
  // L'uscita verso chi ha preso comincia AWAY_DELAY_MS dopo che la presa si vede, anche dopo un ridisegno
  const awayDelay = `${Math.round(AWAY_DELAY_MS - shownFor)}ms`;
  const cards = lastTrick.cards.map(({ seat, card }) => {
    const slot = el('div', {
      class: `trick__card trick__card--${positionOf(seat)}${seat === winner ? ' trick__card--winner' : ''}`,
      data: { trickSeat: seat },
    }, [ThrownCard(card, thrown[throwKey(card)])]);
    slot.style.animationDelay = awayDelay;
    return slot;
  });
  const label = `${winnerText}: ${lastTrick.cards.map(({ card }) => cardName(card)).join(', ')}`;
  const winnerLabel = el('span', { class: 'trick__winner', text: winnerText, attrs: { 'aria-hidden': 'true' } });
  winnerLabel.style.animationDelay = awayDelay;
  return el('div', {
    class: `trick trick--closed trick--to-${positionOf(winner)}`,
    data: { lastTrick: '', winnerSeat: winner, count: lastTrick.cards.length },
    attrs: { role: 'group', 'aria-label': label },
  }, [...cards, winnerLabel]);
}

/**
 * P77: mazzo finito, il seme della briscola resta dov'era il mazzo fino a fine mano.
 * La carta coperta è invisibile e tiene solo il posto, con la misura del mazzo.
 * @param {string} trump seme di briscola
 * @returns {HTMLElement}
 */
function EmptyDeck(trump) {
  const slot = CardBack();
  slot.classList.add('deck__slot');
  return el('div', {
    class: 'deck deck--empty',
    data: { deckEmpty: '' },
    attrs: { role: 'img', 'aria-label': `Mazzo finito. Briscola: ${trump}` },
  }, [
    slot,
    el('img', { class: 'deck__trump', data: { trump }, attrs: { src: `${IMG_BASE}asso-${trump}-figura.webp`, alt: '' } }),
  ]);
}

/**
 * Mazzo coperto con le carte rimaste e, al centro sopra il mazzo, il seme della
 * briscola (P71): niente nome del seme (lo leggono solo i lettori di schermo) e
 * niente scritta prima del canto del 40. P77: è l'unico posto dove si vede la
 * briscola; a mazzo finito, al posto del mazzo, resta il seme (EmptyDeck).
 * @param {number} deckCount carte rimaste nel mazzo
 * @param {string|null} trump seme di briscola, null finché nessuno ha cantato 40
 * @param {number|null} [shuffled] P70: millisecondi dall'inizio della mescolata a inizio
 *   mano, o null: due mezzi mazzi si aprono ai lati e si richiudono
 * @returns {HTMLElement|null}
 */
export function DeckAndTrump(deckCount, trump, shuffled = null) {
  if (deckCount <= 0) return trump ? EmptyDeck(trump) : null;
  const label = trump ? `Mazzo: ${deckCount} carte. Briscola: ${trump}` : `Mazzo: ${deckCount} carte`;
  const riffle = shuffled == null ? [] : ['left', 'right'].map((side) => {
    const half = CardBack();
    half.classList.add('deck__half', `deck__half--${side}`);
    half.style.animationDelay = `${Math.round(-shuffled)}ms`;
    return half;
  });
  return el('div', {
    class: 'deck',
    data: { deckCount, ...(shuffled == null ? {} : { shuffling: '' }) },
    attrs: { role: 'img', 'aria-label': label },
  }, [
    CardBack(),
    ...riffle,
    trump
      ? el('img', { class: 'deck__trump', data: { trump }, attrs: { src: `${IMG_BASE}asso-${trump}-figura.webp`, alt: '' } })
      : null,
    el('span', { class: 'deck__count', text: deckCount, attrs: { 'aria-hidden': 'true' } }),
  ]);
}
