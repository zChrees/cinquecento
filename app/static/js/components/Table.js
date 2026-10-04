/**
 * Il tavolo di gioco (P21), costruito tutto dalla vista (contratto 3.3).
 *
 * Tu sei sempre in basso; gli altri si dispongono nell'ordine dei posti, verso
 * destra (D11): nel 1v1 l'avversario in alto; nel 2v2 a destra chi gioca dopo di
 * te, in alto il compagno, a sinistra chi gioca prima di te. Le loro carte coperte
 * (P70) sono ventagli agganciati al bordo dello schermo dal loro lato, per metà
 * fuori; quello in alto sta dietro la barra con "Esci" e il punteggio.
 *
 *   [Esci]        Punteggio      (P90: sotto 1024 px niente punteggio, Esci solo icona)
 *              (giocatore in alto)
 *   (sinistra)  presa · mazzo  (destra)
 *   [punti]       (tu)       [Frasi]
 *   pulsanti Canta · la tua mano
 *
 * La pagina non calcola regole: le carte giocabili sono legal.play e i canti
 * legal.sing (entrambi vuoti quando non è il tuo turno).
 *
 * I momenti del tavolo (P57) arrivano in `moments`, già decisi da pages/game.js,
 * che sa quando cominciano e quando finiscono: la presa appena chiusa, il
 * riepilogo di fine mano e le carte del canto (D15). Qui si disegnano soltanto.
 * Allo stesso modo le frasi del tavolo (P56) arrivano in `phrases`: pulsante sopra
 * la mano a destra (P71), elenco che si apre verso l'alto e fumetti accanto a chi
 * ha parlato. La briscola si vede solo sul mazzo, e a mazzo finito al suo posto (P77,
 * DeckAndTrump di Trick.js).
 * I punti della mano in corso (P72, D44): i tuoi sopra la mano a sinistra; quelli degli
 * avversari a sinistra dell'avversario in alto (1v1) o sopra quello a sinistra (2v2).
 * P85: "Cala le carte" accanto ai canti (legal.lay_down); quando qualcuno cala, per un
 * momento (moments.laidDown) i ventagli degli altri entrano scoperti nel tavolo
 * (RevealedHand), la tua mano è quella della calata e al centro c'è chi ha calato.
 * Stile in css/components/table.css, trick.css, hand-summary.css e css/pages/game.css.
 */

import { el, icon } from '../utils/dom.js';
import { Avatar } from './Avatar.js';
import { Card, cardName } from './Card.js';
import { EdgeHand, Hand, RevealedHand } from './Hand.js';
import { HandSummary } from './HandSummary.js';
import { Scoreboard } from './Scoreboard.js';
import { SingButtons } from './SingButtons.js';
import { PhraseBubble, PhrasesButton, PhrasesMenu } from './TablePhrases.js';
import { Timer } from './Timer.js';
import { DeckAndTrump, LastTrick, Trick } from './Trick.js';

const IMG_BASE = new URL('../../img/cards-bg/', import.meta.url).href;
const POSITIONS = {
  2: ['bottom', 'top'],
  4: ['bottom', 'right', 'top', 'left'],
};

function positionFn(view) {
  const n = view.players.length;
  const names = POSITIONS[n];
  return (seat) => names[(seat - view.you.seat + n) % n];
}

/** I canti di un giocatore, come icone fisse accanto al nome (D15). */
function SingBadges(view, seat) {
  const sings = view.sings.filter((sing) => sing.seat === seat);
  if (!sings.length) return null;
  return el('div', { class: 'seat__sings' }, sings.map((sing) =>
    el('span', {
      class: `sing-badge sing-badge--${sing.suit}`,
      data: { singSeat: seat, suit: sing.suit },
      // P34: con role="img" l'etichetta si legge (su uno span senza ruolo non vale)
      attrs: { role: 'img', title: `Ha cantato ${sing.points} a ${sing.suit}`, 'aria-label': `Ha cantato ${sing.points} a ${sing.suit}` },
    }, [
      el('img', { attrs: { src: `${IMG_BASE}asso-${sing.suit}-figura.webp`, alt: '' } }),
      el('span', { text: sing.points, attrs: { 'aria-hidden': 'true' } }),
    ]),
  ));
}

