/**
 * Carta siciliana (P20, P35). La faccia è l'immagine della carta vera,
 * img/cards/<seme>-<valore>.webp (per esempio coppe-10.webp: il nome è il codice
 * della carta nel motore), ritagliata dalle scansioni di Matsoftware (CC BY-SA
 * 3.0, vedi img/cards/LICENZA.md). Come sulle carte siciliane vere, niente valore
 * negli angoli (scelta di P35). Il dorso è quello delle altre pagine
 * (img/cards-bg/dorso.webp).
 *
 * La carta arriva dal server nella forma del contratto: {"suit": "coppe", "rank": 10}
 * (1 = Asso, 8 = Fante, 9 = Cavallo, 10 = Re). Una carta fuori elenco si rifiuta
 * con un errore, senza correzioni silenziose. Ogni carta ha data-suit e data-rank
 * stabili, per i test.
 *
 *   Card({ suit: 'coppe', rank: 10 })                         // carta scoperta
 *   Card({ suit: 'coppe', rank: 10 }, { onPlay, playable })   // pulsante nella mano
 *   CardBack()                                               // carta coperta
 *   reuseCardImages(root)   // P70: prima di ridisegnare, riusa le immagini già caricate
 *   preloadCardImages()     // P79: scarica subito tutte le immagini del tavolo
 *
 * Stile in css/components/card.css.
 */

import { el } from '../utils/dom.js';

export const SUITS = ['denari', 'coppe', 'spade', 'bastoni'];

/** Nomi dei valori, come RANK_NAMES del motore (app/game/engine/cards.py). */
export const RANK_NAMES = {
  1: 'Asso', 2: '2', 3: '3', 4: '4', 5: '5', 6: '6', 7: '7', 8: 'Fante', 9: 'Cavallo', 10: 'Re',
};

const FACE_BASE = new URL('../../img/cards/', import.meta.url).href;
const BACK_URL = new URL('../../img/cards-bg/dorso.webp', import.meta.url).href;

// P79: assi "figura" di briscola e canti, gli stessi file che usano Table.js e Trick.js
const FIGURE_BASE = new URL('../../img/cards-bg/', import.meta.url).href;

// P70: immagini della pagina di prima, da riusare al prossimo ridisegno (reuseCardImages)
let reusable = new Map();

// P79: immagini scaricate all'apertura del tavolo (preloadCardImages)
let preloaded = null;

/**
 * Scarica subito tutte le immagini che il tavolo può mostrare: le 40 facce, il
 * dorso, i quattro assi "figura" (P79) e Cavallo e Re di ogni seme (P108). Senza, l'immagine di una carta si
 * scaricava la prima volta che la carta compariva e, con una rete lenta, la carta
 * restava bianca per qualche secondo. Le immagini restano in memoria (`preloaded`),
 * così il browser non le butta via. Chiamata più volte, scarica una volta sola.
 * @returns {Promise<boolean>} true quando sono tutte pronte, false se una non è arrivata
 */
export function preloadCardImages() {
  if (preloaded) return preloaded.ready;
  const urls = [BACK_URL];
  for (const suit of SUITS) {
    urls.push(`${FIGURE_BASE}asso-${suit}-figura.webp`);
    // P108: Cavallo e Re della briscola, nell'angolo del tavolo (TrumpBadge di Trick.js)
    urls.push(`${FIGURE_BASE}cavallo-${suit}.webp`, `${FIGURE_BASE}re-${suit}.webp`);
    for (let rank = 1; rank <= 10; rank += 1) urls.push(`${FACE_BASE}${suit}-${rank}.webp`);
  }
  const images = urls.map((src) => {
    const img = new Image();
    img.src = src;
    return img;
  });
  const ready = Promise.all(images.map((img) => img.decode().then(() => true, () => false)))
    .then((results) => results.every(Boolean));
  preloaded = { images, ready };
  return ready;
}

/**
 * Prende da `root` le immagini delle carte già disegnate, così le carte del
 * ridisegno successivo riusano gli stessi elementi <img> invece di crearne di
 * nuovi (P70). Un'immagine nuova, finché il browser non l'ha pronta, per un attimo
 * mostra il fondo bianco della carta: è il lampo bianco trovato giocando dal
 * telefono. Da chiamare subito prima di ridisegnare dentro `root`.
 * P119: lo stesso per le immagini degli avatar e della briscola nell'angolo
 * (REUSED_IMAGES), che a ogni lancio o pescata lampeggiavano: le riprendono
 * Avatar.js e TrumpBadge (Trick.js) con reusedImage().
 * @param {HTMLElement} root
 */
export function reuseCardImages(root) {
  reusable = new Map();
  for (const img of root.querySelectorAll(REUSED_IMAGES)) {
    const key = `${img.className} ${img.src}`;
    if (!reusable.has(key)) reusable.set(key, []);
    reusable.get(key).push(img);
  }
}

const REUSED_IMAGES = 'img.card__face, img.card__back, img.avatar__img, img.trump-badge__card';

/**
 * Un'immagine con classe `className` e indirizzo `src` (assoluto, come img.src):
 * quella del disegno di prima, se c'era (reuseCardImages), altrimenti una nuova con
 * gli attributi `attrs` in più.
 */
export function reusedImage(className, src, attrs = {}) {
  const old = reusable.get(`${className} ${src}`)?.pop();
  if (old) return old;
  return el('img', { class: className, attrs: { src, alt: '', draggable: 'false', ...attrs } });
}

function cardImage(className, src) {
  return reusedImage(className, src);
}

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
  // Il nome lo dà l'etichetta della carta (aria-label): l'immagine è solo decorativa
  const face = [cardImage('card__face', `${FACE_BASE}${card.suit}-${card.rank}.webp`)];
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
    cardImage('card__back', BACK_URL),
  ]);
}
