/**
 * Finestra chat con un amico (P46), dal prototipo (P52): si apre dentro il
 * pannello amici (FriendsPanel.js), che su telefono è a tutto schermo. Stile in
 * css/components/chat.css.
 *
 *   const chat = ChatWindow({ friend, meId, messages, canWrite, notice, hasMore,
 *                             onSend, onLoadMore, onBack, onClose });
 *   appendMessage(chat, message, meId);
 *   disableWriting(chat, 'Bloccato: non potete più scrivervi.');
 *   setChatOnline(chat, false);   // P33: senza connessione "Invia" è spento
 *
 * I messaggi hanno la forma del contratto (5.4): { id, from_user_id, to_user_id,
 * text, sent_at }. Il testo entra SEMPRE come testo (textContent), mai come HTML,
 * e si mostra così com'è. Il componente non parla con il server (lo fa
 * FriendsPanel.js, P48): chiama onSend(text), che restituisce una promessa
 * (risolta con il messaggio salvato, o rifiutata con un Error il cui message si
 * mostra sotto il campo; se l'Error ha `closesChat`, la scrittura si chiude), e
 * onLoadMore(), per "Messaggi precedenti" (risolta con { messages, has_more }).
 */

import { el, icon } from '../utils/dom.js';

export const MAX_LENGTH = 1000;   // D26, come CHAT_MAX_LENGTH in config.py

const PRESENCE = { online: 'Online', in_game: 'In partita', offline: 'Offline' };

function timeOf(sentAt) {
  const date = new Date(sentAt);
  if (Number.isNaN(date.getTime())) return '';
  return date.toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' });
}

function messageItem(message, meId) {
  const mine = message.from_user_id === meId;
  return el('li', { class: `chat__msg${mine ? ' chat__msg--mine' : ''}`, data: { messageId: message.id } }, [
    message.text,
    el('span', { class: 'chat__time', text: timeOf(message.sent_at) }),
  ]);
}

function emptyItem() {
  return el('li', { class: 'chat__empty', data: { chatEmpty: '' }, text: 'Nessun messaggio: scrivi tu per primo.' });
}

/** Aggiunge un messaggio in fondo e scorre fino a lui (una volta sola per id). */
export function appendMessage(chat, message, meId) {
  const list = chat.querySelector('[data-chat-messages]');
  if (list.querySelector(`[data-message-id="${CSS.escape(String(message.id))}"]`)) return;
  list.querySelector('[data-chat-empty]')?.remove();
  list.append(messageItem(message, meId));
  list.scrollTop = list.scrollHeight;
}

/** Chiude la scrittura (amicizia finita o blocco, D24) e dice perché in cima. */
export function disableWriting(chat, text) {
  const input = chat.querySelector('#chat-input');
  input.disabled = true;
  input.placeholder = 'Non puoi più scrivere a questo utente';
  chat.querySelector('[data-chat-form] button[type="submit"]').disabled = true;
  let notice = chat.querySelector('[data-chat-notice]');
  if (!notice) {
    notice = el('p', { class: 'chat__notice', data: { chatNotice: '' } });
    chat.querySelector('[data-chat-messages]').before(notice);
  }
  notice.textContent = text;
}

/** P33: senza connessione "Invia" è spento; al ritorno si riaccende, se si può ancora scrivere. */
export function setChatOnline(chat, online) {
  chat.toggleAttribute('data-offline', !online);
  const input = chat.querySelector('#chat-input');
  chat.querySelector('[data-chat-form] button[type="submit"]').disabled = !online || input.disabled;
}

/**
 * @param {object} options
 * @param {object} options.friend      amico ({ user_id, username, presence })
 * @param {number} options.meId        id dell'utente collegato
 * @param {Array} options.messages     messaggi, dal più vecchio al più nuovo
 * @param {boolean} options.canWrite   false: si legge ma non si scrive (D24)
 * @param {string} [options.notice]    avviso in cima (per esempio "Bloccato: …")
 * @param {boolean} [options.hasMore]  ci sono messaggi più vecchi da caricare
 * @param {Function} options.onSend    (text) => Promise<message>
 * @param {Function} [options.onLoadMore] () => Promise<{ messages, has_more }> (i più vecchi)
 * @param {Function} options.onBack    torna alla lista degli amici
 * @param {Function} options.onClose   chiude il pannello
 * @returns {HTMLElement}
 */
