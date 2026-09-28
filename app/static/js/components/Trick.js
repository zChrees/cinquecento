/**
 * Presa in corso al centro del tavolo (P21): ogni carta sta dal lato di chi l'ha
 * giocata (in basso la tua, poi destra, in alto e sinistra, come i posti).
 * Accanto, il mazzo coperto con le carte rimaste e la briscola (oppure "Carte
 * franche" finché nessuno ha cantato 40). Stile in css/components/trick.css.
 * P57: LastTrick, la presa appena chiusa, per un momento.
 */

import { el } from '../utils/dom.js';
import { Card, CardBack, cardName } from './Card.js';

const IMG_BASE = new URL('../../img/cards-bg/', import.meta.url).href;

/**
 * @param {object} trick il campo trick della vista ({leader_seat, cards: [{seat, card}]})
 * @param {function} positionOf posto → 'bottom' | 'right' | 'top' | 'left'
 * @returns {HTMLElement}
 */
export function Trick(trick, positionOf) {
  const cards = trick.cards.map(({ seat, card }) =>
    el('div', { class: `trick__card trick__card--${positionOf(seat)}`, data: { trickSeat: seat } }, [Card(card)]),
  );
  const label = trick.cards.length
    ? `Presa in corso: ${trick.cards.map(({ card }) => cardName(card)).join(', ')}`
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
 * @returns {HTMLElement}
 */
export function LastTrick(lastTrick, positionOf, winnerText) {
  const winner = lastTrick.winner_seat;
  const cards = lastTrick.cards.map(({ seat, card }) =>
    el('div', {
      class: `trick__card trick__card--${positionOf(seat)}${seat === winner ? ' trick__card--winner' : ''}`,
      data: { trickSeat: seat },
    }, [Card(card)]),
  );
  const label = `${winnerText}: ${lastTrick.cards.map(({ card }) => cardName(card)).join(', ')}`;
  return el('div', {
    class: `trick trick--closed trick--to-${positionOf(winner)}`,
    data: { lastTrick: '', winnerSeat: winner, count: lastTrick.cards.length },
    attrs: { role: 'group', 'aria-label': label },
  }, [...cards, el('span', { class: 'trick__winner', text: winnerText, attrs: { 'aria-hidden': 'true' } })]);
}

/**
 * Mazzo e briscola.
 * @param {number} deckCount carte rimaste nel mazzo
 * @param {string|null} trump seme di briscola, null = carte franche
 */
export function DeckAndTrump(deckCount, trump) {
  const deck = deckCount > 0
    ? el('div', { class: 'deck', data: { deckCount }, attrs: { 'aria-label': `Mazzo: ${deckCount} carte` } }, [
      CardBack(),
      el('span', { class: 'deck__count', text: deckCount, attrs: { 'aria-hidden': 'true' } }),
    ])
    : el('p', { class: 'deck deck--empty', data: { deckCount: 0 }, text: 'Mazzo finito' });

  const trumpInfo = trump
    ? el('div', { class: `trump trump--${trump}`, data: { trump } }, [
      el('img', { class: 'trump__suit', attrs: { src: `${IMG_BASE}asso-${trump}-figura.webp`, alt: '' } }),
      el('span', { class: 'trump__text' }, [el('small', { text: 'Briscola' }), ` ${trump}`]),
    ])
    : el('div', { class: 'trump trump--none', data: { trump: '' } }, [
      el('span', { class: 'trump__text', text: 'Carte franche' }),
    ]);
  return el('div', { class: 'deck-trump' }, [deck, trumpInfo]);
}
