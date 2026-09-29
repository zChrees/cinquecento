/**
 * Pagina del tavolo (P21, P24). Un'unica funzione render(vista) ridisegna il tavolo
 * dalla vista ricevuta (contratto 3.3): niente stato sparso nella pagina.
 *
 * - Prova: con ?demo=1v1 o ?demo=2v2 (attributo data-demo-url) disegna una vista
 *   finta e non si collega al server.
 * - Partita (P24): si collega, manda game:join (anche dopo ogni riconnessione) e a
 *   ogni game:state chiama render(vista). Le mosse vanno al server con
 *   game:play_card e game:sing, con la version della vista su cui si è deciso;
 *   finché non arriva la risposta carte e pulsanti restano disattivati.
 * - Se la partita si apre in un'altra scheda (game:replaced, D14) questa si ferma.
 * - P33: senza connessione carte, canti e frasi sono spenti; l'avviso in cima alla
 *   pagina lo mostra core/socket.js; al ritorno game:join rimanda la vista attuale.
 * - P25: "Esci", dopo la conferma, manda game:leave (la partita è persa per abbandono)
 *   e poi torna alla home; a partita finita torna alla home senza chiedere.
 *   I secondi del turno e quelli per rientrare di chi è scollegato arrivano con la
 *   vista; la pagina li fa scendere da sola (contratto 1.1), contando dal momento in
 *   cui la vista è arrivata.
 * - P57, momenti del tavolo, decisi confrontando la vista nuova con quella di prima
 *   (mai alla prima vista, né dopo un rientro nella pagina):
 *   - presa appena chiusa (last_trick cambiato nella stessa mano): resta al centro
 *     per LAST_TRICK_MS, o finché qualcuno gioca la prima carta della presa nuova;
 *     la mano non si blocca mai;
 *   - fine mano (hand_number salito): prima l'ultima presa della mano, che arriva in
 *     last_hand.last_trick (P58: la mano nuova parte con last_trick null), come una
 *     presa qualsiasi; poi il riepilogo di fine mano per SUMMARY_MS, o fino a "Ok";
 *   - P69: finché si vedono l'ultima presa della mano e il riepilogo le carte sono
 *     spente (toccando in fretta si giocava una carta della mano nuova senza
 *     volerlo); "Ok" chiude il riepilogo e le riaccende;
 *   - carte del canto (game:sang, D15): accanto a chi ha cantato per show_seconds.
 *   - P70, lancio: ogni carta che arriva sul tavolo (anche quella che chiude la
 *     presa o la mano) vola al suo posto in THROW_MS; finché vola, un tocco sulle
 *     proprie carte non gioca niente. I tempi di lanci e presa chiusa passano al
 *     tavolo, così un ridisegno a metà non fa ripartire le animazioni. Prima di ogni
 *     ridisegno le immagini delle carte si riusano (reuseCardImages): un'immagine
 *     nuova per un attimo si vede bianca.
 *   - P70, pescata: quando il mazzo cala nella stessa mano, ognuno pesca a turno
 *     partendo da chi ha preso (DRAW_STEP_MS l'uno dall'altro, DRAW_MS ciascuno): la
 *     carta arriva nel ventaglio dell'avversario, o nella propria mano.
 *   - P70, distribuzione: a ogni mano nuova (non alla prima vista) le carte restano
 *     nascoste finché si vedono l'ultima presa e il riepilogo; poi il mazzo si
 *     mescola (SHUFFLE_MS) e le carte partono una alla volta, a giro dal giocatore
 *     dopo il mazziere (DEAL_STEP_MS l'una dall'altra). Fino alla fine un tocco sulle
 *     proprie carte non gioca niente.
 *   Con "riduci movimento" i tempi sono gli stessi, senza animazioni.
 * - P56, frasi del tavolo (D24): l'elenco arriva con game:phrases a ogni game:join
 *   (la pagina non ne tiene una copia sua; senza elenco il pulsante non c'è). Una
 *   frase scelta parte con game:send_phrase; dopo l'invio il pulsante resta spento
 *   PHRASE_PAUSE_MS, o i retry_after secondi di too_fast. game:phrase {seat, code}
 *   mostra il fumetto accanto a chi ha parlato per BUBBLE_MS (anche il proprio: il
 *   server lo rimanda a tutti). Si mandano anche a partita finita, per i saluti.
 *   L'elenco si chiude con una frase, con Esc o toccando fuori.
 * - Solo nella prova (?demo=): la pagina accetta gli eventi del browser "demo:state"
 *   (una vista nuova), "demo:sang" (un canto), "demo:phrases" (l'elenco delle frasi)
 *   e "demo:phrase" (una frase detta) sull'elemento [data-table], per i test e per
 *   provare dalla console; una frase scelta nella prova mostra subito il proprio
 *   fumetto, senza server.
 */

