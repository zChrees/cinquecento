/**
 * Le carte del tavolo React: nomi, confronti e indirizzi delle immagini. È la parte
 * "senza disegno" di app/static/js/components/Card.js e Trick.js (P20, P35, P70),
 * con gli stessi risultati.
 *
 * Cosa contiene:
 *   SUITS                         ['denari', 'coppe', 'spade', 'bastoni']
 *   RANK_NAMES[10]                'Re'
 *   checkCard(card)               la carta, se è nella forma del contratto; altrimenti errore
 *   cardName({ suit: 'coppe', rank: 10 })   'Re di coppe'
 *   sameCard(a, b)                true se sono la stessa carta
 *   throwKey({ suit: 'coppe', rank: 10 })   'coppe-10'
 *   faceUrl(card), BACK_URL, FIGURE_BASE    gli indirizzi delle immagini
 *   preloadCardImages()           scarica subito tutte le immagini del tavolo (P79, dal lotto 8b)
 *
 * DA DOVE ARRIVANO I DATI: le carte arrivano dal server dentro la vista di gioco
 * (types/view.ts); i componenti di frontend/src/game/ chiamano queste funzioni
 * mentre la disegnano.
 */

import type { Card, Rank, Suit } from '../types/card';

// SUITS: i quattro semi, nell'ordine di Card.js
export const SUITS: Suit[] = ['denari', 'coppe', 'spade', 'bastoni'];

// RANK_NAMES: il nome di ogni valore, come RANK_NAMES del motore
// (app/game/engine/cards.py). Record<Rank, string> vuol dire "un oggetto con una
// chiave per ogni valore da 1 a 10, e un testo per ciascuna".
export const RANK_NAMES: Record<Rank, string> = {
  1: 'Asso', 2: '2', 3: '3', 4: '4', 5: '5', 6: '6', 7: '7', 8: 'Fante', 9: 'Cavallo', 10: 'Re',
};

// FACE_BASE: la cartella delle facce, una per carta (img/cards/coppe-10.webp)
const FACE_BASE = '/static/img/cards/';
// BACK_URL: il dorso delle carte coperte
export const BACK_URL = '/static/img/cards-bg/dorso.webp';
// FIGURE_BASE: gli Assi "figura" (canti) e Cavallo e Re della briscola (P79, P108)
export const FIGURE_BASE = '/static/img/cards-bg/';

/**
 * Controlla che una carta sia nella forma del contratto e la restituisce.
 *
 * @param {Card} card la carta da controllare
 * @returns {Card} la stessa carta
 * @throws {Error} "Carta non valida." per qualunque altro valore
 *
 * In parole semplici:
 *   checkCard({ suit: 'coppe', rank: 10 })   → la stessa carta
 *   checkCard({ suit: 'cuori', rank: 10 })   → errore "Carta non valida."
 *   Il tipo Card dice già com'è fatta una carta, ma la vista arriva dalla rete
 *   (o, nella prova, da un evento mandato da un test): TypeScript non può
 *   controllarla mentre il programma gira. Come Card.js, una carta sbagliata si
 *   rifiuta con un errore, senza correzioni silenziose (P20).
 */
export function checkCard(card: Card): Card {
  let ok = false;
  if (card !== null && typeof card === 'object' && SUITS.includes(card.suit)
    && Number.isInteger(card.rank) && card.rank >= 1 && card.rank <= 10) {
    ok = true;
  }
  if (!ok) {
    throw new Error('Carta non valida.');
  }
  return card;
}

/**
 * Il nome da leggere di una carta.
 *
 * @param {Card} card la carta
 * @returns {string} per esempio 'Re di coppe' o '7 di denari'
 *
 * In parole semplici:
 *   cardName({ suit: 'coppe', rank: 10 })   → 'Re di coppe'
 *   Lo usano le etichette per i lettori di schermo ("Gioca Re di coppe") e la riga
 *   di stato della prova ("Prova: hai scelto Re di coppe...").
 */
export function cardName(card: Card): string {
  checkCard(card);
  return `${RANK_NAMES[card.rank]} di ${card.suit}`;
}

