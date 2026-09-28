/**
 * Pagina del tavolo (P21). Un'unica funzione render(vista) ridisegna il tavolo
 * dalla vista ricevuta (contratto 3.3): niente stato sparso nella pagina.
 *
 * Per ora funziona con le viste finte (?demo=1v1, ?demo=2v2: attributo
 * data-demo-url). P24 collega i socket: game:join all'apertura, poi a ogni
 * game:state chiama render(vista); le mosse vanno al server con game:play_card e
 * game:sing, "Esci" con game:leave.
 */

import { initLayout } from '../core/layout.js';
import { confirmModal } from '../components/Modal.js';
import { Table } from '../components/Table.js';
import { cardName } from '../components/Card.js';

initLayout();

const root = document.querySelector('[data-table]');
const demo = Boolean(root.dataset.demoUrl);
let view = null;
let status = '';

function showMessage(text) {
  root.replaceChildren();
  const message = document.createElement('p');
  message.className = 'table__message';
  message.dataset.tableMessage = '';
  message.textContent = text;
  root.append(message);
}

/** Ridisegna il tavolo dalla vista. È l'unico punto che tocca il DOM del tavolo. */
function render(next) {
  view = next;
  root.replaceChildren(Table(view, { onPlay, onSing, onLeave }, status));
}

function setStatus(text) {
  status = text;
  if (view) render(view);
}

function onPlay(card) {
  // P24: game:play_card con game_id, version e card; pulsanti disattivati fino alla risposta
  if (demo) setStatus(`Prova: hai scelto ${cardName(card)}. In partita la carta va al server.`);
}

function onSing(suit) {
  // P24: game:sing con game_id, version e suit
  if (demo) setStatus(`Prova: vuoi cantare a ${suit}. In partita il canto va al server.`);
}

async function onLeave() {
  const ok = await confirmModal({
    title: 'Vuoi uscire dalla partita?',
    message: view && view.mode === '2v2'
      ? 'La partita sarà persa per abbandono, anche per il tuo compagno.'
      : 'La partita sarà persa per abbandono.',
    confirmLabel: 'Esci',
    danger: true,
  });
  if (!ok) return;
  // P24: game:leave, poi la home
  window.location.assign('/');
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

if (demo) {
  loadDemo(root.dataset.demoUrl);
} else {
  showMessage('In attesa della partita…');
}
