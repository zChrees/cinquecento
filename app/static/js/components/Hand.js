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
 *   EdgeHand(3, 'top', drawn, dealt) // P70: carte coperte di un avversario, dal bordo
 *   RevealedHand(cards, 'top', seat) // P85: le carte di un altro giocatore scoperte, dentro il tavolo
 *   Hand(view.hand, { ..., advice: { card, name } }) // P93: la carta consigliata dal compagno, segnata
 *
 * Stile in css/components/hand.css.
 */

import { el } from '../utils/dom.js';
import { Card, CardBack, cardName, sameCard } from './Card.js';

/**
 * @param {Array<{suit: string, rank: number}>} cards carte in mano, nell'ordine del server
 * @param {object} [options]
 * @param {Array<{suit: string, rank: number}>} [options.playable] carte giocabili (solo con onPlay)
 * @param {function} [options.onPlay] chiamata con la carta toccata
 * @param {object} [options.drawn] P70: carta ("coppe-10") → millisecondi da quando è stata pescata
 * @param {object} [options.dealt] P70: carta ("coppe-10") → millisecondi da quando è partita nella distribuzione
 * @param {object|null} [options.advice] P93: { card, name }, la carta che ti ha consigliato il compagno
 * @returns {HTMLElement}
 */
export function Hand(cards, { playable = [], onPlay = null, drawn = {}, dealt = {}, advice = null } = {}) {
  const items = cards.map((card) => {
    const item = Card(card, onPlay ? { onPlay, playable: playable.some((legal) => sameCard(legal, card)) } : {});
    // P93: la carta consigliata dal compagno ha il bordo e l'etichetta "consiglio di …"
    if (advice && sameCard(advice.card, card)) {
      item.classList.add('card--advice');
      item.dataset.advice = '';
      item.setAttribute('aria-label', `${item.getAttribute('aria-label')}, consigliata da ${advice.name}`);
      item.append(el('span', { class: 'card__advice', text: `consiglio di ${advice.name}`, attrs: { 'aria-hidden': 'true' } }));
    }
    // P70: la carta appena pescata, o distribuita a inizio mano, vola dal mazzo nella
    // mano (millisecondi da quando parte; negativo = parte tra poco, e fino ad allora
    // non si vede)
    const key = `${card.suit}-${card.rank}`;
    const since = dealt[key] ?? drawn[key];
    if (since != null) {
      item.classList.add(dealt[key] != null ? 'card--dealt-mine' : 'card--drawn-mine');
      item.dataset[dealt[key] != null ? 'dealt' : 'drawn'] = '';
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
 * @param {Array<number>|null} [dealt] P70, distribuzione: per ogni carta i millisecondi
 *   da quando è partita dal mazzo (negativi: parte tra poco e fino ad allora non si vede)
 * @returns {HTMLElement}
 */
export function EdgeHand(count, side, drawn = null, dealt = null) {
  const items = Array.from({ length: count }, (_, i) => {
    const back = CardBack();
    back.style.setProperty('--i', i);
    if (dealt && dealt[i] != null) {
      back.classList.add('card--dealt');
      back.style.animationDelay = `${Math.round(-dealt[i])}ms`;
    } else if (drawn != null) {
      back.classList.add(i === count - 1 ? 'card--drawn' : 'card--making-room');
      back.style.animationDelay = `${Math.round(-drawn)}ms`;
    }
    return back;
  });
  const hand = el('div', {
    class: `edge-hand edge-hand--${side}`,
    data: { edgeHand: side, count, ...(drawn != null ? { drawing: '' } : {}), ...(dealt ? { dealing: '' } : {}) },
    attrs: { role: 'group', 'aria-label': `${count} carte coperte` },
  }, items);
  hand.style.setProperty('--n', count);
  hand.style.setProperty('--n-before', Math.max(count - 1, 1));
  return hand;
}

/**
 * Le carte di un altro giocatore scoperte (P85, carte calate): il suo ventaglio entra
 * dal bordo nel tavolo finché le carte si vedono intere e dritte, anche quello in
 * alto (non capovolto), un po' più aperto del ventaglio coperto. Copre per un momento
 * nome e avatar di quel giocatore. Stile in css/components/table.css.
 *
 * P93: le carte del compagno (partner_hand) usano lo stesso ventaglio, un po' più
 * grande e con le carte che si toccano per consigliargli quale giocare (`advise`).
 *
 * @param {Array<{suit: string, rank: number}>} cards le sue carte
 * @param {string} side 'top' | 'left' | 'right'
 * @param {number} seat il suo posto (data-revealed-seat, per i test)
 * @param {string} [label] etichetta per i lettori di schermo
 * @param {object|null} [advise] P93, solo per il compagno
 * @param {function} advise.onPick chiamata con la carta toccata
 * @param {object|null} advise.picked la carta che hai consigliato, segnata
 * @param {boolean} advise.disabled carte spente (per esempio senza connessione)
 * @param {string} advise.name il nome del compagno, per le etichette
 * @returns {HTMLElement}
 */
export function RevealedHand(cards, side, seat, label = 'Carte scoperte', advise = null) {
  const items = cards.map((card, i) => {
    const face = advise ? Card(card, { onPlay: advise.onPick, playable: !advise.disabled }) : Card(card);
    if (advise) {
      const picked = advise.picked && sameCard(advise.picked, card);
      face.setAttribute('aria-label', `Consiglia a ${advise.name}: ${cardName(card)}`);
      face.setAttribute('aria-pressed', picked ? 'true' : 'false');
      face.dataset.adviseCard = '';
      if (picked) {
        face.classList.add('card--advised');
        face.dataset.advised = '';
      }
    }
    face.style.setProperty('--i', i);
    return face;
  });
  const hand = el('div', {
    class: `revealed-hand revealed-hand--${side}${advise ? ' revealed-hand--partner' : ''}`,
    data: { revealedHand: side, revealedSeat: seat, count: cards.length },
    attrs: { role: 'group', 'aria-label': label },
  }, items);
  hand.style.setProperty('--n', cards.length);
  return hand;
}
