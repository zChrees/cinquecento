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
 * - P25: "Esci", dopo la conferma, manda game:leave (la partita è persa per abbandono)
 *   e poi torna alla home; a partita finita torna alla home senza chiedere.
 *   I secondi del turno e quelli per rientrare di chi è scollegato arrivano con la
 *   vista; la pagina li fa scendere da sola (contratto 1.1), contando dal momento in
 *   cui la vista è arrivata.
 * - P57, momenti del tavolo, decisi confrontando la vista nuova con quella di prima
 *   (mai alla prima vista, né dopo un rientro nella pagina):
 *   - presa appena chiusa (last_trick cambiato nella stessa mano): resta al centro
 *     per LAST_TRICK_MS, o finché qualcuno gioca la prima carta della presa nuova;
 *     la mano non si blocca mai. L'ultima presa di una mano non arriva (il motore
 *     comincia subito la mano nuova, con last_trick null): si vede il riepilogo;
 *   - riepilogo di fine mano (hand_number salito): SUMMARY_MS, o fino a "Ok";
 *   - carte del canto (game:sang, D15): accanto a chi ha cantato per show_seconds.
 *   Con "riduci movimento" i tempi sono gli stessi, senza animazioni.
 * - Solo nella prova (?demo=): la pagina accetta gli eventi del browser "demo:state"
 *   (una vista nuova) e "demo:sang" (un canto) sull'elemento [data-table], per i
 *   test e per provare i momenti dalla console.
 */

import { initLayout } from '../core/layout.js';
import { connect, on, onStatus, send } from '../core/socket.js';
import { EVENTS, NOT_LOGGED_IN } from '../core/events.js';
import { confirmModal } from '../components/Modal.js';
import { Table } from '../components/Table.js';
import { cardName } from '../components/Card.js';

initLayout();

const root = document.querySelector('[data-table]');
const gameId = root.dataset.gameId;
const demo = Boolean(root.dataset.demoUrl);
const NO_MOVES = Object.freeze({ play: [], sing: [] });
const LAST_TRICK_MS = 1500;
const SUMMARY_MS = 5000;

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
const sang = {}; // posto → { event, timer }

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

function hideLastTrick() {
  clearTimeout(lastTrickTimer);
  lastTrick = null;
}

function closeSummary() {
  clearTimeout(summaryTimer);
  summary = null;
}

/** Momenti che cominciano con la vista nuova (P57): presa appena chiusa, fine mano. */
function noticeMoments(previous, next) {
  if (!previous) return; // prima vista: niente da mostrare "per un momento"
  if (next.hand_number !== previous.hand_number) hideLastTrick();
  if (next.last_trick && next.hand_number === previous.hand_number
      && JSON.stringify(next.last_trick) !== JSON.stringify(previous.last_trick)) {
    hideLastTrick();
    lastTrick = next.last_trick;
    lastTrickTimer = setTimeout(() => { lastTrick = null; redraw(); }, LAST_TRICK_MS);
  }
  if (next.hand_number > previous.hand_number && next.last_hand) {
    closeSummary();
    summary = next.last_hand;
    summaryTimer = setTimeout(() => { summary = null; redraw(); }, SUMMARY_MS);
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
  // Mentre si aspetta la risposta a una mossa nessuna carta e nessun canto sono attivi
  const shown = timed(waiting || leaving ? { ...view, legal: NO_MOVES } : view);
  const moments = {
    lastTrick,
    summary,
    onCloseSummary: () => { closeSummary(); redraw(); },
    sang: Object.fromEntries(Object.entries(sang).map(([seat, { event }]) => [seat, event])),
  };
  root.replaceChildren(Table(shown, { onPlay, onSing, onLeave }, status, moments));
}

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
    } else if (view) {
      setStatus('Connessione persa: riprovo a collegarmi…');
    }
  });
  connect();
}

if (demo) {
  // Solo nella prova: viste e canti finti mandati dai test o dalla console (P57)
  root.addEventListener('demo:state', (event) => onState(event.detail));
  root.addEventListener('demo:sang', (event) => onSang(event.detail));
  loadDemo(root.dataset.demoUrl);
} else {
  showMessage('In attesa della partita…');
  startGame();
}
