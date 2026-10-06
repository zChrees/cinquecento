/**
 * Pannello amici (P46), dal prototipo (P52): si apre dall'icona degli amici della
 * navbar, da ogni pagina che ha la navbar (non dal tavolo). Su telefono è a tutto
 * schermo, su computer laterale. Stile in css/components/friends-panel.css.
 *
 *   import { initFriendsPanel } from '../components/FriendsPanel.js';
 *   initFriendsPanel(document.querySelector('[data-friends-button]'));   // lo fa core/layout.js
 *
 * Dati VERI, dalle richieste HTTP di P45 (contratto 2.2): GET /friends/ per la
 * lista e il contatore, POST e DELETE per richieste, amicizie e blocchi, con il
 * codice CSRF nell'intestazione X-CSRFToken e request_id dove serve (1.3).
 * Dentro: cerca uno username (esatto, D33) e manda la richiesta; richieste
 * ricevute (accetta, rifiuta); amici online, in partita e offline con i messaggi
 * non letti, "Chatta" e "Altro" (rimuovi, blocca, con conferma); richieste
 * mandate (annulla); bloccati (sblocca). Gli inviti a partita stanno solo nella
 * carta-modal della home (DECISIONI.md, P46).
 * P47: la lista si aggiorna da sola, senza ricaricare la pagina: con
 * friends:presence (un amico entra, esce, comincia o finisce una partita) e con
 * friends:changed (richieste, amicizie e blocchi) si rilegge GET /friends/
 * (contratto 5.2: la forma della lista resta una sola).
 * La chat (ChatWindow.js) è quella vera (P48, contratto 5.4): chat:history
 * all'apertura (e "Messaggi precedenti"), chat:send, chat:read, chat:message.
 * Con un blocco o senza più amicizia si legge ma non si scrive, e la chat lo dice.
 * P33: senza connessione "Invia" della chat è spento (l'avviso in cima alla pagina
 * lo mostra core/socket.js); al ritorno si rilegge la lista e la chat aperta
 * riceve i messaggi arrivati nel frattempo.
 * Si chiude con la X, con Esc, toccando fuori e con "indietro" del browser o del
 * telefono (dalla chat, "indietro" torna alla lista).
 * Tutti i testi degli utenti entrano come testo, mai come HTML.
 */

import { el, icon } from '../utils/dom.js';
import { on, onStatus, send } from '../core/socket.js';
import { EVENTS } from '../core/events.js';
import { playSound, preloadSounds } from '../core/sounds.js';
import { Avatar } from './Avatar.js';
import { confirmModal, openModal } from './Modal.js';
import { ChatWindow, appendMessage, disableWriting, setChatOnline } from './ChatWindow.js';

const PRESENCE_LABEL = { online: 'Online', in_game: 'In partita', offline: 'Offline' };
const GROUPS = [['online', 'Online'], ['in_game', 'In partita'], ['offline', 'Offline']];


// ------------------------------------------------------------
// Richieste HTTP (contratto 1.2, 1.3, 1.5 e 2.2)
// ------------------------------------------------------------

class ApiError extends Error {
  constructor(code, message) {
    super(message);
    this.code = code;
  }
}

function csrfToken() {
  return document.querySelector('meta[name="csrf-token"]')?.content ?? '';
}

