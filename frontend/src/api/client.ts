/**
 * Le richieste HTTP della SPA (passo 4 della migrazione): le rotte JSON di Flask
 * sotto /api/ (DECISIONI.md, 19/10/2026).
 *
 * Cosa contiene:
 *   loadSession()              GET /api/auth/session, una volta sola per pagina
 *   getJson(indirizzo)         una richiesta GET che risponde in JSON (per esempio /stats/me)
 *   postJson(indirizzo, dati)  una richiesta POST in JSON con il codice CSRF
 *
 * Per esempio:
 *   const answer = await postJson<LoginBody, AuthDone>('/api/auth/login', body);
 *   if (answer.ok) { window.location.assign(answer.data.redirect); }
 *
 * Come send() di socket/client.ts, queste funzioni non falliscono mai: la
 * risposta è sempre { ok: true, data } oppure { ok: false, error }. Senza rete
 * l'errore è 'no_connection' (NoConnection), con un messaggio da mostrare.
 *
 * DA DOVE ARRIVANO I DATI: da Flask (app/blueprints/auth/api.py, e le altre rotte
 * /api/ dei passi dopo), sullo stesso indirizzo della pagina: il cookie della
 * sessione va da solo. In sviluppo il proxy di Vite gira /api a Flask.
 */

import type { ErrorResponse, NoConnection, OkWithData } from '../types/common';
import type { Session } from '../types/api';

// Answer<T>: quello che restituiscono le funzioni di questo file: i dati di tipo T,
// oppure l'errore del server, oppure "niente connessione"
export type Answer<T> = OkWithData<T> | ErrorResponse | NoConnection;

// NO_CONNECTION: la risposta quando la richiesta non arriva al server
const NO_CONNECTION: NoConnection = {
  ok: false,
  error: { code: 'no_connection', message: 'Connessione assente: riprova quando torna la connessione.' },
};

// SERVER_ERROR: la risposta quando il server risponde con qualcosa che non è il
// JSON del contratto (per esempio una pagina di errore)
const SERVER_ERROR: ErrorResponse = {
  ok: false,
  error: { code: 'server_error', message: 'Errore del server: riprova tra poco.' },
};

// sessionRequest: la richiesta di GET /api/auth/session, fatta una volta sola per
// pagina; null finché nessuno l'ha chiesta. Si tiene la Promise (la risposta che
// arriverà), così chi la chiede mentre è ancora in viaggio aspetta la stessa.
let sessionRequest: Promise<Answer<Session>> | null = null;

/**
 * Legge una risposta di Flask come JSON del contratto.
 *
 * @param {Response} response la risposta di fetch
 * @returns {Promise<Answer<T>>}
 *
 * In parole semplici:
 *   readAnswer(response)
 *   Se il corpo è un oggetto con il campo ok (la forma del contratto, 1.2) lo
 *   restituisce così com'è, anche se è un errore (per esempio 400 con i campi
 *   sbagliati); altrimenti restituisce SERVER_ERROR.
 *
 *   unknown: "un valore di cui non si sa ancora il tipo". A differenza di any,
 *   TypeScript obbliga a controllarlo prima di usarlo.
 */
async function readAnswer<T>(response: Response): Promise<Answer<T>> {
  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    // il corpo non è JSON (per esempio la pagina 500 in HTML)
    return SERVER_ERROR;
  }
  if (typeof body !== 'object' || body === null || !('ok' in body)) {
    return SERVER_ERROR;
  }
  // Qui il corpo ha la forma del contratto: lo controlla il server, e i tipi di
  // types/ copiano il contratto (test_tipi.py). "as" dice a TypeScript di
  // fidarsi: è l'unico punto in cui un dato arriva da fuori senza un tipo, come
  // quando in C si legge una struct da un file.
  return body as Answer<T>;
}

/**
 * Chiede la sessione al server, una volta sola per pagina.
 *
 * @returns {Promise<Answer<Session>>}
 *
 * In parole semplici:
 *   const answer = await loadSession();
 *   La prima volta fa GET /api/auth/session; le volte dopo restituisce la stessa
 *   risposta. Dentro c'è il codice CSRF che postJson manda con ogni POST, e i
 *   messaggi lasciati da un'altra pagina.
 */
export function loadSession(): Promise<Answer<Session>> {
  if (sessionRequest !== null) {
    return sessionRequest;
  }

  /**
   * La richiesta vera: fetch, poi la lettura della risposta. Se non riesce
   * (niente rete, errore del server) si dimentica, così la volta dopo si riprova.
   */
  async function request(): Promise<Answer<Session>> {
    let answer: Answer<Session> = NO_CONNECTION;
    try {
      const response = await fetch('/api/auth/session', { headers: { Accept: 'application/json' } });
      answer = await readAnswer<Session>(response);
    } catch {
      // fetch fallisce solo se la richiesta non parte o non arriva (niente rete)
      answer = NO_CONNECTION;
    }
    if (!answer.ok) {
      sessionRequest = null;
    }
    return answer;
  }

  sessionRequest = request();
  return sessionRequest;
}

/**
 * Manda una richiesta POST in JSON con il codice CSRF.
 *
 * @param {string} url l'indirizzo, per esempio '/api/auth/login'
 * @param {B} body i dati da mandare
 * @returns {Promise<Answer<T>>} la risposta
 *
 * In parole semplici:
 *   const answer = await postJson<LoginBody, AuthDone>('/api/auth/login', body);
 *   Prende il codice CSRF dalla sessione (loadSession) e lo mette
 *   nell'intestazione X-CSRFToken, come vuole Flask-WTF (contratto 1.5).
 *   <B, T>: due segnaposto per i tipi, B quello dei dati mandati e T quello dei
 *   dati della risposta; li sceglie chi chiama.
 */
export async function postJson<B, T>(url: string, body: B): Promise<Answer<T>> {
  const session = await loadSession();
  if (!session.ok) {
    return session;
  }
  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
        'X-CSRFToken': session.data.csrf_token,
      },
      body: JSON.stringify(body),
    });
    return await readAnswer<T>(response);
  } catch {
    return NO_CONNECTION;
  }
}

/**
 * Chiede dei dati al server con una richiesta GET.
 *
 * @param {string} url l'indirizzo, per esempio '/stats/me'
 * @returns {Promise<Answer<T>>} la risposta
 *
 * In parole semplici:
 *   const answer = await getJson<Stats>('/stats/me');
 *   Senza rete risponde subito NO_CONNECTION, senza provarci (come fetchStats di
 *   StatsPanel.js); T è il tipo dei dati della risposta, scelto da chi chiama.
 */
export async function getJson<T>(url: string): Promise<Answer<T>> {
  if (!navigator.onLine) {
    return NO_CONNECTION;
  }
  try {
    const response = await fetch(url, { headers: { Accept: 'application/json' } });
    return await readAnswer<T>(response);
  } catch {
    return NO_CONNECTION;
  }
}