import { initLayout } from '../core/layout.js';
import { connect, isConnected, on, onStatus, send } from '../core/socket.js';
import { EVENTS, NOT_LOGGED_IN } from '../core/events.js';
import { confirmModal } from '../components/Modal.js';
import { Table } from '../components/Table.js';
import { cardName, reuseCardImages } from '../components/Card.js';
import { throwKey } from '../components/Trick.js';

initLayout();

const root = document.querySelector('[data-table]');
const gameId = root.dataset.gameId;
const demo = Boolean(root.dataset.demoUrl);
const NO_MOVES = Object.freeze({ play: [], sing: [] });
const LAST_TRICK_MS = 1500;
const SUMMARY_MS = 5000;
const PHRASE_PAUSE_MS = 3000; // come TABLE_PHRASE_MIN_INTERVAL_SECONDS del server (P55)
const BUBBLE_MS = 4000;
const THROW_MS = 400; // come la durata di card-throw in css/components/trick.css (P70)
const DRAW_MS = 500; // come la durata di card-draw in css/components/hand.css (P70)
const DRAW_STEP_MS = 150; // tra la pescata di un giocatore e quella del successivo
const SHUFFLE_MS = 600; // come la durata di deck-riffle in css/components/trick.css (P70)
const DEAL_STEP_MS = 80; // tra una carta distribuita e la successiva
const HIDDEN = -1e6; // "parte tra molto": la carta resta nascosta finché la distribuzione non comincia

let view = null;
let viewAt = 0; // quando è arrivata la vista (performance.now), per far scendere i secondi
let status = '';
let waiting = false; // una mossa è partita e si aspetta la risposta
let replaced = false; // la partita è aperta in un'altra scheda
let leaving = false; // "Esci" confermato: si aspetta la risposta a game:leave

// Momenti del tavolo (P57): cosa si vede adesso e il timer che lo toglie
let lastTrick = null;
let lastTrickTimer = 0;
let summary = null;
let summaryTimer = 0;
let nextSummary = null; // riepilogo che aspetta la fine dell'ultima presa della mano
const sang = {}; // posto → { event, timer }
let lastTrickAt = 0; // quando si è vista la presa chiusa (performance.now), per le animazioni
const throws = new Map(); // P70: throwKey(carta) → performance.now() del lancio
let throwTimer = 0;
const drawsBySeat = new Map(); // P70: posto → performance.now() della sua pescata (anche nel futuro)
const drawsOfMine = new Map(); // P70: throwKey(carta pescata da te) → performance.now() della pescata
let drawTimer = 0;
let dealWaiting = false; // P70: mano nuova, la distribuzione aspetta la fine di presa e riepilogo
let dealAt = 0; // P70: performance.now() dell'inizio della mescolata
let dealEnd = 0; // P70: performance.now() dell'ultima carta arrivata
let dealTimer = 0;

// Frasi del tavolo (P56)
let phrases = null; // elenco di game:phrases: [{code, text}]
let phrasesOpen = false;
let phraseSending = false; // una frase è partita e si aspetta la risposta
let phrasePausedUntil = 0; // performance.now() fino a cui il pulsante resta spento
let phrasePauseTimer = 0;
const bubbles = {}; // posto → { text, timer }

function showMessage(text) {
  root.replaceChildren();
  const message = document.createElement('p');
  message.className = 'table__message';
  message.dataset.tableMessage = '';
  message.textContent = text;
  root.append(message);
}

/**
 * La vista con i secondi (turno e rientro) scesi dal momento in cui è arrivata.
 * Nella prova (?demo=) la vista finta è una fotografia: i secondi restano fermi.
 */
function timed(current) {
  if (demo) return current;
  const elapsed = (performance.now() - viewAt) / 1000;
  const later = (seconds) => Math.max(0, seconds - elapsed);
  return {
    ...current,
    turn: current.turn && { ...current.turn, seconds_left: later(current.turn.seconds_left) },
    players: current.players.map((player) => (player.reconnect_seconds_left == null
      ? player
      : { ...player, reconnect_seconds_left: later(player.reconnect_seconds_left) })),
  };
}

