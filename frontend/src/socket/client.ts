/**
 * La connessione in tempo reale della SPA (passo 3 della migrazione): la
 * traduzione in TypeScript di app/static/js/core/socket.js (P23, contratto 1.4),
 * con gli stessi comportamenti e in più i tipi del contratto (types/events.ts).
 *
 * Cosa contiene:
 *   connect()                     apre la connessione, una sola per scheda
 *   getStatus(), isConnected()    lo stato della connessione adesso
 *   onStatus(listener)            avvisa a ogni cambio di stato
 *   on('game:state', listener)    ascolta un evento del server
 *   send('game:join', { ... })    manda un evento e aspetta la risposta
 *
 * Per esempio:
 *   connect();
 *   const stop = on('home:status', handleStatus);   // handleStatus(dati: HomeStatus)
 *   const answer = await send('queue:join', { request_id: id, mode: '1v1', target_score: 500 });
 *   if (answer.ok) { ... answer.data è un QueueStatus ... }
 *   stop();                                         // smette di ascoltare
 *
 * I componenti React non lo usano direttamente: passano dagli hook di
 * hooks.ts (useSocketEvent, useConnection), che smettono di ascoltare da soli.
 *
 * DA DOVE ARRIVANO I DATI: dal server Flask-SocketIO (app/sockets/), sullo
 * stesso indirizzo della pagina: in sviluppo il proxy di Vite gira /socket.io a
 * Flask (vite.config.ts). Si collega solo chi ha fatto il login: il cookie della
 * sessione va con la connessione (withCredentials).
 *
 * Cosa NON c'è rispetto a core/socket.js: l'avviso in cima alla pagina
 * ("Connessione persa: riprovo…", P33). È un pezzo dell'interfaccia: si rifà
 * come componente React con la cornice delle pagine (passo 5), leggendo lo stato
 * da useConnection.
 */

import { io } from 'socket.io-client';
import type { Socket } from 'socket.io-client';
import type { NoConnection } from '../types/common';
import type { ClientAnswers, ClientEvents, ServerEvents } from '../types/events';

// ConnectionStatus: lo stato della connessione.
//   'connecting'     si sta collegando, o ricollegando dopo una caduta
//   'connected'      collegata: si può mandare
//   'disconnected'   chiusa dal server, e non si riprova (per esempio "Esci" da un'altra scheda)
//   'not_logged_in'  il server l'ha rifiutata perché manca il login (contratto 1.4)
export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'not_logged_in';

// NoConnection (types/common.ts): la risposta che send dà da solo, senza chiedere
// al server, quando la connessione manca o il server non risponde in tempo.

// ANSWER_TIMEOUT_MS: quanto aspettare la risposta del server (10 secondi, come core/socket.js)
const ANSWER_TIMEOUT_MS = 10000;

// NOT_LOGGED_IN: il messaggio con cui il server rifiuta chi non ha il login (contratto 1.4)
const NOT_LOGGED_IN = 'not_logged_in';

// NO_CONNECTION e NO_ANSWER: le due risposte "fatte in casa" di send
const NO_CONNECTION: NoConnection = {
  ok: false,
  error: { code: 'no_connection', message: 'Connessione assente: riprova quando torna la connessione.' },
};
const NO_ANSWER: NoConnection = {
  ok: false,
  error: { code: 'no_connection', message: 'Il server non risponde: riprova tra poco.' },
};

// StatusListener: una funzione da chiamare a ogni cambio di stato. In C
// sarebbe un puntatore a funzione: void (*listener)(ConnectionStatus status)
export type StatusListener = (status: ConnectionStatus) => void;

// I TIPI DEGLI EVENTI stanno nelle funzioni on() e send() qui sotto, che sono
// quelle che usano i componenti: un nome sbagliato o un dato della forma
// sbagliata è un errore di TypeScript lì. La connessione della libreria
// (Socket) resta "senza tipi degli eventi": con un nome di evento generico (E)
// la libreria non riesce a dedurre da sola quale funzione si aspetta, e darle
// i nostri elenchi non basta (prova fatta il 19/10/2026 con socket.io-client 4.8.1).

