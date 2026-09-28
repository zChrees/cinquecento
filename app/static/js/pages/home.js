/**
 * Pagina della home (P22), dal prototipo approvato (P52).
 *
 * - Parti comuni (navbar, pannello statistiche, finestra "Accedi o registrati"):
 *   core/layout.js (P40).
 * - Un'unica funzione render(state) ridisegna "giocatori online", l'avviso di
 *   rientro e la schermata di coda dallo stato della pagina. Lo stato ha la forma
 *   del contratto (docs/CONTRATTO-SOCKET.md): home:status (5.1), queue:status (4),
 *   la lista degli amici di GET /friends/ (2.2) e i rating di GET /stats/me (2.1).
 * - Per ora lo stato viene dai dati finti di app/static/dev/ (attributi
 *   data-demo-*, solo in sviluppo e nei test; con ?demo=rientro c'è l'avviso di
 *   rientro). Più avanti: la coda con i socket (P28), home:status (P44), gli
 *   inviti veri (P47). Senza dati finti (demo vera) "giocatori online" resta
 *   nascosto e "Gioca" avvisa che la ricerca non è ancora attiva.
 * - Carte-pulsante: senza login aprono "Accedi o registrati" (P40); con il login
 *   la carta-modal della modalità (components/ModeModal.js).
 */

import { initLayout, isLoggedIn } from '../core/layout.js';
import { openLoginPrompt } from '../components/LoginPrompt.js';
import { initCardBackground } from '../components/CardBackground.js';
import { openModeModal, setInviteStatus } from '../components/ModeModal.js';
import { QueueOverlay, setQueueSeconds } from '../components/QueueOverlay.js';
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
  if (queueView.overlay) {
    clearInterval(queueView.timer);
    queueView.overlay.close();
    queueView.overlay.remove();
    queueView.overlay = null;
  }
  queueView.queue = queue;
  if (!queue) return;
  const overlay = QueueOverlay(queue, { imgBase, onCancel: leaveQueue });
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

let demoData = null;     // home_esempio.json
let inviteTimer = null;

// Dati finti: l'amico accetta dopo 2 secondi, come nel prototipo. Gli inviti veri arrivano con P47.
function sendInvite({ friend }) {
  clearTimeout(inviteTimer);
  inviteTimer = setTimeout(() => setInviteStatus(friend.user_id, 'accepted'), 2000);
}

function cancelInvite() {
  clearTimeout(inviteTimer);
}

function play({ kind, mode, targetScore, invitee }) {
  clearTimeout(inviteTimer);
  if (!navigator.onLine) {
    showMessage('Sei offline: potrai giocare appena torna la connessione.', 'error');
    return;
  }
  if (!demo || !demoData) {
    // La coda arriva con P28, gli inviti con P47
    showMessage('La ricerca della partita non è ancora attiva.', 'info');
    return;
  }
  if (kind === 'amico' && mode === '1v1') {
    showMessage(`Prova: qui comincerebbe la partita contro ${invitee.username}.`, 'info');
    return;
  }
  // Dati finti: si entra subito in coda. Con P28: queue:join, poi la risposta del server.
  const example = invitee ? demoData['queue:status 2v2 con un amico'] : demoData['queue:status'];
  const partner = invitee ? { user_id: invitee.user_id, username: invitee.username, avatar: invitee.avatar } : null;
  state.queue = { ...example, mode, target_score: targetScore, partner };
  render(state);
}

// Dati finti: si esce subito dalla coda. Con P28: queue:leave, e la schermata si chiude con la risposta.
function leaveQueue() {
  state.queue = null;
  render(state);
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
    demoData = home.value;
    state.status = demoState === 'rientro' ? demoData['home:status con partita in corso'] : demoData['home:status'];
  }
  if (friends.status === 'fulfilled') state.friends = friends.value['GET /friends/']?.friends ?? [];
  if (stats.status === 'fulfilled') state.ratings = stats.value.ratings ?? null;
  render(state);
}

initCardBackground(background);
render(state);
if (demo) loadDemo();
