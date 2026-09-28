/**
 * Connessione in tempo reale della pagina (P23, contratto 1.4).
 *
 *   import { connect, send, on, onStatus } from '../core/socket.js';
 *   connect();                                   // una connessione per scheda
 *   onStatus((status) => render(...));           // 'connecting' | 'connected' | 'disconnected' | 'not_logged_in'
 *   on(EVENTS.GAME_STATE, (view) => render(view));
 *   const answer = await send(EVENTS.GAME_JOIN, { game_id });   // sempre {ok, data} o {ok: false, error}
 *
 * - Riconnessione automatica (Socket.IO); dopo il rientro il server rimanda lo stato.
 * - Senza connessione `send` non manda niente e risponde subito con un errore da
 *   mostrare: nessuna azione parte se la connessione manca.
 * - Chi non ha fatto il login viene rifiutato dal server: lo stato diventa
 *   'not_logged_in' e non si riprova.
 */

import { io } from '../vendor/socket.io.min.js';
import { NOT_LOGGED_IN } from './events.js';

const ANSWER_TIMEOUT_MS = 10000;

const NO_CONNECTION = Object.freeze({
  ok: false,
  error: { code: 'no_connection', message: 'Connessione assente: riprova quando torna la connessione.' },
});
const NO_ANSWER = Object.freeze({
  ok: false,
  error: { code: 'no_connection', message: 'Il server non risponde: riprova tra poco.' },
});

let socket = null;
let status = 'disconnected';
const statusListeners = new Set();

function setStatus(next) {
  if (next === status) return;
  status = next;
  statusListeners.forEach((listener) => listener(status));
}

/** Apre la connessione (una volta sola per scheda) e la restituisce. */
export function connect() {
  if (socket) return socket;
  setStatus('connecting');
  socket = io({ withCredentials: true });
  socket.on('connect', () => setStatus('connected'));
  socket.on('disconnect', () => setStatus(socket.active ? 'connecting' : 'disconnected'));
  socket.on('connect_error', (err) => {
    // Rifiuto del server (niente login): Socket.IO non riprova da solo.
    if (err && err.message === NOT_LOGGED_IN) setStatus(NOT_LOGGED_IN);
    else setStatus(socket.active ? 'connecting' : 'disconnected');
  });
  return socket;
}

/** Stato attuale della connessione. */
export function getStatus() {
  return status;
}

export function isConnected() {
  return status === 'connected';
}

/** Chiama `listener(status)` a ogni cambio di stato; restituisce la funzione per smettere. */
export function onStatus(listener) {
  statusListeners.add(listener);
  return () => statusListeners.delete(listener);
}

/** Ascolta un evento del server; restituisce la funzione per smettere. */
export function on(event, listener) {
  connect().on(event, listener);
  return () => socket.off(event, listener);
}

/**
 * Manda un evento e aspetta la risposta del server.
 * Non rifiuta mai: in ogni caso risolve con {ok: true, data} o {ok: false, error}.
 */
export function send(event, data = {}) {
  if (!socket || !isConnected()) return Promise.resolve(NO_CONNECTION);
  return new Promise((resolve) => {
    socket.timeout(ANSWER_TIMEOUT_MS).emit(event, data, (err, answer) => {
      resolve(err ? NO_ANSWER : answer);
    });
  });
}
