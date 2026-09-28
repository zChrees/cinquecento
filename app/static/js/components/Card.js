/**
 * Carta siciliana (P20): segnaposto disegnato in CSS finché P35 non porta le
 * carte vere. Faccia crema con il valore negli angoli (A, 2–7, F, C, R) nel
 * colore del seme e, al centro, la figura dell'Asso di quel seme; il dorso è
 * quello delle altre pagine (img/cards-bg/dorso.webp).
 *
 * La carta arriva dal server nella forma del contratto: {"suit": "coppe", "rank": 10}
 * (1 = Asso, 8 = Fante, 9 = Cavallo, 10 = Re). Una carta fuori elenco si rifiuta
 * con un errore, senza correzioni silenziose. Ogni carta ha data-suit e data-rank
 * stabili, per i test.
 *
 *   Card({ suit: 'coppe', rank: 10 })                         // carta scoperta
 *   Card({ suit: 'coppe', rank: 10 }, { onPlay, playable })   // pulsante nella mano
 *   CardBack()                                               // carta coperta
 *
 * Stile in css/components/card.css.
 */

import { el } from '../utils/dom.js';

export const SUITS = ['denari', 'coppe', 'spade', 'bastoni'];

/** Nomi dei valori, come RANK_NAMES del motore (app/game/engine/cards.py). */
export const RANK_NAMES = {
  1: 'Asso', 2: '2', 3: '3', 4: '4', 5: '5', 6: '6', 7: '7', 8: 'Fante', 9: 'Cavallo', 10: 'Re',
};

/** Il valore scritto negli angoli della carta. */
export const RANK_LABELS = {
  1: 'A', 2: '2', 3: '3', 4: '4', 5: '5', 6: '6', 7: '7', 8: 'F', 9: 'C', 10: 'R',
};

const IMG_BASE = new URL('../../img/cards-bg/', import.meta.url).href;

/**
 * Controlla che una carta sia nella forma del contratto e la restituisce.
 * @throws {Error} "Carta non valida." per qualunque altro valore
 */
export function checkCard(card) {
  const ok = card !== null && typeof card === 'object'
    && SUITS.includes(card.suit)
    && Number.isInteger(card.rank) && card.rank >= 1 && card.rank <= 10;
  if (!ok) throw new Error('Carta non valida.');
  return card;
}

/** Nome da leggere: "Re di coppe", "7 di denari". */
export function cardName(card) {
  checkCard(card);
  return `${RANK_NAMES[card.rank]} di ${card.suit}`;
}

/** true se le due carte sono la stessa. */
export function sameCard(a, b) {
  return a.suit === b.suit && a.rank === b.rank;
}

/**
 * Carta scoperta.
 *
 * @param {{suit: string, rank: number}} card
 * @param {object} [options]
 * @param {function} [options.onPlay] se c'è, la carta è un pulsante che la gioca
 * @param {boolean} [options.playable] con onPlay: false = pulsante disattivato (mossa non ammessa)
 * @returns {HTMLElement}
 */
export function Card(card, { onPlay = null, playable = true } = {}) {
  const name = cardName(card);
  const face = [
    el('span', { class: 'card__rank card__rank--top', text: RANK_LABELS[card.rank], attrs: { 'aria-hidden': 'true' } }),
    el('img', { class: 'card__suit', attrs: { src: `${IMG_BASE}asso-${card.suit}-figura.webp`, alt: '', draggable: 'false' } }),
    el('span', { class: 'card__rank card__rank--bottom', text: RANK_LABELS[card.rank], attrs: { 'aria-hidden': 'true' } }),
  ];
  const data = { suit: card.suit, rank: card.rank };

  if (!onPlay) {
    return el('div', { class: `card card--${card.suit}`, data, attrs: { role: 'img', 'aria-label': name } }, face);
  }
  return el(
    'button',
    {
      class: `card card--${card.suit}`,
      data,
      attrs: { type: 'button', 'aria-label': `Gioca ${name}`, disabled: !playable },
      on: { click: () => onPlay(card) },
    },
    face,
  );
}

/** Carta coperta (dorso): per le carte degli avversari e il mazzo. */
export function CardBack() {
  return el('div', { class: 'card card--back', data: { back: '' }, attrs: { role: 'img', 'aria-label': 'Carta coperta' } }, [
    el('img', { class: 'card__back', attrs: { src: `${IMG_BASE}dorso.webp`, alt: '', draggable: 'false' } }),
  ]);
}
