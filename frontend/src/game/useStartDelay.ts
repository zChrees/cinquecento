/**
 * Il ritardo di un'animazione, che resta fermo finché l'animazione è la stessa
 * (lotti 8c e 8d della migrazione, "Rischi principali" del piano del passo 8).
 *
 * Perché serve: il tavolo di prima (Jinja, tolto al 9a) ricreava tutti gli elementi a ogni
 * ridisegno, quindi ogni volta dava all'animazione il tempo già passato come
 * ritardo negativo (P70, P119) e l'animazione riprendeva dal punto giusto. React
 * invece tiene lo stesso elemento tra un disegno e l'altro: l'animazione continua
 * da sola, e cambiarle il ritardo a metà la sposterebbe in avanti. Per questo il
 * ritardo si tiene quello del disegno in cui l'animazione è cominciata.
 *
 * Come riconosce "la stessa animazione": chi disegna passa sempre il ritardo
 * calcolato da quando l'animazione è partita (per esempio -200 ms vuol dire "partita
 * 200 ms fa", +300 ms "parte tra 300 ms"). Adesso + ritardo è quindi l'ora di
 * partenza, che per la stessa animazione resta uguale a ogni disegno; un'ora di
 * partenza diversa vuol dire un'animazione nuova (per esempio una carta già in mano
 * che fa spazio a una pescata), e il ritardo si prende di nuovo.
 *
 * Cosa contiene:
 *   useStartDelay('-200ms')   il ritardo da scrivere nello stile
 *
 * DA DOVE ARRIVANO I DATI: il ritardo lo calcola chi disegna (Table.tsx, Trick.tsx,
 * Hand.tsx, CardView.tsx) dai millisecondi dei momenti, decisi dallo store (tableStore.ts).
 */

import { useRef } from 'react';

// SAME_START_MS: due ore di partenza più vicine di così sono la stessa animazione
// (i ritardi sono arrotondati al millisecondo, e tra il calcolo del ritardo e
// questo controllo passa un attimo)
const SAME_START_MS = 50;

// Remembered: il ritardo ricordato e l'ora di partenza della sua animazione
interface Remembered {
  // il ritardo scritto nello stile, per esempio '-200ms'; undefined se nessuno
  delay: string | undefined;
  // performance.now() della partenza, oppure null se nessuna animazione
  start: number | null;
}

/**
 * Il ritardo dell'animazione da scrivere nello stile.
 *
 * @param {string | undefined} delay il ritardo di adesso, per esempio '-200ms'; undefined se l'elemento non si anima
 * @returns {string | undefined} il ritardo del disegno in cui l'animazione è cominciata
 *
 * In parole semplici:
 *   const delay = useStartDelay(`${-Math.round(shownFor)}ms`);
 *   Al primo disegno di un'animazione restituisce delay; ai disegni dopo, finché
 *   l'ora di partenza è la stessa, restituisce ancora quel primo valore. useRef è
 *   una "scatola" che React tiene tra un disegno e l'altro dello stesso elemento:
 *   qui ricorda ritardo e ora di partenza.
 */
export function useStartDelay(delay: string | undefined): string | undefined {
  const remembered = useRef<Remembered>({ delay: undefined, start: null });
  if (delay === undefined) {
    remembered.current = { delay: undefined, start: null };
    return undefined;
  }
  // start: l'ora di partenza (parseFloat('-200ms') dà -200: legge il numero all'inizio del testo)
  const start = performance.now() + parseFloat(delay);
  const before = remembered.current.start;
  if (before !== null && Math.abs(start - before) < SAME_START_MS) {
    return remembered.current.delay;
  }
  remembered.current = { delay: delay, start: start };
  return delay;
}
