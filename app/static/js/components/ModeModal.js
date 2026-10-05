/**
 * Modal della modalità (P22), dal prototipo (P52, prototipo.js "Modal della
 * modalità"): la carta-pulsante toccata vola al centro ingrandendosi e si gira;
 * sulla faccia bianca ci sono titolo, descrizione, punti per vincere (150, 300,
 * 500) e "Gioca"; nella Partita Veloce anche "In breve" e "Lo sapevi?", con un
 * amico la lista degli amici online da invitare. Stile in css/components/mode-modal.css.
 *
 *   import { openModeModal, setInviteStatus } from '../components/ModeModal.js';
 *   openModeModal({ kind: 'veloce', mode: '1v1', tile, ratings, friends,
 *                   onPlay, onInvite, onCancelInvite });
 *
 * Il modal non parla con il server: lo fa la pagina con i callback.
 * - onPlay({ kind, mode, targetScore, invitees, cpu }): "Gioca" (la coda è di P28,
 *   gli inviti di P47); `invitees` sono gli amici che hanno accettato; `cpu` è true
 *   se nella Partita Veloce 1v1 è scelto "Avversario: CPU" (P73). Il modal si
 *   chiude da solo.
 * - onInvite({ friend, mode, targetScore }): "Invita" (contratto 5.3, invite:send).
 *   Il risultato arriva con setInviteStatus(userId, status) (invite:update):
 *   "accepted" attiva "Gioca"; "declined", "expired" e "cancelled" chiudono
 *   quell'invito con un avviso e si può invitare un altro amico (D27).
 * - onCancelInvite({ friend }): il modal si chiude senza "Gioca", una chiamata per
 *   ogni invito aperto (contratto 5.3: l'invito diventa "cancelled").
 * - setModeModalOnline(online) (P33): senza connessione "Gioca" e "Invita" sono spenti.
 * Nel 1v1 un invito alla volta; nel 2v2 fino a MAX_INVITES["2v2"] amici (P59), e
 * "Gioca" si attiva appena uno ha accettato. Mentre c'è un invito aperto i punti
 * sono fermi, perché gli inviti portano già i punti scelti.
 * Con "riduci movimento" il modal compare e sparisce senza animazione.
 * I testi (nomi degli amici compresi) entrano sempre come testo, mai come HTML.
 */

import { clear, el, icon } from '../utils/dom.js';
import { Avatar } from './Avatar.js';

// Testi della faccia per ogni modalità: solo regole e decisioni già prese
// (rating: 1v1 contro un amico non conta, 2v2 con un amico sì; code separate per punteggio).
const MODE_TEXTS = {
  'veloce-1v1': {
    desc: 'Entri in coda e ti troviamo un avversario del tuo livello. Una sfida secca, uno contro uno, carta dopo carta.',
    facts: (rating) => [
      ['person_search', 'Avversario scelto in base al rating'],
      ['trending_up', `Conta per il tuo rating 1v1${rating('1v1')}`],
      ['timer', '15 secondi per ogni turno'],
    ],
  },
  'veloce-2v2': {
    desc: 'Entri in coda da solo: ti troviamo un compagno e una coppia avversaria del vostro livello.',
    facts: (rating) => [
      ['handshake', 'Compagno e avversari arrivano dalla coda'],
      ['event_seat', 'Il compagno siede di fronte a te'],
      ['trending_up', `Conta per il tuo rating 2v2${rating('2v2')}`],
    ],
  },
  'amico-1v1': {
    desc: 'Scegli i punti e invita un amico online: la partita parte appena accetta. Non conta per il rating.',
  },
  'amico-2v2': {
    desc: 'Invita fino a tre amici. Con uno siete in squadra, contro una coppia dalla coda; con più amici, squadre a sorte.',
  },
};

// P73: Partita Veloce 1v1 con "Avversario: CPU" (D43: solo 1v1, non conta per il rating)
const CPU_TEXTS = {
  desc: 'Giochi subito contro il computer, senza coda: allenati quanto vuoi.',
  facts: [
    ['smart_toy', 'Parte subito, senza coda'],
    ['trending_up', 'Non conta per il rating'],
    ['timer', '15 secondi per ogni turno'],
  ],
};

