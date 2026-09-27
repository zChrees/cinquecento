/*
 * Cinquecento · prototipo della home (P52)
 * Script classico (non modulo): il prototipo si apre con un doppio clic.
 * I dati sono finti. Il testo non viene mai inserito come HTML: solo textContent.
 */
(function () {
  'use strict';

  function $(selector, root) {
    return (root || document).querySelector(selector);
  }

  function $all(selector, root) {
    return Array.from((root || document).querySelectorAll(selector));
  }

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function iconEl(name) {
    const i = el('span', 'icon', name);
    i.setAttribute('aria-hidden', 'true');
    return i;
  }

  // ------------------------------------------------------------
  // Dati finti
  // ------------------------------------------------------------
  const friends = [
    { name: 'Giulia', online: true, status: 'Online' },
    { name: 'Salvo', online: true, status: 'Online' },
    { name: 'Rosalia', online: true, status: 'In partita' },
    { name: 'Turi', online: false, status: 'Visto 2 ore fa' },
    { name: 'Nina', online: false, status: 'Visto ieri' },
    { name: 'Pippo', online: false, status: 'Visto 3 giorni fa' }
  ];

  let requests = ['Totò'];

  const chats = {
    Giulia: [
      { mine: false, text: 'Ciao! Stasera una partita?' },
      { mine: true, text: 'Certo, dopo cena!' }
    ]
  };

  function initialOf(name) {
    return name.charAt(0).toUpperCase();
  }

  function colorIndex(name) {
    let sum = 0;
    for (let i = 0; i < name.length; i += 1) sum += name.charCodeAt(i);
    return sum % 4;
  }

  function miniAvatar(name, online) {
    const wrap = el('span', 'mini-avatar__wrap');
    wrap.setAttribute('aria-hidden', 'true');
    wrap.append(el('span', 'mini-avatar mini-avatar--' + colorIndex(name), initialOf(name)));
    if (online !== undefined) {
      wrap.append(el('span', 'mini-avatar__status' + (online ? ' mini-avatar__status--online' : '')));
    }
    return wrap;
  }

  // ------------------------------------------------------------
  // Messaggio breve
  // ------------------------------------------------------------
  const toast = $('[data-toast]');
  let toastTimer = null;

  function showToast(text) {
    toast.textContent = text;
    toast.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { toast.hidden = true; }, 2600);
  }

  // ------------------------------------------------------------
  // Finestre: apertura, chiusura con X, con Esc e toccando fuori
  // ------------------------------------------------------------

  // Le finestre con data-animated si chiudono dopo l'animazione di uscita (.is-closing).
  // Se le animazioni sono spente (es. "riduci movimento"), si chiudono subito.
  function closeDialog(dialog) {
    if (!dialog.open || dialog.classList.contains('is-closing')) return;
    if (!dialog.hasAttribute('data-animated')) {
      dialog.close();
      return;
    }
    dialog.classList.add('is-closing');
    if (getComputedStyle(dialog).animationName === 'none') {
      dialog.classList.remove('is-closing');
      dialog.close();
      return;
    }
    dialog.addEventListener('animationend', function onEnd(e) {
      if (e.target !== dialog) return;
      dialog.removeEventListener('animationend', onEnd);
      dialog.classList.remove('is-closing');
      dialog.close();
    });
  }

  $all('dialog').forEach(function (dialog) {
    dialog.addEventListener('click', function (e) {
      if (e.target !== dialog) return;
      const r = dialog.getBoundingClientRect();
      const inside = e.clientX >= r.left && e.clientX <= r.right && e.clientY >= r.top && e.clientY <= r.bottom;
      if (!inside) closeDialog(dialog);
    });

    // Esc: il browser chiuderebbe subito; lo fermiamo per far vedere l'animazione
    if (dialog.hasAttribute('data-animated')) {
      dialog.addEventListener('cancel', function (e) {
        e.preventDefault();
        closeDialog(dialog);
      });
    }
  });

  $all('[data-close]').forEach(function (b) {
    b.addEventListener('click', function () { closeDialog(b.closest('dialog')); });
  });

  $all('[data-open]').forEach(function (b) {
    b.addEventListener('click', function () {
      const dialog = document.getElementById(b.dataset.open);
      if (b.dataset.open === 'friends') showFriendsList();
      dialog.showModal();
    });
  });

  // ------------------------------------------------------------
  // Pannello amici
  // ------------------------------------------------------------
  const friendsDialog = $('#friends');
  const listView = $('[data-view="list"]', friendsDialog);
  const chatView = $('[data-view="chat"]', friendsDialog);
  const badge = $('[data-friends-badge]');
  const friendsButton = $('[data-open="friends"]');

  function renderRequests() {
    const list = $('[data-requests-list]');
    list.replaceChildren();
    $('[data-requests-section]').hidden = requests.length === 0;

    requests.forEach(function (name) {
      const li = el('li', 'friend');
      const text = el('span', 'friend__text');
      text.append(el('span', 'friend__name', name), el('span', 'friend__status', 'Vuole essere tuo amico'));

      const actions = el('span', 'friend__actions');
      const accept = el('button', 'icon-btn icon-btn--ok');
      accept.type = 'button';
      accept.setAttribute('aria-label', 'Accetta la richiesta di ' + name);
      accept.append(iconEl('check'));
      accept.addEventListener('click', function () {
        requests = requests.filter(function (n) { return n !== name; });
        friends.push({ name: name, online: true, status: 'Online' });
        renderFriends();
        showToast(name + ' ora è tuo amico');
      });

      const decline = el('button', 'icon-btn icon-btn--no');
      decline.type = 'button';
      decline.setAttribute('aria-label', 'Rifiuta la richiesta di ' + name);
      decline.append(iconEl('close'));
      decline.addEventListener('click', function () {
        requests = requests.filter(function (n) { return n !== name; });
        renderFriends();
      });

      actions.append(accept, decline);
      li.append(miniAvatar(name), text, actions);
      list.append(li);
    });

    badge.textContent = String(requests.length);
    badge.hidden = requests.length === 0;
    friendsButton.setAttribute('aria-label', requests.length
      ? 'Amici: ' + requests.length + (requests.length === 1 ? ' richiesta di amicizia' : ' richieste di amicizia')
      : 'Amici');
  }

  function friendRow(friend) {
    const li = el('li', 'friend' + (friend.online ? '' : ' friend--offline'));
    const text = el('span', 'friend__text');
    text.append(el('span', 'friend__name', friend.name), el('span', 'friend__status', friend.status));

    const actions = el('span', 'friend__actions');
    const chatBtn = el('button', 'icon-btn');
    chatBtn.type = 'button';
    chatBtn.setAttribute('aria-label', 'Chatta con ' + friend.name);
    chatBtn.append(iconEl('chat'));
    chatBtn.addEventListener('click', function () { openChat(friend.name); });
    actions.append(chatBtn);

    li.append(miniAvatar(friend.name, friend.online), text, actions);
    return li;
  }

  function renderFriends() {
    renderRequests();
    const online = friends.filter(function (f) { return f.online; });
    const offline = friends.filter(function (f) { return !f.online; });
    $('[data-friends-online]').replaceChildren.apply($('[data-friends-online]'), online.map(friendRow));
    $('[data-friends-offline]').replaceChildren.apply($('[data-friends-offline]'), offline.map(friendRow));
    $('[data-online-count]').textContent = '(' + online.length + ')';
    $('[data-offline-count]').textContent = '(' + offline.length + ')';
  }

  function showFriendsList() {
    chatView.hidden = true;
    listView.hidden = false;
  }

  // Invio della richiesta di amicizia: username obbligatorio
  const addForm = $('[data-add-friend]');
  const addError = $('[data-add-friend-error]');
  addForm.addEventListener('submit', function (e) {
    e.preventDefault();
    const input = addForm.elements.username;
    const name = input.value.trim();
    if (!name) {
      addError.hidden = false;
      input.focus();
      return;
    }
    addError.hidden = true;
    input.value = '';
    showToast('Richiesta inviata a ' + name);
  });

  // ------------------------------------------------------------
  // Chat
  // ------------------------------------------------------------
  const chatMessages = $('[data-chat-messages]');
  const chatForm = $('[data-chat-form]');
  let chatWith = null;

  function renderChat() {
    const messages = chats[chatWith] || [];
    chatMessages.replaceChildren.apply(chatMessages, messages.map(function (m) {
      return el('li', 'chat__msg' + (m.mine ? ' chat__msg--mine' : ''), m.text);
    }));
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  function openChat(name) {
    chatWith = name;
    $('[data-chat-name]').textContent = name;
    listView.hidden = true;
    chatView.hidden = false;
    renderChat();
    chatForm.elements.text.focus();
  }

  $('[data-chat-back]').addEventListener('click', showFriendsList);

  chatForm.addEventListener('submit', function (e) {
    e.preventDefault();
    const input = chatForm.elements.text;
    const text = input.value.trim();
    if (!text) return;
    if (!chats[chatWith]) chats[chatWith] = [];
    chats[chatWith].push({ mine: true, text: text });
    input.value = '';
    renderChat();
  });

  // ------------------------------------------------------------
  // Modal della modalità
  // ------------------------------------------------------------
  const modal = $('#mode-modal');
  const playBtn = $('[data-play]');
  const inviteSection = $('[data-invite-section]');
  const inviteList = $('[data-invite-list]');
  const inviteHint = $('[data-invite-hint]');
  let current = { kind: 'veloce', mode: '1v1' };
  let inviteTimer = null;

  function inviteRow(friend) {
    const li = el('li', 'invite__item');
    li.dataset.state = 'idle';
    const btn = el('button', 'invite__btn');
    btn.type = 'button';
    btn.dataset.state = 'idle';
    btn.append(iconEl('send'), document.createTextNode('Invita'));
    btn.setAttribute('aria-label', 'Invita ' + friend.name);

    btn.addEventListener('click', function () {
      // Un invito alla volta: gli altri pulsanti si disattivano
      $all('.invite__btn', inviteList).forEach(function (b) { if (b !== btn) b.disabled = true; });
      btn.disabled = true;
      btn.dataset.state = 'pending';
      btn.replaceChildren(iconEl('progress_activity'), document.createTextNode('In attesa…'));
      btn.setAttribute('aria-label', 'Invito a ' + friend.name + ' in attesa');
      inviteHint.textContent = 'Invito inviato a ' + friend.name + '. Aspettiamo che accetti…';

      // Nel prototipo l'amico accetta dopo 2 secondi
      inviteTimer = setTimeout(function () {
        li.dataset.state = 'accepted';
        btn.dataset.state = 'accepted';
        btn.replaceChildren(iconEl('check_circle'), document.createTextNode('Ha accettato'));
        btn.setAttribute('aria-label', friend.name + ' ha accettato');
        inviteHint.textContent = friend.name + ' ha accettato: puoi giocare!';
        playBtn.disabled = false;
      }, 2000);
    });

    const text = el('span', 'invite__name', friend.name);
    li.append(miniAvatar(friend.name, true), text, btn);
    return li;
  }

  function openModeModal(kind, mode) {
    current = { kind: kind, mode: mode };
    clearTimeout(inviteTimer);
    $('[data-modal-kicker]').textContent = kind === 'amico' ? 'Gioca con un amico' : 'Partita Veloce';
    $('[data-modal-title]').textContent = mode;
    modal.querySelector('input[name="target"][value="500"]').checked = true;

    const withFriend = kind === 'amico';
    inviteSection.hidden = !withFriend;
    playBtn.disabled = withFriend;

    if (withFriend) {
      $('[data-invite-title]').textContent = mode === '2v2' ? 'Invita il tuo compagno di squadra' : 'Invita un amico da sfidare';
      inviteHint.textContent = "Potrai giocare quando l'amico avrà accettato.";
      const online = friends.filter(function (f) { return f.online && f.status === 'Online'; });
      inviteList.replaceChildren.apply(inviteList, online.map(inviteRow));
    }

    modal.showModal();
  }

  modal.addEventListener('close', function () { clearTimeout(inviteTimer); });

  $all('[data-kind]').forEach(function (tile) {
    tile.addEventListener('click', function () {
      openModeModal(tile.dataset.kind, tile.dataset.mode);
    });
  });

  // Carte-pulsante in 3D: con il mouse la carta si inclina verso il puntatore e il
  // riflesso di luce lo segue. Solo con un mouse vero e senza "riduci movimento".
  const tiltAllowed = window.matchMedia('(hover: hover) and (pointer: fine)').matches &&
    !window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const tiltMax = 10;   // gradi di inclinazione massima

  if (tiltAllowed) {
    $all('.mode-tile').forEach(function (tile) {
      tile.addEventListener('pointermove', function (e) {
        // Posizione del puntatore sulla carta, da 0 a 1 in orizzontale e in verticale
        const r = tile.getBoundingClientRect();
        const px = Math.min(1, Math.max(0, (e.clientX - r.left) / r.width));
        const py = Math.min(1, Math.max(0, (e.clientY - r.top) / r.height));
        tile.style.setProperty('--ry', ((px - 0.5) * 2 * tiltMax).toFixed(1) + 'deg');
        tile.style.setProperty('--rx', ((0.5 - py) * 2 * tiltMax).toFixed(1) + 'deg');
        tile.style.setProperty('--gx', (px * 100).toFixed(0) + '%');
        tile.style.setProperty('--gy', (py * 100).toFixed(0) + '%');
      });
      tile.addEventListener('pointerleave', function () {
        ['--rx', '--ry', '--gx', '--gy'].forEach(function (name) { tile.style.removeProperty(name); });
      });
    });
  }

  playBtn.addEventListener('click', function () {
    if (playBtn.disabled) return;
    const target = modal.querySelector('input[name="target"]:checked').value;
    playBtn.disabled = true;   // niente doppio clic
    modal.close();
    showToast('Cerco una partita ' + current.mode + ' a ' + target + ' punti… (prototipo)');
  });

  // ------------------------------------------------------------
  // Sfondo: una cascata di carte che cade dall'alto senza fermarsi
  // Carte di dorso e, di faccia, Assi, Tre (i carichi) e coppie Cavallo + Re
  // a ventaglio (cantare 40). Passano dietro a tutto, anche dietro la navbar.
  // ------------------------------------------------------------
  const bgDeco = $('[data-bg-cards]');

  // Carte di faccia, a turno: ogni tanto una coppia Cavallo + Re, poi Assi e Tre
  const bgFaces = [
    'pair:coppe', 'asso-denari', 'tre-spade',
    'pair:bastoni', 'asso-coppe', 'tre-denari',
    'pair:spade', 'asso-bastoni', 'tre-coppe',
    'pair:denari', 'asso-spade', 'tre-bastoni'
  ];

  // Numero "casuale" ma sempre uguale per la stessa carta, così lo sfondo non cambia a ogni apertura
  function pseudoRandom(i, k) {
    const x = Math.sin(i * 12.9898 + k * 78.233) * 43758.5453;
    return x - Math.floor(x);
  }

  function bgImage(name) {
    const img = document.createElement('img');
    img.src = 'img/' + name + '.webp';
    img.alt = '';
    return img;
  }

  function bgCard(kind) {
    if (kind.indexOf('pair:') === 0) {
      const seme = kind.slice(5);
      const pair = el('span', 'bg-fall bg-pair');
      pair.append(bgImage('cavallo-' + seme), bgImage('re-' + seme));
      return pair;
    }
    const card = bgImage(kind);
    card.className = 'bg-fall';
    return card;
  }

  // Carte sparse su tutta la larghezza, di misure diverse. Le più piccole sembrano
  // più lontane: cadono più lente, sono più scure e passano dietro alle grandi
  // (sono piene, non trasparenti: chi sta davanti copre chi sta dietro).
  function renderBackground() {
    const cardW = parseFloat(getComputedStyle(bgDeco).getPropertyValue('--bg-card-w'));
    const area = bgDeco.getBoundingClientRect();
    const count = Math.max(8, Math.min(26, Math.round(area.width / cardW * 1.3)));
    const cards = [];
    let faces = 0;
    for (let i = 0; i < count; i += 1) {
      const rnd = function (k) { return pseudoRandom(i + 1, k + 20); };
      const depth = 0.55 + rnd(1) * 0.45;
      // Due carte su cinque cadono di dorso, alternate a quelle di faccia
      const back = i % 5 === 1 || i % 5 === 3;
      const node = back ? bgCard('dorso') : bgCard(bgFaces[faces % bgFaces.length]);
      if (!back) faces += 1;
      const dur = (9 + rnd(4) * 5) / depth;
      const r0 = (rnd(6) * 2 - 1) * 40;
      const r1 = r0 + (rnd(7) < 0.5 ? -1 : 1) * (90 + rnd(8) * 180);
      const props = {
        '--bg-card-w': (cardW * depth).toFixed(1) + 'px',
        '--x': (((i + 0.2 + rnd(3) * 0.6) / count) * area.width).toFixed(1) + 'px',
        '--y': (rnd(10) * area.height).toFixed(1) + 'px',   // posizione da ferma, senza animazioni
        '--dur': dur.toFixed(2) + 's',
        '--delay': (-rnd(5) * dur).toFixed(2) + 's',
        '--r0': r0.toFixed(1) + 'deg',
        '--r1': r1.toFixed(1) + 'deg',
        '--drift': ((rnd(9) * 2 - 1) * cardW * 1.2).toFixed(1) + 'px',
        '--shade': (0.45 + depth * 0.4).toFixed(2)   // luce: 0,67 per le lontane, 0,85 per le vicine
      };
      Object.keys(props).forEach(function (name) { node.style.setProperty(name, props[name]); });
      cards.push({ depth: depth, node: node });
    }
    // Prima le lontane, poi le vicine: nella pagina chi viene dopo sta davanti
    cards.sort(function (a, b) { return a.depth - b.depth; });
    bgDeco.replaceChildren.apply(bgDeco, cards.map(function (c) { return c.node; }));
  }

  // Si ricrea solo quando cambia la misura della finestra (la cascata riparte da capo)
  let bgTimer = null;
  window.addEventListener('resize', function () {
    clearTimeout(bgTimer);
    bgTimer = setTimeout(renderBackground, 120);
  });
  renderBackground();

  // ------------------------------------------------------------
  // Link finti
  // ------------------------------------------------------------
  $all('a[href="#"]').forEach(function (a) {
    a.addEventListener('click', function (e) { e.preventDefault(); });
  });

  // Stato iniziale dall'indirizzo (utile per confrontare): ?apri=statistiche|amici|chat|veloce|amico|invito
  const open = new URLSearchParams(window.location.search).get('apri');

  renderFriends();

  if (open === 'statistiche') $('#stats').showModal();
  if (open === 'amici') { showFriendsList(); friendsDialog.showModal(); }
  if (open === 'chat') { friendsDialog.showModal(); openChat('Giulia'); }
  if (open === 'veloce') openModeModal('veloce', '1v1');
  if (open === 'amico') openModeModal('amico', '2v2');
  if (open === 'invito') { openModeModal('amico', '2v2'); $('.invite__btn', inviteList).click(); }
})();
