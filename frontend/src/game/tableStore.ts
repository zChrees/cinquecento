/**
 * Lo stato del tavolo React (passo 8 della migrazione): uno "store", cioè un
 * oggetto che tiene i dati della pagina e avvisa chi lo ascolta quando cambiano.
 * È quasi una traduzione di app/static/js/pages/game.js (scelta di Christian del
 * 20/10/2026, "Piano del passo 8"): le stesse regole, negli stessi punti; React lo
 * legge con useSyncExternalStore (useTable.ts) e ridisegna a ogni cambio.
 *
 * Cosa contiene:
 *   startTable('e5f6a7b8', null)     avvia il tavolo (partita vera o prova); restituisce la funzione per fermarlo
 *   subscribe(listener), getSnapshot()   per useSyncExternalStore
 *   viewForTable(snapshot, adesso)   la vista da disegnare (secondi scesi, mosse spente)
 *   playCard(card), sing(suit), layDown(), advise(card)   le mosse
 *   askLeave(), answerLeave(scelta)  "Esci" con la finestra di conferma
 *   togglePhrases(), closePhrases(), pickPhrase(code)     le frasi (nella prova)
 *   closeHandSummary()               "Ok" del riepilogo di fine mano
 *   handEnding(snapshot), handTotals(lastHand)   per i momenti da disegnare (GamePage.tsx)
 *   demoState(dati), demoSang(dati), demoPhrases(dati), demoPhrase(dati)  gli eventi della prova
 *
 * Partita vera (lotto 8b): si collega, manda game:join (anche dopo ogni
 * riconnessione: il server rimanda la vista attuale) e a ogni game:state tiene la
 * vista nuova; una più vecchia (version minore) si ignora. Le mosse partono con la
 * version della vista su cui si è deciso; finché non arriva la risposta carte e
 * pulsanti sono spenti (waiting). Senza connessione sono spenti (P33). Se la
 * partita si apre in un'altra scheda (game:replaced, D14) questa si ferma; se al
 * rientro la partita non c'è più (not_found, P95) compare "La partita è stata
 * interrotta" e dopo GONE_HOME_MS si torna alla home. "Esci", dopo la conferma,
 * manda game:leave (partita persa per abbandono) e torna alla home. I secondi di chi
 * è scollegato scendono da soli, ogni secondo.
 * Prova (?demo=): niente server; vista finta ed eventi demo:* come in game.js.
 *
 * Momenti del tavolo (lotto 8c, P57: noticeMoments di game.js), decisi confrontando
 * la vista nuova con quella di prima (mai alla prima vista):
 *   - presa appena chiusa (last_trick cambiato nella stessa mano): resta al centro
 *     per LAST_TRICK_MS, o finché qualcuno gioca la prima carta della presa nuova;
 *   - fine mano (hand_number salito): prima l'ultima presa della mano
 *     (last_hand.last_trick, P58), poi il riepilogo per SUMMARY_MS, o fino a "Ok";
 *     intanto carte e canti sono spenti (P69) e i punti della mano sono quelli
 *     della mano appena chiusa (P72);
 *   - carte calate (last_hand.laid_down nuovo, P85): per LAID_DOWN_MS al posto
 *     dell'ultima presa, poi il riepilogo;
 *   - carte del compagno scoperte adesso (P93): entrano, e per PARTNER_NOTICE_MS
 *     c'è la scritta "Mazzo finito: ora vedi le carte di …";
 *   - canto (game:sang, D15; demo:sang nella prova): Re e Cavallo accanto a chi ha
 *     cantato per show_seconds, e la frase nella riga di stato.
 * Restano ai lotti dopo: lanci e pescate (8d), distribuzione e anello del tempo
 * fermo nelle pause (8e), frasi e suoni nella partita vera (8f).
 *
 * DA DOVE ARRIVANO I DATI (la catena delle chiamate):
 *   1. GamePage.tsx chiama startTable con il codice della partita e ?demo=;
 *   2. lo store si collega (socket/client.ts) o carica la vista finta;
 *   3. a ogni cambio avvisa React, che chiede getSnapshot() e ridisegna il tavolo.
 */

import { connect, getStatus, isConnected, on, onStatus, send } from '../socket/client';
import type { ConnectionStatus } from '../socket/client';
import type { Card, Suit } from '../types/card';
import type { ErrorResponse, NoConnection, OkEmpty } from '../types/common';
import type { Phrase, SangEvent } from '../types/events';
import type { Advice, GameView, LaidDown, LastHand, LastTrick, Legal, PlayerView, TeamTotal } from '../types/view';
import { preloadSounds } from '../utils/sounds';
import {
  BUBBLE_MS, GONE_HOME_MS, LAID_DOWN_MS, LAST_TRICK_MS, PARTNER_NOTICE_MS, PHRASE_PAUSE_MS, SUMMARY_MS,
  TIMER_SLACK_MS,
} from './animations';
import { cardName, preloadCardImages, sameCard } from './cards';

// DEMO_VIEWS: le viste finte della prova, come DEMO_VIEWS di app/blueprints/game/routes.py
const DEMO_VIEWS: Record<string, string> = {
  '1v1': '/static/dev/vista_1v1.json',
  '2v2': '/static/dev/vista_2v2.json',
};

// I messaggi al posto del tavolo, gli stessi di table.html e game.js
const LOADING = 'Caricamento della partita…';
const WAITING = 'In attesa della partita…';
const DEMO_FAILED = 'Non riesco a caricare la partita di prova.';
const REPLACED = 'Questa partita è aperta in un\'altra scheda o su un altro dispositivo.';
const LOG_IN = 'Accedi per giocare.';