/**
 * Re e Cavallo appena cantati (game:sang, D15), accanto a chi ha cantato, verso il
 * centro del tavolo; spariscono dopo show_seconds (lo decide pages/game.js).
 */
function SangCards(sang, position) {
  return el('div', {
    class: `sang sang--${position}`,
    data: { sangSeat: sang.seat, suit: sang.suit, points: sang.points },
    attrs: { 'aria-hidden': 'true' }, // lo annuncia già la riga di stato
  }, [
    el('div', { class: 'sang__cards' }, sang.cards.map((card) => Card(card))),
    el('span', { class: 'sang__points', text: `Canta ${sang.points}` }),
  ]);
}

/**
 * Punti di una squadra nella mano in corso (P72, D44): sul telefono solo il numero,
 * da 1024 px in su "N punti" (la parola si nasconde in table.css).
 */
function HandPoints(points, label) {
  return el('span', {
    class: 'hand-points',
    data: { handPoints: points.total, team: points.team },
    attrs: { role: 'img', 'aria-label': `${label}: ${points.total}`, title: `${label}: ${points.total}` },
  }, [
    el('span', { class: 'hand-points__total', text: points.total }),
    el('span', { class: 'hand-points__word', text: ' punti', attrs: { 'aria-hidden': 'true' } }),
  ]);
}

/**
 * P89: il rating del giocatore (campo rating della vista, P88) in una pillola accanto
 * al nome, solo da computer (table.css); tratteggiata se è ancora provvisorio. La CPU
 * e chi non ha il rating (null) non hanno la pillola.
 */
function Rating(rating) {
  if (!rating) return null;
  const { value, provisional } = rating;
  return el('span', {
    class: `seat__rating${provisional ? ' seat__rating--provisional' : ''}`,
    data: { rating: value, ...(provisional ? { provisional: '' } : {}) },
    attrs: { title: `Rating ${value}${provisional ? ', provvisorio' : ''}` },
  }, [
    el('span', { class: 'visually-hidden', text: 'rating ' }),
    String(value),
    provisional ? el('span', { class: 'visually-hidden', text: ', provvisorio' }) : null,
  ]);
}

/** Un giocatore al tavolo: avatar (con l'anello del tempo se tocca a lui), nome, stato. */
function Seat(view, player, position, sang = null, phrase = null, points = null) {
  const isTurn = view.turn !== null && view.turn.seat === player.seat;
  const isMe = player.seat === view.you.seat;
  const partner = view.mode === '2v2' && !isMe && player.team === view.players[view.you.seat].team;

  const notes = [];
  if (partner) notes.push('compagno');
  if (!player.connected) {
    const left = player.reconnect_seconds_left;
    notes.push(left === null ? 'scollegato' : `scollegato · ${Math.ceil(left)} s`);
  }

  // P72: in alto i punti stanno a sinistra dell'avatar, per non alzare il posto
  // (sui portatili bassi la presa toccherebbe l'avversario); a sinistra sopra l'avatar
  const pointsBeside = position === 'top';
  const avatar = el('span', { class: 'seat__avatar' }, [
    pointsBeside ? points : null,
    Avatar(player),
    isTurn ? Timer(view.turn) : null,
    phrase ? PhraseBubble(player.username, phrase, position) : null,
  ]);
  const label = el('div', { class: 'seat__label' }, [
    el('span', { class: 'seat__title' }, [
      el('span', { class: 'seat__name', text: isMe ? `${player.username} (tu)` : player.username }),
      Rating(player.rating),
    ]),
    notes.length ? el('span', { class: 'seat__note', text: notes.join(' · ') }) : null,
  ]);

  return el('section', {
    class: `seat seat--${position}${isTurn ? ' seat--turn' : ''}${player.connected ? '' : ' seat--offline'}`,
    data: { seat: player.seat, position, team: player.team, turn: isTurn ? 'yes' : 'no' },
    attrs: { 'aria-label': `${player.username}${isTurn ? ', di turno' : ''}` },
  }, [
    pointsBeside ? null : points,
    avatar,
    label,
    SingBadges(view, player.seat),
    sang ? SangCards(sang, position) : null,
  ]);
}

