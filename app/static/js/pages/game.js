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
 * - P95: se al rientro (game:join) la partita non esiste più (not_found, per esempio
 *   dopo un riavvio del server), al posto del tavolo c'è il riquadro "La partita è
 *   stata interrotta" e dopo 5 secondi si torna alla home.
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
 *   - P85, carte calate (last_hand.laid_down nuovo): per LAID_DOWN_MS, al posto
 *     dell'ultima presa, i ventagli degli altri entrano scoperti nel tavolo, la tua
 *     mano è quella del momento della calata e al centro c'è "Turi cala le carte";
 *     poi il riepilogo (o, se la calata chiude la partita, il riquadro finale).
 *     "Cala le carte" manda game:lay_down con la version, come una carta.
 *   - P70, lancio: ogni carta che arriva sul tavolo (anche quella che chiude la
 *     presa o la mano) vola al suo posto in THROW_MS (P99: la tua in MY_THROW_MS;
 *     P107: ognuna da dove stava, aimThrows); finché vola, un tocco sulle
 *     proprie carte non gioca niente. P78: i lanci vanno in fila: una carta arrivata
 *     mentre un'altra vola parte quando quella si è posata (fino ad allora non si
 *     vede). I tempi di lanci e presa chiusa passano al
 *     tavolo, così un ridisegno a metà non fa ripartire le animazioni. Prima di ogni
 *     ridisegno le immagini delle carte si riusano (reuseCardImages): un'immagine
 *     nuova per un attimo si vede bianca.
 *   - P70, pescata: quando il mazzo cala nella stessa mano, ognuno pesca a turno
 *     partendo da chi ha preso: la carta arriva nel ventaglio dell'avversario, o nella
 *     propria mano. P78: una pescata alla volta (DRAW_MS ciascuna, la successiva
 *     quando la precedente è finita), dopo che la carta che ha chiuso la presa si è posata.
 *   - P70, distribuzione: a ogni mano nuova (non alla prima vista) le carte restano
 *     nascoste finché si vedono l'ultima presa e il riepilogo; poi il mazzo si
 *     mescola (SHUFFLE_MS) e le carte partono una alla volta, a giro dal giocatore
 *     dopo il mazziere (DEAL_STEP_MS l'una dall'altra). Fino alla fine un tocco sulle
 *     proprie carte non gioca niente.
 *   Con "riduci movimento" i tempi sono gli stessi, senza animazioni.
 * - P79: appena si apre il tavolo si scaricano tutte le immagini delle carte
 *   (preloadCardImages), altrimenti con una rete lenta una carta mai vista restava
 *   bianca per qualche secondo; quando sono pronte [data-table] ha data-cards-ready.
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
import { el } from '../utils/dom.js';
import { connect, isConnected, on, onStatus, send } from '../core/socket.js';
import { EVENTS, NOT_LOGGED_IN } from '../core/events.js';
import { confirmModal } from '../components/Modal.js';
import { Table } from '../components/Table.js';
import { cardName, preloadCardImages, reuseCardImages, sameCard } from '../components/Card.js';
import { throwKey } from '../components/Trick.js';
import { playSound, preloadSounds } from '../core/sounds.js';

initLayout();

