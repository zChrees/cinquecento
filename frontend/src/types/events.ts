/**
 * Gli eventi Socket.IO del contratto (docs/CONTRATTO-SOCKET.md, sezioni 3, 4 e 5).
 * Esempi: app/static/dev/home_esempio.json e amici_esempio.json, controllati da
 * tests/frontend/test_tipi.py.
 *
 * Cosa contiene:
 *   ServerEvents    evento mandato dal server → i suoi dati
 *   ClientEvents    evento mandato dalla pagina → i suoi dati
 *   ClientAnswers   evento mandato dalla pagina → la risposta del server (ack)
 *   e i tipi dei dati: QueueStatus, Invite, ChatMessage, ...
 *
 * DA DOVE ARRIVANO I DATI: gli eventi del server li mandano app/sockets/ e
 * app/realtime/ (socketio.emit); quelli della pagina partono da
 * frontend/src/socket/, che usa questi elenchi per controllare nome ed eventi: un nome sbagliato o un dato mancante diventa un errore di
 * TypeScript invece di un errore nel browser.
 *
 * Gli elenchi sono "interface" con il nome dell'evento come chiave: per
 * esempio ServerEvents['game:state'] è il tipo dei dati di game:state (GameView).
 * È come una tabella: nome dell'evento → struct dei dati.
 */

import type { Card, Suit } from './card';
import type { ErrorResponse, Mode, OkEmpty, OkWithData, TargetScore, UserRef } from './common';
import type { GameView } from './view';
import type { Presence } from './api';

// --- Partita (3.2) -----------------------------------------------------------

// SangEvent: i dati di game:sang, mandato a tutti quando qualcuno canta (D15)
export interface SangEvent {
  // chi ha cantato
  seat: number;
  // il seme
  suit: Suit;
  // 40 o 20
  points: 40 | 20;
  // le due carte mostrate: Re e Cavallo del seme
  cards: Card[];
  // per quanti secondi mostrarle (3)
  show_seconds: number;
}

// Phrase: una frase pronta del tavolo (D24)
export interface Phrase {
  // il codice, che la pagina rimanda con game:send_phrase
  code: string;
  // il testo da mostrare (con textContent, mai come HTML)
  text: string;
}

// GameStart: i dati di game:start, quando la coda o un invito creano la partita
export interface GameStart {
  // il codice della stanza
  game_id: string;
  // l'indirizzo del tavolo, per esempio '/game/a1b2c3d4'
  url: string;
}

// --- Code (4) ----------------------------------------------------------------

// RatingRange: l'intervallo di rating accettato in coda
export interface RatingRange {
  min: number;
  max: number;
}

// QueueStatus: lo stato della coda (queue:status, e la risposta di queue:join)
export interface QueueStatus {
  // modalità e punti della coda
  mode: Mode;
  target_score: TargetScore;
  // da quanti secondi si è in coda; la pagina poi conta da sola
  seconds_waiting: number;
  // l'intervallo di rating accettato adesso; null = qualunque avversario
  rating_range: RatingRange | null;
  // l'amico compagno nel 2v2, altrimenti null
  partner: UserRef | null;
  // gli avversari già noti (P59): vuota tranne nel gruppo di tre amici
  opponents: UserRef[];
}

// QueueLeft: i dati di queue:left
export interface QueueLeft {
  // 'cancelled' (hai annullato, anche da un'altra scheda) oppure 'partner_left'
  reason: 'cancelled' | 'partner_left';
}

// --- Home (5.1) --------------------------------------------------------------

// Resume: la partita in corso da cui rientrare
export interface Resume {
  game_id: string;
  // l'indirizzo del tavolo
  url: string;
  mode: Mode;
  target_score: TargetScore;
}

// HomeStatus: i dati di home:status
export interface HomeStatus {
  // quanti utenti sono collegati (lo stesso utente con due schede conta una volta)
  online_count: number;
  // la partita in corso, oppure null
  resume: Resume | null;
}

// --- Amici e inviti (5.2, 5.3) -----------------------------------------------

// FriendsPresence: i dati di friends:presence
export interface FriendsPresence {
  // l'amico che ha cambiato stato
  user_id: number;
  presence: Presence;
}

// FriendsChanged: i dati di friends:changed; la pagina rilegge GET /api/friends/
export interface FriendsChanged {
  reason: 'request_received' | 'request_accepted' | 'request_declined' | 'friend_removed' | 'blocked';
}

// InviteStatus: lo stato di un invito
export type InviteStatus = 'pending' | 'accepted' | 'declined' | 'expired' | 'cancelled' | 'started';

// Invite: un invito a partita
export interface Invite {
  // il codice dell'invito, per esempio 'inv_9c1e'
  invite_id: string;
  // chi invita e chi è invitato
  from: UserRef;
  to: UserRef;
  mode: Mode;
  target_score: TargetScore;
  status: InviteStatus;
  // i secondi che restano per rispondere (60 all'inizio)
  seconds_left: number;
}

// InviteUpdate: i dati di invite:update
export interface InviteUpdate {
  invite_id: string;
  status: InviteStatus;
}