// Screen: cosa si vede al posto del tavolo. 'message' un testo, 'table' il
// tavolo, 'gone' il riquadro della partita interrotta (P95)
export type Screen = 'message' | 'table' | 'gone';

// BubbleEntry: un fumetto che si vede adesso (P56)
export interface BubbleEntry {
  // il testo della frase
  text: string;
  // performance.now() di quando è comparso (P130: un ridisegno non rifà l'entrata)
  since: number;
}

// SangEntry: le carte di un canto che si vedono adesso (D15)
export interface SangEntry {
  // l'evento game:sang (chi, seme, punti, carte, per quanti secondi)
  event: SangEvent;
  // performance.now() di quando è arrivato (P119: un ridisegno non rifà l'entrata)
  at: number;
}

// TableSnapshot: la "fotografia" dello stato in un momento. Non si modifica mai:
// a ogni cambio lo store ne fa una nuova, e React confronta le due (se è un
// oggetto diverso, ridisegna)
export interface TableSnapshot {
  // il codice della partita, per esempio 'e5f6a7b8'; da /game/<codice>
  gameId: string;
  // true nella prova (?demo=)
  demo: boolean;
  // l'indirizzo della vista finta, oppure null fuori dalla prova
  demoUrl: string | null;
  // cosa si vede
  screen: Screen;
  // il testo con screen 'message', per esempio 'In attesa della partita…'
  message: string;
  // l'ultima vista arrivata, oppure null
  view: GameView | null;
  // performance.now() di quando è arrivata la vista (per far scendere i secondi)
  viewAt: number;
  // la riga sotto la mano, per esempio un errore del server
  status: string;
  // true mentre una mossa aspetta la risposta
  waiting: boolean;
  // true dopo "Esci" confermato, mentre si aspetta la risposta a game:leave
  leaving: boolean;
  // true mentre è aperta la finestra "Vuoi uscire dalla partita?"
  confirmingLeave: boolean;
  // true se la partita si è aperta altrove o non c'è più: la pagina si ferma
  replaced: boolean;
  // lo stato della connessione (P33)
  connection: ConnectionStatus;
  // P93: la carta del compagno che gli hai consigliato, oppure null
  myAdvice: Card | null;
  // P93: true mentre il consiglio aspetta la risposta
  adviceSending: boolean;
  // P93: la carta che ti ha consigliato il compagno, oppure null
  receivedAdvice: Advice | null;
  // P56: l'elenco delle frasi, oppure null finché non arriva
  phrases: Phrase[] | null;
  // P56: l'elenco aperto, e da quando (P110)
  phrasesOpen: boolean;
  phrasesOpenedAt: number;
  // P56: performance.now() fino a cui il pulsante delle frasi resta spento
  phrasePausedUntil: number;
  // P56: posto → il fumetto che si vede
  bubbles: Record<number, BubbleEntry>;
  // P79: true quando tutte le immagini del tavolo sono pronte (data-cards-ready)
  cardsReady: boolean;
  // P57: la presa appena chiusa che si vede, oppure null; e da quando (performance.now())
  lastTrick: LastTrick | null;
  lastTrickAt: number;
  // P57: il riepilogo di fine mano che si vede, oppure null
  summary: LastHand | null;
  // P58: il riepilogo che aspetta la fine dell'ultima presa (o delle carte calate)
  nextSummary: LastHand | null;
  // P85: le carte calate che si vedono, oppure null; e da quando
  laidDown: LaidDown | null;
  laidDownAt: number;
  // P93: performance.now() di quando le carte del compagno si sono scoperte (0: alla
  // prima vista, l'entrata è già finita)
  partnerSince: number;
  // P93: true finché c'è la scritta "Mazzo finito: ora vedi le carte di …"
  partnerNotice: boolean;
  // D15: posto → le carte del canto che si vedono
  sang: Record<number, SangEntry>;
  // un contatore che sale a ogni ridisegno chiesto dal tempo (secondi che
  // scendono, fine di una pausa): cambia la fotografia anche se il resto è uguale
  tick: number;
}

// NO_MOVES: le mosse quando non se ne può fare nessuna (mossa in viaggio, uscita,
// senza connessione)
const NO_MOVES: Legal = { play: [], sing: [], lay_down: false };

/**
 * La fotografia di partenza.
 *
 * @param {string} gameId il codice della partita
 * @param {string | null} demo il valore di ?demo=, oppure null
 * @returns {TableSnapshot}
 */
function initialSnapshot(gameId: string, demo: string | null): TableSnapshot {
  let demoUrl: string | null = null;
  if (demo !== null && DEMO_VIEWS[demo] !== undefined) {
    demoUrl = DEMO_VIEWS[demo];
  }
  return {
    gameId: gameId,
    demo: demo !== null,
    demoUrl: demoUrl,
    screen: 'message',
    message: LOADING,
    view: null,
    viewAt: 0,
    status: '',
    waiting: false,
    leaving: false,
    confirmingLeave: false,
    replaced: false,
    connection: getStatus(),
    myAdvice: null,
    adviceSending: false,
    receivedAdvice: null,
    phrases: null,
    phrasesOpen: false,
    phrasesOpenedAt: 0,
    phrasePausedUntil: 0,
    bubbles: {},
    cardsReady: false,
    lastTrick: null,
    lastTrickAt: 0,
    summary: null,
    nextSummary: null,
    laidDown: null,
    laidDownAt: 0,
    partnerSince: 0,
    partnerNotice: false,
    sang: {},
    tick: 0,
  };
}

