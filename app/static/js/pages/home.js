/**
 * Pagina della home (P22), dal prototipo approvato (P52).
 *
 * - Parti comuni (navbar, pannello statistiche, finestra "Accedi o registrati"):
 *   core/layout.js (P40).
 * - Un'unica funzione render(state) ridisegna "giocatori online", l'avviso di
 *   rientro e la schermata di coda dallo stato della pagina. Lo stato ha la forma
 *   del contratto (docs/CONTRATTO-SOCKET.md): home:status (5.1), queue:status (4),
 *   la lista degli amici di GET /friends/ (2.2) e i rating di GET /stats/me (2.1).
 * - Coda vera (P28, P29): "Gioca" nella Partita Veloce (1v1 e 2v2) manda
 *   queue:join (con un request_id per clic); la schermata di coda si apre con la
 *   risposta e si aggiorna con queue:status (anche dalle altre schede dello
 *   stesso utente); "Annulla" manda queue:leave e la schermata si chiude con
 *   queue:left (con "partner_left" un messaggio dice che il compagno è uscito);
 *   game:start porta al tavolo.
 * - Stato vero della home (P44): home:status arriva appena la pagina si collega e
 *   a ogni cambiamento (utenti online, partita in corso finita) e prende sempre il
 *   posto di quello dei dati finti. Senza login la pagina non si collega.
 * - Inviti a partita (P47, contratto 5.3): la lista degli amici da invitare viene
 *   da GET /friends/ e si rilegge con friends:presence e friends:changed. "Invita"
 *   manda invite:send; invite:update aggiorna la carta-modal (setInviteStatus);
 *   chiudere la carta con un invito aperto manda invite:cancel; "Gioca" dopo
 *   l'accettazione manda invite:start (1v1: arriva game:start; 2v2: la risposta è
 *   lo stato della coda con il compagno). L'invito ricevuto si apre in una
 *   finestra (components/InviteDialog.js) con "Rifiuta" e "Accetta".
 * - Il resto per ora viene dai dati finti di app/static/dev/ (attributi
 *   data-demo-*, solo in sviluppo e nei test): i rating di "In breve", e lo stato
 *   della home e gli amici finché non arrivano quelli veri. Con ?demo=rientro
 *   l'avviso di rientro resta quello finto (si prova senza una partita vera).
 * - Carte-pulsante: senza login aprono "Accedi o registrati" (P40); con il login
 *   la carta-modal della modalità (components/ModeModal.js).
 */

import { initLayout, isLoggedIn } from '../core/layout.js';
import { connect, on, send } from '../core/socket.js';
import { EVENTS } from '../core/events.js';
import { openLoginPrompt } from '../components/LoginPrompt.js';
import { initCardBackground } from '../components/CardBackground.js';
import { openModeModal, setInviteStatus } from '../components/ModeModal.js';
import { openInviteDialog } from '../components/InviteDialog.js';
import { QueueOverlay, enableQueueCancel, setQueueSeconds } from '../components/QueueOverlay.js';
import { ResumeBanner } from '../components/ResumeBanner.js';
import { el, icon } from '../utils/dom.js';

initLayout();

const root = document.querySelector('[data-home]');
const background = document.querySelector('[data-bg-cards]');
const imgBase = background.dataset.imgBase;
const demo = Boolean(root.dataset.demoHomeUrl);

// Stato della pagina
const state = {
  status: null,     // home:status: { online_count, resume }; null finché non arriva
  queue: null,      // queue:status, oppure null se non si è in coda
  friends: [],      // amici (GET /friends/: friends), per la lista da invitare
  ratings: null,    // rating dell'utente (GET /stats/me: ratings), per "In breve"
};

// Schermata di coda aperta e conteggio dei secondi (la pagina li conta da sola
// tra un queue:status e l'altro, contratto 4)
const queueView = { overlay: null, queue: null, since: 0, timer: null };

// ------------------------------------------------------------
// Disegno
// ------------------------------------------------------------