/**
 * Riquadro di fine partita (result della vista). Se la partita è finita a punti,
 * sotto c'è il riepilogo dell'ultima mano (P57); dopo un abbandono no, perché
 * last_hand sarebbe quello di una mano precedente.
 */
function Result(view) {
  const myTeam = view.players[view.you.seat].team;
  const { winner_team: winner, reason } = view.result;
  let title = 'Pareggio';
  if (winner !== null) title = winner === myTeam ? 'Hai vinto!' : 'Hai perso';
  const text = reason === 'abandon' ? 'La partita è finita per abbandono.' : 'La partita è finita.';
  const summary = reason === 'score' && view.last_hand && view.last_hand.hand_number === view.hand_number
    ? HandSummary(view, view.last_hand)
    : null;
  return el('div', { class: 'table__result panel', data: { result: reason }, attrs: { role: 'status' } }, [
    el('h2', { text: title }),
    el('p', { text }),
    summary,
    el('a', { class: 'btn btn--primary', text: 'Torna alla home', attrs: { href: '/' } }),
  ]);
}

/** "Prendi tu", "Prende Turi". */
function winnerText(view, seat) {
  if (seat === view.you.seat) return 'Prendi tu';
  return `Prende ${view.players[seat]?.username ?? 'un giocatore'}`;
}

/** P85: "Hai calato le carte", "Turi cala le carte". */
function layDownText(view, seat) {
  if (seat === view.you.seat) return 'Hai calato le carte';
  return `${view.players[seat]?.username ?? 'Un giocatore'} cala le carte`;
}

/**
 * P85: la scritta al centro mentre si vedono le carte calate (al posto della presa,
 * che a inizio presa è vuota). Per i lettori di schermo dice anche le carte di tutti.
 */
function LaidDownNotice(view, laid, positionOf) {
  const text = layDownText(view, laid.seat);
  const cards = laid.hands
    .filter(({ cards: list }) => list.length)
    .map(({ seat, cards: list }) => `${seat === view.you.seat ? 'tu' : view.players[seat]?.username}: ${list.map(cardName).join(', ')}`);
  return el('div', {
    class: `laid-down laid-down--from-${positionOf(laid.seat)}`,
    data: { laidDown: '', laidDownSeat: laid.seat },
    attrs: { role: 'status', 'aria-label': `${text}. ${cards.join('; ')}` },
  }, [el('span', { class: 'laid-down__text', text, attrs: { 'aria-hidden': 'true' } })]);
}

/**
 * @param {object} view la vista di gioco
 * @param {object} handlers
 * @param {function} handlers.onPlay carta toccata ({suit, rank})
 * @param {function} handlers.onSing seme da cantare
 * @param {function} handlers.onLeave pulsante "Esci"
 * @param {string} [status] messaggio sotto la mano (es. risposta del server)
 * @param {object} [moments] momenti del tavolo da mostrare adesso (P57)
 * @param {object|null} [moments.lastTrick] la presa appena chiusa (last_trick)
 * @param {number} [moments.lastTrickFor] P70: millisecondi da quando la presa chiusa si vede
 * @param {object} [moments.thrown] P70: carta ("coppe-10") → millisecondi dal lancio, per le carte in volo
 * @param {object} [moments.drawnSeats] P70: posto di un avversario → millisecondi dalla sua pescata
 * @param {object} [moments.drawnCards] P70: carta pescata da te ("coppe-10") → millisecondi dalla pescata
 * @param {object|null} [moments.deal] P70, distribuzione a inizio mano: { shuffled: ms dalla
 *   mescolata o null, mine: carta → ms dalla partenza, seats: posto → [ms per carta] }
 * @param {object|null} [moments.summary] il riepilogo di fine mano (last_hand)
 * @param {Array|null} [moments.handPoints] P72: punti della mano da mostrare al posto di
 *   hand_points (a fine mano, quelli della mano appena chiusa)
 * @param {function} [moments.onCloseSummary] pulsante "Ok" del riepilogo
 * @param {object} [moments.sang] posto → evento game:sang da mostrare
 * @param {object|null} [moments.laidDown] P85: le carte calate (last_hand.laid_down) da mostrare adesso
 * @param {number} [moments.laidDownFor] P85: millisecondi da quando si vedono
 * @param {function} [handlers.onLayDown] P85: pulsante "Cala le carte"
 * @param {function} [handlers.onAdvise] P93: carta del compagno toccata (consiglio)
 * @param {object|null} [moments.partner] P93, carte del compagno scoperte (partner_hand):
 *   { picked: carta che gli hai consigliato o null, disabled, shownFor: ms da quando si
 *   vedono, notice: true finché c'è la scritta "Mazzo finito: …" }
 * @param {object|null} [moments.advice] P93: la carta che ti ha consigliato il compagno (advice.card)
 * @param {object|null} [phrases] frasi del tavolo (P56); null finché l'elenco non arriva
 * @param {Array} phrases.list l'elenco di game:phrases ({code, text})
 * @param {boolean} phrases.open l'elenco è aperto
 * @param {boolean} phrases.disabled pulsante e frasi spenti
 * @param {function} phrases.onToggle apre o chiude l'elenco
 * @param {function} phrases.onPick frase scelta (code)
 * @param {object} phrases.bubbles posto → testo del fumetto da mostrare
 * @returns {HTMLElement}
 */
