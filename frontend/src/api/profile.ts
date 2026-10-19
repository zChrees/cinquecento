/**
 * Le richieste HTTP della pagina delle impostazioni (passo 6 della migrazione):
 * le rotte JSON di app/blueprints/profile/api.py.
 *
 * Cosa contiene:
 *   fetchAvatars()             GET /api/profile/avatars: gli avatar che si possono scegliere
 *   saveAvatar(codice)         POST /api/profile/avatar ('' = l'iniziale del nome)
 *   deleteAccount(password)    POST /api/profile/delete
 *
 * Per esempio:
 *   const answer = await saveAvatar('re_coppe');
 *   if (answer.ok) { window.location.assign(answer.data.redirect); }
 *
 * Come le funzioni di client.ts, non falliscono mai: la risposta è sempre
 * { ok: true, data } oppure { ok: false, error }, e senza rete 'no_connection'.
 *
 * DA DOVE ARRIVANO I DATI: da Flask, con il cookie della sessione e il codice CSRF
 * di /api/auth/session (client.ts).
 */

import type { AuthDone, AvatarBody, AvatarList, DeleteAccountBody } from '../types/api';
import { getJson, postJson } from './client';
import type { Answer } from './client';

/**
 * Gli avatar che si possono scegliere, con il loro nome.
 *
 * In parole semplici:
 *   const answer = await fetchAvatars();   →   answer.data.avatars
 *   Un solo elenco, quello di avatars.py: la pagina non ne tiene una copia.
 */
export function fetchAvatars(): Promise<Answer<AvatarList>> {
  return getJson<AvatarList>('/api/profile/avatars');
}

/**
 * Salva l'avatar scelto.
 *
 * @param {string} code il codice, per esempio 're_coppe', oppure '' per l'iniziale
 * @returns {Promise<Answer<AuthDone>>} se va bene, l'indirizzo da ricaricare
 */
export function saveAvatar(code: string): Promise<Answer<AuthDone>> {
  const body: AvatarBody = { avatar: code };
  return postJson<AvatarBody, AuthDone>('/api/profile/avatar', body);
}

/**
 * Cancella l'account, dopo che il server ha controllato la password.
 *
 * @param {string} password la password scritta nella finestra di conferma
 * @returns {Promise<Answer<AuthDone>>} se va bene, l'indirizzo della home
 */
export function deleteAccount(password: string): Promise<Answer<AuthDone>> {
  const body: DeleteAccountBody = { password: password };
  return postJson<DeleteAccountBody, AuthDone>('/api/profile/delete', body);
}
