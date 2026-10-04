/**
 * Nomi degli eventi in tempo reale (docs/CONTRATTO-SOCKET.md), in un posto solo (P23).
 * Le pagine usano queste costanti invece di scrivere i nomi a mano.
 */

export const EVENTS = Object.freeze({
  // Partita (3.2)
  GAME_JOIN: 'game:join',
  GAME_PLAY_CARD: 'game:play_card',
  GAME_SING: 'game:sing',
  GAME_LAY_DOWN: 'game:lay_down',
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
  // Home (5.1)
  HOME_STATUS: 'home:status',
  // Amici online (5.2)
  FRIENDS_PRESENCE: 'friends:presence',
  FRIENDS_CHANGED: 'friends:changed',
  // Inviti a partita (5.3)
  INVITE_SEND: 'invite:send',
  INVITE_RECEIVED: 'invite:received',
  INVITE_ACCEPT: 'invite:accept',
  INVITE_DECLINE: 'invite:decline',
  INVITE_CANCEL: 'invite:cancel',
  INVITE_START: 'invite:start',
  INVITE_UPDATE: 'invite:update',
  // Chat tra amici (5.4)
  CHAT_HISTORY: 'chat:history',
  CHAT_SEND: 'chat:send',
  CHAT_READ: 'chat:read',
  CHAT_MESSAGE: 'chat:message',
});

/** Motivo del rifiuto della connessione per chi non ha fatto il login (contratto 1.4). */
export const NOT_LOGGED_IN = 'not_logged_in';