/**
 * Dice se due carte sono la stessa.
 *
 * @param {Card} a la prima carta
 * @param {Card} b la seconda carta
 * @returns {boolean}
 *
 * In parole semplici:
 *   sameCard({ suit: 'coppe', rank: 1 }, { suit: 'coppe', rank: 1 })   → true
 *   Due oggetti diversi con gli stessi campi non sono "uguali" per ===, come due
 *   struct del C a indirizzi diversi: si confrontano i campi uno per uno.
 */
export function sameCard(a: Card, b: Card): boolean {
  return a.suit === b.suit && a.rank === b.rank;
}

/**
 * Il codice di una carta, usato come chiave.
 *
 * @param {Card} card la carta
 * @returns {string} per esempio 'coppe-10'
 *
 * In parole semplici:
 *   throwKey({ suit: 'coppe', rank: 10 })   → 'coppe-10'
 *   È lo stesso codice del nome del file dell'immagine e della chiave dei lanci di
 *   game.js (P70). Nei componenti React fa anche da `key` delle carte: una carta
 *   compare una volta sola nel mazzo, quindi il codice è unico.
 */
export function throwKey(card: Card): string {
  return `${card.suit}-${card.rank}`;
}

// Preloaded: le immagini scaricate all'apertura del tavolo e la promessa che dice
// quando sono pronte. Variabile del modulo: si scaricano una volta sola per scheda
interface Preloaded {
  // le immagini; restano qui così il browser non le butta via
  images: HTMLImageElement[];
  // true quando sono tutte pronte, false se una non è arrivata
  ready: Promise<boolean>;
}
let preloaded: Preloaded | null = null;

/**
 * Scarica subito tutte le immagini che il tavolo può mostrare (P79).
 *
 * @returns {Promise<boolean>} true quando sono tutte pronte, false se una non è arrivata
 *
 * In parole semplici:
 *   preloadCardImages().then(markReady)
 *   Le 40 facce, il dorso, i quattro Assi "figura" dei canti e Cavallo e Re di ogni
 *   seme per la briscola (P108), come preloadCardImages di Card.js. Senza, con una
 *   rete lenta una carta mai vista restava bianca per qualche secondo quando
 *   compariva. Chiamata più volte, scarica una volta sola. "Promise" è una risposta
 *   che arriverà più tardi: decode() finisce quando l'immagine è pronta da disegnare.
 */
export function preloadCardImages(): Promise<boolean> {
  if (preloaded !== null) {
    return preloaded.ready;
  }
  const urls: string[] = [BACK_URL];
  for (let i = 0; i < SUITS.length; i++) {
    const suit = SUITS[i];
    urls.push(`${FIGURE_BASE}asso-${suit}-figura.webp`);
    urls.push(`${FIGURE_BASE}cavallo-${suit}.webp`, `${FIGURE_BASE}re-${suit}.webp`);
    for (let rank = 1; rank <= 10; rank++) {
      urls.push(`${FACE_BASE}${suit}-${rank}.webp`);
    }
  }

  // images e decoding: un'immagine e la sua "promessa" di essere pronta, per ogni indirizzo
  const images: HTMLImageElement[] = [];
  const decoding: Promise<boolean>[] = [];
  function decoded(): boolean {
    return true;
  }
  function failed(): boolean {
    return false;
  }
  for (let i = 0; i < urls.length; i++) {
    const img = new Image();
    img.src = urls[i];
    images.push(img);
    decoding.push(img.decode().then(decoded, failed));
  }
  // allReady: true solo se ogni immagine è pronta
  function allReady(results: boolean[]): boolean {
    for (let i = 0; i < results.length; i++) {
      if (!results[i]) {
        return false;
      }
    }
    return true;
  }
  const ready = Promise.all(decoding).then(allReady);
  preloaded = { images: images, ready: ready };
  return ready;
}

/**
 * L'indirizzo dell'immagine della faccia di una carta.
 *
 * @param {Card} card la carta
 * @returns {string} per esempio '/static/img/cards/coppe-10.webp'
 */
export function faceUrl(card: Card): string {
  return `${FACE_BASE}${card.suit}-${card.rank}.webp`;
}