/** Ridisegna, se c'è una vista e la partita non è aperta altrove (per i timer). */
function redraw() {
  if (view && !replaced) render(view);
}

/** Toglie la presa chiusa; se era l'ultima della mano, apre il riepilogo che aspettava. */
function hideLastTrick() {
  clearTimeout(lastTrickTimer);
  lastTrick = null;
  if (nextSummary) {
    const waitingSummary = nextSummary;
    nextSummary = null;
    openSummary(waitingSummary);
  }
}

function showLastTrick(trick) {
  hideLastTrick();
  lastTrick = trick;
  lastTrickAt = performance.now();
  lastTrickTimer = setTimeout(() => { hideLastTrick(); redraw(); }, LAST_TRICK_MS);
}

function openSummary(lastHand) {
  closeSummary();
  summary = lastHand;
  summaryTimer = setTimeout(() => { summary = null; redraw(); }, SUMMARY_MS);
}

function closeSummary() {
  clearTimeout(summaryTimer);
  summary = null;
}

function reducedMotion() {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

/** P70: le carte in volo adesso, throwKey(carta) → millisecondi dal lancio. */
function flying() {
  const now = performance.now();
  const thrown = {};
  for (const [key, at] of throws) {
    if (now - at < THROW_MS) thrown[key] = now - at;
    else throws.delete(key);
  }
  return thrown;
}

/**
 * P70: le carte arrivate sul tavolo con la vista nuova partono con il lancio: quelle
 * nuove nella presa, e quella che ha chiuso la presa o la mano (nella presa chiusa).
 */
function noticeThrows(previous, next) {
  if (reducedMotion()) return;
  const before = new Set(previous.trick.cards.map(({ card }) => throwKey(card)));
  const arrived = [...next.trick.cards];
  if (next.hand_number === previous.hand_number && next.last_trick
      && JSON.stringify(next.last_trick) !== JSON.stringify(previous.last_trick)) {
    arrived.push(...next.last_trick.cards);
  }
  if (next.hand_number > previous.hand_number && next.last_hand?.last_trick) {
    arrived.push(...next.last_hand.last_trick.cards);
  }
  const now = performance.now();
  let started = false;
  for (const { card } of arrived) {
    const key = throwKey(card);
    if (!before.has(key) && !throws.has(key)) {
      throws.set(key, now);
      started = true;
    }
  }
  if (started) {
    clearTimeout(throwTimer);
    throwTimer = setTimeout(redraw, THROW_MS); // a lancio finito le carte tornano ferme
  }
}

/** P70: le pescate in corso, { seats: posto → ms, cards: carta → ms } (ms negativi: tra poco). */
function drawing() {
  const now = performance.now();
  const pick = (map) => {
    const out = {};
    for (const [key, at] of map) {
      if (now - at < DRAW_MS) out[key] = now - at;
      else map.delete(key);
    }
    return out;
  };
  return { seats: pick(drawsBySeat), cards: pick(drawsOfMine) };
}

/**
 * P70: il mazzo è calato nella stessa mano, quindi dopo la presa chi ha preso e poi
 * gli altri, in ordine, hanno pescato una carta ciascuno.
 */
function noticeDraws(previous, next) {
  if (reducedMotion() || next.hand_number !== previous.hand_number || !next.last_trick) return;
  const drawn = previous.deck_count - next.deck_count;
  if (drawn <= 0) return;
  const n = next.players.length;
  const now = performance.now();
  const mine = new Set(previous.hand.map(throwKey));
  for (let step = 0; step < Math.min(drawn, n); step += 1) {
    const seat = (next.last_trick.winner_seat + step) % n;
    const at = now + step * DRAW_STEP_MS;
    if (seat === next.you.seat) {
      for (const card of next.hand) if (!mine.has(throwKey(card))) drawsOfMine.set(throwKey(card), at);
    } else {
      drawsBySeat.set(seat, at);
    }
  }
  clearTimeout(drawTimer);
  drawTimer = setTimeout(redraw, (Math.min(drawn, n) - 1) * DRAW_STEP_MS + DRAW_MS);
}

/**
 * P70: a chi va, in ordine, ogni carta distribuita: a giro dal giocatore dopo il
 * mazziere, una carta alla volta. Restituisce [{ seat, index }] (index = posizione
 * nella mano di quel giocatore).
 */
function dealOrder(current) {
  const n = current.players.length;
  const first = (current.dealer_seat + 1) % n;
  const counts = current.players.map((player) => (player.seat === current.you.seat ? current.hand.length : player.cards_in_hand));
  const order = [];
  for (let round = 0; round < Math.max(...counts); round += 1) {
    for (let step = 0; step < n; step += 1) {
      const seat = (first + step) % n;
      if (round < counts[seat]) order.push({ seat, index: round });
    }
  }
  return order;
}

function startDeal() {
  dealWaiting = false;
  dealAt = performance.now();
  const cards = dealOrder(view).length;
  dealEnd = dealAt + SHUFFLE_MS + Math.max(cards - 1, 0) * DEAL_STEP_MS + DRAW_MS;
  clearTimeout(dealTimer);
  dealTimer = setTimeout(redraw, dealEnd - dealAt);
}

function dealing() {
  return dealWaiting || performance.now() < dealEnd;
}

/** P70: i tempi della distribuzione per il tavolo, o null se non c'è. */
function dealMoments(current) {
  if (!dealing()) return null;
  const now = performance.now();
  const mine = {};
  const seats = {};
  dealOrder(current).forEach(({ seat, index }, k) => {
    const since = dealWaiting ? HIDDEN : now - (dealAt + SHUFFLE_MS + k * DEAL_STEP_MS);
    if (seat === current.you.seat) mine[throwKey(current.hand[index])] = since;
    else (seats[seat] ??= [])[index] = since;
  });
  const shuffled = !dealWaiting && now - dealAt < SHUFFLE_MS ? now - dealAt : null;
  return { shuffled, mine, seats };
}

/** P70: con la mano nuova la distribuzione aspetta; parte quando presa e riepilogo spariscono. */
function noticeDeal(previous, next) {
  if (reducedMotion() || next.hand_number <= previous.hand_number || next.status !== 'playing') return;
  dealWaiting = true;
  dealEnd = 0;
}

/** Momenti che cominciano con la vista nuova (P57, P58): presa appena chiusa, fine mano. */
function noticeMoments(previous, next) {
  if (!previous) return; // prima vista: niente da mostrare "per un momento"
  noticeThrows(previous, next);
  noticeDraws(previous, next);
  noticeDeal(previous, next);
  if (next.hand_number !== previous.hand_number) hideLastTrick();
  if (next.last_trick && next.hand_number === previous.hand_number
      && JSON.stringify(next.last_trick) !== JSON.stringify(previous.last_trick)) {
    showLastTrick(next.last_trick);
  }
  if (next.hand_number > previous.hand_number && next.last_hand) {
    closeSummary();
    if (next.last_hand.last_trick) {
      // Prima la presa che ha chiuso la mano, poi il riepilogo (quando la presa sparisce)
      showLastTrick(next.last_hand.last_trick);
      nextSummary = next.last_hand;
    } else {
      openSummary(next.last_hand);
    }
  }
}

/** Ridisegna il tavolo dalla vista. È l'unico punto che tocca il DOM del tavolo. */
function render(next) {
  if (next !== view) {
    noticeMoments(view, next);
    view = next;
    viewAt = performance.now();
  }
  // La presa chiusa lascia il posto alla presa nuova appena qualcuno gioca
  if (lastTrick && view.trick.cards.length) hideLastTrick();
  // P70: finiti ultima presa e riepilogo, comincia la distribuzione della mano nuova
  if (dealWaiting && !lastTrick && !nextSummary && !summary) startDeal();
  // Mentre si aspetta la risposta a una mossa, senza connessione (P33) o a fine mano,
  // finché si vedono l'ultima presa della mano e il riepilogo (P69), nessuna carta e
  // nessun canto sono attivi
  const offline = !demo && !isConnected();
  const handEnding = Boolean(nextSummary || summary);
  const shown = timed(waiting || leaving || offline || handEnding ? { ...view, legal: NO_MOVES } : view);
  const drawn = drawing();
  const moments = {
    lastTrick,
    lastTrickFor: lastTrick ? performance.now() - lastTrickAt : 0,
    thrown: flying(),
    drawnSeats: drawn.seats,
    drawnCards: drawn.cards,
    deal: dealMoments(view),
    summary,
    onCloseSummary: () => { closeSummary(); redraw(); },
    sang: Object.fromEntries(Object.entries(sang).map(([seat, { event }]) => [seat, event])),
  };
  const phrasesShown = phrases && {
    list: phrases,
    open: phrasesOpen,
    disabled: offline || phraseSending || performance.now() < phrasePausedUntil,
    onToggle: () => { phrasesOpen = !phrasesOpen; redraw(); },
    onPick: sendPhrase,
    bubbles: Object.fromEntries(Object.entries(bubbles).map(([seat, { text }]) => [seat, text])),
  };
  // Il tavolo si ridisegna tutto: chi stava usando le frasi con la tastiera resta dov'era
  const focused = document.activeElement;
  const focusKey = root.contains(focused) && (focused.dataset.phraseCode ?? ('phrasesButton' in focused.dataset ? '' : null));
  reuseCardImages(root); // P70: niente immagini nuove (e lampi bianchi) a ogni ridisegno
  root.replaceChildren(Table(shown, { onPlay, onSing, onLeave }, status, moments, phrasesShown));
  if (typeof focusKey === 'string') {
    const selector = focusKey ? `[data-phrase-code="${CSS.escape(focusKey)}"]` : '[data-phrases-button]';
    root.querySelector(selector)?.focus();
  }
}

// --- Frasi del tavolo (P56) ---

function closePhrases() {
  if (!phrasesOpen) return;
  phrasesOpen = false;
  redraw();
}

/** Spegne il pulsante delle frasi per `ms` millisecondi (dopo l'invio, o con too_fast). */
function pausePhrases(ms) {
  clearTimeout(phrasePauseTimer);
  phrasePausedUntil = performance.now() + ms;
  phrasePauseTimer = setTimeout(redraw, ms);
}

function showBubble(seat, text) {
  clearTimeout(bubbles[seat]?.timer);
  const entry = { text };
  entry.timer = setTimeout(() => {
    if (bubbles[seat] === entry) delete bubbles[seat];
    redraw();
  }, BUBBLE_MS);
  bubbles[seat] = entry;
  redraw();
}

async function sendPhrase(code) {
  if (phraseSending || !view || replaced || performance.now() < phrasePausedUntil) return;
  phrasesOpen = false;
  if (demo) {
    pausePhrases(PHRASE_PAUSE_MS);
    onPhrase({ seat: view.you.seat, code });
    return;
  }
  phraseSending = true;
  redraw();
  const answer = await send(EVENTS.GAME_SEND_PHRASE, { game_id: gameId, code });
  phraseSending = false;
  if (answer.ok) {
    pausePhrases(PHRASE_PAUSE_MS);
  } else if (answer.error.code === 'too_fast') {
    pausePhrases(answer.error.retry_after * 1000);
  } else {
    setStatus(answer.error.message); // per esempio senza connessione (no_connection)
    return;
  }
  redraw();
}

/** game:phrases: l'elenco delle frasi, a ogni ingresso nella stanza. */
function onPhrases(data) {
  if (replaced || !data || !Array.isArray(data.phrases)) return;
  phrases = data.phrases.filter((phrase) => phrase
    && typeof phrase.code === 'string' && typeof phrase.text === 'string');
  redraw();
}

/** game:phrase: il fumetto accanto a chi ha parlato; il testo si prende dall'elenco. */
function onPhrase(data) {
  if (replaced || !phrases || !data) return;
  const phrase = phrases.find((item) => item.code === data.code);
  if (!phrase || !view || !view.players[data.seat]) return;
  showBubble(data.seat, phrase.text);
}

document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && phrasesOpen) {
    closePhrases();
    root.querySelector('[data-phrases-button]')?.focus();
  }
});

