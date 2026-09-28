/**
 * Mano del giocatore (P20): le carte in fila dritta, affiancate, grandi quanto
 * permette lo schermo (a 360 px cinque carte stanno in una riga).
 *
 * Le mosse ammesse le decide il server (legal.cards nella vista, contratto 3.3):
 * la mano rende giocabili solo quelle, le altre restano visibili ma spente.
 *
 *   Hand(view.hand, { playable: view.legal.cards, onPlay: (card) => ... })
 *   Hand(cards)                     // sola lettura (es. pagina di prova)
 *   HiddenHand(3)                   // carte coperte di un avversario
 *
 * Stile in css/components/hand.css.
 */

import { el } from '../utils/dom.js';
import { Card, CardBack, sameCard } from './Card.js';

/**
 * @param {Array<{suit: string, rank: number}>} cards carte in mano, nell'ordine del server
 * @param {object} [options]
 * @param {Array<{suit: string, rank: number}>} [options.playable] carte giocabili (solo con onPlay)
 * @param {function} [options.onPlay] chiamata con la carta toccata
 * @returns {HTMLElement}
 */
export function Hand(cards, { playable = [], onPlay = null } = {}) {
  const items = cards.map((card) =>
    Card(card, onPlay ? { onPlay, playable: playable.some((legal) => sameCard(legal, card)) } : {}),
  );
  return el('div', { class: 'hand', data: { hand: '', count: cards.length }, attrs: { role: 'group', 'aria-label': 'Le tue carte' } }, items);
}

/**
 * Carte coperte, per esempio in mano a un avversario (cards_in_hand nella vista).
 * @param {number} count
 */
export function HiddenHand(count) {
  const items = Array.from({ length: count }, () => CardBack());
  return el('div', { class: 'hand hand--hidden', data: { hand: '', count }, attrs: { role: 'group', 'aria-label': `${count} carte coperte` } }, items);
}
