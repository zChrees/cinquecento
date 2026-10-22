/**
 * Il ritardo di un'animazione d'entrata, fissato quando l'elemento nasce (lotto 8c
 * della migrazione, "Rischi principali" del piano del passo 8).
 *
 * Perché serve: il tavolo Jinja (game.js) ricreava tutti gli elementi a ogni
 * ridisegno, quindi ogni volta dava all'animazione il tempo già passato come
 * ritardo negativo (P70, P119) e l'animazione riprendeva dal punto giusto. React
 * invece tiene lo stesso elemento tra un disegno e l'altro: l'animazione continua
 * da sola, e cambiarle il ritardo a metà la sposterebbe in avanti. Per questo il
 * ritardo si calcola una volta sola, al primo disegno, e poi resta quello; per far
 * ripartire un'entrata si cambia la key dell'elemento (React ne crea uno nuovo).
 *
 * Cosa contiene:
 *   useStartDelay('-200ms')   il ritardo del primo disegno
 *
 * DA DOVE ARRIVANO I DATI: il ritardo lo calcola chi disegna (Table.tsx, Trick.tsx,
 * Hand.tsx) dai millisecondi dei momenti, decisi dallo store (tableStore.ts).
 */

import { useState } from 'react';

/**
 * Il ritardo del primo disegno dell'elemento.
 *
 * @param {string} delay il ritardo di adesso, per esempio '-200ms'
 * @returns {string} il ritardo che aveva quando l'elemento è nato
 *
 * In parole semplici:
 *   const delay = useStartDelay(`${-Math.round(shownFor)}ms`);
 *   Al primo disegno restituisce delay; ai disegni dopo restituisce ancora quel
 *   primo valore, anche se delay è cambiato. useState ricorda un valore tra un
 *   disegno e l'altro: il valore iniziale lo usa solo la prima volta. useState
 *   restituisce due cose, il valore e la funzione per cambiarlo: qui serve solo il
 *   valore, perché non si cambia mai.
 */
export function useStartDelay(delay: string): string {
  const [first] = useState(delay);
  return first;
}