// Consigli dal regolamento (docs/REGOLE-GIOCO.md), uno diverso a ogni apertura
const TIPS = [
  'Il primo canto della mano vale 40 e fa diventare briscola quel seme; i canti dopo valgono 20.',
  'Per cantare servono Re e Cavallo dello stesso seme, nel tuo turno e prima di giocare la carta.',
  "Non c'è obbligo di rispondere al seme: puoi giocare qualsiasi carta.",
  "L'Asso vale 11 punti e il Tre 10: sono i carichi, le carte più forti.",
  'Se il Re o il Cavallo di un seme viene giocato, quel seme non si può più cantare.',
  'A mazzo finito puoi cantare solo se hai ancora almeno 3 carte in mano.',
  "Ogni mano vale 120 punti di carte, più i canti. L'ultima presa non dà punti in più.",
  "All'inizio della mano non c'è briscola: la decide il primo canto.",
];

const TARGETS = [
  { value: 150, word: 'Breve' },
  { value: 300, word: 'Media' },
  { value: 500, word: 'Classica' },
];

const TIMING = { open: 820, close: 620 };

// Inviti aperti insieme per modalità (contratto 5.3; nel 2v2 P59: con chi invita il tavolo è pieno)
const MAX_INVITES = { '1v1': 1, '2v2': 3 };

let dialog = null;     // il <dialog>, creato alla prima apertura
let parts = null;      // le sue parti
let current = null;    // { kind, mode, tile, handlers, invites, started }; invites: Map user_id -> { friend, status }
let busy = false;      // animazione in corso: niente doppi clic
let lastTip = -1;
let offline = false;  // P33: senza connessione "Gioca" e "Invita" sono spenti (setModeModalOnline)
let playReady = false;       // "Gioca" si potrebbe premere (connessione a parte)
let invitesFull = false;     // inviti aperti al massimo: gli altri "Invita" sono fermi

