/**
 * Contenuto del pannello statistiche (P40): partite, vinte, perse, percentuale
 * di vittorie e rating 1v1 e 2v2 (contratto, docs/CONTRATTO-SOCKET.md, 2.1).
 *
 * I dati arrivano da GET /stats/me (P30), nella forma {"ok": true, "data": {...}},
 * sempre, anche in sviluppo; app/static/dev/statistiche_esempio.json resta solo
 * come esempio del contratto.
 * Il pannello (dialog #stats) sta in partials/navbar.html; lo apre js/core/layout.js.
 * Stile in css/components/stats-panel.css.
 */

import { el } from '../utils/dom.js';

function stat(label, value, { modifier = '', note = '' } = {}) {
  return el('div', { class: `stat ${modifier}`.trim(), data: { stat: label } }, [
    el('dt', { text: label }),
    el('dd', {}, [String(value), note ? el('small', { class: 'stat__note', text: note }) : null]),
  ]);
}

function rating(mode, data) {
  return stat(`Rating ${mode}`, data.value, { note: data.provisional ? 'provvisorio' : '' });
}

/**
 * La griglia delle statistiche.
 *
 * @param {object} stats i dati di GET /stats/me (campo data)
 * @returns {HTMLElement}
 */
export function StatsPanel(stats) {
  const winRate = stats.win_rate === null ? '—' : `${stats.win_rate}%`;
  return el('dl', { class: 'stats-grid' }, [
    stat('Partite', stats.games),
    stat('Vinte', stats.wins, { modifier: 'stat--win' }),
    stat('Perse', stats.losses, { modifier: 'stat--lose' }),
    stat('Vittorie', winRate),
    rating('1v1', stats.ratings['1v1']),
    rating('2v2', stats.ratings['2v2']),
  ]);
}

/** Un messaggio al posto della griglia (caricamento, errore, connessione assente). */
export function StatsMessage(text) {
  return el('p', { class: 'sheet__message', text });
}

/**
 * Scarica le statistiche. Rifiuta la promessa se la connessione manca o la
 * risposta non è valida: chi la chiama mostra un messaggio.
 *
 * @param {string} url indirizzo dei dati (attributo data-stats-url del pannello)
 * @returns {Promise<object>} il campo data della risposta
 */
export async function fetchStats(url) {
  if (!navigator.onLine) throw new Error('offline');
  const response = await fetch(url, { headers: { Accept: 'application/json' } });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  const body = await response.json();
  if (!body || body.ok !== true || !body.data) throw new Error('risposta non valida');
  return body.data;
}
