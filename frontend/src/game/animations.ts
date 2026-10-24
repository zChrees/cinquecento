/**
 * Tutte le durate del tavolo React, in un posto solo (passo 8 della migrazione,
 * docs/MIGRAZIONE-FRONTEND.md, "Piano del passo 8").
 *
 * Sono le durate del tavolo. Molte devono restare
 * uguali ad altre copie: a quelle del server in app/realtime/room.py (le pause del
 * tavolo, P94) e alle durate delle animazioni nei CSS (css/components/trick.css,
 * hand.css). Le copie sono tre: room.py, questo file e i CSS (le confronta
 * tests/sockets/test_durate_tavolo.py, i CSS i test del tavolo).
 *
 * Una costante per riga, sempre nella forma
 *     export const NOME_MS: number = 1500;
 * perché i test le leggono con un'espressione regolare (il confronto con room.py
 * è il pezzo di Giuseppe del passo 8, dopo l'8a).
 *
 * Cosa contiene: solo numeri (millisecondi, tranne TICK_SECONDS).
 *
 * DA DOVE ARRIVANO I DATI: scritti a mano qui. Li
 * usano i file di frontend/src/game/.
 */

// Presa appena chiusa, per quanto resta al centro (P57)
export const LAST_TRICK_MS: number = 1500;
// Carte calate scoperte (P85, D45); come LAID_DOWN_SECONDS di app/realtime/room.py (P94)
export const LAID_DOWN_MS: number = 3000;
// La scritta "Mazzo finito: ora vedi le carte di …" (P93, D46)
export const PARTNER_NOTICE_MS: number = 2500;
// Riepilogo di fine mano (P57)
export const SUMMARY_MS: number = 5000;
// Pausa dopo una frase; come TABLE_PHRASE_MIN_INTERVAL_SECONDS di config.py (P55, P56)
export const PHRASE_PAUSE_MS: number = 3000;
// Il fumetto di una frase (P56)
export const BUBBLE_MS: number = 4000;
// Lancio delle carte degli altri; come card-throw in css/components/trick.css e THROW_SECONDS di room.py (P70)
export const THROW_MS: number = 400;
// Lancio della tua carta (P99); come .trick__card--bottom > .card--thrown in trick.css
export const MY_THROW_MS: number = 550;
// Pescata; come card-draw in css/components/hand.css (P70)
export const DRAW_MS: number = 500;
// Mescolata; come deck-riffle in trick.css e SHUFFLE_SECONDS di room.py (P70, P113)
export const SHUFFLE_MS: number = 1300;
// Distribuzione, tra una carta e la successiva (P70)
export const DEAL_STEP_MS: number = 80;
// Le carte della presa chiusa scivolano via; come trick-away in trick.css (P103)
export const TRICK_AWAY_MS: number = 1100;
// Lo stesso ritardo, con il nome che usa Trick.tsx; uguale a TRICK_AWAY_MS
export const AWAY_DELAY_MS: number = 1100;
// Margine dei ridisegni di fine animazione: setTimeout a volte scatta in anticipo (P91)
export const TIMER_SLACK_MS: number = 20;
// Doppio tocco bloccato entro questo tempo, contro lo zoom di Safari (P104)
export const DOUBLE_TAP_MS: number = 300;
// Partita interrotta: dopo quanto si torna alla home da soli (P95)
export const GONE_HOME_MS: number = 5000;
// Ticchettio negli ultimi secondi del tuo turno, in secondi (P103)
export const TICK_SECONDS: number = 5;
