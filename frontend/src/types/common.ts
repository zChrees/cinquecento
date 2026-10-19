/**
 * Tipi usati in tutto il contratto (docs/CONTRATTO-SOCKET.md, sezione 1).
 *
 * Cosa contiene:
 *   Mode, TargetScore, Team       modalità, punti per vincere, squadra
 *   UserRef                       un utente come lo mostrano le pagine
 *   ErrorCode, ErrorInfo          i codici di errore e l'errore completo
 *   OkEmpty, OkWithData<T>,       le risposte del server a una richiesta
 *   ErrorResponse
 *
 * DA DOVE ARRIVANO I DATI: ogni richiesta HTTP (api.ts) e ogni evento
 * Socket.IO mandato dalla pagina (events.ts) riceve una di queste risposte.
 */

// Mode: la modalità della partita, uno contro uno o due contro due
export type Mode = '1v1' | '2v2';

// TargetScore: i punti per vincere la partita; il server rifiuta ogni altro valore
export type TargetScore = 150 | 300 | 500;

// Team: la squadra. Nel 1v1 ogni posto è una squadra (0 e 1); nel 2v2 la
// squadra 0 sono i posti 0 e 2, la squadra 1 i posti 1 e 3 (contratto 3.1)
export type Team = 0 | 1;

// UserRef: un utente come compare in liste, inviti, code (contratto 1.1)
export interface UserRef {
  // il numero dell'utente nel database, per esempio 44
  user_id: number;
  // il nome, per esempio 'Giulia'
  username: string;
  // il codice dell'avatar (per esempio 'cavallo_spade'), oppure null: in quel
  // caso la pagina mostra l'iniziale del nome
  avatar: string | null;
}

// ErrorCode: i codici di errore del contratto (tabella di 1.2). La pagina
// decide cosa fare in base al codice; il testo da mostrare è in ErrorInfo.message.
export type ErrorCode =
  | 'invalid_data'
  | 'not_logged_in'
  | 'not_allowed'
  | 'blocked'
  | 'not_found'
  | 'not_friends'
  | 'not_your_turn'
  | 'illegal_move'
  | 'stale_state'
  | 'busy'
  | 'already_exists'
  | 'request_from_them'
  | 'limit_reached'
  | 'too_fast'
  | 'expired'
  | 'offline'
  | 'server_error';

// ErrorInfo: l'errore dentro una risposta rifiutata
export interface ErrorInfo {
  // il codice, per esempio 'not_your_turn'
  code: ErrorCode;
  // il testo in italiano da mostrare così com'è, per esempio 'Non è il tuo turno.'
  message: string;
  // solo con 'too_fast': i secondi da aspettare prima di riprovare. Il ? vuol
  // dire "può mancare": con gli altri codici il campo non c'è (vale undefined)
  retry_after?: number;
}

// OkEmpty: risposta "fatto", senza dati (per esempio a game:play_card)
export interface OkEmpty {
  ok: true;
}

// OkWithData<T>: risposta "fatto" con dei dati. T è un segnaposto per il tipo
// dei dati, scelto da chi usa il tipo: OkWithData<Stats> ha data di tipo Stats.
// È come una funzione che riceve un tipo invece di un valore (in C si userebbe
// void* perdendo i controlli; qui il tipo resta).
export interface OkWithData<T> {
  ok: true;
  // i dati della risposta, per esempio le statistiche
  data: T;
}

// ErrorResponse: risposta "rifiutata"
export interface ErrorResponse {
  ok: false;
  // perché è stata rifiutata
  error: ErrorInfo;
}