function renderQueue(queue) {
  if (queueView.queue === queue) return;
  // Un queue:status nuovo (intervallo allargato) ridisegna la schermata: se "Annulla"
  // aspettava già la risposta del server, resta disattivato.
  const cancelling = Boolean(queueView.overlay?.querySelector('[data-queue-cancel]').disabled);
  if (queueView.overlay) {
    clearInterval(queueView.timer);
    queueView.overlay.close();
    queueView.overlay.remove();
    queueView.overlay = null;
  }
  queueView.queue = queue;
  if (!queue) return;
  const overlay = QueueOverlay(queue, { imgBase, onCancel: leaveQueue });
  if (cancelling) overlay.querySelector('[data-queue-cancel]').disabled = true;
  document.body.append(overlay);
  overlay.showModal();
  queueView.overlay = overlay;
  queueView.since = Date.now();
  queueView.timer = setInterval(() => {
    setQueueSeconds(overlay, queue.seconds_waiting + (Date.now() - queueView.since) / 1000);
  }, 1000);
}

/** Ridisegna la home dallo stato. */
function render(current) {
  const { status } = current;
  const banner = status?.resume ? ResumeBanner(status.resume) : null;
  const resumeSlot = root.querySelector('[data-resume-slot]');
  resumeSlot.replaceChildren(...(banner ? [banner] : []));
  resumeSlot.hidden = !banner;

  // "giocatori online" nello stesso spazio: nascosto mentre c'è l'avviso di rientro
  const online = root.querySelector('[data-online]');
  online.hidden = Boolean(banner) || typeof status?.online_count !== 'number';
  root.querySelector('[data-online-count]').textContent = online.hidden ? '' : String(status.online_count);

  renderQueue(current.queue);
}

// ------------------------------------------------------------
// Messaggi nella pagina (stesso aspetto di quelli del server, partials/flash.html)
// ------------------------------------------------------------

const MESSAGE_ICONS = { info: 'info', error: 'error', success: 'check_circle' };

function showMessage(text, kind = 'info') {
  let list = document.querySelector('[data-flash]');
  if (!list) {
    list = el('div', { class: 'flash-list', data: { flash: '' } });
    document.body.append(list);
  }
  const item = el('p', {
    class: `flash flash--${kind}`,
    attrs: { role: kind === 'error' ? 'alert' : 'status' },
    data: { flashKind: kind },
  }, [icon(MESSAGE_ICONS[kind]), el('span', { text })]);
  list.append(item);
  setTimeout(() => item.remove(), 7500);   // sparisce dopo 7 secondi (layout.css)
}

// ------------------------------------------------------------
// Azioni: carta-pulsante, inviti, Gioca, Annulla
// ------------------------------------------------------------

// ------------------------------------------------------------
// Inviti a partita (P47, contratto 5.3)
// ------------------------------------------------------------

let outgoing = null;     // invito mandato e aperto: { id, friendId, status }
let incoming = null;     // finestra dell'invito ricevuto (InviteDialog)
let realFriends = false; // è arrivata la lista vera: i dati finti non la sostituiscono più
let sending = false;     // invite:send in attesa di risposta
let cancelAfterSend = false;   // la carta si è chiusa prima della risposta: si annulla appena arriva

async function sendInvite({ friend, mode, targetScore }) {
  sending = true;
  cancelAfterSend = false;
  const answer = await send(EVENTS.INVITE_SEND, {
    request_id: newRequestId(), user_id: friend.user_id, mode, target_score: targetScore,
  });
  sending = false;
  if (answer.ok && cancelAfterSend) {
    send(EVENTS.INVITE_CANCEL, { invite_id: answer.data.invite_id });
    return;
  }
  if (!answer.ok) {
    showMessage(answer.error.message, 'error');
    setInviteStatus(friend.user_id, 'cancelled');   // si può invitare di nuovo
    return;
  }
  outgoing = { id: answer.data.invite_id, friendId: friend.user_id, status: answer.data.status };
}

function cancelInvite() {
  if (sending) cancelAfterSend = true;
  if (!outgoing) return;
  send(EVENTS.INVITE_CANCEL, { invite_id: outgoing.id });
  outgoing = null;
}

