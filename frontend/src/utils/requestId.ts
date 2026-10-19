/**
 * Il codice anti-doppione delle richieste che creano qualcosa (contratto 1.3):
 * la versione TypeScript di newRequestId() di app/static/js/components/FriendsPanel.js.
 *
 * Cosa contiene:
 *   newRequestId()   un codice casuale nuovo, per esempio '3f2b8c1e-9a4d-4c7e-8b1f-2d6e0a5c9b17'
 *
 * Il server ricorda il codice di ogni richiesta: se la stessa richiesta arriva due
 * volte con lo stesso codice (per esempio dopo una rete caduta a metà), la fa una
 * volta sola. Per questo chi riprova deve rimandare lo STESSO codice
 * (api/friends.ts, withRequestId).
 *
 * DA DOVE ARRIVANO I DATI: dal generatore di numeri casuali del browser (crypto).
 */

/**
 * Un codice casuale nuovo, nel formato UUID versione 4.
 *
 * @returns {string} per esempio '3f2b8c1e-9a4d-4c7e-8b1f-2d6e0a5c9b17'
 *
 * In parole semplici:
 *   const id = newRequestId();
 *   crypto.randomUUID esiste solo in https o su localhost (P46): in http su
 *   un'altra macchina della rete non c'è, e allora il codice si costruisce a mano
 *   da 16 byte casuali (getRandomValues), come fa randomUUID.
 */
export function newRequestId(): string {
  // "typeof ... === 'function'": la funzione c'è davvero (in http manca)
  if (typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }

  // bytes: 16 numeri casuali da 0 a 255 (un Uint8Array è un array di unsigned char del C)
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  // Due byte hanno dei bit fissi che dicono "versione 4" e "variante standard":
  // si azzerano con & (AND sui bit) e si accendono con | (OR sui bit), come in C
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;

  // hex: i 16 byte scritti in esadecimale, due cifre per byte, per esempio '3f2b8c1e...'
  let hex = '';
  for (let i = 0; i < bytes.length; i++) {
    hex = hex + bytes[i].toString(16).padStart(2, '0');
  }
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}
