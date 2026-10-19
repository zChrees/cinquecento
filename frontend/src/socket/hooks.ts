/**
 * Gli hook di React per il tempo reale (passo 3 della migrazione).
 *
 * Un hook è una funzione di React che un componente chiama in cima, a ogni
 * disegno, per "agganciarsi" a qualcosa che sta fuori (qui: la connessione).
 * Il nome comincia sempre con "use". Si chiamano sempre in cima al componente,
 * mai dentro un if o un for: React li riconosce dall'ordine in cui vengono chiamati.
 *
 * Cosa contiene:
 *   useSocketEvent('home:status', handleStatus)   ascolta un evento finché il componente c'è
 *   useConnection()                               lo stato della connessione, aggiornato
 *
 * Per esempio, in un componente:
 *   const status = useConnection();              // 'connected', 'connecting', ...
 *   useSocketEvent('home:status', handleStatus);  // handleStatus(dati: HomeStatus)
 *
 * DA DOVE ARRIVANO I DATI: da client.ts, che tiene l'unica connessione della scheda.
 */

import { useEffect, useRef, useState } from 'react';
import type { RefObject } from 'react';
import type { ServerEvents } from '../types/events';
import { connect, getStatus, on, onStatus } from './client';
import type { ConnectionStatus } from './client';

/**
 * Ascolta un evento del server finché il componente è nella pagina.
 *
 * @param {E} event il nome dell'evento, per esempio 'game:state'
 * @param {(data: ServerEvents[E]) => void} listener la funzione da chiamare con i dati
 * @returns {void}
 *
 * In parole semplici:
 *   useSocketEvent('home:status', handleStatus);
 *   Quando il componente compare si mette in ascolto; quando sparisce smette da
 *   solo, così non restano ascolti "orfani" che chiamano un componente che non c'è più.
 *
 *   Il listener cambia a ogni disegno (è una funzione nuova scritta dentro il
 *   componente): per non togliere e rimettere l'ascolto ogni volta, si tiene
 *   l'ultimo in un "ref" (latest) e l'ascolto chiama sempre quello.
 */
export function useSocketEvent<E extends keyof ServerEvents>(
  event: E,
  listener: (data: ServerEvents[E]) => void,
): void {
  // latest: una scatola che React conserva tra un disegno e l'altro (useRef);
  // latest.current è l'ultimo listener ricevuto. Cambiarla non ridisegna niente.
  const latest: RefObject<(data: ServerEvents[E]) => void> = useRef(listener);
  latest.current = listener;

  /**
   * L'effetto: parte dopo che il componente è comparso nella pagina.
   * Restituisce la funzione di pulizia, che React chiama quando il componente
   * sparisce (o prima di rifare l'effetto).
   */
  function listen(): () => void {
    /** Chiama l'ultimo listener con i dati arrivati. */
    function handleEvent(data: ServerEvents[E]): void {
      latest.current(data);
    }

    // stopListening: la funzione di on() che toglie l'ascolto
    const stopListening = on(event, handleEvent);
    return stopListening;
  }

  // [event]: le "dipendenze" dell'effetto. React lo rifà solo se cambia il nome
  // dell'evento; con lo stesso nome l'ascolto resta quello di prima.
  useEffect(listen, [event]);
}

/**
 * Lo stato della connessione, che fa ridisegnare il componente quando cambia.
 *
 * @returns {ConnectionStatus} per esempio 'connected'
 *
 * In parole semplici:
 *   const status = useConnection();
 *   Apre la connessione se non c'è ancora (connect) e restituisce lo stato.
 *   Quando lo stato cambia (per esempio la rete cade) il componente si ridisegna
 *   con quello nuovo: serve a spegnere i pulsanti del tempo reale senza
 *   connessione (CLAUDE.md, "nessuna azione parte se la connessione manca").
 */
export function useConnection(): ConnectionStatus {
  // useState restituisce due cose: il valore attuale (status, all'inizio quello
  // di getStatus()) e la funzione per cambiarlo (setStatus), che fa ridisegnare
  // il componente. È l'unica destrutturazione ammessa (regole-codice.md, sezione 6).
  const [status, setStatus] = useState<ConnectionStatus>(getStatus());

  /**
   * L'effetto: apre la connessione e si mette in ascolto dei cambi di stato.
   * Rilegge subito lo stato, perché potrebbe essere cambiato tra il primo
   * disegno e questo momento.
   */
  function follow(): () => void {
    connect();
    setStatus(getStatus());
    // stopFollowing: la funzione di onStatus() che toglie l'ascolto
    const stopFollowing = onStatus(setStatus);
    return stopFollowing;
  }

  // []: nessuna dipendenza, l'effetto si fa una volta sola quando il componente compare
  useEffect(follow, []);
  return status;
}
