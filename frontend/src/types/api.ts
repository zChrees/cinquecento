/**
 * Le richieste HTTP in JSON (docs/CONTRATTO-SOCKET.md, sezione 2 e 5.1).
 * Esempi: app/static/dev/statistiche_esempio.json e amici_esempio.json
 * ("GET /friends/"), controllati da tests/frontend/test_tipi.py.
 *
 * Cosa contiene:
 *   Stats, ModeRating             GET /stats/me
 *   FriendsList, Friend, ...      GET /friends/
 *   SentRequestBody, BlockBody    i corpi di POST /friends/requests e /friends/blocks
 *   Online                        GET /online
 *
 * DA DOVE ARRIVANO I DATI: le rotte dei blueprint stats, friends e main di Flask.
 * Ogni risposta ha la forma di common.ts: OkWithData<Stats> | ErrorResponse.
 * (Dal passo 4 della migrazione le rotte nuove stanno sotto /api/; queste si
 * spostano al passo 9.)
 */

import type { UserRef } from './common';

// ModeRating: il rating in una modalità (statistiche, contratto 2.1)
export interface ModeRating {
  // il valore arrotondato; 1500 per chi non ha mai giocato in quella modalità
  value: number;
  // le partite che contano per il rating in quella modalità
  games: number;
  // true per le prime 10 (D9)
  provisional: boolean;
}

// Stats: i dati di GET /stats/me (il pannello statistiche)
export interface Stats {
  // partite giocate, vinte, perse, pareggiate (un abbandono è una sconfitta)
  games: number;
  wins: number;
  losses: number;
  draws: number;
  // la percentuale di vittorie, da 0 a 100; null se non ha ancora giocato
  win_rate: number | null;
  // il rating di ogni modalità. Le chiavi '1v1' e '2v2' vanno tra apici perché
  // cominciano con una cifra
  ratings: {
    '1v1': ModeRating;
    '2v2': ModeRating;
  };
}

// Presence: lo stato di un amico
export type Presence = 'online' | 'in_game' | 'offline';

// Friend: un amico nella lista. "extends UserRef" vuol dire: user_id,
// username e avatar di UserRef, più i campi scritti qui
export interface Friend extends UserRef {
  // se è collegato, in partita o scollegato
  presence: Presence;
  // i messaggi non letti ricevuti da lui
  unread: number;
}

// FriendRequest: una richiesta di amicizia, ricevuta o mandata
export interface FriendRequest extends UserRef {
  // quando è stata mandata, in ISO 8601 UTC, per esempio '2026-09-28T09:41:05.000Z'
  sent_at: string;
}

// FriendsList: i dati di GET /friends/
export interface FriendsList {
  // gli amici: prima online, poi in partita, poi scollegati, per nome
  friends: Friend[];
  // le richieste ricevute, dalla più recente
  requests_in: FriendRequest[];
  // le richieste mandate, dalla più recente
  requests_out: FriendRequest[];
  // gli utenti che hai bloccato
  blocked: UserRef[];
  // i numeri per il contatore sull'icona degli amici (la pagina ne mostra la somma)
  counters: {
    requests_in: number;
    unread_messages: number;
  };
}

// SentRequestBody: il corpo di POST /friends/requests
export interface SentRequestBody {
  // la chiave anti-doppione, la stessa per tutti i tentativi (contratto 1.3)
  request_id: string;
  // il nome esatto dell'utente, maiuscole comprese
  username: string;
}

// BlockBody: il corpo di POST /friends/blocks
export interface BlockBody {
  // la chiave anti-doppione (contratto 1.3)
  request_id: string;
  // l'utente da bloccare
  user_id: number;
}

// Online: i dati di GET /online, l'unica richiesta senza login (5.1)
export interface Online {
  // quanti utenti sono collegati adesso
  online_count: number;
}