// socket: la connessione di Socket.IO; null finché connect() non la apre.
// Variabili del modulo: in tutta la scheda c'è una sola connessione, come in
// core/socket.js, anche se la usano più componenti.
let socket: Socket | null = null;
// status: lo stato attuale
let status: ConnectionStatus = 'disconnected';
// statusListeners: le funzioni da avvisare a ogni cambio di stato. Un Set è un
// elenco senza doppioni: la stessa funzione aggiunta due volte c'è una volta sola.
const statusListeners: Set<StatusListener> = new Set();

/**
 * Cambia lo stato e avvisa chi ascolta.
 *
 * @param {ConnectionStatus} next il nuovo stato
 * @returns {void}
 *
 * In parole semplici:
 *   setStatus('connected')
 *   Se lo stato è già quello non fa niente (niente avvisi doppi); altrimenti
 *   lo salva e chiama ogni funzione di statusListeners con il nuovo stato.
 */
function setStatus(next: ConnectionStatus): void {
  if (next === status) {
    return;
  }
  status = next;
  // for...of: un giro per ogni elemento del Set (che non ha indici come un array)
  for (const listener of statusListeners) {
    listener(status);
  }
}

/**
 * Lo stato da mostrare quando la connessione si chiude o non riesce.
 *
 * @param {Socket} current la connessione
 * @returns {ConnectionStatus}
 *
 * In parole semplici:
 *   statusAfterClose(socket)
 *   current.active vale true se Socket.IO riproverà da solo (la rete è caduta):
 *   allora si sta "ricollegando". Vale false se la connessione l'ha chiusa il
 *   server apposta: allora è "scollegata" e non si riprova.
 */
function statusAfterClose(current: Socket): ConnectionStatus {
  if (current.active) {
    return 'connecting';
  }
  return 'disconnected';
}

/**
 * Apre la connessione, una volta sola per scheda, e la restituisce.
 *
 * @returns {Socket}
 *
 * In parole semplici:
 *   connect()
 *   La prima volta crea la connessione con io() e le dice cosa fare quando si
 *   collega, si scollega o non riesce a collegarsi; le volte dopo restituisce
 *   quella già aperta. Si può chiamare da più parti senza aprirne due.
 */
export function connect(): Socket {
  if (socket !== null) {
    return socket;
  }
  setStatus('connecting');
  // current: la connessione nuova. io() senza indirizzo si collega allo stesso
  // sito della pagina; withCredentials manda anche il cookie del login.
  const current: Socket = io({ withCredentials: true });
  socket = current;

  /** Collegata (anche dopo una caduta): il server rimanda lo stato da solo. */
  function handleConnect(): void {
    setStatus('connected');
  }

  /** Scollegata: si riprova da soli solo se la rete è caduta. */
  function handleDisconnect(): void {
    setStatus(statusAfterClose(current));
  }

  /**
   * Collegamento non riuscito. Se il server ci rifiuta perché manca il login,
   * Socket.IO non riprova da solo: lo stato diventa 'not_logged_in'.
   */
  function handleConnectError(err: Error): void {
    if (err.message === NOT_LOGGED_IN) {
      setStatus('not_logged_in');
    } else {
      setStatus(statusAfterClose(current));
    }
  }

  current.on('connect', handleConnect);
  current.on('disconnect', handleDisconnect);
  current.on('connect_error', handleConnectError);
  return current;
}

/**
 * Lo stato attuale della connessione.
 *
 * In parole semplici:
 *   getStatus()  →  per esempio 'connected'
 */
export function getStatus(): ConnectionStatus {
  return status;
}

/**
 * Dice se adesso si può mandare.
 *
 * In parole semplici:
 *   isConnected()  →  true solo con lo stato 'connected'
 */
export function isConnected(): boolean {
  return status === 'connected';
}

