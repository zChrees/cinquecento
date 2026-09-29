/**
 * Schermata di attesa in coda (P22; DECISIONI.md: "Attesa in coda a tutto
 * schermo", con il tempo trascorso, l'intervallo di rating e "Annulla").
 * Si disegna dallo stato della coda del contratto (4, queue:status):
 * { mode, target_score, seconds_waiting, rating_range: {min, max} | null, partner,
 *   opponents }. `opponents` (P59) ha gli avversari già noti: la coppia e il terzo
 * di un gruppo di tre amici si vedono a vicenda; altrimenti è vuota.
 * La pagina non calcola l'intervallo: lo manda il server (P28), che lo allarga
 * ogni 10 secondi (D16); tra un invio e l'altro la pagina conta solo i secondi,
 * con setQueueSeconds(). Stile in css/components/queue-overlay.css.
 *
 *   const overlay = QueueOverlay(queue, { imgBase, onCancel });
 *   document.body.append(overlay);
 *   overlay.showModal();
 *
 * "Annulla" (o Esc) chiama onCancel una volta sola: il pulsante resta disattivato
 * finché la pagina non chiude la schermata.
 */

import { el, icon } from '../utils/dom.js';

/** Secondi come m:ss (83 → "1:23"). */
export function formatWait(seconds) {
  const total = Math.max(0, Math.floor(seconds));
  const minutes = Math.floor(total / 60);
  return `${minutes}:${String(total % 60).padStart(2, '0')}`;
}

function titleFor(queue) {
  if (queue.mode === '1v1') return 'Cerco un avversario…';
  if (queue.opponents?.length) return 'Cerco il quarto giocatore…';   // gruppo di tre amici (P59)
  return queue.partner ? 'Cerco gli avversari…' : 'Cerco compagno e avversari…';
}

function sectionFor(queue) {
  if (queue.opponents?.length) return 'Con gli amici';
  return queue.partner ? 'Con un amico' : 'Partita Veloce';
}

// "In squadra con Giulia" / "Contro Giulia e Salvo": avatar con l'iniziale e testo
function playersLine(players, text, data) {
  return el('p', { class: 'queue-overlay__partner felt-text', data }, [
    ...players.map((p) => el('span', { class: 'avatar', text: p.username.charAt(0).toUpperCase(), attrs: { 'aria-hidden': 'true' } })),
    el('span', { text }),
  ]);
}

function rangeText(range) {
  if (!range) return 'Va bene qualunque avversario';
  return `Avversari con rating tra ${range.min} e ${range.max}`;
}

/**
 * @param {object} queue            stato della coda (queue:status)
 * @param {object} options
 * @param {string} options.imgBase  cartella delle immagini delle carte (dorso)
 * @param {Function} options.onCancel
 * @returns {HTMLDialogElement}
 */
export function QueueOverlay(queue, { imgBase, onCancel }) {
  const section = sectionFor(queue);
  const cancel = el('button', {
    class: 'btn btn--ghost queue-overlay__cancel',
    attrs: { type: 'button' },
    data: { queueCancel: '' },
    on: { click: () => requestCancel() },
  }, [icon('close'), 'Annulla']);

  const partner = queue.partner
    ? playersLine([queue.partner], `In squadra con ${queue.partner.username}`, { queuePartner: queue.partner.user_id })
    : null;
  const opponents = queue.opponents?.length
    ? playersLine(queue.opponents, `Contro ${queue.opponents.map((p) => p.username).join(' e ')}`,
      { queueOpponents: queue.opponents.map((p) => p.user_id).join(' ') })
    : null;

  const overlay = el('dialog', {
    class: 'queue-overlay',
    attrs: { 'aria-labelledby': 'queue-title' },
    data: { queueOverlay: '', mode: queue.mode, targetScore: queue.target_score },
  }, [
    el('div', { class: 'queue-overlay__body' }, [
      el('div', { class: 'queue-overlay__cards', attrs: { 'aria-hidden': 'true' } },
        [1, 2, 3].map(() => el('img', { attrs: { src: `${imgBase}dorso.webp`, alt: '' } }))),
      el('p', { class: 'queue-overlay__kicker felt-text', text: `${section} · ${queue.mode} · ${queue.target_score} punti` }),
      el('h2', { class: 'queue-overlay__title felt-text', text: titleFor(queue), attrs: { id: 'queue-title' } }),
      el('p', { class: 'queue-overlay__time felt-text' }, [
        el('span', { class: 'visually-hidden', text: 'In attesa da ' }),
        el('span', { data: { queueSeconds: '' } }),
      ]),
      el('p', { class: 'queue-overlay__range felt-text', text: rangeText(queue.rating_range), data: { queueRange: '' } }),
      queue.rating_range ? el('p', { class: 'queue-overlay__hint felt-text', text: "L'intervallo si allarga mentre aspetti." }) : null,
      partner,
      opponents,
      cancel,
    ]),
  ]);

  function requestCancel() {
    if (cancel.disabled) return;
    cancel.disabled = true;   // niente doppio clic: la pagina chiude la schermata quando il server risponde
    onCancel();
  }

  // Esc vale come "Annulla"
  overlay.addEventListener('cancel', (event) => {
    event.preventDefault();
    requestCancel();
  });

  setQueueSeconds(overlay, queue.seconds_waiting);
  return overlay;
}

/** Aggiorna il tempo trascorso (la pagina lo chiama ogni secondo). */
export function setQueueSeconds(overlay, seconds) {
  overlay.querySelector('[data-queue-seconds]').textContent = formatWait(seconds);
}

/** Riattiva "Annulla" (per esempio se il server ha risposto con un errore). */
export function enableQueueCancel(overlay) {
  overlay.querySelector('[data-queue-cancel]').disabled = false;
}