document.addEventListener('pointerdown', (event) => {
  if (phrasesOpen && !event.target.closest('[data-phrases-menu], [data-phrases-button]')) closePhrases();
});

// Chi è scollegato: "scollegato · 48 s" scende ogni secondo, senza aspettare il server
setInterval(() => {
  if (!demo && view && !replaced && view.status === 'playing'
      && view.players.some((player) => player.reconnect_seconds_left != null)) {
    render(view);
  }
}, 1000);

function setStatus(text) {
  status = text;
  if (view) render(view);
}

/** Manda una mossa con la version della vista attuale; disattiva tutto fino alla risposta. */
async function sendMove(event, data) {
  if (waiting || !view || replaced) return;
  waiting = true;
  setStatus('');
  const answer = await send(event, { game_id: gameId, version: view.version, ...data });
  waiting = false;
  // Con stale_state il server ha già mandato la vista attuale: basta dirlo
  setStatus(answer.ok ? '' : answer.error.message);
}

function onPlay(card) {
  // P70: finché una carta vola sul tavolo, o si distribuisce, non se ne gioca un'altra
  if (Object.keys(flying()).length || dealing()) return;
  if (demo) {
    setStatus(`Prova: hai scelto ${cardName(card)}. In partita la carta va al server.`);
    return;
  }
  sendMove(EVENTS.GAME_PLAY_CARD, { card });
}

