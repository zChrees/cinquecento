/**
 * Nomi degli eventi in tempo reale (docs/CONTRATTO-SOCKET.md), in un posto solo (P23).
 * Le pagine usano queste costanti invece di scrivere i nomi a mano.
 */

export const EVENTS = Object.freeze({
  // Partita (3.2)
  GAME_JOIN: 'game:join',
  GAME_PLAY_CARD: 'game:play_card',
  GAME_SING: 'game:sing',
  GAME_SEND_PHRASE: 'game:send_phrase',
  GAME_LEAVE: 'game:leave',
  GAME_STATE: 'game:state',
  GAME_SANG: 'game:sang',
  GAME_PHRASES: 'game:phrases',
  GAME_PHRASE: 'game:phrase',
  GAME_REPLACED: 'game:replaced',
  GAME_START: 'game:start',
  // Code di matchmaking (4)
  QUEUE_JOIN: 'queue:join',
  QUEUE_LEAVE: 'queue:leave',
  QUEUE_STATUS: 'queue:status',
  QUEUE_LEFT: 'queue:left',
});

/** Motivo del rifiuto della connessione per chi non ha fatto il login (contratto 1.4). */
export const NOT_LOGGED_IN = 'not_logged_in';
