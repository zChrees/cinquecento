/*
 * Briscola · prototipo della home (P52)
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
  $all('dialog').forEach(function (dialog) {
    dialog.addEventListener('click', function (e) {
      if (e.target !== dialog) return;
      const r = dialog.getBoundingClientRect();
      const inside = e.clientX >= r.left && e.clientX <= r.right && e.clientY >= r.top && e.clientY <= r.bottom;
      if (!inside) dialog.close();
    });
  });

  $all('[data-close]').forEach(function (b) {
    b.addEventListener('click', function () { b.closest('dialog').close(); });
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

  playBtn.addEventListener('click', function () {
    if (playBtn.disabled) return;
    const target = modal.querySelector('input[name="target"]:checked').value;
    playBtn.disabled = true;   // niente doppio clic
    modal.close();
    showToast('Cerco una partita ' + current.mode + ' a ' + target + ' punti… (prototipo)');
  });

  // ------------------------------------------------------------
  // Sfondo: carte siciliane negli spazi vuoti
  // Lo script guarda dove sono le carte-pulsante, i titoli e "giocatori online"
  // e mette le carte solo dove non toccano né quelle zone né le altre carte già
  // messe. Solo Cavallo e Re di una coppia si sovrappongono, fra loro.
  // Se lo sfondo resta troppo vuoto, altre carte vanno dietro le carte-pulsante,
  // sempre visibili almeno per un terzo. Dietro la navbar trasparente si vedono sfocate.
  // ------------------------------------------------------------
  const bgDeco = $('[data-bg-cards]');

  // Coppie Cavallo + Re dei quattro semi, e carte singole: Assi e Tre (i carichi)
  const bgPairs = ['pair:coppe', 'pair:bastoni', 'pair:spade', 'pair:denari'];
  const bgSingles = ['asso-denari', 'tre-spade', 'asso-coppe', 'tre-denari', 'asso-bastoni', 'tre-coppe', 'asso-spade', 'tre-bastoni'];

  // Zone da lasciare libere: le scritte sempre; le carte-pulsante tranne quando lo sfondo resta troppo vuoto
  const bgLabelSelector = '.online, .mode-section__title';
  const bgTileSelector = '.mode-tile';
  // Sotto questa parte di spazio libero coperta, le carte vanno anche dietro le carte-pulsante
  const bgMinCoverage = 0.45;

  // Numero "casuale" ma sempre uguale per lo stesso punto, così lo sfondo non cambia a ogni ridisegno
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

  function bgGroup(kind) {
    if (kind.indexOf('pair:') === 0) {
      const seme = kind.slice(5);
      const pair = el('span', 'bg-pair');
      pair.append(bgImage('cavallo-' + seme), bgImage('re-' + seme));
      return pair;
    }
    const card = bgImage(kind);
    card.className = 'bg-card';
    return card;
  }

  // Rettangolo occupato da un gruppo largo w e alto h, centrato in (cx, cy) e ruotato di deg gradi
  function boxOf(cx, cy, w, h, deg) {
    const a = Math.abs(deg) * Math.PI / 180;
    const bw = w * Math.cos(a) + h * Math.sin(a);
    const bh = h * Math.cos(a) + w * Math.sin(a);
    return { l: cx - bw / 2, t: cy - bh / 2, r: cx + bw / 2, b: cy + bh / 2 };
  }

  // Area della parte comune a due rettangoli (0 se non si toccano)
  function overlapArea(a, b) {
    const w = Math.min(a.r, b.r) - Math.max(a.l, b.l);
    const h = Math.min(a.b, b.b) - Math.max(a.t, b.t);
    return w > 0 && h > 0 ? w * h : 0;
  }

  function touchesAny(box, list, pad) {
    return list.some(function (o) {
      return box.l < o.r + pad && box.r > o.l - pad && box.t < o.b + pad && box.b > o.t - pad;
    });
  }

  function renderBackground() {
    const cardW = parseFloat(getComputedStyle(bgDeco).getPropertyValue('--bg-card-w'));
    const cardH = cardW / 0.61;
    const area = bgDeco.getBoundingClientRect();
    const gap = cardW * 0.12;   // spazio minimo tra due gruppi e attorno alle zone libere

    function rectOf(node) {
      const r = node.getBoundingClientRect();
      return { l: r.left - area.left, t: r.top - area.top, r: r.right - area.left, b: r.bottom - area.top };
    }

    // Zone da lasciare libere: le scritte sempre, le carte-pulsante solo nel primo giro
    const labels = $all(bgLabelSelector).map(rectOf);
    const tiles = $all(bgTileSelector).map(rectOf);
    const screen = { l: 0, t: 0, r: area.width, b: area.height };

    const placed = [];
    const groups = [];
    const step = Math.max(8, Math.round(cardW * 0.2));   // passo fitto: si riempiono anche i buchi piccoli
    const next = { pair: 0, single: 0 };   // prossima coppia e prossima carta da usare

    // Prova tutti i punti dello schermo con le passate indicate e mette le carte dove c'è posto.
    // avoid: zone da non toccare. behindTiles: le carte possono stare dietro le carte-pulsante,
    // ma devono restare visibili almeno per un terzo.
    function fill(passes, avoid, behindTiles, seed) {
      passes.forEach(function (passInfo, pass) {
        const scale = passInfo[0];
        const list = passInfo[1];
        const counter = list === bgPairs ? 'pair' : 'single';
        const salt = (seed + pass) * 7919;
        let spot = 0;   // numero del punto provato, per la casualità ripetibile
        for (let y = 0; y <= area.height; y += step) {
          for (let x = 0; x <= area.width; x += step) {
            spot += 1;
            const kind = list[next[counter] % list.length];
            const isPair = kind.indexOf('pair:') === 0;
            // Le coppie si provano solo in circa un punto su tre, così resta spazio per Assi e Tre
            if (isPair && pseudoRandom(spot + salt, 9) > 0.35) continue;
            const cw = cardW * scale;
            const ch = cardH * scale;
            // Una coppia a ventaglio occupa circa 1,75 carte in larghezza
            const w = isPair ? cw * 1.75 : cw;
            const h = isPair ? ch * 1.08 : ch;
            const deg = (pseudoRandom(spot + salt, 3) * 2 - 1) * (isPair ? 8 : 14);
            const cx = x + (pseudoRandom(spot + salt, 1) * 2 - 1) * step * 0.45;
            const cy = y + (pseudoRandom(spot + salt, 2) * 2 - 1) * step * 0.45;
            const box = boxOf(cx, cy, w, h, deg);
            const bw = box.r - box.l;
            const bh = box.b - box.t;
            // Può uscire dallo schermo al massimo per il 40%: le carte "spuntano" dai bordi
            const out = 0.4;
            if (box.l < -bw * out || box.r > area.width + bw * out || box.t < -bh * out || box.b > area.height + bh * out) continue;
            if (touchesAny(box, avoid, gap) || touchesAny(box, placed, gap * scale)) continue;
            if (behindTiles) {
              const hidden = tiles.reduce(function (sum, tile) { return sum + overlapArea(box, tile); }, 0);
              if (hidden > (bw * bh) * (2 / 3)) continue;
            }

            const node = bgGroup(kind);
            node.style.setProperty('--bg-card-w', cw.toFixed(1) + 'px');
            node.style.setProperty('--x', cx.toFixed(1) + 'px');
            node.style.setProperty('--y', cy.toFixed(1) + 'px');
            node.style.setProperty('--r', deg.toFixed(1) + 'deg');
            placed.push(box);
            groups.push(node);
            next[counter] += 1;
          }
        }
      });
    }

    // Primo giro: solo negli spazi vuoti. A misura piena prima le coppie e poi le carte singole,
    // poi le stesse al 75%, infine carte singole al 55% nei buchi rimasti.
    fill([
      [1, bgPairs], [1, bgSingles],
      [0.75, bgPairs], [0.75, bgSingles],
      [0.55, bgSingles]
    ], labels.concat(tiles), false, 0);

    // Quanta parte dello spazio libero è coperta dalle carte?
    const freeArea = area.width * area.height -
      labels.concat(tiles).reduce(function (sum, r) { return sum + overlapArea(r, screen); }, 0);
    const covered = placed.reduce(function (sum, b) { return sum + overlapArea(b, screen); }, 0);

    // Secondo giro, solo se lo sfondo è rimasto troppo vuoto (succede sui telefoni stretti):
    // le carte possono stare anche dietro le carte-pulsante e spuntare nello spazio vuoto.
    if (freeArea > 0 && covered / freeArea < bgMinCoverage) {
      fill([[1, bgPairs], [1, bgSingles], [0.75, bgSingles]], labels, true, 100);
    }

    bgDeco.replaceChildren.apply(bgDeco, groups);
  }

  // Si ridisegna quando cambia la finestra e quando titoli e carte-pulsante si spostano:
  // succede per esempio quando arrivano i font da Google, che cambiano le misure dei testi.
  let bgTimer = null;
  function scheduleBackground() {
    clearTimeout(bgTimer);
    bgTimer = setTimeout(renderBackground, 120);
  }
  window.addEventListener('resize', scheduleBackground);
  if (document.fonts) document.fonts.addEventListener('loadingdone', scheduleBackground);
  new ResizeObserver(scheduleBackground).observe($('.home__sections'));
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