// --- Lo stato del modulo ---------------------------------------------------------

// snapshot: la fotografia attuale. Variabili del modulo: c'è un solo tavolo per
// scheda, come in game.js
let snapshot: TableSnapshot = initialSnapshot('', null);
// listeners: le funzioni da avvisare a ogni cambio (React, tramite useTable)
const listeners: Set<() => void> = new Set();
// generation: sale a ogni startTable e stopTable. Una risposta arrivata dopo che
// il tavolo è stato fermato (o riavviato) porta il numero vecchio e si ignora
let generation = 0;
// timers: i timer da fermare con stopTable
let timers: number[] = [];
// stops: le funzioni che smettono di ascoltare (socket, stato, load)
let stops: (() => void)[] = [];

/**
 * Cambia lo stato e avvisa chi ascolta.
 *
 * @param {Partial<TableSnapshot>} changes i campi che cambiano, per esempio { status: '' }
 * @returns {void}
 *
 * In parole semplici:
 *   update({ waiting: true })
 *   Fa una fotografia nuova: quella di prima con i campi cambiati.
 *   Partial<TableSnapshot> vuol dire "alcuni campi di TableSnapshot, non per forza
 *   tutti". Object.assign copia i campi uno per uno in un oggetto nuovo.
 */
function update(changes: Partial<TableSnapshot>): void {
  snapshot = Object.assign({}, snapshot, changes);
  for (const listener of listeners) {
    listener();
  }
}

/**
 * Una copia della fotografia attuale, da cambiare e poi applicare con commit.
 *
 * @returns {TableSnapshot}
 *
 * In parole semplici:
 *   const d = draft();   hideLastTrick(d);   d.view = next;   commit(d);
 *   Serve quando un evento cambia più cose insieme (una vista nuova chiude la presa
 *   e apre il riepilogo): si cambiano tutte sulla copia e React vede solo la
 *   fotografia finale, mai una a metà.
 */
function draft(): TableSnapshot {
  return Object.assign({}, snapshot);
}

/**
 * Applica la copia preparata con draft e avvisa chi ascolta.
 *
 * @param {TableSnapshot} next la copia cambiata
 */
function commit(next: TableSnapshot): void {
  snapshot = next;
  for (const listener of listeners) {
    listener();
  }
}

/** Fa ridisegnare la pagina senza cambiare dati (il tempo è passato). */
function redraw(): void {
  update({ tick: snapshot.tick + 1 });
}

/**
 * Un timer che parte solo se il tavolo è ancora quello di adesso, e che stopTable ferma.
 *
 * @param {() => void} work cosa fare
 * @param {number} ms tra quanti millisecondi
 */
function later(work: () => void, ms: number): void {
  const mine = generation;
  function run(): void {
    if (mine === generation) {
      work();
    }
  }
  timers.push(window.setTimeout(run, ms));
}

/**
 * Per useSyncExternalStore: aggiunge chi ascolta.
 *
 * @param {() => void} listener la funzione da chiamare a ogni cambio
 * @returns {() => void} la funzione per smettere
 */
export function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  function stop(): void {
    listeners.delete(listener);
  }
  return stop;
}

/**
 * Per useSyncExternalStore: la fotografia attuale.
 *
 * @returns {TableSnapshot}
 */
export function getSnapshot(): TableSnapshot {
  return snapshot;
}

/**
 * Il testo di una risposta del server: '' se è "fatto", altrimenti il messaggio dell'errore.
 *
 * @param {OkEmpty | ErrorResponse | NoConnection} answer la risposta
 * @returns {string}
 */
function answerText(answer: OkEmpty | ErrorResponse | NoConnection): string {
  if (answer.ok) {
    return '';
  }
  return answer.error.message;
}

// --- La vista da disegnare ----------------------------------------------------------

/**
 * La vista da disegnare adesso: con le mosse spente quando non si può muovere e i
 * secondi (turno e rientro) scesi dal momento in cui è arrivata.
 *
 * @param {TableSnapshot} current la fotografia
 * @param {number} now performance.now() di adesso
 * @returns {GameView | null} null se non c'è una vista
 *
 * In parole semplici:
 *   viewForTable(snapshot, performance.now())
 *   Come timed() e render() di game.js: nella prova la vista finta è una
 *   fotografia e i secondi restano fermi. Con una mossa in viaggio, dopo "Esci",
 *   senza connessione o a fine mano (P69: finché si vedono l'ultima presa della
 *   mano, le carte calate e il riepilogo) legal diventa vuoto: nessuna carta e
 *   nessun canto accesi.
 *   Le pause del tavolo (P132) arrivano con i lotti 8d-8e: per ora il turno scende subito.
 */
export function viewForTable(current: TableSnapshot, now: number): GameView | null {
  const view = current.view;
  if (view === null) {
    return null;
  }
  let offline = false;
  if (!current.demo && current.connection !== 'connected') {
    offline = true;
  }
  // shown: una copia della vista, con i campi cambiati qui sotto
  const shown: GameView = Object.assign({}, view);
  if (current.waiting || current.leaving || offline || handEnding(current)) {
    shown.legal = NO_MOVES;
  }
  if (current.demo) {
    return shown;
  }
  // passed: i secondi passati da quando la vista è arrivata
  const passed = (now - current.viewAt) / 1000;
  if (view.turn !== null) {
    shown.turn = Object.assign({}, view.turn, { seconds_left: Math.max(0, view.turn.seconds_left - passed) });
  }
  const players: PlayerView[] = [];
  for (let i = 0; i < view.players.length; i++) {
    const player = view.players[i];
    if (player.reconnect_seconds_left === null) {
      players.push(player);
    } else {
      players.push(Object.assign({}, player, { reconnect_seconds_left: Math.max(0, player.reconnect_seconds_left - passed) }));
    }
  }
  shown.players = players;
  return shown;
}

