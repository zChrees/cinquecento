/**
 * Parti comuni a tutte le pagine (P40): navbar, pannello statistiche, logo e
 * finestra "Accedi o registrati". Ogni pagina lo importa e lo avvia una volta:
 *
 *   import { initLayout } from '../core/layout.js';
 *   initLayout();
 *
 * Il markup sta in partials/navbar.html. Più avanti qui si aggancia anche il
 * pannello amici (P46).
 */

import { clear } from '../utils/dom.js';
import { openLoginPrompt } from '../components/LoginPrompt.js';
import { StatsPanel, StatsMessage, fetchStats } from '../components/StatsPanel.js';

function reduceMotion() {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

/** true se l'utente ha fatto il login (attributi del <body>, contratto 1.5). */
export function isLoggedIn() {
  return document.body.dataset.userId !== '';
}

// ------------------------------------------------------------
// Finestre della navbar: si chiudono con la X, con Esc e toccando fuori,
// dopo l'animazione di uscita (.is-closing). Con "riduci movimento" subito.
// ------------------------------------------------------------

function closeDialog(dialog) {
  if (!dialog.open || dialog.classList.contains('is-closing')) return;
  const done = () => {
    dialog.classList.remove('is-closing');
    dialog.close();
  };
  if (reduceMotion()) {
    done();
    return;
  }
  dialog.classList.add('is-closing');
  if (getComputedStyle(dialog).animationName === 'none') {
    done();
    return;
  }
  dialog.addEventListener('animationend', function onEnd(event) {
    if (event.target !== dialog) return;
    dialog.removeEventListener('animationend', onEnd);
    done();
  });
  // Se l'animazione non parte (per esempio scheda in secondo piano), chiude comunque
  setTimeout(() => dialog.classList.contains('is-closing') && done(), 400);
}

function wireDialog(dialog) {
  // Esc: il browser chiuderebbe subito; lo fermiamo per far vedere l'animazione
  dialog.addEventListener('cancel', (event) => {
    event.preventDefault();
    closeDialog(dialog);
  });
  // Tocco fuori: il clic arriva al <dialog> stesso, fuori dal suo riquadro
  dialog.addEventListener('click', (event) => {
    if (event.target !== dialog) return;
    const r = dialog.getBoundingClientRect();
    const inside = event.clientX >= r.left && event.clientX <= r.right
      && event.clientY >= r.top && event.clientY <= r.bottom;
    if (!inside) closeDialog(dialog);
  });
  for (const button of dialog.querySelectorAll('[data-close]')) {
    button.addEventListener('click', () => closeDialog(dialog));
  }
}

// ------------------------------------------------------------
// Pannello statistiche: si apre dall'avatar e a ogni apertura ricarica i dati
// ------------------------------------------------------------

function initStats() {
  const dialog = document.getElementById('stats');
  const opener = document.querySelector('[data-open-stats]');
  if (!dialog || !opener) return;
  const body = dialog.querySelector('[data-stats-body]');
  let loading = false;

  async function load() {
    if (loading) return;
    loading = true;
    if (!body.firstChild) body.append(StatsMessage('Caricamento…'));
    try {
      const stats = await fetchStats(dialog.dataset.statsUrl);
      clear(body);
      body.append(StatsPanel(stats));
    } catch (error) {
      clear(body);
      body.append(StatsMessage(
        error.message === 'offline'
          ? 'Sei offline: le statistiche arrivano appena torna la connessione.'
          : 'Statistiche non disponibili. Riprova tra poco.',
      ));
    } finally {
      loading = false;
    }
  }

  wireDialog(dialog);
  opener.addEventListener('click', () => {
    if (dialog.open) return;   // doppio clic
    dialog.showModal();
    load();
  });

  // Esci: niente doppio invio del modulo
  const logout = dialog.querySelector('[data-logout]');
  logout?.form.addEventListener('submit', (event) => {
    if (!navigator.onLine) {
      event.preventDefault();
      return;
    }
    logout.disabled = true;
  });
}

// ------------------------------------------------------------
// Senza login: avatar e amici aprono "Accedi o registrati per giocare"
// ------------------------------------------------------------

function initLoginPrompt() {
  for (const button of document.querySelectorAll('[data-login-prompt]')) {
    button.addEventListener('click', () => openLoginPrompt());
  }
}

// ------------------------------------------------------------
// Logo: le due carte di dorso ogni tanto si girano e mostrano Cavallo e Re
// di un seme, poi tornano sul dorso; al giro dopo tocca al seme successivo.
// Con "riduci movimento" restano ferme sul dorso.
// ------------------------------------------------------------

const LOGO_SUITS = ['coppe', 'denari', 'spade', 'bastoni'];
const LOGO_TIMING = { back: 3000, front: 2600, stagger: 180, flip: 900 };

function initLogo() {
  const mark = document.querySelector('[data-logo-cards]');
  if (!mark || reduceMotion()) return;
  const cards = mark.querySelectorAll('.logo__card');
  if (cards.length !== 2) return;
  const base = mark.dataset.imgBase;
  const faces = [...cards].map((card) => card.querySelector('.logo__face--front'));
  const src = (who, suit) => `${base}${who}-${suit}.webp`;

  function flip(card, front) {
    card.classList.add('is-flipping');
    card.classList.toggle('is-front', front);
    setTimeout(() => card.classList.remove('is-flipping'), LOGO_TIMING.flip);
  }

  function cycle(i) {
    const suit = LOGO_SUITS[i % LOGO_SUITS.length];
    // Le facce si cambiano mentre si vede il dorso, quindi il cambio non si nota
    faces[0].src = src('cavallo', suit);
    faces[1].src = src('re', suit);
    setTimeout(() => {
      flip(cards[0], true);
      setTimeout(() => flip(cards[1], true), LOGO_TIMING.stagger);
      setTimeout(() => {
        flip(cards[0], false);
        setTimeout(() => flip(cards[1], false), LOGO_TIMING.stagger);
        setTimeout(() => cycle(i + 1), LOGO_TIMING.flip + LOGO_TIMING.stagger);
      }, LOGO_TIMING.flip + LOGO_TIMING.front);
    }, LOGO_TIMING.back);
  }

  // Tutte le figure caricate prima, così il giro non scatta
  const preload = LOGO_SUITS.flatMap((suit) => ['cavallo', 're'].map((who) => {
    const img = new Image();
    img.src = src(who, suit);
    return img.decode().catch(() => {});
  }));
  Promise.all(preload).then(() => cycle(0));
}

let started = false;

/** Avvia navbar, pannello statistiche, logo e finestra di accesso. Da chiamare una volta per pagina. */
export function initLayout() {
  if (started) return;
  started = true;
  initStats();
  initLoginPrompt();
  initLogo();
}