function onSing(suit) {
  if (demo) {
    setStatus(`Prova: vuoi cantare a ${suit}. In partita il canto va al server.`);
    return;
  }
  sendMove(EVENTS.GAME_SING, { suit });
}

async function onLeave() {
  if (leaving) return;
  // Partita finita, o aperta altrove: si torna alla home senza abbandonare niente
  if (replaced || (view && view.status === 'finished')) {
    window.location.assign('/');
    return;
  }
  const ok = await confirmModal({
    title: 'Vuoi uscire dalla partita?',
    message: view && view.mode === '2v2'
      ? 'La partita sarà persa per abbandono, anche per il tuo compagno.'
      : 'La partita sarà persa per abbandono.',
    confirmLabel: 'Esci',
    danger: true,
  });
  if (!ok || leaving) return;
  if (demo) {
    window.location.assign('/');
    return;
  }
  leaving = true;
  if (view) render(view);
  const answer = await send(EVENTS.GAME_LEAVE, { game_id: gameId });
  if (answer.ok) {
    window.location.assign('/');
    return;
  }
  // Per esempio senza connessione (no_connection): si resta al tavolo e lo si dice
  leaving = false;
  setStatus(answer.error.message);
}

async function loadDemo(url) {
  try {
    const response = await fetch(url, { headers: { Accept: 'application/json' } });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    render(await response.json());
  } catch {
    showMessage('Non riesco a caricare la partita di prova.');
  }
}