// --- I momenti del tavolo (P57, lotto 8c) ------------------------------------------------

/**
 * La mano sta finendo: si vedono l'ultima presa della mano (con il riepilogo che
 * aspetta), le carte calate o il riepilogo. Intanto carte, canti e consigli sono
 * spenti (P69).
 *
 * @param {TableSnapshot} current la fotografia
 * @returns {boolean}
 */
export function handEnding(current: TableSnapshot): boolean {
  return current.nextSummary !== null || current.summary !== null || current.laidDown !== null;
}

/**
 * P72: i punti di una mano finita (last_hand) nella forma di hand_points.
 *
 * @param {LastHand} lastHand il riepilogo della mano
 * @returns {TeamTotal[]} per esempio [{ team: 0, total: 64 }, { team: 1, total: 56 }]
 */
export function handTotals(lastHand: LastHand): TeamTotal[] {
  const totals: TeamTotal[] = [];
  for (let i = 0; i < lastHand.teams.length; i++) {
    totals.push({ team: lastHand.teams[i].team, total: lastHand.teams[i].hand_total });
  }
  return totals;
}

/**
 * Un campo della vista c'è: né null né assente.
 *
 * @param {T | null | undefined} value il campo
 * @returns {boolean} true se c'è
 *
 * In parole semplici:
 *   present(lastHand.last_trick)
 *   Come "if (lastHand.last_trick)" di game.js: il contratto dice null quando un
 *   campo non c'è, ma una vista più vecchia (prima di P58, e le viste finte dei
 *   test) può non avere proprio il campo. "value is T" dice a TypeScript che,
 *   quando la risposta è true, il valore non è né null né undefined.
 */
function present<T>(value: T | null | undefined): value is T {
  return value !== null && value !== undefined;
}

/**
 * Le carte del compagno nella vista, oppure null (nel 1v1 il campo non c'è).
 *
 * @param {GameView} view la vista
 * @returns {Card[] | null}
 */
function partnerHandOf(view: GameView): Card[] | null {
  if (view.mode === '2v2') {
    return view.partner_hand;
  }
  return null;
}

/**
 * Apre il riepilogo di fine mano, per SUMMARY_MS (o fino a "Ok").
 *
 * @param {TableSnapshot} d la copia da cambiare
 * @param {LastHand} lastHand il riepilogo
 */
function openSummary(d: TableSnapshot, lastHand: LastHand): void {
  d.summary = lastHand;
  // hide: lo chiude, ma solo se nel frattempo non se ne è aperto un altro
  function hide(): void {
    if (snapshot.summary === lastHand) {
      update({ summary: null });
    }
  }
  later(hide, SUMMARY_MS);
}

/**
 * Toglie la presa chiusa; se era l'ultima della mano, apre il riepilogo che aspettava.
 *
 * @param {TableSnapshot} d la copia da cambiare
 */
function hideLastTrick(d: TableSnapshot): void {
  d.lastTrick = null;
  if (d.nextSummary !== null) {
    const waiting = d.nextSummary;
    d.nextSummary = null;
    openSummary(d, waiting);
  }
}

/**
 * P85: toglie le carte calate; se il riepilogo aspettava, lo apre (come hideLastTrick).
 *
 * @param {TableSnapshot} d la copia da cambiare
 */
function hideLaidDown(d: TableSnapshot): void {
  d.laidDown = null;
  if (d.nextSummary !== null) {
    const waiting = d.nextSummary;
    d.nextSummary = null;
    openSummary(d, waiting);
  }
}

/**
 * Mostra la presa appena chiusa per LAST_TRICK_MS.
 *
 * @param {TableSnapshot} d la copia da cambiare
 * @param {LastTrick} trick la presa
 */
function showLastTrick(d: TableSnapshot, trick: LastTrick): void {
  hideLastTrick(d);
  d.lastTrick = trick;
  d.lastTrickAt = performance.now();
  // hide: la toglie, ma solo se è ancora quella (una presa nuova ha il suo timer)
  function hide(): void {
    if (snapshot.lastTrick === trick) {
      const next = draft();
      hideLastTrick(next);
      commit(next);
    }
  }
  later(hide, LAST_TRICK_MS);
}

/**
 * P85: mostra le carte calate per LAID_DOWN_MS.
 *
 * @param {TableSnapshot} d la copia da cambiare
 * @param {LaidDown} laid le carte calate
 */
function showLaidDown(d: TableSnapshot, laid: LaidDown): void {
  hideLaidDown(d);
  d.laidDown = laid;
  d.laidDownAt = performance.now();
  function hide(): void {
    if (snapshot.laidDown === laid) {
      const next = draft();
      hideLaidDown(next);
      commit(next);
    }
  }
  later(hide, LAID_DOWN_MS);
}

/**
 * P93: le carte del compagno si sono appena scoperte: l'entrata parte adesso e la
 * scritta "Mazzo finito: …" resta per PARTNER_NOTICE_MS.
 *
 * @param {TableSnapshot} d la copia da cambiare
 */
function showPartnerNotice(d: TableSnapshot): void {
  const since = performance.now();
  d.partnerSince = since;
  d.partnerNotice = true;
  // hide: toglie la scritta, se nel frattempo le carte non si sono riscoperte
  function hide(): void {
    if (snapshot.partnerSince === since) {
      update({ partnerNotice: false });
    }
  }
  later(hide, PARTNER_NOTICE_MS);
}

