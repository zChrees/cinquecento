/**
 * Pagina di prova delle carte (P20): le 40 carte, il dorso, una mano da 5
 * giocabile e le carte coperte di un avversario. Solo per sviluppo.
 */

import { el } from '../js/utils/dom.js';
import { Card, CardBack, SUITS, cardName } from '../js/components/Card.js';
import { Hand, HiddenHand } from '../js/components/Hand.js';

const hand = [
  { suit: 'coppe', rank: 1 },
  { suit: 'coppe', rank: 10 },
  { suit: 'denari', rank: 7 },
  { suit: 'spade', rank: 9 },
  { suit: 'bastoni', rank: 3 },
];
const playable = [hand[0], hand[1], hand[4]];

const status = document.querySelector('[data-demo-status]');
document.querySelector('[data-demo-hand]').append(
  Hand(hand, { playable, onPlay: (card) => { status.textContent = `Hai giocato: ${cardName(card)}`; } }),
);

document.querySelector('[data-demo-hidden]').append(HiddenHand(3));

const deck = document.querySelector('[data-demo-deck]');
for (const suit of SUITS) {
  const row = el('div', { class: 'dev-cards__suit', data: { demoSuit: suit } });
  for (let rank = 1; rank <= 10; rank += 1) row.append(Card({ suit, rank }));
  deck.append(row);
}
deck.append(el('div', { class: 'dev-cards__suit' }, [CardBack()]));