export function ChatWindow({
  friend, meId, messages, canWrite, notice = '', hasMore = false, onSend, onLoadMore, onBack, onClose,
}) {
  const list = el('ol', { class: 'chat__messages', attrs: { 'aria-live': 'polite' }, data: { chatMessages: '' } },
    messages.length ? messages.map((m) => messageItem(m, meId)) : [emptyItem()]);

  // "Messaggi precedenti" (contratto 5.4: before_id = il più vecchio già caricato)
  const more = el('li', { class: 'chat__empty', attrs: { hidden: !hasMore } }, [
    el('button', {
      class: 'btn btn--ghost btn--small', text: 'Messaggi precedenti', attrs: { type: 'button' },
      data: { chatMore: '' }, on: { click: () => loadMore() },
    }),
  ]);
  list.prepend(more);

  async function loadMore() {
    const button = more.querySelector('button');
    if (button.disabled || !onLoadMore) return;
    button.disabled = true;
    try {
      const older = await onLoadMore();
      const height = list.scrollHeight;
      more.after(...older.messages.map((m) => messageItem(m, meId)));
      list.scrollTop += list.scrollHeight - height;   // resta sul messaggio che si stava leggendo
      more.hidden = !older.has_more;
    } catch (err) {
      showError(err.message);
    } finally {
      button.disabled = false;
    }
  }

  const input = el('input', {
    class: 'input',
    attrs: {
      id: 'chat-input', name: 'text', type: 'text', autocomplete: 'off',
      maxlength: MAX_LENGTH, placeholder: canWrite ? 'Scrivi un messaggio' : 'Non puoi più scrivere a questo utente',
      disabled: !canWrite,
    },
  });
  const send = el('button', {
    class: 'icon-btn icon-btn--filled',
    attrs: { type: 'submit', 'aria-label': 'Invia messaggio', disabled: !canWrite },
  }, [icon('send')]);
  const error = el('p', { class: 'chat__error', attrs: { role: 'alert', hidden: true }, data: { chatError: '' } });

  function showError(text) {
    error.textContent = text;
    error.hidden = !text;
  }

  const form = el('form', { class: 'chat__form', attrs: { novalidate: true }, data: { chatForm: '' } }, [
    el('label', { class: 'visually-hidden', text: 'Scrivi un messaggio', attrs: { for: 'chat-input' } }),
    input, send, error,
  ]);
  // P81: toccando "Invia" il fuoco passava al pulsante e il telefono chiudeva la
  // tastiera (riaperta poi da input.focus()). Il pulsante non prende il fuoco, il clic
  // resta; sul modulo, così vale anche per un tocco sul pulsante spento durante l'invio
  form.addEventListener('mousedown', (event) => {
    if (event.target !== input) event.preventDefault();
  });

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (send.disabled) return;   // niente doppio invio mentre si aspetta la risposta
    const text = input.value;
    // Come il server (contratto 5.4): niente messaggi vuoti o fatti solo di spazi, al massimo 1000 caratteri
    if (!text.trim()) {
      showError('Scrivi un messaggio.');
      return;
    }
    if (text.length > MAX_LENGTH) {
      showError(`Al massimo ${MAX_LENGTH} caratteri.`);
      return;
    }
    if (!navigator.onLine) {
      showError('Sei offline: il messaggio partirà quando torna la connessione. Riprova tra poco.');
      return;
    }
    showError('');
    send.disabled = true;
    try {
      const message = await onSend(text);
      input.value = '';
      appendMessage(chat, message, meId);
    } catch (err) {
      showError(err.message);
      if (err.closesChat) {
        disableWriting(chat, err.message);
        return;
      }
    } finally {
      if (!input.disabled) {
        send.disabled = chat.hasAttribute('data-offline');
        input.focus();
      }
    }
  });

  const chat = el('div', { class: 'drawer__view chat', data: { view: 'chat', chatWith: friend.user_id } }, [
    el('div', { class: 'drawer__head' }, [
      el('button', {
        class: 'icon-btn', attrs: { type: 'button', 'aria-label': 'Torna agli amici' },
        data: { chatBack: '' }, on: { click: onBack },
      }, [icon('arrow_back')]),
      el('div', { class: 'chat__title' }, [
        el('h2', { class: 'drawer__title', text: friend.username, attrs: { id: 'chat-title' } }),
        el('span', { class: 'chat__presence', text: PRESENCE[friend.presence] ?? '' }),
      ]),
      el('button', {
        class: 'icon-btn', attrs: { type: 'button', 'aria-label': 'Chiudi' }, on: { click: onClose },
      }, [icon('close')]),
    ]),
    notice ? el('p', { class: 'chat__notice', text: notice, data: { chatNotice: '' } }) : null,
    list,
    form,
  ]);
  chat.setAttribute('aria-labelledby', 'chat-title');
  return chat;
}