/**
 * I momenti che cominciano con la vista nuova (noticeMoments di game.js).
 *
 * @param {GameView} previous la vista di prima
 * @param {GameView} next la vista nuova
 * @param {TableSnapshot} d la copia da cambiare
 *
 * In parole semplici:
 *   noticeMoments(vistaDiPrima, vistaNuova, d)
 *   Confronta le due viste: carte del compagno appena scoperte, presa appena
 *   chiusa, mano finita (prima l'ultima presa, poi il riepilogo), carte calate.
 *   Le prese si confrontano come testo (JSON.stringify): la vista nuova è sempre un
 *   oggetto nuovo, anche quando la presa è la stessa.
 */
function noticeMoments(previous: GameView, next: GameView, d: TableSnapshot): void {
  // P93: le carte del compagno si scoprono adesso: entrano e c'è la scritta
  if (partnerHandOf(next) !== null && partnerHandOf(previous) === null) {
    showPartnerNotice(d);
  }
  if (next.hand_number !== previous.hand_number) {
    hideLastTrick(d);
  }
  // P85: qualcuno ha calato (la mano finita è nuova e ha laid_down): le carte calate
  // al posto dell'ultima presa, poi il riepilogo; se la calata chiude la partita
  // (hand_number non sale) il riepilogo è nel riquadro finale
  let previousLastHand: number | null = null;
  if (previous.last_hand !== null) {
    previousLastHand = previous.last_hand.hand_number;
  }
  if (next.last_hand !== null && present(next.last_hand.laid_down) && next.last_hand.hand_number !== previousLastHand) {
    hideLastTrick(d);
    d.summary = null;
    showLaidDown(d, next.last_hand.laid_down);
    if (next.hand_number > previous.hand_number) {
      d.nextSummary = next.last_hand;
    }
    return;
  }
  if (next.last_trick !== null && next.hand_number === previous.hand_number
    && JSON.stringify(next.last_trick) !== JSON.stringify(previous.last_trick)) {
    showLastTrick(d, next.last_trick);
  }
  if (next.hand_number > previous.hand_number && next.last_hand !== null) {
    d.summary = null;
    if (present(next.last_hand.last_trick)) {
      // Prima la presa che ha chiuso la mano, poi il riepilogo (quando la presa sparisce)
      showLastTrick(d, next.last_hand.last_trick);
      d.nextSummary = next.last_hand;
    } else {
      openSummary(d, next.last_hand);
    }
  }
}

/** "Ok" del riepilogo di fine mano: lo chiude e riaccende le carte. */
export function closeHandSummary(): void {
  update({ summary: null });
}

/**
 * D15: Re e Cavallo cantati restano accanto a chi ha cantato per show_seconds
 * secondi (P57); la frase nella riga di stato, per i lettori di schermo, dura
 * uguale se nel frattempo non arriva un altro messaggio.
 *
 * @param {SangEvent} event l'evento game:sang (o demo:sang nella prova)
 */
function showSang(event: SangEvent): void {
  if (snapshot.replaced) {
    return;
  }
  const ms = event.show_seconds * 1000;
  const entry: SangEntry = { event: event, at: performance.now() };
  const d = draft();
  d.sang = Object.assign({}, d.sang);
  d.sang[event.seat] = entry;
  let who = 'Un giocatore';
  if (d.view !== null && d.view.players[event.seat] !== undefined) {
    who = d.view.players[event.seat].username;
  }
  const text = `${who} ha cantato ${event.points} a ${event.suit}.`;
  d.status = text;
  commit(d);
  // hide: toglie le carte, ma solo se nel frattempo quel posto non ha cantato di nuovo
  function hide(): void {
    if (snapshot.sang[event.seat] !== entry) {
      return;
    }
    const left: Record<number, SangEntry> = Object.assign({}, snapshot.sang);
    delete left[event.seat];
    update({ sang: left });
  }
  // clearText: toglie la frase, se è ancora quella
  function clearText(): void {
    if (snapshot.status === text) {
      update({ status: '' });
    }
  }
  later(hide, ms);
  later(clearText, ms);
}

// --- Avvio e arresto ----------------------------------------------------------------

/**
 * Avvia il tavolo.
 *
 * @param {string} gameId il codice della partita, per esempio 'e5f6a7b8'
 * @param {string | null} demo il valore di ?demo= ('1v1', '2v2', ...), oppure null
 * @returns {() => void} la funzione che ferma il tavolo
 *
 * In parole semplici:
 *   const stop = startTable('prova', '1v1');   ...   stop();
 *   Riparte da zero (ogni startTable è un tavolo nuovo), scarica suoni e immagini e:
 *   nella prova carica la vista finta; nella partita vera si mette in ascolto del
 *   server e si collega. La funzione restituita smette di ascoltare e ferma i timer
 *   (React la chiama quando la pagina sparisce).
 */