async function startInvite() {
  if (!outgoing || outgoing.status !== 'accepted') return;
  const answer = await send(EVENTS.INVITE_START, { invite_id: outgoing.id });
  if (!answer.ok) {
    showMessage(answer.error.message, 'error');
    return;
  }
  outgoing = null;
  if (answer.data) showQueue(answer.data);   // 2v2: la coppia è in coda; 1v1: arriva game:start
}

function onInviteReceived(invite) {
  if (starting || !invite?.invite_id) return;
  incoming?.close();
  incoming = openInviteDialog(invite, {
    onAccept: () => send(EVENTS.INVITE_ACCEPT, { invite_id: invite.invite_id }),
    onDecline: () => send(EVENTS.INVITE_DECLINE, { invite_id: invite.invite_id }),
  });
}

function onInviteUpdate({ invite_id: id, status } = {}) {
  if (outgoing && outgoing.id === id) {
    outgoing.status = status;
    if (status !== 'started') setInviteStatus(outgoing.friendId, status);
    if (status !== 'pending' && status !== 'accepted') outgoing = null;
  }
  if (incoming && incoming.inviteId === id) {
    incoming.setStatus(status);
    if (status !== 'pending' && status !== 'accepted') incoming = null;
  }
}

async function loadFriends() {
  const url = document.querySelector('[data-friends-button]')?.dataset.friendsUrl;
  if (!url) return;
  try {
    const response = await fetch(`${url.replace(/\/$/, '')}/`, {
      headers: { Accept: 'application/json' }, credentials: 'same-origin',
    });
    const body = await response.json();
    if (!body.ok) return;
    realFriends = true;
    state.friends = body.data.friends;
  } catch {
    // senza lista nuova resta quella di prima
  }
}

// ------------------------------------------------------------
// Coda vera (P28, contratto 4)
// ------------------------------------------------------------

let realQueue = false;   // la coda aperta è quella del server (non quella dei dati finti)
let joining = false;     // queue:join in attesa di risposta: niente doppio invio
let starting = false;    // è arrivato game:start: si sta andando al tavolo

/** request_id (contratto 1.3): un codice casuale per ogni clic su "Gioca". */
function newRequestId() {
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  return [...bytes].map((b) => b.toString(16).padStart(2, '0')).join('');
}

async function joinQueue(mode, targetScore) {
  if (joining || state.queue || starting) return;
  joining = true;
  const answer = await send(EVENTS.QUEUE_JOIN, { request_id: newRequestId(), mode, target_score: targetScore });
  joining = false;
  if (!answer.ok) {
    showMessage(answer.error.message, 'error');
    return;
  }
  if (starting) return;
  realQueue = true;
  state.queue = answer.data;
  render(state);
}

function showQueue(queue) {
  if (starting) return;
  realQueue = true;
  state.queue = queue;
  render(state);
}

function closeQueue() {
  realQueue = false;
  state.queue = null;
  render(state);
}

function onQueueLeft({ reason } = {}) {
  if (reason === 'partner_left' && state.queue) {
    showMessage('Il tuo compagno è uscito dalla coda.', 'info');
  }
  closeQueue();
}

// ------------------------------------------------------------
// Stato vero della home (P44, contratto 5.1)
// ------------------------------------------------------------

let realStatus = false;   // è arrivato home:status: i dati finti non lo sostituiscono più

function showStatus(status) {
  if (root.dataset.demoState === 'rientro') return;   // prova dell'avviso con i dati finti
  realStatus = true;
  state.status = status;
  render(state);
}

function goToTable({ url } = {}) {
  if (typeof url !== 'string' || !url.startsWith('/game/')) return;
  starting = true;
  window.location.assign(url);
}

function play({ kind, mode, targetScore }) {
  if (!navigator.onLine) {
    showMessage('Sei offline: potrai giocare appena torna la connessione.', 'error');
    return;
  }
  if (kind === 'veloce') joinQueue(mode, targetScore);
  else startInvite();   // "Gioca con un amico": si attiva solo dopo l'accettazione
}

