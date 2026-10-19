/**
 * Le carte, come le descrive il contratto (docs/CONTRATTO-SOCKET.md, 1.1).
 *
 * Cosa contiene:
 *   Suit   il seme, per esempio 'coppe'
 *   Rank   il valore, da 1 (Asso) a 10 (Re)
 *   Card   una carta: { suit: 'coppe', rank: 10 }
 *
 * DA DOVE ARRIVANO I DATI: dal server, dentro la vista di gioco (view.ts) e
 * negli eventi del tavolo (events.ts). La pagina non inventa mai carte: usa
 * quelle che riceve.
 *
 * Un "type" con la | (per esempio 'denari' | 'coppe') vuol dire "uno di questi
 * valori e nessun altro", come un enum del C: se il server mandasse 'cuori',
 * TypeScript lo segnalerebbe negli esempi controllati da test_tipi.py.
 */

// Suit: i quattro semi delle carte siciliane (nomi propri del gioco, in italiano)
export type Suit = 'denari' | 'coppe' | 'spade' | 'bastoni';

// Rank: il valore della carta. 1 = Asso, da 2 a 7 le carte numerate,
// 8 = Fante, 9 = Cavallo, 10 = Re
export type Rank = 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10;

// Card: una carta. È la struct del C con due campi:
//   struct carta { char *suit; int rank; };
// Sono gli stessi valori degli attributi data-suit e data-rank delle carte
// disegnate nella pagina (P20).
export interface Card {
  // il seme, per esempio 'coppe'
  suit: Suit;
  // il valore, per esempio 10 (il Re)
  rank: Rank;
}