export function startTable(gameId: string, demo: string | null): () => void {
  generation += 1;
  const mine = generation;
  snapshot = initialSnapshot(gameId, demo);

  // P118: i suoni e il contesto audio subito, prima della prima vista
  preloadSounds(true);
  // P79: le immagini delle carte dopo il "load" della pagina, come game.js
  function loadCards(): void {
    function markReady(ok: boolean): void {
      if (ok && mine === generation) {
        update({ cardsReady: true });
      }
    }
    preloadCardImages().then(markReady);
  }
  if (document.readyState === 'complete') {
    loadCards();
  } else {
    window.addEventListener('load', loadCards, { once: true });
    stops.push(function stopLoad(): void {
      window.removeEventListener('load', loadCards);
    });
  }

  if (snapshot.demo) {
    loadDemo(mine);
  } else {
    startGame();
  }
  // Chi è scollegato: "scollegato · 48 s" scende ogni secondo, senza aspettare il server
  const countdown = window.setInterval(tickReconnect, 1000);
  stops.push(function stopCountdown(): void {
    window.clearInterval(countdown);
  });

  function stop(): void {
    stopTable(mine);
  }
  return stop;
}

/**
 * Ferma il tavolo: smette di ascoltare e ferma i timer.
 *
 * @param {number} which il numero del tavolo da fermare (se nel frattempo ne è
 *   partito un altro, non si tocca)
 */
function stopTable(which: number): void {
  if (which !== generation) {
    return;
  }
  generation += 1;
  for (let i = 0; i < timers.length; i++) {
    window.clearTimeout(timers[i]);
  }
  timers = [];
  for (let i = 0; i < stops.length; i++) {
    stops[i]();
  }
  stops = [];
}

/** Ogni secondo: se qualcuno è scollegato, ridisegna (i secondi scendono). */
function tickReconnect(): void {
  const view = snapshot.view;
  if (snapshot.demo || view === null || snapshot.replaced || view.status !== 'playing') {
    return;
  }
  for (let i = 0; i < view.players.length; i++) {
    if (view.players[i].reconnect_seconds_left !== null) {
      redraw();
      return;
    }
  }
}

/**
 * Prova: carica la vista finta.
 *
 * @param {number} mine il numero del tavolo che l'ha chiesta
 */
async function loadDemo(mine: number): Promise<void> {
  const url = snapshot.demoUrl;
  if (url === null) {
    update({ message: DEMO_FAILED });
    return;
  }
  try {
    const response = await fetch(url, { headers: { Accept: 'application/json' } });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    // la vista finta, che si fida del file come la pagina si fida del server
    const loaded: GameView = await response.json();
    if (mine === generation) {
      showView(loaded);
    }
  } catch {
    if (mine === generation) {
      update({ message: DEMO_FAILED });
    }
  }
}

/** Partita vera: gli ascolti del server e il collegamento (startGame di game.js). */
function startGame(): void {
  update({ message: WAITING });
  stops.push(on('game:state', onState));
  stops.push(on('game:sang', showSang));
  stops.push(on('game:advice', onAdvice));
  stops.push(on('game:replaced', onReplaced));
  stops.push(onStatus(onConnection));
  connect();
  update({ connection: getStatus() });
  // La connessione c'è già (per esempio arrivando dalla home senza ricaricare, dal
  // lotto 8h): onStatus non avvisa, quindi game:join parte subito
  if (isConnected()) {
    join();
  }
}

/**
 * Un cambio della connessione.
 *
 * @param {ConnectionStatus} now il nuovo stato
 */
function onConnection(now: ConnectionStatus): void {
  if (snapshot.replaced) {
    return;
  }
  update({ connection: now });
  if (now === 'connected') {
    if (snapshot.view !== null) {
      update({ status: '' });
    }
    // anche dopo una riconnessione: il server rimanda la vista attuale
    join();
  } else if (now === 'not_logged_in') {
    update({ screen: 'message', message: LOG_IN });
  }
}

/** game:join: entra nella stanza; il server risponde mandando la vista. */
async function join(): Promise<void> {
  const mine = generation;
  const answer = await send('game:join', { game_id: snapshot.gameId });
  if (mine !== generation || answer.ok) {
    return;
  }
  if (snapshot.view !== null && answer.error.code === 'not_found') {
    showGone();
  } else if (snapshot.view !== null) {
    update({ status: answer.error.message });
  } else {
    update({ screen: 'message', message: answer.error.message });
  }
}

/**
 * P95: la partita non esiste più (per esempio il server si è riavviato: le partite
 * stanno solo in memoria). Al posto del tavolo il riquadro, e dopo GONE_HOME_MS la home.
 */
function showGone(): void {
  update({ replaced: true, screen: 'gone', confirmingLeave: false });
  function goHome(): void {
    window.location.assign('/');
  }
  later(goHome, GONE_HOME_MS);
}

/**
 * Una vista nuova: la tiene, se non è più vecchia di quella mostrata.
 *
 * @param {GameView} next la vista
 */
function showView(next: GameView): void {
  if (snapshot.replaced || (snapshot.view !== null && next.version < snapshot.view.version)) {
    return;
  }
  const d = draft();
  // P57: i momenti che cominciano adesso (mai alla prima vista)
  if (snapshot.view !== null) {
    noticeMoments(snapshot.view, next, d);
  }
  d.view = next;
  d.viewAt = performance.now();
  d.screen = 'table';
  // P93: il consiglio ricevuto lo ripete la vista (advice, solo nel 2v2); quello
  // dato vale finché la carta è ancora in mano al compagno
  if (next.mode === '2v2') {
    d.receivedAdvice = next.advice;
    let stillThere = false;
    if (snapshot.myAdvice !== null && next.partner_hand !== null) {
      for (let i = 0; i < next.partner_hand.length; i++) {
        if (sameCard(next.partner_hand[i], snapshot.myAdvice)) {
          stillThere = true;
        }
      }
    }
    if (!stillThere) {
      d.myAdvice = null;
    }
  }
  if (partnerHandOf(next) === null) {
    d.partnerNotice = false;
  }
  // La presa chiusa (o le carte calate, P85) lascia il posto alla presa nuova appena qualcuno gioca
  if (d.lastTrick !== null && next.trick.cards.length > 0) {
    hideLastTrick(d);
  }
  if (d.laidDown !== null && next.trick.cards.length > 0) {
    hideLaidDown(d);
  }
  commit(d);
}