// --- Chat (5.4) --------------------------------------------------------------

// ChatMessage: un messaggio
export interface ChatMessage {
  // il numero del messaggio, che serve anche a chiedere quelli prima (before_id)
  id: number;
  from_user_id: number;
  to_user_id: number;
  // il testo, così come l'ha scritto (si mostra con textContent, mai come HTML)
  text: string;
  // quando è stato mandato, in ISO 8601 UTC
  sent_at: string;
}

// ChatHistory: la risposta di chat:history
export interface ChatHistory {
  // al massimo 50, dal più vecchio al più nuovo
  messages: ChatMessage[];
  // true se ci sono messaggi ancora più vecchi
  has_more: boolean;
  // false se l'amicizia è finita o c'è un blocco: si legge ma non si scrive
  can_write: boolean;
  // perché non si può scrivere (D41): null se si può, altrimenti il motivo,
  // così la pagina scrive "Bloccato" e non solo che non si può scrivere
  cannot_write: 'not_friends' | 'blocked' | null;
}

// --- Gli elenchi -------------------------------------------------------------

// ServerEvents: gli eventi che manda il server, con i loro dati
export interface ServerEvents {
  'game:state': GameView;
  'game:sang': SangEvent;
  'game:phrases': { phrases: Phrase[] };
  'game:phrase': { seat: number; code: string };
  // solo al compagno (P92): chi consiglia e la carta, null se tolto
  'game:advice': { seat: number; card: Card | null };
  'game:replaced': { game_id: string };
  'game:start': GameStart;
  'queue:status': QueueStatus;
  'queue:left': QueueLeft;
  'home:status': HomeStatus;
  'friends:presence': FriendsPresence;
  'friends:changed': FriendsChanged;
  'invite:received': Invite;
  'invite:update': InviteUpdate;
  'chat:message': { message: ChatMessage };
}

// ClientEvents: gli eventi che manda la pagina, con i loro dati.
// request_id è la chiave anti-doppione (contratto 1.3); version il numero della
// vista su cui l'utente ha deciso (3.2).
export interface ClientEvents {
  'game:join': { game_id: string };
  'game:play_card': { game_id: string; version: number; card: Card };
  'game:sing': { game_id: string; version: number; suit: Suit };
  'game:lay_down': { game_id: string; version: number };
  // card null toglie il consiglio
  'game:advise': { game_id: string; card: Card | null };
  'game:send_phrase': { game_id: string; code: string };
  'game:leave': { game_id: string };
  'queue:join': { request_id: string; mode: Mode; target_score: TargetScore };
  // nessun dato: un oggetto vuoto
  'queue:leave': Record<string, never>;
  // la home chiede lo stato quando compare con il collegamento già aperto
  'home:refresh': Record<string, never>;
  'cpu:start': { request_id: string; target_score: TargetScore; mode: Mode };
  'invite:send': { request_id: string; user_id: number; mode: Mode; target_score: TargetScore };
  'invite:accept': { invite_id: string };
  'invite:decline': { invite_id: string };
  'invite:cancel': { invite_id: string };
  'invite:start': { invite_id: string };
  // before_id: null per gli ultimi messaggi, oppure l'id del più vecchio già caricato
  'chat:history': { user_id: number; before_id: number | null };
  'chat:send': { request_id: string; user_id: number; text: string };
  'chat:read': { user_id: number };
}

// ClientAnswers: per ogni evento della pagina, la risposta del server (ack):
// "fatto" (con o senza dati) oppure l'errore. Le chiavi sono le stesse di
// ClientEvents (lo controlla test_tipi.py).
export interface ClientAnswers {
  'game:join': OkEmpty | ErrorResponse;
  'game:play_card': OkEmpty | ErrorResponse;
  'game:sing': OkEmpty | ErrorResponse;
  'game:lay_down': OkEmpty | ErrorResponse;
  'game:advise': OkEmpty | ErrorResponse;
  'game:send_phrase': OkEmpty | ErrorResponse;
  'game:leave': OkEmpty | ErrorResponse;
  'queue:join': OkWithData<QueueStatus> | ErrorResponse;
  'queue:leave': OkEmpty | ErrorResponse;
  'home:refresh': OkWithData<HomeStatus> | ErrorResponse;
  'cpu:start': OkWithData<{ game_id: string }> | ErrorResponse;
  'invite:send': OkWithData<Invite> | ErrorResponse;
  'invite:accept': OkEmpty | ErrorResponse;
  'invite:decline': OkEmpty | ErrorResponse;
  'invite:cancel': OkEmpty | ErrorResponse;
  // lo stato della coda, oppure nessun dato quando la partita parte subito
  // (il server toglie data quando vale null)
  'invite:start': OkWithData<QueueStatus> | OkEmpty | ErrorResponse;
  'chat:history': OkWithData<ChatHistory> | ErrorResponse;
  'chat:send': OkWithData<{ message: ChatMessage }> | ErrorResponse;
  'chat:read': OkEmpty | ErrorResponse;
}
