/**
 * Il tavolo dentro React (passo 8 della migrazione): avvia lo store del tavolo
 * (tableStore.ts) quando la pagina compare, lo ferma quando sparisce, e
 * restituisce la sua fotografia, ridisegnando la pagina a ogni cambio.
 *
 * Cosa contiene:
 *   const table = useTable('e5f6a7b8', null);   la fotografia (TableSnapshot)
 *
 * useSyncExternalStore è l'hook di React per leggere dati che stanno fuori da
 * React (qui lo store): gli si danno la funzione per ascoltare i cambi
 * (subscribe) e quella che restituisce i dati di adesso (getSnapshot). È la
 * scelta del piano al posto di useReducer (Christian, 20/10/2026).
 *
 * DA DOVE ARRIVANO I DATI: GamePage.tsx passa il codice della partita e ?demo=,
 * presi dall'indirizzo; lo store fa il resto.
 */

import { useEffect, useSyncExternalStore } from 'react';
import { getSnapshot, startTable, subscribe } from './tableStore';
import type { TableSnapshot } from './tableStore';

/**
 * Lo stato del tavolo, per un componente React.
 *
 * @param {string} gameId il codice della partita, per esempio 'e5f6a7b8'
 * @param {string | null} demo il valore di ?demo=, oppure null fuori dalla prova
 * @param {() => void} home la funzione che torna alla home (passo 8h: navigate, senza ricaricare)
 * @returns {TableSnapshot}
 *
 * In parole semplici:
 *   const table = useTable(gameId, demo, goHome);
 *   Quando la pagina compare avvia il tavolo (startTable); quando sparisce, o se
 *   cambiano partita o prova, lo ferma (la funzione restituita da startTable).
 *   In sviluppo React (StrictMode) avvia, ferma e riavvia apposta una volta: lo
 *   store riparte da zero a ogni avvio, quindi va bene.
 */
export function useTable(gameId: string, demo: string | null, home: () => void): TableSnapshot {
  /** Effetto: avvia il tavolo e restituisce la funzione che lo ferma. */
  function start(): () => void {
    const stop = startTable(gameId, demo, home);
    return stop;
  }
  // [gameId, demo]: si rifà solo se cambiano la partita o la prova (home non cambia
  // di significato tra un disegno e l'altro: torna sempre a /)
  useEffect(start, [gameId, demo]);
  return useSyncExternalStore(subscribe, getSnapshot);
}