async function api(method, url, body = null) {
  if (!navigator.onLine) throw new ApiError('no_connection', 'Sei offline: riprova quando torna la connessione.');
  const headers = { Accept: 'application/json' };
  if (body) headers['Content-Type'] = 'application/json';
  if (method !== 'GET') headers['X-CSRFToken'] = csrfToken();
  let response;
  try {
    response = await fetch(url, {
      method, headers, credentials: 'same-origin', body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError('no_connection', 'Connessione non riuscita: riprova tra poco.');
  }
  let payload = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }
  if (payload?.ok === true) return payload.data;
  if (payload?.ok === false && payload.error) throw new ApiError(payload.error.code, payload.error.message);
  // Risposta non JSON: per esempio il 400 di Flask-WTF senza codice CSRF valido
  throw new ApiError('server_error', response.status === 400
    ? 'Richiesta rifiutata: ricarica la pagina e riprova.'
    : 'Qualcosa non ha funzionato: riprova tra poco.');
}

/**
 * request_id (contratto 1.3): un codice casuale, lo stesso per tutti i tentativi
 * della stessa azione finché il server non ha risposto. crypto.randomUUID esiste
 * solo in https o su localhost: nella demo in rete locale (http) si usa getRandomValues.
 */
function newRequestId() {
  if (crypto.randomUUID) return crypto.randomUUID();
  const b = crypto.getRandomValues(new Uint8Array(16));
  b[6] = (b[6] & 0x0f) | 0x40;
  b[8] = (b[8] & 0x3f) | 0x80;
  const hex = [...b].map((x) => x.toString(16).padStart(2, '0')).join('');
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

const pendingIds = new Map();   // azione → request_id, finché il server non risponde

async function withRequestId(action, send) {
  if (!pendingIds.has(action)) pendingIds.set(action, newRequestId());
  try {
    const data = await send(pendingIds.get(action));
    pendingIds.delete(action);
    return data;
  } catch (error) {
    // Senza risposta del server si riprova con lo stesso codice: niente doppioni
    if (error.code !== 'no_connection') pendingIds.delete(action);
    throw error;
  }
}

// ------------------------------------------------------------
// Pezzi della lista
// ------------------------------------------------------------

function colorIndex(name) {
  let sum = 0;
  for (let i = 0; i < name.length; i += 1) sum += name.charCodeAt(i);
  return sum % 4;
}

// Immagine dell'avatar (P43) o iniziale su un colore a rotazione
function miniAvatar(user, presence = null) {
  return el('span', { class: 'mini-avatar__wrap', attrs: { 'aria-hidden': 'true' } }, [
    Avatar(user, `mini-avatar mini-avatar--${colorIndex(user.username)}`),
    presence ? el('span', { class: `mini-avatar__status mini-avatar__status--${presence}` }) : null,
  ]);
}

function iconButton(name, label, extra = {}) {
  return el('button', {
    class: `icon-btn ${extra.class ?? ''}`.trim(),
    attrs: { type: 'button', 'aria-label': label },
    data: extra.data ?? {},
    on: extra.on ?? {},
  }, [icon(name)]);
}

function row({ user, status, presence, extra = null, actions, modifier = '' }) {
  return el('li', { class: `friend ${modifier}`.trim(), data: { userId: user.user_id } }, [
    miniAvatar(user, presence),
    el('span', { class: 'friend__text' }, [
      el('span', { class: 'friend__name', text: user.username }),
      el('span', { class: 'friend__status', text: status }),
    ]),
    extra,
    el('span', { class: 'friend__actions' }, actions),
  ]);
}

function group(title, items, { data = {}, empty = '' } = {}) {
  if (!items.length && !empty) return null;
  return el('section', { class: 'friends-group', data }, [
    el('h3', { class: 'friends-group__title', text: title }),
    items.length ? el('ul', { class: 'friends-list' }, items) : el('p', { class: 'friends-empty', text: empty }),
  ]);
}

// ------------------------------------------------------------
// Pannello
// ------------------------------------------------------------

/** Crea il pannello amici e lo aggancia al pulsante degli amici della navbar. */
export function initFriendsPanel(button) {
  if (!button?.dataset.friendsUrl) return;
  const baseUrl = button.dataset.friendsUrl.replace(/\/$/, '');
  const meId = Number(document.body.dataset.userId);
  const badge = button.querySelector('[data-friends-badge]');
  // P115: i suoni del menu (sul tavolo li ha già preparati game.js: qui non fa niente). Il contesto
  // audio subito, come al tavolo (P118): chi arriva da un clic di questo sito sente gli avvisi
  preloadSounds({ now: true });

  let overview = null;     // ultima risposta di GET /friends/
  let loadSeq = 0;         // solo l'ultima lettura ridisegna
  let loadError = '';

  // --- Struttura (una volta sola) ---
  const notice = el('p', { class: 'friends-notice', attrs: { role: 'status', hidden: true }, data: { friendsNotice: '' } });
  const addInput = el('input', {
    class: 'input',
    attrs: {
      id: 'add-friend-input', name: 'username', type: 'text', maxlength: 20,
      placeholder: 'Cerca uno username', autocomplete: 'off', autocapitalize: 'off', spellcheck: 'false',
    },
  });
  const addButton = el('button', { class: 'btn btn--primary btn--small', attrs: { type: 'submit' } }, [icon('person_add'), 'Invia']);
  const addError = el('p', { class: 'add-friend__error', attrs: { role: 'alert', hidden: true }, data: { addFriendError: '' } });
  const addForm = el('form', { class: 'add-friend', attrs: { novalidate: true }, data: { addFriend: '' } }, [
    el('label', { class: 'visually-hidden', text: "Username esatto dell'amico da aggiungere", attrs: { for: 'add-friend-input' } }),
    addInput, addButton, addError,
  ]);
  const body = el('div', { data: { friendsBody: '' } });
  const listView = el('div', { class: 'drawer__view', data: { view: 'list' } }, [
    el('div', { class: 'drawer__head' }, [
      el('h2', { class: 'drawer__title', text: 'Amici', attrs: { id: 'friends-title' } }),
      iconButton('close', 'Chiudi', { on: { click: () => requestClose() } }),
    ]),
    notice, addForm, body,
  ]);
  let chatView = null;

  const dialog = el('dialog', {
    class: 'drawer',
    attrs: { id: 'friends', 'aria-labelledby': 'friends-title' },
    data: { animated: '', friendsPanel: '' },
  }, [listView]);
  document.body.append(dialog);

  // --- Contatore sull'icona: richieste ricevute + messaggi non letti (contratto 2.2) ---
  function renderBadge() {
    const total = overview ? overview.counters.requests_in + overview.counters.unread_messages : 0;
    badge.textContent = String(total);
    badge.hidden = total === 0;
    button.setAttribute('aria-label', total ? `Amici: ${total} novità (richieste e messaggi)` : 'Amici');
  }

  function setNotice(text, kind = 'ok') {
    notice.textContent = text;
    notice.dataset.kind = kind;
    notice.hidden = !text;
  }

  // --- Lista ---
  function renderList() {
    if (!overview) {
      const message = loadError || 'Caricamento…';
      body.replaceChildren(el('div', { class: 'friends-message', data: { friendsMessage: '' } }, [
        el('p', { text: message }),
        loadError ? el('button', {
          class: 'btn btn--ghost btn--small', attrs: { type: 'button' }, on: { click: () => load() },
        }, [icon('refresh'), 'Riprova']) : null,
      ]));
      return;
    }
    const friends = overview.friends;
    const sections = [
      group('Richieste di amicizia', overview.requests_in.map(requestInRow), { data: { requestsIn: '' } }),
      ...GROUPS.map(([presence, title]) => group(
        `${title} (${friends.filter((f) => f.presence === presence).length})`,
        friends.filter((f) => f.presence === presence).map(friendRow),
        { data: { friendsGroup: presence } },
      )),
      friends.length ? null : el('p', { class: 'friends-empty', text: 'Non hai ancora amici: cerca uno username qui sopra.' }),
      group('Richieste mandate', overview.requests_out.map(requestOutRow), { data: { requestsOut: '' } }),
      overview.blocked.length ? blockedGroup(overview.blocked) : null,
    ];
    body.replaceChildren(...sections.filter(Boolean));
  }

  function requestInRow(request) {
    const name = request.username;
    return row({
      user: request,
      status: 'Vuole essere tuo amico',
      actions: [
        iconButton('check', `Accetta la richiesta di ${name}`, {
          class: 'icon-btn--ok', data: { accept: request.user_id },
          on: { click: (e) => act(e.currentTarget, () => api('POST', `${baseUrl}/requests/${request.user_id}/accept`), `Ora tu e ${name} siete amici.`) },
        }),
        iconButton('close', `Rifiuta la richiesta di ${name}`, {
          class: 'icon-btn--no', data: { decline: request.user_id },
          on: { click: (e) => act(e.currentTarget, () => api('POST', `${baseUrl}/requests/${request.user_id}/decline`), `Richiesta di ${name} rifiutata.`) },
        }),
      ],
    });
  }

  function friendRow(friend) {
    const name = friend.username;
    const unread = friend.unread > 0
      ? el('span', { class: 'friend__unread', data: { unread: friend.unread } }, [
        String(friend.unread),
        el('span', { class: 'visually-hidden', text: friend.unread === 1 ? ' messaggio non letto' : ' messaggi non letti' }),
      ])
      : null;
    return row({
      user: friend,
      status: PRESENCE_LABEL[friend.presence] ?? '',
      presence: friend.presence,
      modifier: friend.presence === 'offline' ? 'friend--offline' : '',
      extra: unread,
      actions: [
        iconButton('chat', `Chatta con ${name}`, { data: { chatOpen: friend.user_id }, on: { click: () => openChat(friend) } }),
        iconButton('more_vert', `Altre azioni per ${name}`, { data: { friendMore: friend.user_id }, on: { click: (e) => moreActions(e.currentTarget, friend) } }),
      ],
    });
  }

  function requestOutRow(request) {
    const name = request.username;
    return row({
      user: request,
      status: 'In attesa di risposta',
      actions: [el('button', {
        class: 'btn btn--ghost', attrs: { type: 'button', 'aria-label': `Annulla la richiesta a ${name}` },
        data: { cancelRequest: request.user_id },
        on: { click: (e) => act(e.currentTarget, () => api('DELETE', `${baseUrl}/requests/${request.user_id}`), `Richiesta a ${name} annullata.`) },
      }, ['Annulla'])],
    });
  }

  function blockedGroup(blocked) {
    const items = blocked.map((user) => row({
      user,
      status: 'Bloccato',
      actions: [el('button', {
        class: 'btn btn--ghost', attrs: { type: 'button', 'aria-label': `Sblocca ${user.username}` },
        data: { unblock: user.user_id },
        on: { click: (e) => act(e.currentTarget, () => api('DELETE', `${baseUrl}/blocks/${user.user_id}`), `${user.username} non è più bloccato.`) },
      }, ['Sblocca'])],
    }));
    return el('details', { class: 'friends-group friends-group--blocked', data: { blocked: '' } }, [
      el('summary', { class: 'friends-group__title' }, [icon('chevron_right'), `Bloccati (${blocked.length})`]),
      el('ul', { class: 'friends-list' }, items),
    ]);
  }

  // --- Azioni ---
  async function act(control, request, okText) {
    const rowButtons = control.closest('.friend')?.querySelectorAll('button') ?? [control];
    for (const b of rowButtons) b.disabled = true;   // niente doppio clic
    try {
      await request();
      setNotice(okText);
    } catch (error) {
      setNotice(error.message, 'error');
    }
    await load();
  }

  async function moreActions(control, friend) {
    const name = friend.username;
    const choice = await openModal({
      title: name,
      message: 'Cosa vuoi fare?',
      actions: [
        { label: 'Rimuovi amico', value: 'remove', variant: 'ghost' },
        { label: 'Blocca', value: 'block', variant: 'ghost' },   // la conferma, dopo, è rossa
      ],
    });
    if (choice === 'remove') {
      const sure = await confirmModal({
        title: `Togliere ${name} dagli amici?`,
        message: 'Sparirà dalla tua lista e tu dalla sua. Potrete mandarvi di nuovo una richiesta.',
        confirmLabel: 'Rimuovi',
        danger: true,
      });
      if (sure) await act(control, () => api('DELETE', `${baseUrl}/${friend.user_id}`), `${name} non è più tuo amico.`);
    } else if (choice === 'block') {
      const sure = await confirmModal({
        title: `Bloccare ${name}?`,
        message: 'Non potrà mandarti richieste né messaggi, e non sarete più amici. Puoi sbloccarlo quando vuoi.',
        confirmLabel: 'Blocca',
        danger: true,
      });
      if (sure) {
        await act(control, () => withRequestId(`block:${friend.user_id}`,
          (requestId) => api('POST', `${baseUrl}/blocks`, { request_id: requestId, user_id: friend.user_id })), `${name} è bloccato.`);
      }
    }
  }

  addForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (addButton.disabled) return;
    const username = addInput.value;
    if (!username) {
      addError.textContent = 'Scrivi uno username.';
      addError.hidden = false;
      addInput.focus();
      return;
    }
    addError.hidden = true;
    addButton.disabled = true;
    try {
      const sent = await withRequestId(`request:${username}`,
        (requestId) => api('POST', `${baseUrl}/requests`, { request_id: requestId, username }));
      addInput.value = '';
      setNotice(`Richiesta inviata a ${sent?.username ?? username}.`);
      await load();
    } catch (error) {
      addError.textContent = error.message;
      addError.hidden = false;
    } finally {
      addButton.disabled = false;
    }
  });

  async function load() {
    const seq = ++loadSeq;
    try {
      const data = await api('GET', `${baseUrl}/`);
      if (seq !== loadSeq) return;
      overview = data;
      loadError = '';
    } catch (error) {
      if (seq !== loadSeq) return;
      loadError = error.code === 'no_connection' ? error.message : 'Amici non disponibili. Riprova tra poco.';
      if (!dialog.open) return;   // senza pannello aperto basta lasciare il contatore com'era
      overview = null;
    }
    renderBadge();
    if (dialog.open) renderList();
  }

  // --- Chat vera (P48, contratto 5.4) ---
  const CHAT_CLOSED = {
    blocked: 'Bloccato: non potete più scrivervi.',
    not_friends: 'Non siete più amici: puoi leggere la conversazione, ma non scrivere.',
  };

  function chatError(answer) {
    const error = new Error(answer.error?.message ?? 'Qualcosa non ha funzionato: riprova.');
    error.closesChat = answer.error?.code === 'blocked' || answer.error?.code === 'not_friends';
    return error;
  }

  async function openChat(friend) {
    const answer = await send(EVENTS.CHAT_HISTORY, { user_id: friend.user_id, before_id: null });
    if (!answer.ok) {
      setNotice(answer.error.message, 'error');
      return;
    }
    const conversation = answer.data;
    let oldest = conversation.messages[0]?.id ?? null;
    chatView = ChatWindow({
      friend,
      meId,
      messages: conversation.messages,
      canWrite: conversation.can_write,
      notice: CHAT_CLOSED[conversation.cannot_write] ?? '',
      hasMore: conversation.has_more,
      onSend: async (text) => {
        const reply = await send(EVENTS.CHAT_SEND, { request_id: newRequestId(), user_id: friend.user_id, text });
        if (!reply.ok) throw chatError(reply);
        return reply.data.message;
      },
      onLoadMore: async () => {
        const reply = await send(EVENTS.CHAT_HISTORY, { user_id: friend.user_id, before_id: oldest });
        if (!reply.ok) throw chatError(reply);
        oldest = reply.data.messages[0]?.id ?? oldest;
        return reply.data;
      },
      onBack: () => backToList(),
      onClose: () => requestClose(),
    });
    dialog.querySelector('[data-view="chat"]')?.remove();
    dialog.append(chatView);
    listView.hidden = true;
    history.pushState({ friendsPanel: 'chat' }, '');
    const messages = chatView.querySelector('[data-chat-messages]');
    messages.scrollTop = messages.scrollHeight;
    if (conversation.can_write) chatView.querySelector('#chat-input').focus();
    // Aprire la chat ha segnato come letti i messaggi ricevuti (lo fa il server): contatore aggiornato
    if (overview && friend.unread > 0) {
      overview.counters.unread_messages = Math.max(0, overview.counters.unread_messages - friend.unread);
      friend.unread = 0;
      renderBadge();
      renderList();
    }
  }

  // Messaggio arrivato (o mandato da un'altra scheda): nella chat aperta con quell'amico
  // si aggiunge e si segna come letto; altrimenti si aggiorna il contatore dei non letti.
  function onChatMessage({ message } = {}) {
    if (!message) return;
    if (message.from_user_id !== meId) playSound('message');   // P115: non i tuoi, dalle altre schede
    const other = message.from_user_id === meId ? message.to_user_id : message.from_user_id;
    if (chatView && Number(chatView.dataset.chatWith) === other) {
      appendMessage(chatView, message, meId);
      if (message.from_user_id !== meId) send(EVENTS.CHAT_READ, { user_id: other });
    } else if (message.from_user_id !== meId) {
      load();
    }
  }

  function showList() {
    dialog.querySelector('[data-view="chat"]')?.remove();
    chatView = null;
    listView.hidden = false;
  }

  function backToList() {
    if (history.state?.friendsPanel === 'chat') history.back();   // popstate mostra la lista
    else showList();
  }

  // --- Apertura e chiusura, anche con "indietro" ---
  function open() {
    if (dialog.open) return;   // doppio clic
    showList();
    setNotice('');
    addError.hidden = true;
    renderList();
    dialog.showModal();
    history.pushState({ friendsPanel: 'list' }, '');
    load();
  }

  function closeNow() {
    if (!dialog.open || dialog.classList.contains('is-closing')) return;
    const done = () => {
      dialog.classList.remove('is-closing');
      dialog.close();
      showList();
    };
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      done();
      return;
    }
    dialog.classList.add('is-closing');
    dialog.addEventListener('animationend', function onEnd(event) {
      if (event.target !== dialog) return;
      dialog.removeEventListener('animationend', onEnd);
      done();
    });
    // Se l'animazione non parte (per esempio scheda in secondo piano), chiude comunque
    setTimeout(() => dialog.classList.contains('is-closing') && done(), 400);
  }

  function requestClose() {
    const layer = history.state?.friendsPanel;
    if (layer) history.go(layer === 'chat' ? -2 : -1);   // popstate chiude
    else closeNow();
  }

  // P34: dopo un ricaricamento con il pannello aperto il browser tiene ancora lo stato
  // del pannello nella cronologia ({friendsPanel: 'chat'}), ma il pannello è chiuso: si
  // toglie, altrimenti al pannello riaperto "indietro" non lo chiuderebbe
  if (history.state?.friendsPanel) {
    const { friendsPanel, ...rest } = history.state;
    history.replaceState(Object.keys(rest).length ? rest : null, '');
  }

  window.addEventListener('popstate', () => {
    if (!dialog.open) return;
    const layer = history.state?.friendsPanel;
    if (layer === 'list') showList();
    else if (!layer) closeNow();
  });

  dialog.addEventListener('cancel', (event) => {
    event.preventDefault();   // Esc: chiusura con l'animazione e la cronologia a posto
    requestClose();
  });
  dialog.addEventListener('click', (event) => {
    if (event.target !== dialog) return;   // tocco fuori dal pannello
    const r = dialog.getBoundingClientRect();
    const inside = event.clientX >= r.left && event.clientX <= r.right
      && event.clientY >= r.top && event.clientY <= r.bottom;
    if (!inside) requestClose();
  });

  // --- Connessione (P33) ---
  let wasOnline = false;

  // Al ritorno della connessione: i messaggi arrivati nel frattempo nella chat aperta
  async function refreshChat() {
    const other = Number(chatView?.dataset.chatWith);
    if (!other) return;
    const answer = await send(EVENTS.CHAT_HISTORY, { user_id: other, before_id: null });
    if (!answer.ok || Number(chatView?.dataset.chatWith) !== other) return;
    for (const message of answer.data.messages) appendMessage(chatView, message, meId);
    if (!answer.data.can_write) disableWriting(chatView, CHAT_CLOSED[answer.data.cannot_write] ?? 'Non puoi più scrivere a questo utente.');
  }

  onStatus((now) => {
    const online = now === 'connected';
    if (chatView) setChatOnline(chatView, online);
    if (online && wasOnline) {
      load();
      refreshChat();
    }
    if (online) wasOnline = true;
  });

  button.addEventListener('click', open);
  load();   // contatore sull'icona appena si apre la pagina
  on(EVENTS.FRIENDS_PRESENCE, () => load());   // P47
  on(EVENTS.FRIENDS_CHANGED, ({ reason } = {}) => {
    if (reason === 'request_received') playSound('friend_request');   // P115
    load();
  });
  on(EVENTS.CHAT_MESSAGE, onChatMessage);   // P48
}
