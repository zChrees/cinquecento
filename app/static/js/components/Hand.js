/**
 * Mano del giocatore (P20): le carte in fila dritta, affiancate, grandi quanto
 * permette lo schermo (a 360 px cinque carte stanno in una riga).
 *
 * Le mosse ammesse le decide il server (legal.play nella vista, contratto 3.3):
 * la mano rende giocabili solo quelle, le altre restano visibili ma spente.
 *
 *   Hand(view.hand, { playable: view.legal.play, onPlay: (card) => ... })
 *   Hand(cards)                     // sola lettura (es. pagina di prova)
 *   HiddenHand(3)                   // carte coperte (fila semplice)
 *   EdgeHand(3, 'top', drawn)       // P70: carte coperte di un avversario, dal bordo
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
 * @param {object} [options.drawn] P70: carta ("coppe-10") → millisecondi da quando è stata pescata
 * @returns {HTMLElement}
 */
export function Hand(cards, { playable = [], onPlay = null, drawn = {} } = {}) {
  const items = cards.map((card) => {
    const item = Card(card, onPlay ? { onPlay, playable: playable.some((legal) => sameCard(legal, card)) } : {});
    // P70: la carta appena pescata vola dal mazzo nella mano (millisecondi dalla pescata)
    const since = drawn[`${card.suit}-${card.rank}`];
    if (since != null) {
      item.classList.add('card--drawn-mine');
      item.dataset.drawn = '';
      item.style.animationDelay = `${Math.round(-since)}ms`;
    }
    return item;
  });
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

/**
 * Carte coperte di un avversario al tavolo (P70): un ventaglio agganciato al bordo
 * dello schermo dal suo lato ('top', 'left' o 'right'), per metà fuori, aperto verso
 * il centro del tavolo. Il ventaglio si disegna "in piedi" e il CSS lo gira verso
 * il suo lato; l'angolo di ogni carta dipende dalla sua posizione (--i) e da quante
 * sono (--n).
 *
 * P70, pescata: con `drawn` (millisecondi da quando ha pescato; negativo = pesca tra
 * poco) l'ultima carta arriva dal centro del tavolo e le altre si allargano per farle
 * posto, partendo dal ventaglio di prima (--n-before). Il tempo diventa un ritardo
 * dell'animazione, così un ridisegno a metà non la fa ripartire.
 *
 * @param {number} count carte in mano (cards_in_hand)
 * @param {string} side 'top' | 'left' | 'right'
 * @param {number|null} [drawn] millisecondi dalla pescata, o null
 * @returns {HTMLElement}
 */
export function EdgeHand(count, side, drawn = null) {
  const items = Array.from({ length: count }, (_, i) => {
    const back = CardBack();
    back.style.setProperty('--i', i);
    if (drawn != null) {
      back.classList.add(i === count - 1 ? 'card--drawn' : 'card--making-room');
      back.style.animationDelay = `${Math.round(-drawn)}ms`;
    }
    return back;
  });
  const hand = el('div', {
    class: `edge-hand edge-hand--${side}`,
    data: { edgeHand: side, count, ...(drawn != null ? { drawing: '' } : {}) },
    attrs: { role: 'group', 'aria-label': `${count} carte coperte` },
  }, items);
  hand.style.setProperty('--n', count);
  hand.style.setProperty('--n-before', Math.max(count - 1, 1));
  return hand;
}
