/**
 * Le richieste HTTP della home.
 *
 * Cosa contiene:
 *   fetchOnlineCount()   GET /api/online: quanti utenti sono collegati (anche senza login, P82)
 *   fetchDemoStatus()    l'avviso "Hai una partita in corso" finto di ?demo=rientro
 *   DEMO_RESUME          il valore di ?demo= che lo chiede ('rientro')
 *
 * Per esempio:
 *   const answer = await fetchOnlineCount();
 *   if (answer.ok) { setOnline(answer.data.online_count); }
 *
 * Come le funzioni di client.ts, fetchOnlineCount non fallisce mai: la risposta è
 * sempre { ok: true, data } oppure { ok: false, error }, e senza rete 'no_connection'.
 *
 * DA DOVE ARRIVANO I DATI: GET /api/online da app/blueprints/main/routes.py (contratto
 * 5.1); i dati finti da app/static/dev/home_esempio.json, che c'è solo in sviluppo
 * e nei test (in main non ci va, P136).
 */

import type { Online } from '../types/api';
import type { HomeStatus } from '../types/events';
import { getJson } from './client';
import type { Answer } from './client';

// DEMO_RESUME: ?demo=rientro mostra l'avviso di rientro con i dati finti
// (i valori ammessi sono DEMO_STATES di app/blueprints/main/routes.py)
export const DEMO_RESUME = 'rientro';

// DEMO_URL e DEMO_KEY: il file dei dati finti della home e la voce con la
// partita in corso (le chiavi del file sono i nomi dei messaggi del contratto)
const DEMO_URL = '/static/dev/home_esempio.json';
const DEMO_KEY = 'home:status con partita in corso';

/**
 * Quanti utenti sono collegati adesso.
 *
 * @returns {Promise<Answer<Online>>}
 *
 * In parole semplici:
 *   const answer = await fetchOnlineCount();   →   answer.data.online_count, per esempio 3
 *   È la sola richiesta che funziona anche senza login: la usa la home di chi
 *   non ha fatto il login, che non si collega al tempo reale e quindi non riceve
 *   home:status.
 */
export function fetchOnlineCount(): Promise<Answer<Online>> {
  return getJson<Online>('/api/online');
}

/**
 * Lo stato finto della home con una partita in corso, per ?demo=rientro.
 *
 * @returns {Promise<HomeStatus | null>} lo stato, oppure null se il file non arriva
 *
 * In parole semplici:
 *   const status = await fetchDemoStatus();   →   { online_count: 24, resume: { game_id: 'a1b2c3d4', ... } }
 *   Serve a vedere l'avviso "Hai una partita in corso" senza una partita vera.
 *   Il file non ha la forma { ok, data } del contratto (è un elenco di esempi),
 *   per questo non passa da getJson.
 */
export async function fetchDemoStatus(): Promise<HomeStatus | null> {
  // file: il contenuto del file, di tipo ancora sconosciuto (unknown: va
  // controllato prima di usarlo, a differenza di any)
  let file: unknown = null;
  try {
    const response = await fetch(DEMO_URL, { headers: { Accept: 'application/json' } });
    if (!response.ok) {
      return null;
    }
    file = await response.json();
  } catch {
    // niente rete, oppure il file non è JSON
    return null;
  }
  if (typeof file !== 'object' || file === null || !(DEMO_KEY in file)) {
    return null;
  }
  // "as" dice a TypeScript di fidarsi: il file è un esempio del contratto e
  // tests/frontend/test_tipi.py lo confronta con i tipi di types/ (come readAnswer
  // di client.ts, l'unico altro punto in cui un dato arriva da fuori senza tipo)
  const examples = file as Record<string, HomeStatus>;
  return examples[DEMO_KEY];
}