/** game:state: le viste arrivano in ordine di version (contratto 3.2). */
function onState(next: GameView): void {
  showView(next);
}

/** game:advice: il compagno ti consiglia una carta (o toglie il consiglio, card null). */
function onAdvice(data: { seat: number; card: Card | null }): void {
  if (snapshot.replaced) {
    return;
  }
  if (data.card === null) {
    update({ receivedAdvice: null });
  } else {
    update({ receivedAdvice: { seat: data.seat, card: data.card } });
  }
}

/** game:replaced (D14): la partita è aperta in un'altra scheda; questa si ferma. */
function onReplaced(): void {
  update({ replaced: true, screen: 'message', message: REPLACED, confirmingLeave: false });
}

// --- Le mosse -------------------------------------------------------------------------

/**
 * Prepara una mossa: false se adesso non se ne può mandare (un'altra aspetta la
 * risposta, niente vista, partita altrove).
 */
function beginMove(): boolean {
  if (snapshot.waiting || snapshot.view === null || snapshot.replaced) {
    return false;
  }
  update({ waiting: true, status: '' });
  return true;
}

/** Fine di una mossa: con stale_state il server ha già mandato la vista attuale, basta dirlo. */
function endMove(mine: number, answer: OkEmpty | ErrorResponse | NoConnection): void {
  if (mine !== generation) {
    return;
  }
  update({ waiting: false, status: answerText(answer) });
}

/**
 * Una carta della tua mano toccata.
 *
 * @param {Card} card la carta
 */
export async function playCard(card: Card): Promise<void> {
  if (snapshot.demo) {
    update({ status: `Prova: hai scelto ${cardName(card)}. In partita la carta va al server.` });
    return;
  }
  const view = snapshot.view;
  if (view === null || !beginMove()) {
    return;
  }
  const mine = generation;
  const answer = await send('game:play_card', { game_id: snapshot.gameId, version: view.version, card: card });
  endMove(mine, answer);
}

/**
 * Un pulsante "Canta" toccato.
 *
 * @param {Suit} suit il seme
 */
export async function sing(suit: Suit): Promise<void> {
  if (snapshot.demo) {
    update({ status: `Prova: vuoi cantare a ${suit}. In partita il canto va al server.` });
    return;
  }
  const view = snapshot.view;
  if (view === null || !beginMove()) {
    return;
  }
  const mine = generation;
  const answer = await send('game:sing', { game_id: snapshot.gameId, version: view.version, suit: suit });
  endMove(mine, answer);
}

/** P85: "Cala le carte" (solo con legal.lay_down; il doppio clic lo ferma waiting, e la version). */
export async function layDown(): Promise<void> {
  if (snapshot.demo) {
    update({ status: 'Prova: vuoi calare le carte. In partita la richiesta va al server.' });
    return;
  }
  const view = snapshot.view;
  if (view === null || !beginMove()) {
    return;
  }
  const mine = generation;
  const answer = await send('game:lay_down', { game_id: snapshot.gameId, version: view.version });
  endMove(mine, answer);
}

/**
 * P93: consiglio al compagno (D46). Toccando una sua carta gliela consigli;
 * toccando quella già consigliata il consiglio si toglie. Uno alla volta.
 *
 * @param {Card} card la carta del compagno toccata
 */
export async function advise(card: Card): Promise<void> {
  if (snapshot.adviceSending || snapshot.view === null || snapshot.replaced) {
    return;
  }
  let next: Card | null = card;
  if (snapshot.myAdvice !== null && sameCard(snapshot.myAdvice, card)) {
    next = null;
  }
  if (snapshot.demo) {
    if (next === null) {
      update({ myAdvice: null, status: 'Prova: consiglio tolto.' });
    } else {
      update({ myAdvice: next, status: `Prova: consigli ${cardName(next)}. In partita il consiglio va al compagno.` });
    }
    return;
  }
  const mine = generation;
  update({ adviceSending: true });
  const answer = await send('game:advise', { game_id: snapshot.gameId, card: next });
  if (mine !== generation) {
    return;
  }
  if (answer.ok) {
    update({ adviceSending: false, myAdvice: next, status: '' });
  } else {
    update({ adviceSending: false, status: answer.error.message });
  }
}

/**
 * "Esci". A partita finita, o aperta altrove, si torna alla home senza abbandonare
 * niente; altrimenti si apre la finestra di conferma.
 */
export function askLeave(): void {
  if (snapshot.leaving) {
    return;
  }
  const view = snapshot.view;
  if (snapshot.replaced || (view !== null && view.status === 'finished')) {
    window.location.assign('/');
    return;
  }
  update({ confirmingLeave: true });
}

/**
 * La risposta della finestra di conferma.
 *
 * @param {string | null} choice 'confirm' per uscire; altro (Annulla, X, Esc) per restare
 *
 * In parole semplici:
 *   answerLeave('confirm')
 *   Nella prova torna alla home. Nella partita vera manda game:leave (la partita è
 *   persa per abbandono) e poi torna alla home; se non riesce (per esempio senza
 *   connessione) si resta al tavolo e lo si dice nella riga di stato.
 */