const root = document.querySelector('[data-table]');
const gameId = root.dataset.gameId;
const demo = Boolean(root.dataset.demoUrl);
const NO_MOVES = Object.freeze({ play: [], sing: [], lay_down: false });
const LAST_TRICK_MS = 1500;
const LAID_DOWN_MS = 3000; // P85, D45: carte calate scoperte; come LAID_DOWN_SECONDS di app/realtime/room.py (P94)
const PARTNER_NOTICE_MS = 2500; // P93, D46: la scritta "Mazzo finito: ora vedi le carte di …"
const SUMMARY_MS = 5000;
const PHRASE_PAUSE_MS = 3000; // come TABLE_PHRASE_MIN_INTERVAL_SECONDS del server (P55)
const BUBBLE_MS = 4000;
const THROW_MS = 400; // come la durata di card-throw in css/components/trick.css (P70)
const MY_THROW_MS = 550; // P99: il lancio della tua carta, come animation-duration di .trick__card--bottom > .card--thrown in trick.css
const DRAW_MS = 500; // come la durata di card-draw in css/components/hand.css (P70)
const SHUFFLE_MS = 600; // come la durata di deck-riffle in css/components/trick.css (P70)
const DEAL_STEP_MS = 80; // tra una carta distribuita e la successiva
const HIDDEN = -1e6; // "parte tra molto": la carta resta nascosta finché la distribuzione non comincia
const TRICK_AWAY_MS = 1100; // P103: le carte della presa chiusa scivolano via (AWAY_DELAY_MS di Trick.js)
const TICK_SECONDS = 5; // P103: il ticchettio negli ultimi secondi del tuo turno

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
let laidDown = null; // P85: le carte calate (last_hand.laid_down) mentre si vedono
let laidDownAt = 0;
let laidDownTimer = 0;

// P93, carte del compagno e consiglio (D46)
let partnerSince = 0; // performance.now() di quando le carte del compagno si sono scoperte
let partnerNotice = false;
let partnerNoticeTimer = 0;
let myAdvice = null; // la carta del compagno che gli hai consigliato
let adviceSending = false;
let receivedAdvice = null; // { seat, card }: la carta che ti ha consigliato il compagno
const sang = {}; // posto → { event, timer }
let lastTrickAt = 0; // quando si è vista la presa chiusa (performance.now), per le animazioni
// P70: throwKey(carta) → { at: performance.now() del lancio (P78: anche nel futuro), ms: durata,
// from: P99, P107, da dove parte: { cx, cy, w, tilt } (centro, larghezza, rotazione), o null }
const throws = new Map();
let throwTimer = 0;
let throwsEnd = 0; // P78: performance.now() in cui si posa l'ultima carta in fila
const drawsBySeat = new Map(); // P70: posto → performance.now() della sua pescata (anche nel futuro)
const drawsOfMine = new Map(); // P70: throwKey(carta pescata da te) → performance.now() della pescata
let drawTimer = 0;
let dealWaiting = false; // P70: mano nuova, la distribuzione aspetta la fine di presa e riepilogo
let dealAt = 0; // P70: performance.now() dell'inizio della mescolata
let dealEnd = 0; // P70: performance.now() dell'ultima carta arrivata
let dealTimer = 0;

// P103, suoni: il tuo turno annunciato o che aspetta la fine delle pause, il ticchettio,
// il riquadro di fine partita che aspetta di comparire
let turnKey = null;
let turnPending = null;
let tickTimers = [];
let resultPending = false;

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

/**
 * P91: ridisegna tra `ms` millisecondi, quando un momento misurato con performance.now()
 * (lanci, pescate, distribuzione, pausa delle frasi) è finito. setTimeout a volte scatta
 * poco prima del tempo chiesto (fino a circa 1 ms in Chrome): senza il margine il momento
 * risultava ancora in corso e restava sul tavolo fino alla vista successiva. 20 ms in più
 * non si vedono.
 */