export function Table(view, { onPlay, onSing, onLeave, onLayDown = null, onAdvise = null }, status = '', moments = {}, phrases = null) {
  const {
    lastTrick = null, lastTrickFor = 0, thrown = {}, drawnSeats = {}, drawnCards = {},
    deal = null, summary = null, onCloseSummary = null, sang = {},
    laidDown = null, laidDownFor = 0, partner = null, advice = null,
  } = moments;
  // P85: mentre si vedono le carte calate, posto → le sue carte
  const laidHands = laidDown ? Object.fromEntries(laidDown.hands.map(({ seat, cards }) => [seat, cards])) : null;
  const bubbles = phrases ? phrases.bubbles : {};
  const positionOf = positionFn(view);
  const me = view.players.find((player) => player.seat === view.you.seat);
  const others = view.players.filter((player) => player.seat !== view.you.seat);
  // P93: nel 2v2, a mazzo finito con la briscola, le carte del compagno (partner_hand) si vedono
  const mate = view.mode === '2v2' ? others.find((player) => player.team === me.team) : null;
  const mateCards = !laidDown && mate && view.partner_hand && view.partner_hand.length ? view.partner_hand : null;
  const adviceFrom = advice ? view.players.find((player) => player.seat === advice.seat) : null;

  // P72 (D44): i punti della mano in corso, i tuoi sopra la tua mano; quelli degli
  // avversari una volta sola, sotto il ventaglio in alto (1v1) o accanto a quello a sinistra (2v2)
  const handPoints = moments.handPoints ?? view.hand_points ?? [];
  const myPoints = handPoints.find((points) => points.team === me.team);
  const theirPoints = handPoints.find((points) => points.team !== me.team);
  const theirSeat = others.find((player) => positionOf(player.seat) === (view.mode === '2v2' ? 'left' : 'top'));
  const points = {};
  if (myPoints) {
    points[me.seat] = HandPoints(myPoints,
      view.mode === '2v2' ? 'Punti della tua squadra in questa mano' : 'I tuoi punti in questa mano');
  }
  if (theirPoints && theirSeat) {
    points[theirSeat.seat] = HandPoints(theirPoints,
      view.mode === '2v2' ? 'Punti degli avversari in questa mano' : `Punti di ${theirSeat.username} in questa mano`);
  }

  const topbar = el('header', { class: 'table__top' }, [
    el('button', {
      class: 'btn btn--ghost btn--small table__leave',
      data: { leave: '' },
      attrs: { type: 'button' },
      on: { click: onLeave },
    }, [icon('logout'), el('span', { class: 'table__leave-text', text: 'Esci' })]), // P90: sotto 1024 px solo l'icona
    Scoreboard(view),
  ]);

  const board = el('div', { class: `table__board table__board--${view.mode}` }, [
    ...others.map((player) =>
      Seat(view, player, positionOf(player.seat), sang[player.seat], bubbles[player.seat], points[player.seat])),
    el('div', { class: 'table__center' }, [
      laidDown ? LaidDownNotice(view, laidDown, positionOf) : null,
      lastTrick && !laidDown
        ? LastTrick(lastTrick, positionOf, winnerText(view, lastTrick.winner_seat), { shownFor: lastTrickFor, thrown })
        : null,
      !lastTrick && !laidDown ? Trick(view.trick, positionOf, thrown) : null,
      DeckAndTrump(view.deck_count, view.trump, deal ? deal.shuffled : null),
    ]),
    summary ? HandSummary(view, summary, { onClose: onCloseSummary }) : null,
    // P93: per un momento, quando le carte del compagno si scoprono
    mateCards && partner?.notice
      ? el('p', {
        class: 'partner-notice',
        data: { partnerNotice: '' },
        attrs: { role: 'status' },
        text: `Mazzo finito: ora vedi le carte di ${mate.username}`,
      })
      : null,
  ]);

  // Sopra la mano: i tuoi punti a sinistra, tu al centro, le frasi a destra (P71, P72, P77)
  const meRow = el('div', { class: 'table__me' }, [
    el('div', { class: 'table__me-side' }, [points[me.seat] ?? null]),
    Seat(view, me, 'bottom', sang[me.seat], bubbles[me.seat]),
    phrases ? PhrasesButton(phrases) : null,
    phrases && phrases.open ? PhrasesMenu(phrases.list, phrases) : null,
  ]);
  const mine = el('div', { class: 'table__mine' }, [
    meRow,
    SingButtons(view.legal.sing, view.sings, onSing, { can: Boolean(view.legal.lay_down), onLayDown }),
    // P85: mentre si vedono le carte calate, la tua mano è quella del momento in cui si è calato
    laidHands
      ? Hand(laidHands[me.seat] ?? [])
      : Hand(view.hand, {
        playable: view.legal.play, onPlay, drawn: drawnCards, dealt: deal ? deal.mine : {},
        advice: adviceFrom ? { card: advice.card, name: adviceFrom.username } : null,
      }),
    el('p', { class: 'table__status', text: status, data: { tableStatus: '' }, attrs: { role: 'status', 'aria-live': 'polite' } }),
  ]);

  // P70: le carte coperte degli altri, a ventaglio dal bordo dello schermo dal loro lato;
  // P85: mentre si vedono le carte calate, scoperte e dentro il tavolo
  const edgeHands = others.map((player) => {
    const side = positionOf(player.seat);
    if (laidHands) {
      const cards = laidHands[player.seat] ?? [];
      if (!cards.length) return null;
      const revealed = RevealedHand(cards, side, player.seat, `Carte di ${player.username}`);
      revealed.style.animationDelay = `${-Math.round(laidDownFor)}ms`;
      return revealed;
    }
    if (mateCards && player.seat === mate.seat) {
      const revealed = RevealedHand(mateCards, side, player.seat, `Carte di ${player.username}`, {
        onPick: onAdvise, picked: partner?.picked ?? null, disabled: !onAdvise || Boolean(partner?.disabled), name: player.username,
      });
      revealed.style.animationDelay = `${-Math.round(partner?.shownFor ?? 0)}ms`;
      return revealed;
    }
    return EdgeHand(player.cards_in_hand, side, drawnSeats[player.seat] ?? null,
      deal ? deal.seats[player.seat] ?? null : null);
  });

  // A fine partita il riquadro arriva dopo che si è vista l'ultima presa (o le carte calate, P85)
  const result = view.result && !lastTrick && !laidDown ? Result(view) : null;
  return el('div', {
    // P93: con le carte del compagno scoperte il compagno si sposta per non stare sotto il ventaglio
    class: `table__inner${mateCards ? ' table__inner--mate-cards' : ''}`,
    data: { mode: view.mode, version: view.version, status: view.status },
  }, [...edgeHands.filter(Boolean), topbar, board, mine, result]);
}