export async function answerLeave(choice: string | null): Promise<void> {
  update({ confirmingLeave: false });
  if (choice !== 'confirm' || snapshot.leaving) {
    return;
  }
  if (snapshot.demo) {
    window.location.assign('/');
    return;
  }
  const mine = generation;
  update({ leaving: true });
  const answer = await send('game:leave', { game_id: snapshot.gameId });
  if (mine !== generation) {
    return;
  }
  if (answer.ok) {
    window.location.assign('/');
    return;
  }
  update({ leaving: false, status: answer.error.message });
}

// --- Le frasi (P56) ---------------------------------------------------------------------

/** Apre o chiude l'elenco delle frasi. */
export function togglePhrases(): void {
  update({ phrasesOpen: !snapshot.phrasesOpen, phrasesOpenedAt: performance.now() });
}

/** Chiude l'elenco delle frasi (Esc o tocco fuori). */
export function closePhrases(): void {
  if (snapshot.phrasesOpen) {
    update({ phrasesOpen: false });
  }
}

/**
 * Il fumetto di una frase accanto a chi ha parlato, per BUBBLE_MS.
 *
 * @param {number} seat il posto di chi ha parlato
 * @param {string} text il testo
 */
function showBubble(seat: number, text: string): void {
  const entry: BubbleEntry = { text: text, since: performance.now() };
  const bubbles: Record<number, BubbleEntry> = Object.assign({}, snapshot.bubbles);
  bubbles[seat] = entry;
  update({ bubbles: bubbles });
  // hide: toglie il fumetto, ma solo se nel frattempo non ne è arrivato un altro
  function hide(): void {
    if (snapshot.bubbles[seat] !== entry) {
      return;
    }
    const left: Record<number, BubbleEntry> = Object.assign({}, snapshot.bubbles);
    delete left[seat];
    update({ bubbles: left });
  }
  later(hide, BUBBLE_MS);
}

/**
 * Una frase scelta. Nella prova mostra subito il proprio fumetto, senza server, e
 * spegne il pulsante per PHRASE_PAUSE_MS; nella partita vera l'invio arriva con il lotto 8f.
 *
 * @param {string} code il codice della frase
 */
export function pickPhrase(code: string): void {
  const view = snapshot.view;
  const phrases = snapshot.phrases;
  if (view === null || phrases === null || performance.now() < snapshot.phrasePausedUntil) {
    return;
  }
  update({ phrasesOpen: false });
  if (!snapshot.demo) {
    return;
  }
  update({ phrasePausedUntil: performance.now() + PHRASE_PAUSE_MS });
  later(redraw, PHRASE_PAUSE_MS + TIMER_SLACK_MS);
  for (let i = 0; i < phrases.length; i++) {
    if (phrases[i].code === code) {
      showBubble(view.you.seat, phrases[i].text);
    }
  }
}

// --- Gli eventi della prova (?demo=) ------------------------------------------------------

/**
 * demo:state: una vista nuova mandata da un test o dalla console.
 *
 * @param {unknown} detail i dati dell'evento: la vista
 */
export function demoState(detail: unknown): void {
  if (!snapshot.demo || detail === null || typeof detail !== 'object') {
    return;
  }
  // next: la vista del test, presa come una vista del server (anche quella non si
  // controlla campo per campo). "as" dice a TypeScript di fidarsi: qui serve,
  // perché un evento del browser non ha un tipo
  const next = detail as GameView;
  showView(next);
}

/**
 * demo:sang: un canto mandato da un test o dalla console (P57), come game:sang.
 *
 * @param {unknown} detail i dati dell'evento, per esempio
 *   { seat: 1, suit: 'coppe', points: 40, cards: [...], show_seconds: 3 }
 */
export function demoSang(detail: unknown): void {
  if (!snapshot.demo || detail === null || typeof detail !== 'object' || !('seat' in detail)
    || !('show_seconds' in detail) || typeof detail.seat !== 'number' || typeof detail.show_seconds !== 'number') {
    return;
  }
  // event: il canto del test, preso come un evento del server (come demoState)
  const event = detail as SangEvent;
  showSang(event);
}

/**
 * demo:phrases: l'elenco delle frasi; una voce senza codice o testo si salta.
 *
 * @param {unknown} detail i dati dell'evento, per esempio { phrases: [{ code, text }] }
 */
export function demoPhrases(detail: unknown): void {
  if (!snapshot.demo || detail === null || typeof detail !== 'object' || !('phrases' in detail)
    || !Array.isArray(detail.phrases)) {
    return;
  }
  const list: Phrase[] = [];
  for (let i = 0; i < detail.phrases.length; i++) {
    const item: unknown = detail.phrases[i];
    if (item !== null && typeof item === 'object' && 'code' in item && 'text' in item
      && typeof item.code === 'string' && typeof item.text === 'string') {
      list.push({ code: item.code, text: item.text });
    }
  }
  update({ phrases: list });
}

/**
 * demo:phrase: una frase detta { seat, code }; il testo si prende dall'elenco.
 *
 * @param {unknown} detail i dati dell'evento
 */
export function demoPhrase(detail: unknown): void {
  const view = snapshot.view;
  const phrases = snapshot.phrases;
  if (!snapshot.demo || view === null || phrases === null || detail === null || typeof detail !== 'object'
    || !('seat' in detail) || !('code' in detail) || typeof detail.seat !== 'number') {
    return;
  }
  const seat = detail.seat;
  if (view.players[seat] === undefined) {
    return;
  }
  for (let i = 0; i < phrases.length; i++) {
    if (phrases[i].code === detail.code) {
      showBubble(seat, phrases[i].text);
      return;
    }
  }
}