const TIMER_SLACK_MS = 20;
function redrawAfter(ms) {
  return setTimeout(redraw, ms + TIMER_SLACK_MS);
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

/** P85: toglie le carte calate; se il riepilogo aspettava, lo apre (come hideLastTrick). */
function hideLaidDown() {
  clearTimeout(laidDownTimer);
  laidDown = null;
  if (nextSummary) {
    const waitingSummary = nextSummary;
    nextSummary = null;
    openSummary(waitingSummary);
  }
}

function showLaidDown(laid) {
  hideLaidDown();
  laidDown = laid;
  laidDownAt = performance.now();
  playSound('lay_down'); // P103
  laidDownTimer = setTimeout(() => { hideLaidDown(); redraw(); }, LAID_DOWN_MS);
}

function showLastTrick(trick) {
  hideLastTrick();
  lastTrick = trick;
  lastTrickAt = performance.now();
  playSound('trick', TRICK_AWAY_MS); // P103: quando le carte scivolano verso chi ha preso
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

/** P70: le carte in volo adesso, throwKey(carta) → millisecondi dal lancio (P78: negativi, in fila). */
function flying() {
  const now = performance.now();
  const thrown = {};
  for (const [key, { at, ms }] of throws) {
    if (now - at < ms) thrown[key] = now - at;
    else throws.delete(key);
  }
  return thrown;
}

// P107: come sono girate le carte coperte nel ventaglio di ogni lato (table.css, .edge-hand--…);
// ai lati un po' meno, così la carta si raddrizza in volo senza fare un giro intero
const FAN_TILT = { top: 0, left: 70, right: -70 };

/**
 * P99, P107: da dove parte la carta di `seat` che arriva sul tavolo, misurata sul
 * tavolo disegnato prima di questa vista: la tua dal suo posto nella mano; quella di
 * un altro dalle sue carte scoperte (P85, P93), se c'è, altrimenti dal suo ventaglio
 * coperto. null se non si trova (per esempio la prima vista dopo un rientro).
 */
function throwStart(seat, card, mine) {
  const box = (e, w, tilt) => {
    const r = e.getBoundingClientRect();
    return { cx: r.left + r.width / 2, cy: r.top + r.height / 2, w, tilt };
  };
  const same = `[data-suit="${card.suit}"][data-rank="${card.rank}"]`;
  if (mine) {
    const button = root.querySelector(`.table__mine .hand > .card${same}`);
    return button ? box(button, button.getBoundingClientRect().width, 0) : null;
  }
  const shown = root.querySelector(`[data-revealed-seat="${seat}"] ${same}`);
  if (shown) return box(shown, shown.offsetWidth, 0);
  const side = root.querySelector(`.seat[data-seat="${seat}"]`)?.dataset.position;
  const fan = side && root.querySelector(`[data-edge-hand="${side}"]`);
  return fan ? box(fan, fan.offsetWidth, FAN_TILT[side] ?? 0) : null;
}

/**
 * P99, P107: dopo il ridisegno, per ogni carta in volo dice al CSS (card-throw) da dove
 * parte rispetto al suo posto sul tavolo: spostamento, misura, rotazione iniziale, verso
 * in cui gira e direzione in cui si stacca (verso il centro). Senza il punto di
 * partenza restano i valori di trick.css: arriva dal suo lato.
 */
function aimThrows() {
  for (const face of root.querySelectorAll('.trick__card > [data-thrown]')) {
    const from = throws.get(`${face.dataset.suit}-${face.dataset.rank}`)?.from;
    if (!from || !face.offsetWidth) continue;
    // Dove si posa: la carta senza l'animazione (il ritardo scritto da Trick.js resta)
    face.style.animationName = 'none';
    const to = face.getBoundingClientRect();
    face.style.animationName = '';
    // Lo spostamento dell'animazione è girato con la casella della presa (un po' ruotata)
    // e ingrandito con la carta che vince (P76): si riporta nelle sue misure
    const { a, b, c, d } = new DOMMatrix(getComputedStyle(face.parentElement).transform);
    const scale = parseFloat(getComputedStyle(face).scale) || 1;
    const det = (a * d - b * c) * scale;
    const sx = from.cx - (to.left + to.width / 2);
    const sy = from.cy - (to.top + to.height / 2);
    const dx = (d * sx - c * sy) / det;
    const dy = (a * sy - b * sx) / det;
    face.style.setProperty('--from-x', `${dx.toFixed(1)}px`);
    face.style.setProperty('--from-y', `${dy.toFixed(1)}px`);
    face.style.setProperty('--from-scale', (from.w / (face.offsetWidth * scale)).toFixed(3));
    // All'inizio com'era dov'è partita (dritta in mano, girata nel ventaglio), meno la
    // rotazione della casella
    face.style.setProperty('--from-tilt', `${(from.tilt - Math.atan2(b, a) * 180 / Math.PI).toFixed(1)}deg`);
    // Gira verso il centro: da destra in senso antiorario, da sinistra in senso orario
    face.style.setProperty('--from-turn', `${dx > 0 ? -14 : 14}deg`);
    // Si stacca di 16 px verso il suo posto, prima di volare
    const far = Math.hypot(dx, dy) || 1;
    face.style.setProperty('--lift-x', `${(-dx / far * 16).toFixed(1)}px`);
    face.style.setProperty('--lift-y', `${(-dy / far * 16).toFixed(1)}px`);
  }
}

/**
 * P70: le carte arrivate sul tavolo con la vista nuova partono con il lancio: quelle
 * nuove nella presa, e quella che ha chiuso la presa o la mano (nella presa chiusa).
 * P78: in fila, ognuna quando si è posata la precedente (anche di una vista di prima).
 */
function noticeThrows(previous, next) {
  const before = new Set(previous.trick.cards.map(({ card }) => throwKey(card)));
  const arrived = [...next.trick.cards]; // { seat, card }
  if (next.hand_number === previous.hand_number && next.last_trick
      && JSON.stringify(next.last_trick) !== JSON.stringify(previous.last_trick)) {
    arrived.push(...next.last_trick.cards);
  }
  // P85: con una calata last_hand.last_trick è una presa già vista, nessuna carta vola
  if (next.hand_number > previous.hand_number && next.last_hand?.last_trick && !next.last_hand.laid_down) {
    arrived.push(...next.last_hand.last_trick.cards);
  }
  const now = performance.now();
  if (reducedMotion()) {
    // P103: niente volo, ma il suono della carta giocata sì
    if (arrived.some(({ card }) => !before.has(throwKey(card)))) playSound('card');
    return;
  }
  let at = Math.max(now, throwsEnd);
  for (const { seat, card } of arrived) {
    const key = throwKey(card);
    if (!before.has(key) && !throws.has(key)) {
      // P99, P107: la carta parte da dov'era (la tua anche se giocata dalla mossa
      // automatica), sul tavolo ancora disegnato prima di questa vista
      const mine = seat === next.you.seat;
      const ms = mine ? MY_THROW_MS : THROW_MS;
      throws.set(key, { at, ms, from: throwStart(seat, card, mine) });
      playSound('card', at - now + ms); // P103, P109: la carta che si posa, a fine volo
      at += ms;
    }
  }
  if (at > Math.max(now, throwsEnd)) {
    throwsEnd = at;
    clearTimeout(throwTimer);
    throwTimer = redrawAfter(throwsEnd - now); // a lanci finiti le carte tornano ferme
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
 * gli altri, in ordine, hanno pescato una carta ciascuno. P78: una alla volta, a
 * partire da quando si è posata la carta che ha chiuso la presa.
 */
function noticeDraws(previous, next) {
  if (next.hand_number !== previous.hand_number || !next.last_trick) return;
  const drawn = previous.deck_count - next.deck_count;
  if (drawn <= 0) return;
  if (reducedMotion()) {
    playSound('draw'); // P103: niente animazione, il suono sì
    return;
  }
  const n = next.players.length;
  const now = performance.now();
  const start = Math.max(now, throwsEnd);
  const mine = new Set(previous.hand.map(throwKey));
  for (let step = 0; step < Math.min(drawn, n); step += 1) {
    const seat = (next.last_trick.winner_seat + step) % n;
    const at = start + step * DRAW_MS;
    playSound('draw', at - now); // P103
    if (seat === next.you.seat) {
      for (const card of next.hand) if (!mine.has(throwKey(card))) drawsOfMine.set(throwKey(card), at);
    } else {
      drawsBySeat.set(seat, at);
    }
  }
  clearTimeout(drawTimer);
  drawTimer = redrawAfter(start - now + Math.min(drawn, n) * DRAW_MS);
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
  playSound('shuffle'); // P103, P109: la mescolata, poi la distribuzione (un suono solo)
  playSound('deal', SHUFFLE_MS);
  clearTimeout(dealTimer);
  dealTimer = redrawAfter(dealEnd - dealAt);
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
  if (next.result && !previous.result) resultPending = true; // P103: suona quando compare il riquadro
  // P93: le carte del compagno si scoprono adesso (non alla prima vista): entrano e c'è la scritta
  if (next.partner_hand && !previous.partner_hand) {
    partnerSince = performance.now();
    partnerNotice = true;
    clearTimeout(partnerNoticeTimer);
    partnerNoticeTimer = setTimeout(() => { partnerNotice = false; redraw(); }, PARTNER_NOTICE_MS);
  }
  noticeThrows(previous, next);
  noticeDraws(previous, next);
  noticeDeal(previous, next);
  if (next.hand_number !== previous.hand_number) hideLastTrick();
  // P85: qualcuno ha calato (la mano finita è nuova e ha laid_down): le carte calate
  // si vedono per LAID_DOWN_MS al posto dell'ultima presa, poi il riepilogo; se la
  // calata chiude la partita (hand_number non sale) il riepilogo è nel riquadro finale
  const laid = next.last_hand?.laid_down;
  if (laid && next.last_hand.hand_number !== previous.last_hand?.hand_number) {
    hideLastTrick();
    closeSummary();
    showLaidDown(laid);
    if (next.hand_number > previous.hand_number) nextSummary = next.last_hand;
    return;
  }
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

/** P72: i punti di una mano finita (last_hand) nella forma di hand_points. */
function handTotals(lastHand) {
  return lastHand.teams.map(({ team, hand_total: total }) => ({ team, total }));
}

/** Ridisegna il tavolo dalla vista. È l'unico punto che tocca il DOM del tavolo. */
function render(next) {
  if (next !== view) {
    noticeMoments(view, next);
    view = next;
    viewAt = performance.now();
    // P93: il consiglio ricevuto lo ripete la vista (advice, solo nel 2v2); quello dato
    // vale finché la carta è ancora in mano al compagno
    if ('advice' in next) receivedAdvice = next.advice;
    if (myAdvice && !(next.partner_hand ?? []).some((card) => sameCard(card, myAdvice))) myAdvice = null;
    if (!next.partner_hand) {
      partnerNotice = false;
      clearTimeout(partnerNoticeTimer);
    }
  }
  // La presa chiusa (o le carte calate, P85) lascia il posto alla presa nuova appena qualcuno gioca
  if (lastTrick && view.trick.cards.length) hideLastTrick();
  if (laidDown && view.trick.cards.length) hideLaidDown();
  // P70: finiti ultima presa (o carte calate) e riepilogo, comincia la distribuzione della mano nuova
  if (dealWaiting && !lastTrick && !laidDown && !nextSummary && !summary) startDeal();
  // Mentre si aspetta la risposta a una mossa, senza connessione (P33) o a fine mano,
  // finché si vedono l'ultima presa della mano e il riepilogo (P69), nessuna carta e
  // nessun canto sono attivi
  const offline = !demo && !isConnected();
  const handEnding = Boolean(nextSummary || summary || laidDown);
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
    // P72: finché si vedono l'ultima presa e il riepilogo, i punti della mano appena chiusa
    handPoints: nextSummary || summary ? handTotals(nextSummary || summary) : null,
    onCloseSummary: () => { closeSummary(); redraw(); },
    sang: Object.fromEntries(Object.entries(sang).map(([seat, { event }]) => [seat, event])),
    laidDown,
    laidDownFor: laidDown ? performance.now() - laidDownAt : 0,
    partner: view.partner_hand ? {
      picked: myAdvice,
      disabled: offline || adviceSending || handEnding,
      shownFor: performance.now() - partnerSince,
      notice: partnerNotice,
    } : null,
    advice: receivedAdvice && !handEnding ? receivedAdvice : null,
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
  const hovered = root.querySelector('button.card:hover');
  reuseCardImages(root); // P70: niente immagini nuove (e lampi bianchi) a ogni ridisegno
  root.replaceChildren(Table(shown, { onPlay, onSing, onLeave, onLayDown, onAdvise }, status, moments, phrasesShown));
  if (hovered) keepHover(hovered);
  aimThrows();
  turnSounds();
  resultSound();
  if (typeof focusKey === 'string') {
    const selector = focusKey ? `[data-phrase-code="${CSS.escape(focusKey)}"]` : '[data-phrases-button]';
    root.querySelector(selector)?.focus();
  }
}

/**
 * P103: il ticchettio degli ultimi TICK_SECONDS secondi del tuo turno (il suono di
 * "tocca a te" è stato tolto in P109). Il turno comincia quando il tavolo ha finito
 * le pause (lanci, pescate, ultima presa, carte calate, riepilogo, distribuzione), come
 * il conto alla rovescia del server (P94): fino ad allora il turno aspetta
 * (turnPending). Un turno è nuovo quando cambiano la mano o la presa (un canto lascia
 * il turno a te: il ticchettio non riparte).
 */
function turnSounds() {
  const mine = !replaced && view.status === 'playing' && view.turn && view.turn.seat === view.you.seat;
  if (!mine) {
    turnKey = null;
    turnPending = null;
    clearTicks();
    return;
  }
  const key = JSON.stringify([view.hand_number, view.hand, view.trick.cards.length]);
  if (key !== turnKey && key !== turnPending) {
    turnPending = key;
    clearTicks();
  }
  const draws = drawing();
  const busy = Object.keys(flying()).length || Object.keys(draws.seats).length || Object.keys(draws.cards).length
    || dealing() || lastTrick || laidDown || summary || nextSummary;
  if (!turnPending || busy) return;
  turnKey = turnPending;
  turnPending = null;
  // Durante le pause la vista dice il turno pieno: il conto parte adesso
  const left = view.turn.seconds_left * 1000;
  for (let s = TICK_SECONDS; s >= 1; s -= 1) {
    const wait = left - s * 1000;
    if (wait >= 0) tickTimers.push(setTimeout(() => playSound(s === 1 ? 'last_tick' : 'tick'), wait));
  }
}

function clearTicks() {
  tickTimers.forEach(clearTimeout);
  tickTimers = [];
}

/** P103: vittoria, sconfitta o pareggio, quando compare il riquadro di fine partita. */
function resultSound() {
  if (!resultPending || !view.result || lastTrick || laidDown) return;
  resultPending = false;
  const winner = view.result.winner_team;
  const myTeam = view.players.find((player) => player.seat === view.you.seat).team;
  playSound(winner === null ? 'tie' : winner === myTeam ? 'win' : 'lose');
}

/**
 * P97: la carta che era sotto il mouse, ridisegnata, nasce già sollevata
 * (card--hover-kept, css/components/card.css); altrimenti il pulsante nuovo parte
 * abbassato e si rialza con la transizione a ogni vista. Al primo movimento vero del
 * mouse decide di nuovo ":hover".
 */
function keepHover(old) {
  const same = [...root.querySelectorAll('button.card')].find((card) => card.dataset.suit === old.dataset.suit
    && card.dataset.rank === old.dataset.rank && ('adviseCard' in card.dataset) === ('adviseCard' in old.dataset));
  if (!same) return;
  same.classList.add('card--hover-kept');
  document.addEventListener('pointermove', dropKeptHover, { once: true });
}

function dropKeptHover() {
  root.querySelectorAll('.card--hover-kept').forEach((card) => card.classList.remove('card--hover-kept'));
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
  phrasePauseTimer = redrawAfter(ms);
}

function showBubble(seat, text) {
  playSound('phrase'); // P109: anche le frasi del tavolo hanno il loro suono
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

/*
 * P104: su iPhone Safari ingrandisce la pagina con il doppio tocco anche con
 * touch-action: manipulation (P69, P98). Al tavolo, il secondo tocco con un dito che
 * arriva entro DOUBLE_TAP_MS dal precedente non lascia fare lo zoom (preventDefault
 * sul touchend); così però il browser non manda nemmeno il clic, e la pagina lo
 * manda da sé al pulsante o alla carta toccata: due tocchi veloci non si perdono.
 * Lo zoom con due dita resta.
 */
const DOUBLE_TAP_MS = 300;
let lastTapEnd = -Infinity;
document.addEventListener('touchend', (event) => {
  if (event.touches.length || event.changedTouches.length !== 1) return; // dita ancora giù: due dita
  const now = event.timeStamp;
  const double = now - lastTapEnd <= DOUBLE_TAP_MS;
  lastTapEnd = now;
  if (!double || !event.cancelable) return;
  event.preventDefault();
  const target = event.target instanceof Element
    ? event.target.closest('button, a[href], [role="button"], summary, label') : null;
  if (target && !target.disabled) target.click();
}, { passive: false });

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

/**
 * P93: consiglio al compagno (D46). Toccando una sua carta gliela consigli; toccando
 * quella già consigliata il consiglio si toglie (card null). Uno alla volta: finché
 * non arriva la risposta le sue carte sono spente.
 */
async function onAdvise(card) {
  if (adviceSending || !view || replaced) return;
  const next = myAdvice && sameCard(myAdvice, card) ? null : card;
  if (demo) {
    myAdvice = next;
    setStatus(next ? `Prova: consigli ${cardName(next)}. In partita il consiglio va al compagno.` : 'Prova: consiglio tolto.');
    return;
  }
  adviceSending = true;
  redraw();
  const answer = await send(EVENTS.GAME_ADVISE, { game_id: gameId, card: next });
  adviceSending = false;
  if (answer.ok) myAdvice = next;
  setStatus(answer.ok ? '' : answer.error.message);
}

/** game:advice: il compagno ti consiglia una carta (o toglie il consiglio, card null). */
function onAdvice(data) {
  if (replaced || !data) return;
  receivedAdvice = data.card ? { seat: data.seat, card: data.card } : null;
  redraw();
}

/** P85: "Cala le carte" (solo con legal.lay_down; il doppio clic lo ferma waiting, e la version). */
function onLayDown() {
  if (demo) {
    setStatus('Prova: vuoi calare le carte. In partita la richiesta va al server.');
    return;
  }
  sendMove(EVENTS.GAME_LAY_DOWN, {});
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
    if (view && answer.error.code === 'not_found') showGone();
    else if (view) setStatus(answer.error.message);
    else showMessage(answer.error.message);
  }
}

const GONE_HOME_MS = 5000;

/**
 * P95: la partita che si stava giocando non esiste più (per esempio il server si è
 * riavviato: le partite stanno solo in memoria). Al posto del tavolo un riquadro con
 * "Torna alla home", e dopo GONE_HOME_MS si torna alla home da soli. La pagina si
 * ferma come per game:replaced: niente più ridisegni né mosse.
 */
function showGone() {
  replaced = true;
  clearTicks(); // P103
  const panel = el('div', { class: 'table__gone panel', data: { gameGone: '' }, attrs: { role: 'alert' } }, [
    el('h2', { text: 'La partita è stata interrotta' }),
    el('p', { text: 'Il server si è riavviato o la partita non esiste più.' }),
    el('a', { class: 'btn btn--primary', text: 'Torna alla home', attrs: { href: '/' } }),
  ]);
  root.replaceChildren(panel);
  setTimeout(() => window.location.assign('/'), GONE_HOME_MS);
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
  playSound('sing'); // P103

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
  on(EVENTS.GAME_ADVICE, onAdvice);
  on(EVENTS.GAME_REPLACED, () => {
    replaced = true;
    clearTicks(); // P103
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

// P79: tutte le immagini delle carte subito, così nessuna carta resta bianca quando
// compare; data-cards-ready (per i test) quando sono pronte. Dopo il load della
// pagina: prima le immagini già sul tavolo, e il load non aspetta le altre 45
function preloadCards() {
  preloadCardImages().then((ok) => {
    if (ok) root.dataset.cardsReady = '1';
  });
  preloadSounds(); // P109: anche i suoni, dopo il load (non lo fanno aspettare)
}
if (document.readyState === 'complete') preloadCards();
else window.addEventListener('load', preloadCards, { once: true });

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
