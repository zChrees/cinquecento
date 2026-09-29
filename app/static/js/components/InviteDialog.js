/**
 * Invito a partita ricevuto (P47; contratto 5.3; scelta di Giuseppe: solo nella home).
 * Finestra nella pagina con lo stile di Modal.js (css/components/modal.css): chi
 * invita, modalità e punti, il conto alla rovescia (seconds_left, la pagina conta da
 * sola), "Rifiuta" e "Accetta". Dopo "Accetta" aspetta che chi ha invitato avvii la
 * partita ("Rifiuta" resta, per uscire). X ed Esc valgono come "Rifiuta".
 *
 *   const dialog = openInviteDialog(invite, { onAccept, onDecline });
 *   dialog.setStatus('accepted' | 'declined' | 'expired' | 'cancelled' | 'started');
 *   dialog.setOnline(false);   // P33: senza connessione "Accetta" e "Rifiuta" sono spenti
 *
 * onAccept e onDecline mandano la richiesta e restituiscono la risposta del server
 * ({ok, error}): finché non arriva i pulsanti sono disattivati (doppio clic).
 * Con "started" la finestra si chiude (la pagina va al tavolo o in coda); con gli
 * altri stati finali mostra il motivo e si chiude dopo qualche secondo.
 * I nomi degli utenti entrano sempre come testo, mai come HTML.
 */

import { el, icon } from '../utils/dom.js';
import { formatWait } from './QueueOverlay.js';

const CLOSE_AFTER_MS = 4000;   // quanto resta il motivo di un invito finito

function describe(invite) {
  const role = invite.mode === '2v2' ? 'in squadra con te nel 2v2' : 'contro di te nel 1v1';
  return `${invite.from.username} ti invita a giocare ${role}, a ${invite.target_score} punti.`;
}

/**
 * @param {object} invite  invito del contratto (invite:received)
 * @param {object} handlers
 * @param {Function} handlers.onAccept   () => Promise<{ok, error}>
 * @param {Function} handlers.onDecline  () => Promise<{ok, error}>
 * @param {boolean} [online]           c'è la connessione quando si apre (P33)
 * @returns {{ setStatus: Function, setOnline: Function, close: Function, inviteId: string }}
 */
export function openInviteDialog(invite, { onAccept, onDecline }, online = true) {
  const from = invite.from.username;
  let status = invite.status;
  let waiting = false;     // richiesta in attesa di risposta
  let closed = false;

  const seconds = el('span', { data: { inviteSeconds: '' } });
  const timeLine = el('p', { class: 'dialog__body' }, ['Rispondi entro ', seconds]);
  const note = el('p', { class: 'dialog__body', attrs: { role: 'status' }, data: { inviteNote: '' } });
  const decline = el('button', {
    class: 'btn btn--ghost', text: 'Rifiuta', attrs: { type: 'button' },
    data: { inviteDecline: '' }, on: { click: () => answer('decline') },
  });
  const accept = el('button', {
    class: 'btn btn--primary', text: 'Accetta', attrs: { type: 'button', autofocus: true },
    data: { inviteAccept: '' }, on: { click: () => answer('accept') },
  });
  const closeButton = el('button', {
    class: 'icon-btn', attrs: { type: 'button', 'aria-label': 'Rifiuta e chiudi' },
    on: { click: () => dismiss() },
  }, icon('close'));

  const dialog = el('dialog', {
    class: 'dialog', attrs: { 'aria-labelledby': 'invite-title' },
    data: { inviteDialog: invite.invite_id, inviteStatus: status },
  }, [
    el('div', { class: 'dialog__head' }, [
      el('h2', { class: 'dialog__title', text: 'Invito a partita', attrs: { id: 'invite-title' } }),
      closeButton,
    ]),
    el('p', { class: 'dialog__body', text: describe(invite) }),
    timeLine,
    note,
    el('div', { class: 'dialog__actions' }, [decline, accept]),
  ]);

  // Conto alla rovescia: la pagina conta da sola dai secondi rimasti (contratto 1.1)
  const deadline = Date.now() + invite.seconds_left * 1000;
  function tick() {
    seconds.textContent = formatWait(Math.max(0, (deadline - Date.now()) / 1000));
  }
  tick();
  const timer = setInterval(tick, 1000);

  function render() {
    dialog.dataset.inviteStatus = status;
    timeLine.hidden = status !== 'pending';
    accept.hidden = status !== 'pending';
    decline.textContent = status === 'accepted' ? 'Esci' : 'Rifiuta';
    const open = status === 'pending' || status === 'accepted';
    for (const button of [accept, decline]) button.disabled = waiting || !open || !online;
    closeButton.disabled = waiting;
    const notes = {
      accepted: `Hai accettato: aspettiamo che ${from} avvii la partita…`,
      expired: "L'invito è scaduto.",
      cancelled: `${from} ha annullato l'invito.`,
      declined: 'Hai rifiutato l\'invito.',
    };
    note.textContent = notes[status] ?? '';
  }

  async function answer(kind) {
    if (waiting || closed || !(status === 'pending' || status === 'accepted')) return;
    if (kind === 'accept' && status !== 'pending') return;
    if (!navigator.onLine) {
      note.textContent = 'Sei offline: rispondi appena torna la connessione.';
      return;
    }
    waiting = true;
    render();
    const reply = await (kind === 'accept' ? onAccept() : onDecline());
    waiting = false;
    if (closed) return;
    if (!reply?.ok) {
      render();
      note.textContent = reply?.error?.message ?? 'Qualcosa non ha funzionato: riprova.';
      return;
    }
    if (kind === 'decline') {
      close();
      return;
    }
    setStatus('accepted');
  }

  function setStatus(next) {
    if (closed || next === status) return;
    status = next;
    if (status === 'started' || status === 'declined') {
      close();
      return;
    }
    render();
    if (status !== 'pending' && status !== 'accepted') setTimeout(close, CLOSE_AFTER_MS);
  }

  function setOnline(next) {
    if (closed || next === online) return;
    online = next;
    render();
  }

  function close() {
    if (closed) return;
    closed = true;
    clearInterval(timer);
    if (dialog.open) dialog.close();
    dialog.remove();
  }

  // X ed Esc: "Rifiuta" finché l'invito è aperto, poi chiudono e basta
  function dismiss() {
    if (status === 'pending' || status === 'accepted') answer('decline');
    else close();
  }
  dialog.addEventListener('cancel', (event) => {
    event.preventDefault();
    dismiss();
  });

  render();
  document.body.append(dialog);
  dialog.showModal();
  return { setStatus, setOnline, close, inviteId: invite.invite_id };
}