/**
 * Avvisa a ogni cambio di stato.
 *
 * @param {StatusListener} listener la funzione da chiamare con il nuovo stato
 * @returns {() => void} la funzione per smettere di avvisare
 *
 * In parole semplici:
 *   const stop = onStatus(handleStatus);  ...  stop();
 *   Aggiunge listener all'elenco; la funzione restituita lo toglie.
 *   () => void è il tipo di "una funzione senza parametri che non restituisce
 *   niente", come void (*stop)(void) in C.
 */
export function onStatus(listener: StatusListener): () => void {
  statusListeners.add(listener);

  function stop(): void {
    statusListeners.delete(listener);
  }

  return stop;
}

/**
 * Ascolta un evento del server.
 *
 * @param {E} event il nome dell'evento, per esempio 'game:state'
 * @param {(data: ServerEvents[E]) => void} listener la funzione da chiamare con i dati
 * @returns {() => void} la funzione per smettere di ascoltare
 *
 * In parole semplici:
 *   const stop = on('game:state', handleView);
 *   Ogni volta che arriva game:state chiama handleView(vista).
 *
 *   <E extends keyof ServerEvents>: E è un segnaposto per il nome dell'evento,
 *   e "extends keyof ServerEvents" vuol dire "solo uno dei nomi dell'elenco
 *   ServerEvents". Così TypeScript sa che con 'game:state' i dati sono una
 *   GameView, e rifiuta un nome che non esiste (per esempio 'game:stato').
 */
export function on<E extends keyof ServerEvents>(event: E, listener: (data: ServerEvents[E]) => void): () => void {
  const current = connect();
  // name: il nome dell'evento come semplice testo, la forma che la libreria
  // accetta (vedi il commento su socket in cima al file). Il controllo dei tipi
  // l'ha già fatto TypeScript su event e listener.
  const name: string = event;
  current.on(name, listener);

  function stop(): void {
    current.off(name, listener);
  }

  return stop;
}

/**
 * Manda un evento al server e aspetta la risposta.
 *
 * @param {E} event il nome dell'evento, per esempio 'game:play_card'
 * @param {ClientEvents[E]} data i dati, con la forma che vuole quell'evento
 * @returns {Promise<ClientAnswers[E] | NoConnection>} la risposta
 *
 * In parole semplici:
 *   const answer = await send('game:play_card', { game_id: id, version: v, card: c });
 *   Non fallisce mai: la risposta è sempre { ok: true, ... } oppure
 *   { ok: false, error }. Senza connessione non manda niente e risponde subito
 *   NO_CONNECTION (nessuna azione parte se la connessione manca); se il server
 *   non risponde entro 10 secondi risponde NO_ANSWER.
 *
 *   Promise: una risposta che arriverà più tardi. "await" aspetta che arrivi,
 *   senza bloccare la pagina (come un callback chiamato quando ha finito).
 */
export function send<E extends keyof ClientEvents>(
  event: E,
  data: ClientEvents[E],
): Promise<ClientAnswers[E] | NoConnection> {
  if (socket === null || !isConnected()) {
    return Promise.resolve(NO_CONNECTION);
  }
  const current: Socket = socket;
  // name: il nome come semplice testo, come in on()
  const name: string = event;

  /**
   * Il lavoro della Promise: manda l'evento e, quando arriva la risposta (o
   * passa il tempo), chiama resolve con il risultato.
   */
  function waitForAnswer(resolve: (answer: ClientAnswers[E] | NoConnection) => void): void {
    /** La risposta del server (ack); err non è null se il tempo è scaduto. */
    function handleAnswer(err: Error | null, answer: ClientAnswers[E]): void {
      if (err !== null) {
        resolve(NO_ANSWER);
      } else {
        resolve(answer);
      }
    }

    current.timeout(ANSWER_TIMEOUT_MS).emit(name, data, handleAnswer);
  }

  return new Promise(waitForAnswer);
}