// "Annulla": con la coda vera queue:leave, e la schermata si chiude con la risposta;
// con i dati finti si esce subito.
async function leaveQueue() {
  if (!realQueue) {
    closeQueue();
    return;
  }
  const answer = await send(EVENTS.QUEUE_LEAVE, {});
  if (!answer.ok) {
    showMessage(answer.error.message, 'error');
    if (queueView.overlay) enableQueueCancel(queueView.overlay);
    return;
  }
  closeQueue();
}

function openTile(tile) {
  if (!isLoggedIn()) {
    openLoginPrompt();
    return;
  }
  if (state.queue) return;
  openModeModal({
    kind: tile.dataset.kind,
    mode: tile.dataset.mode,
    tile,
    ratings: state.ratings,
    friends: state.friends,
    onPlay: play,
    onInvite: sendInvite,
    onCancelInvite: cancelInvite,
  });
}

// Carte-pulsante in 3D: con il mouse la carta si inclina verso il puntatore e il
// riflesso di luce lo segue. Solo con un mouse vero e senza "riduci movimento".
const TILT_MAX = 10;   // gradi di inclinazione massima

function initTilt(tile) {
  const allowed = window.matchMedia('(hover: hover) and (pointer: fine)').matches
    && !window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (!allowed) return;
  tile.addEventListener('pointermove', (event) => {
    // Posizione del puntatore sulla carta, da 0 a 1 in orizzontale e in verticale
    const r = tile.getBoundingClientRect();
    const px = Math.min(1, Math.max(0, (event.clientX - r.left) / r.width));
    const py = Math.min(1, Math.max(0, (event.clientY - r.top) / r.height));
    tile.style.setProperty('--ry', `${((px - 0.5) * 2 * TILT_MAX).toFixed(1)}deg`);
    tile.style.setProperty('--rx', `${((0.5 - py) * 2 * TILT_MAX).toFixed(1)}deg`);
    tile.style.setProperty('--gx', `${(px * 100).toFixed(0)}%`);
    tile.style.setProperty('--gy', `${(py * 100).toFixed(0)}%`);
  });
  tile.addEventListener('pointerleave', () => {
    for (const name of ['--rx', '--ry', '--gx', '--gy']) tile.style.removeProperty(name);
  });
}

for (const tile of root.querySelectorAll('[data-tile]')) {
  tile.addEventListener('click', () => openTile(tile));
  initTilt(tile);
}

// ------------------------------------------------------------
// Dati finti (solo in sviluppo e nei test)
// ------------------------------------------------------------

async function fetchJson(url) {
  const response = await fetch(url, { headers: { Accept: 'application/json' } });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

async function loadDemo() {
  const { demoHomeUrl, demoFriendsUrl, demoStatsUrl, demoState } = root.dataset;
  const [home, friends, stats] = await Promise.allSettled([
    fetchJson(demoHomeUrl), fetchJson(demoFriendsUrl), fetchJson(demoStatsUrl),
  ]);
  if (home.status === 'fulfilled') {
    const demoData = home.value;
    if (demoState === 'rientro') state.status = demoData['home:status con partita in corso'];
    else if (!realStatus) state.status = demoData['home:status'];
  }
  if (friends.status === 'fulfilled' && !realFriends) state.friends = friends.value['GET /friends/']?.friends ?? [];
  if (stats.status === 'fulfilled') state.ratings = stats.value.ratings ?? null;
  render(state);
}

initCardBackground(background);
render(state);
if (isLoggedIn()) {
  on(EVENTS.HOME_STATUS, showStatus);
  on(EVENTS.QUEUE_STATUS, showQueue);
  on(EVENTS.QUEUE_LEFT, onQueueLeft);
  on(EVENTS.GAME_START, goToTable);
  on(EVENTS.INVITE_RECEIVED, onInviteReceived);
  on(EVENTS.INVITE_UPDATE, onInviteUpdate);
  on(EVENTS.FRIENDS_PRESENCE, loadFriends);
  on(EVENTS.FRIENDS_CHANGED, loadFriends);
  connect();
  loadFriends();
}
if (demo) loadDemo();