function reduceMotion() {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

// ------------------------------------------------------------
// Costruzione (una volta sola)
// ------------------------------------------------------------

function build() {
  const kicker = el('p', { class: 'mode-modal__kicker' });
  const title = el('h2', { class: 'mode-modal__title', attrs: { id: 'mode-title' } });
  const desc = el('p', { class: 'mode-modal__desc', data: { modalDesc: '' } });

  const targetNote = el('p', { class: 'target__note', attrs: { 'aria-live': 'polite' } });
  const target = el('fieldset', { class: 'target' }, [
    el('legend', { class: 'target__legend', text: 'Punti per vincere' }),
    el('div', { class: 'target__options' }, TARGETS.map(({ value, word }) => el('label', { class: 'target__option' }, [
      el('input', { attrs: { type: 'radio', name: 'target', value }, on: { change: renderTargetNote } }),
      el('span', {}, [el('b', { text: value }), el('small', { text: word })]),
    ]))),
    targetNote,
  ]);

  // P73: solo nella Partita Veloce 1v1, chi è l'avversario (D43)
  const opponent = el('fieldset', { class: 'target opponent', data: { opponent: '' }, attrs: { hidden: true } }, [
    el('legend', { class: 'target__legend', text: 'Avversario' }),
    el('div', { class: 'target__options' }, [['person', 'player', 'Giocatore'], ['smart_toy', 'cpu', 'CPU']].map(([name, value, word]) => (
      el('label', { class: 'target__option' }, [
        el('input', { attrs: { type: 'radio', name: 'opponent', value }, on: { change: renderOpponent } }),
        el('span', { class: 'opponent__choice' }, [icon(name), el('b', { text: word })]),
      ])
    ))),
  ]);

  const factsList = el('ul', { class: 'facts' });
  const facts = el('section', { class: 'mode-modal__facts', attrs: { 'aria-labelledby': 'facts-title' } }, [
    el('h3', { class: 'mode-modal__section-title', text: 'In breve', attrs: { id: 'facts-title' } }),
    factsList,
  ]);

  const inviteTitle = el('h3', { class: 'invite__title' });
  const inviteList = el('ul', { class: 'invite__list', data: { inviteList: '' } });
  const inviteHint = el('p', { class: 'invite__hint', attrs: { 'aria-live': 'polite' }, data: { inviteHint: '' } });
  const invite = el('section', { class: 'invite', attrs: { hidden: true } }, [inviteTitle, inviteList, inviteHint]);

  const tipText = el('span');
  const tip = el('aside', { class: 'mode-modal__tip' }, [
    icon('lightbulb'),
    el('p', {}, [el('strong', { text: 'Lo sapevi?' }), ' ', tipText]),
  ]);

  const play = el('button', {
    class: 'btn btn--primary btn--big',
    attrs: { type: 'button' },
    data: { play: '' },
    on: { click: onPlayClick },
  }, [icon('play_arrow'), 'Gioca']);

  const close = el('button', {
    class: 'icon-btn mode-modal__close',
    attrs: { type: 'button', 'aria-label': 'Chiudi' },
    on: { click: closeModeModal },
  }, [icon('close')]);

  const body = el('div', { class: 'mode-modal__body' }, [
    el('div', { class: 'mode-modal__head' }, [kicker, title]),
    desc, target, opponent, facts, invite, tip, play,
  ]);
  const back = el('div', { class: 'mode-modal__back', attrs: { 'aria-hidden': 'true' } });
  const flip = el('div', { class: 'mode-modal__flip' }, [
    back,
    el('div', { class: 'mode-modal__face' }, [close, body]),
  ]);

  dialog = el('dialog', {
    class: 'mode-modal',
    attrs: { id: 'mode-modal', 'aria-labelledby': 'mode-title' },
    data: { modeModal: '' },
  }, [flip]);

  // Esc: il browser chiuderebbe subito; lo fermiamo per far vedere il ritorno della carta
  dialog.addEventListener('cancel', (event) => {
    event.preventDefault();
    closeModeModal();
  });
  // Tocco fuori dalla carta
  dialog.addEventListener('click', (event) => {
    if (event.target !== dialog) return;
    const r = dialog.getBoundingClientRect();
    const inside = event.clientX >= r.left && event.clientX <= r.right
      && event.clientY >= r.top && event.clientY <= r.bottom;
    if (!inside) closeModeModal();
  });
  dialog.addEventListener('close', () => {
    dialog.classList.remove('is-closing');
    if (current) current.tile.style.visibility = '';
  });

  document.body.append(dialog);
  parts = {
    flip, back, body, kicker, title, desc, target, targetNote, opponent, facts, factsList,
    invite, inviteTitle, inviteList, inviteHint, tip, tipText, play,
  };
}

// ------------------------------------------------------------
// Contenuto
// ------------------------------------------------------------

function selectedTarget() {
  return Number(dialog.querySelector('input[name="target"]:checked').value);
}

// Solo nella Partita Veloce: le code sono separate per punteggio
function renderTargetNote() {
  parts.targetNote.textContent = `Incontri solo chi ha scelto ${selectedTarget()} punti.`;
}

function ratingText(ratings) {
  return (mode) => {
    const rating = ratings?.[mode];
    if (!rating || typeof rating.value !== 'number') return '';
    return rating.provisional ? ` (${rating.value}, provvisorio)` : ` (${rating.value})`;
  };
}

function colorIndex(name) {
  let sum = 0;
  for (let i = 0; i < name.length; i += 1) sum += name.charCodeAt(i);
  return sum % 4;
}

// Immagine dell'avatar (P43) o iniziale su un colore a rotazione
function miniAvatar(friend) {
  return el('span', { class: 'mini-avatar__wrap', attrs: { 'aria-hidden': 'true' } }, [
    Avatar(friend, `mini-avatar mini-avatar--${colorIndex(friend.username)}`),
    el('span', { class: 'mini-avatar__status' }),
  ]);
}

function setInviteButton(button, state, name) {
  const look = {
    idle: ['send', 'Invita', `Invita ${name}`],
    pending: ['progress_activity', 'In attesa…', `Invito a ${name} in attesa`],
    accepted: ['check_circle', 'Ha accettato', `${name} ha accettato`],
  }[state];
  button.dataset.state = state;
  button.replaceChildren(icon(look[0]), look[1]);
  button.setAttribute('aria-label', look[2]);
  button.closest('.invite__item').dataset.state = state;
}

function inviteRow(friend) {
  const button = el('button', {
    class: 'invite__btn',
    attrs: { type: 'button' },
    data: { inviteUser: friend.user_id },
    on: { click: () => sendInvite(friend) },
  });
  const row = el('li', { class: 'invite__item', data: { userId: friend.user_id } }, [
    miniAvatar(friend),
    el('span', { class: 'invite__name', text: friend.username }),
    button,
  ]);
  setInviteButton(button, 'idle', friend.username);
  return row;
}

function renderInviteList(friends) {
  const online = friends.filter((f) => f.presence === 'online');
  if (online.length) {
    parts.inviteList.replaceChildren(...online.map(inviteRow));
  } else {
    parts.inviteList.replaceChildren(el('li', { class: 'invite__empty', text: 'Nessun amico online in questo momento.' }));
  }
  parts.inviteList.scrollTop = 0;
}

function setPlayReady(ready) {
  playReady = ready;
  parts.play.disabled = !ready || offline;
}

/**
 * P33: con online false "Gioca" e "Invita" si spengono (senza connessione non partono);
 * con true tornano come erano. La pagina la chiama quando cambia la connessione.
 */
export function setModeModalOnline(online) {
  offline = !online;
  if (!dialog) return;
  parts.play.disabled = !playReady || offline;
  refreshInviteButtons();
}

/** "Invita" si preme solo per chi non ha già un invito aperto, finché c'è posto. */
function refreshInviteButtons() {
  for (const button of parts.inviteList.querySelectorAll('.invite__btn')) {
    const invited = Boolean(current?.invites.has(Number(button.dataset.inviteUser)));
    button.disabled = invited || invitesFull || offline;
  }
}

/** Dopo ogni cambio degli inviti aperti: punti fermi se ce n'è uno, "Invita" e "Gioca". */
function refreshInvites() {
  const open = current.invites.size;
  invitesFull = open >= MAX_INVITES[current.mode];
  refreshInviteButtons();
  for (const input of dialog.querySelectorAll('input[name="target"]')) input.disabled = open > 0;
  setPlayReady(acceptedFriends().length > 0);
}

function acceptedFriends() {
  return [...current.invites.values()].filter((i) => i.status === 'accepted').map((i) => i.friend);
}

function inviteButton(userId) {
  return parts.inviteList.querySelector(`[data-invite-user="${CSS.escape(String(userId))}"]`);
}

function sendInvite(friend) {
  if (!current || busy || current.invites.has(friend.user_id) || invitesFull) return;
  if (!navigator.onLine) {
    parts.inviteHint.textContent = 'Sei offline: potrai invitare appena torna la connessione.';
    return;
  }
  current.invites.set(friend.user_id, { friend, status: 'pending' });
  const button = inviteButton(friend.user_id);
  if (button) setInviteButton(button, 'pending', friend.username);
  refreshInvites();
  parts.inviteHint.textContent = `Invito inviato a ${friend.username}. Aspettiamo che accetti…`;
  current.handlers.onInvite?.({ friend, mode: current.mode, targetScore: selectedTarget() });
}

/** Il suggerimento sotto la lista quando un amico accetta (nel 2v2 si può aspettare gli altri). */
function acceptedHint() {
  const names = acceptedFriends().map((f) => f.username);
  const who = names.length === 1 ? `${names[0]} ha accettato` : `${names.join(' e ')} hanno accettato`;
  const waiting = [...current.invites.values()].some((i) => i.status === 'pending');
  if (waiting) return `${who}: puoi giocare subito (chi non ha ancora risposto resta fuori) o aspettare gli altri.`;
  // Quattro amici al tavolo: come il 1v1 tra amici, non conta per il rating (P59)
  return names.length === 3 ? `${who}: puoi giocare! Tra quattro amici non conta per il rating.` : `${who}: puoi giocare!`;
}

/**
 * Risultato di un invito (contratto 5.3, invite:update): "accepted", "declined",
 * "expired" o "cancelled". Gli stati di amici senza un invito aperto si ignorano.
 */
export function setInviteStatus(userId, status) {
  const invite = current?.invites.get(userId);
  if (!invite) return;
  const { friend } = invite;
  const button = inviteButton(userId);
  if (status === 'accepted') {
    invite.status = 'accepted';
    if (button) setInviteButton(button, 'accepted', friend.username);
    refreshInvites();
    parts.inviteHint.textContent = acceptedHint();
    return;
  }
  const notes = {
    declined: `${friend.username} ha rifiutato l'invito. Puoi invitare un altro amico.`,
    expired: `${friend.username} non ha risposto in tempo. Puoi invitare un altro amico.`,
    cancelled: `L'invito a ${friend.username} è stato annullato.`,
  };
  if (!notes[status]) return;
  current.invites.delete(userId);
  if (button) setInviteButton(button, 'idle', friend.username);
  refreshInvites();
  parts.inviteHint.textContent = notes[status];
}

function renderFacts(facts) {
  parts.factsList.replaceChildren(...facts.map(([name, text]) => el('li', {}, [
    icon(name),
    el('span', { text }),
  ])));
}

/** true se nella Partita Veloce 1v1 è scelta la CPU come avversario (P73). */
function cpuChosen() {
  return !parts.opponent.hidden && dialog.querySelector('input[name="opponent"]:checked')?.value === 'cpu';
}

// P73: con la CPU descrizione e "In breve" sono i suoi, e la frase dei punti
// ("Incontri solo chi ha scelto…") non serve; con "Giocatore" tornano quelli della coda
function renderOpponent() {
  const cpu = cpuChosen();
  const texts = MODE_TEXTS[`${current.kind}-${current.mode}`];
  parts.desc.textContent = cpu ? CPU_TEXTS.desc : texts.desc;
  renderFacts(cpu ? CPU_TEXTS.facts : texts.facts(ratingText(current.ratings)));
  parts.targetNote.hidden = cpu;
  dialog.dataset.opponent = cpu ? 'cpu' : 'player';
}

function renderTexts(kind, mode, ratings) {
  const texts = MODE_TEXTS[`${kind}-${mode}`];
  const quick = kind === 'veloce';
  parts.kicker.textContent = quick ? 'Partita Veloce' : 'Gioca con un amico';
  parts.title.textContent = mode;
  parts.desc.textContent = texts.desc;
  dialog.querySelector('input[name="target"][value="500"]').checked = true;
  renderTargetNote();

  // "In breve", la frase dei punti e "Lo sapevi?" solo nella Partita Veloce:
  // con un amico lo spazio serve alla lista da invitare
  parts.facts.hidden = !quick;
  parts.targetNote.hidden = !quick;
  parts.tip.hidden = !quick;
  if (quick) {
    renderFacts(texts.facts(ratingText(ratings)));
  } else {
    clear(parts.factsList);
  }
  // P73: la scelta dell'avversario c'è solo nella Partita Veloce 1v1; si riparte da "Giocatore"
  parts.opponent.hidden = !(quick && mode === '1v1');
  dialog.querySelector('input[name="opponent"][value="player"]').checked = true;
  let tip = Math.floor(Math.random() * TIPS.length);
  if (tip === lastTip) tip = (tip + 1) % TIPS.length;
  lastTip = tip;
  parts.tipText.textContent = TIPS[tip];
}

// ------------------------------------------------------------
// Apertura e chiusura: la carta-pulsante vola al centro, ingrandendosi, e si
// gira; chiudendo fa il percorso al contrario.
// ------------------------------------------------------------

// Retro della carta grande: una copia della carta-pulsante alla sua misura vera,
// ingrandita fino alla carta grande (così all'inizio è identica all'originale)
function fillBack(tile) {
  const copy = el('div', { class: tile.className });
  copy.append(...[...tile.childNodes].map((node) => node.cloneNode(true)));
  copy.style.width = `${tile.offsetWidth}px`;
  copy.style.height = `${tile.offsetHeight}px`;
  copy.style.transform = `scale(${dialog.clientWidth / tile.offsetWidth}, ${dialog.clientHeight / tile.offsetHeight})`;
  parts.back.replaceChildren(copy);
}

// Posizione della carta grande: spostata di (dx, dy) dal centro, rimpicciolita
// (sx in larghezza, sy in altezza) e girata. easing: come si muove fino alla successiva.
// sx e sy sono diversi solo su telefono, dove la carta grande è più alta del normale.
function frame(dx, dy, sx, sy, turn, easing = 'linear') {
  return { transform: `translate(${dx}px, ${dy}px) scale(${sx}, ${sy}) rotateY(${turn}deg)`, easing };
}

function flip(opening) {
  const { tile } = current;
  if (reduceMotion() || !parts.flip.animate) {
    if (!opening) dialog.close();
    return;
  }
  busy = true;
  fillBack(tile);

  // Partenza: sopra la carta-pulsante, alla sua misura, girata sul retro
  const from = tile.getBoundingClientRect();
  const to = dialog.getBoundingClientRect();
  const dx = from.left + from.width / 2 - (to.left + to.width / 2);
  const dy = from.top + from.height / 2 - (to.top + to.height / 2);
  const sx = tile.offsetWidth / dialog.clientWidth;
  const sy = tile.offsetHeight / dialog.clientHeight;
  // A metà la carta è di taglio, già vicina al centro e quasi grande.
  // Aprendo: prima si stacca e gira con calma, poi rallenta arrivando al centro.
  // Chiudendo: parte piano, poi accelera verso il suo posto.
  const start = frame(dx, dy, sx, sy, 180, 'cubic-bezier(0.45, 0, 0.55, 1)');
  const middle = frame(dx * 0.35, dy * 0.35, sx + (1 - sx) * 0.72, sy + (1 - sy) * 0.72, 90,
    opening ? 'cubic-bezier(0.15, 0.6, 0.3, 1)' : 'cubic-bezier(0.45, 0, 0.55, 1)');
  const center = frame(0, 0, 1, 1, 0, 'cubic-bezier(0.6, 0, 0.9, 0.5)');

  tile.style.visibility = 'hidden';
  dialog.classList.toggle('is-closing', !opening);

  const animation = parts.flip.animate(opening ? [start, middle, center] : [center, middle, start], {
    duration: opening ? TIMING.open : TIMING.close,
    fill: 'both',
  });

  // Il contenuto della faccia compare con un attimo di ritardo, quando la carta è quasi girata
  if (opening) {
    [...parts.body.children].forEach((child, i) => {
      child.animate([
        { opacity: 0, transform: 'translateY(10px)' },
        { opacity: 1, transform: 'none' },
      ], { duration: 320, delay: TIMING.open * 0.45 + i * 50, easing: 'ease-out', fill: 'backwards' });
    });
  }

  animation.finished.then(() => {
    if (!opening) dialog.close();
    animation.cancel();
    busy = false;
  });
}

/**
 * Apre la carta-modal partendo dalla carta-pulsante `tile`.
 *
 * @param {object} options
 * @param {'veloce'|'amico'} options.kind
 * @param {'1v1'|'2v2'} options.mode
 * @param {HTMLElement} options.tile        carta-pulsante toccata (colore e punto di partenza)
 * @param {object|null} [options.ratings]   rating dell'utente ({"1v1": {value, provisional}, ...}), o null
 * @param {Array} [options.friends]         amici ({user_id, username, avatar, presence}): si invitano gli "online"
 * @param {Function} [options.onPlay]
 * @param {Function} [options.onInvite]
 * @param {Function} [options.onCancelInvite]
 */
export function openModeModal({ kind, mode, tile, ratings = null, friends = [], onPlay, onInvite, onCancelInvite }) {
  if (!MODE_TEXTS[`${kind}-${mode}`]) return;
  if (!dialog) build();
  if (dialog.open || busy) return;
  current = { kind, mode, tile, ratings, handlers: { onPlay, onInvite, onCancelInvite }, invites: new Map(), started: false };

  renderTexts(kind, mode, ratings);
  dialog.dataset.opponent = 'player';
  dialog.dataset.kind = kind;   // per il CSS: con un amico, sui telefoni bassi, meno testi
  dialog.style.setProperty('--tile', getComputedStyle(tile).getPropertyValue('--tile'));

  const withFriend = kind === 'amico';
  parts.invite.hidden = !withFriend;
  setPlayReady(!withFriend);   // con un amico: solo dopo che ha accettato
  if (withFriend) {
    parts.inviteTitle.textContent = mode === '2v2' ? 'Invita da uno a tre amici' : 'Invita un amico da sfidare';
    parts.inviteHint.textContent = mode === '2v2'
      ? 'Potrai giocare appena un amico avrà accettato.'
      : "Potrai giocare quando l'amico avrà accettato.";
    renderInviteList(friends);
    refreshInvites();
  }

  dialog.showModal();
  flip(true);
}

/** Chiude la carta-modal (X, Esc, tocco fuori). Un invito aperto si annulla. */
export function closeModeModal() {
  if (!dialog?.open || busy) return;
  if (!current.started) {
    const open = [...current.invites.values()];
    current.invites.clear();
    for (const invite of open) current.handlers.onCancelInvite?.({ friend: invite.friend });
  }
  flip(false);
}

function onPlayClick() {
  if (!current || parts.play.disabled || busy) return;
  const detail = {
    kind: current.kind,
    mode: current.mode,
    targetScore: selectedTarget(),
    invitees: acceptedFriends(),
    cpu: cpuChosen(),   // P73: Partita Veloce 1v1 contro la CPU
  };
  setPlayReady(false);   // niente doppio clic
  current.started = true;
  closeModeModal();
  current.handlers.onPlay?.(detail);
}