// --- Partita vera (P24) ---

async function join() {
  const answer = await send(EVENTS.GAME_JOIN, { game_id: gameId });
  if (!answer.ok) {
    if (view) setStatus(answer.error.message);
    else showMessage(answer.error.message);
  }
}

function onState(next) {
  // Le viste arrivano in ordine di version: una più vecchia di quella mostrata si ignora
  if (replaced || (view && next.version < view.version)) return;
  render(next);
}

/**
 * D15: Re e Cavallo cantati restano accanto a chi ha cantato per show_seconds
 * secondi (P57); la frase nella riga di stato, per i lettori di schermo, dura
 * uguale se nel frattempo non arriva un altro messaggio.
 */
function onSang(event) {
  if (replaced) return;
  const seconds = event.show_seconds * 1000;
  clearTimeout(sang[event.seat]?.timer);
  const timer = setTimeout(() => {
    if (sang[event.seat]?.event === event) delete sang[event.seat];
    redraw();
  }, seconds);
  sang[event.seat] = { event, timer };

  const who = view && view.players[event.seat] ? view.players[event.seat].username : 'Un giocatore';
  const text = `${who} ha cantato ${event.points} a ${event.suit}.`;
  setStatus(text);
  setTimeout(() => {
    if (status === text) setStatus('');
  }, seconds);
}

function startGame() {
  on(EVENTS.GAME_STATE, onState);
  on(EVENTS.GAME_SANG, onSang);
  on(EVENTS.GAME_PHRASES, onPhrases);
  on(EVENTS.GAME_PHRASE, onPhrase);
  on(EVENTS.GAME_REPLACED, () => {
    replaced = true;
    showMessage('Questa partita è aperta in un\'altra scheda o su un altro dispositivo.');
  });
  onStatus((now) => {
    if (replaced) return;
    if (now === 'connected') {
      if (view) setStatus('');
      join(); // anche dopo una riconnessione: il server rimanda la vista attuale
    } else if (now === NOT_LOGGED_IN) {
      showMessage('Accedi per giocare.');
    } else {
      redraw();   // P33: l'avviso è in cima alla pagina (socket.js); qui si spengono carte e canti
    }
  });
  connect();
}

if (demo) {
  // Solo nella prova: viste e canti finti mandati dai test o dalla console (P57)
  root.addEventListener('demo:state', (event) => onState(event.detail));
  root.addEventListener('demo:sang', (event) => onSang(event.detail));
  root.addEventListener('demo:phrases', (event) => onPhrases(event.detail));
  root.addEventListener('demo:phrase', (event) => onPhrase(event.detail));
  loadDemo(root.dataset.demoUrl);
} else {
  showMessage('In attesa della partita…');
  startGame();
}
