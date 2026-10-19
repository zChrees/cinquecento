/**
 * Le richieste HTTP del pannello amici (contratto 2.2, P45): la versione
 * TypeScript di api() e withRequestId() di app/static/js/components/FriendsPanel.js.
 *
 * Cosa contiene:
 *   fetchFriends()               GET /friends/: la lista, le richieste, i bloccati, i contatori
 *   sendFriendRequest(username)  POST /friends/requests (con request_id)
 *   acceptRequest(id)            POST /friends/requests/<id>/accept
 *   declineRequest(id)           POST /friends/requests/<id>/decline
 *   cancelRequest(id)            DELETE /friends/requests/<id>
 *   removeFriend(id)             DELETE /friends/<id>
 *   blockUser(id)                POST /friends/blocks (con request_id)
 *   unblockUser(id)              DELETE /friends/blocks/<id>
 *
 * Per esempio:
 *   const answer = await acceptRequest(31);
 *   if (!answer.ok) { mostra(answer.error.message); }
 *
 * Come le funzioni di client.ts, non falliscono mai: la risposta è sempre
 * { ok: true, data } oppure { ok: false, error }, e senza rete 'no_connection'.
 * Le rotte restano /friends/... fino al passo 9 della migrazione, quando si
 * spostano sotto /api/ (DECISIONI.md, 19/10/2026).
 *
 * DA DOVE ARRIVANO I DATI: da Flask (app/blueprints/friends/routes.py), con il
 * cookie della sessione e il codice CSRF di /api/auth/session (client.ts).
 */

import type { BlockBody, FriendRequest, FriendsList, SentRequestBody } from '../types/api';
import type { NoConnection } from '../types/common';
import { newRequestId } from '../utils/requestId';
import { deleteJson, getJson, postJson } from './client';
import type { Answer } from './client';

// BASE: l'inizio di tutti gli indirizzi degli amici
const BASE = '/friends';

// NoBody: i dati di una richiesta che non ne manda (accetta, rifiuta): un oggetto
// vuoto, {}. Record<string, never> vuol dire "un oggetto senza nessun campo".
type NoBody = Record<string, never>;

// OFFLINE: la risposta che la pagina si dà da sola senza rete, senza provare a
// mandare la richiesta (come api() di FriendsPanel.js)
const OFFLINE: NoConnection = {
  ok: false,
  error: { code: 'no_connection', message: 'Sei offline: riprova quando torna la connessione.' },
};

// pendingIds: per ogni azione (per esempio 'request:Giulia') il request_id del
// tentativo ancora senza risposta. Un Map è una tabella chiave → valore.
const pendingIds: Map<string, string> = new Map();

/**
 * Manda una richiesta che crea qualcosa, con il suo codice anti-doppione.
 *
 * @param {string} action il nome dell'azione, per esempio 'request:Giulia' o 'block:31'
 * @param {(requestId: string) => Promise<Answer<T>>} request la funzione che manda
 *   la richiesta con il codice ricevuto. In C sarebbe un puntatore a funzione.
 * @returns {Promise<Answer<T>>} la risposta
 *
 * In parole semplici:
 *   withRequestId('block:31', sendBlock)
 *   Il codice resta lo stesso per tutti i tentativi della stessa azione finché il
 *   server non ha risposto (contratto 1.3): se la rete cade a metà, il tentativo
 *   dopo rimanda lo stesso codice e il server non crea un doppione. Con una
 *   risposta del server (riuscita o rifiutata) il codice si dimentica.
 */
async function withRequestId<T>(action: string, request: (requestId: string) => Promise<Answer<T>>): Promise<Answer<T>> {
  let requestId = pendingIds.get(action);
  if (requestId === undefined) {
    requestId = newRequestId();
    pendingIds.set(action, requestId);
  }
  const answer = await request(requestId);
  if (answer.ok || answer.error.code !== 'no_connection') {
    pendingIds.delete(action);
  }
  return answer;
}

/**
 * La lista degli amici.
 *
 * In parole semplici:
 *   const answer = await fetchFriends();   →   answer.data.friends, requests_in, ...
 */
export function fetchFriends(): Promise<Answer<FriendsList>> {
  return getJson<FriendsList>(`${BASE}/`);
}

/**
 * Manda una richiesta di amicizia a uno username esatto (D33).
 *
 * @param {string} username il nome scritto nella casella, così com'è
 * @returns {Promise<Answer<FriendRequest>>} la richiesta mandata, con il nome giusto
 */
export async function sendFriendRequest(username: string): Promise<Answer<FriendRequest>> {
  if (!navigator.onLine) {
    return OFFLINE;
  }

  /** La richiesta vera, con il codice anti-doppione. */
  function send(requestId: string): Promise<Answer<FriendRequest>> {
    const body: SentRequestBody = { request_id: requestId, username: username };
    return postJson<SentRequestBody, FriendRequest>(`${BASE}/requests`, body);
  }

  return withRequestId<FriendRequest>(`request:${username}`, send);
}

/** Accetta la richiesta ricevuta da un utente. */
export async function acceptRequest(userId: number): Promise<Answer<null>> {
  if (!navigator.onLine) {
    return OFFLINE;
  }
  const body: NoBody = {};
  return postJson<NoBody, null>(`${BASE}/requests/${userId}/accept`, body);
}

/** Rifiuta la richiesta ricevuta da un utente. */
export async function declineRequest(userId: number): Promise<Answer<null>> {
  if (!navigator.onLine) {
    return OFFLINE;
  }
  const body: NoBody = {};
  return postJson<NoBody, null>(`${BASE}/requests/${userId}/decline`, body);
}

/** Annulla la richiesta mandata a un utente. */
export async function cancelRequest(userId: number): Promise<Answer<null>> {
  if (!navigator.onLine) {
    return OFFLINE;
  }
  return deleteJson<null>(`${BASE}/requests/${userId}`);
}

/** Toglie un amico (tutti e due spariscono dalla lista dell'altro). */
export async function removeFriend(userId: number): Promise<Answer<null>> {
  if (!navigator.onLine) {
    return OFFLINE;
  }
  return deleteJson<null>(`${BASE}/${userId}`);
}

/** Blocca un utente: niente più richieste né messaggi, e l'amicizia finisce. */
export async function blockUser(userId: number): Promise<Answer<null>> {
  if (!navigator.onLine) {
    return OFFLINE;
  }

  /** La richiesta vera, con il codice anti-doppione. */
  function send(requestId: string): Promise<Answer<null>> {
    const body: BlockBody = { request_id: requestId, user_id: userId };
    return postJson<BlockBody, null>(`${BASE}/blocks`, body);
  }

  return withRequestId<null>(`block:${userId}`, send);
}

/** Sblocca un utente. */
export async function unblockUser(userId: number): Promise<Answer<null>> {
  if (!navigator.onLine) {
    return OFFLINE;
  }
  return deleteJson<null>(`${BASE}/blocks/${userId}`);
}
