/**
 * La pagina del tavolo React: /game/<codice>?ui=react (passo 8 della migrazione,
 * docs/MIGRAZIONE-FRONTEND.md, "Piano del passo 8"). È la versione React di
 * app/templates/game/table.html e della parte "disegno" di
 * app/static/js/pages/game.js, con lo stesso HTML: <main class="page page--game">,
 * il titolo nascosto e <div class="table" data-table data-game-id ...> con dentro il tavolo.
 *
 * Cosa contiene:
 *   <GamePage />   (routes.tsx, indirizzo /game/:gameId)
 *
 * Lo stato (vista, mosse, connessione, frasi, ...) sta nello store del tavolo
 * (tableStore.ts), letto con useTable: qui si disegna soltanto, più le cose che
 * riguardano gli elementi della pagina:
 *   - gli eventi della prova (demo:state, demo:sang, demo:phrases, demo:phrase sull'elemento
 *     [data-table]), passati allo store e disegnati subito (flushSync);
 *   - Esc e il tocco fuori, che chiudono l'elenco delle frasi; la sua posizione sul
 *     telefono (P112);
 *   - l'avviso di connessione (P33), solo nella partita vera;
 *   - la finestra "Vuoi uscire dalla partita?" (P25).
 * Al tavolo niente navbar: tutto lo schermo va al gioco.
 *
 * DA DOVE ARRIVANO I DATI (la catena delle chiamate):
 *   1. il browser apre /game/e5f6a7b8?ui=react; Flask (app/blueprints/game/routes.py)
 *      controlla l'indirizzo e manda la pagina della SPA;
 *   2. React Router (routes.tsx) disegna questa pagina, che legge il codice della
 *      partita e ?demo= dall'indirizzo e avvia lo store (useTable);
 *   3. lo store riceve le viste dal server (o la vista finta) e la pagina le passa
 *      a <Table> (Table.tsx).
 */

import { useEffect, useLayoutEffect, useRef } from 'react';
import type { JSX } from 'react';
import { flushSync } from 'react-dom';
import { useParams, useSearchParams } from 'react-router';
import { ConnectionBanner } from '../components/ConnectionBanner';
import { Modal } from '../components/Modal';
import type { ModalAction } from '../components/Modal';
import type { Card } from '../types/card';
import { NO_MOMENTS, Table } from './Table';
import type { BubbleShown, PartnerMoment, SangShown, TableHandlers, TableMoments, TablePhrasesState } from './Table';
import {
  advise, answerLeave, askLeave, closeHandSummary, closePhrases, demoPhrase, demoPhrases, demoSang, demoState,
  drawing, flying, getSnapshot, handEnding, handTotals, layDown, pickPhrase, playCard, sing, togglePhrases,
  viewForTable,
} from './tableStore';
import type { TableSnapshot } from './tableStore';
import { sameCard } from './cards';
import { useTable } from './useTable';

// LEAVE_ACTIONS: i pulsanti della finestra di "Esci", come confirmModal di Modal.js
// (prima Annulla, poi la scelta rossa)
const LEAVE_ACTIONS: ModalAction[] = [
  { label: 'Annulla', value: 'cancel', variant: 'ghost' },
  { label: 'Esci', value: 'confirm', variant: 'danger' },
];

// HANDLERS: le funzioni che il tavolo chiama; sono quelle dello store
const HANDLERS: TableHandlers = {
  onPlay: playCard,
  onSing: sing,
  onLeave: askLeave,
  onLayDown: layDown,
  onAdvise: advise,
};

/**
 * Il riquadro della partita interrotta (P95), al posto del tavolo.
 *
 * @returns {JSX.Element}
 */
function GoneNotice(): JSX.Element {
  return (
    <div className="table__gone panel" data-game-gone="" role="alert">
      <h2>La partita è stata interrotta</h2>
      <p>Il server si è riavviato o la partita non esiste più.</p>
      <a className="btn btn--primary" href="/">Torna alla home</a>
    </div>
  );
}

/**
 * I momenti del tavolo da disegnare adesso.
 *
 * @param {TableSnapshot} table la fotografia dello store
 * @param {number} now performance.now() di adesso
 * @returns {TableMoments}
 *
 * In parole semplici:
 *   momentsOf(table, performance.now())
 *   Come l'oggetto moments di render() in game.js: presa chiusa, riepilogo, punti
 *   della mano appena chiusa (P72), canti, carte calate (P85), carte del compagno e
 *   consigli (P93), lanci e pescate (P70), ognuno con i millisecondi da quando si
 *   vede. Quando e per quanto lo decide lo store (tableStore.ts); la distribuzione
 *   arriva con il lotto 8e (per ora null). Alla prima vista le carte del compagno sono
 *   già lì: partnerSince è 0 e l'entrata è finita.
 */
function momentsOf(table: TableSnapshot, now: number): TableMoments {
  const moments: TableMoments = Object.assign({}, NO_MOMENTS);
  const view = table.view;
  if (view === null) {
    return moments;
  }
  const ending = handEnding(table);
  // P70: le carte in volo e le pescate in corso (lotto 8d)
  moments.thrown = flying(table, now);
  const drawn = drawing(table, now);
  moments.drawnSeats = drawn.seats;
  moments.drawnCards = drawn.cards;
  moments.lastTrick = table.lastTrick;
  if (table.lastTrick !== null) {
    moments.lastTrickFor = now - table.lastTrickAt;
  }
  moments.summary = table.summary;
  // P72: finché si vedono l'ultima presa e il riepilogo, i punti della mano appena chiusa
  if (table.nextSummary !== null) {
    moments.handPoints = handTotals(table.nextSummary);
  } else if (table.summary !== null) {
    moments.handPoints = handTotals(table.summary);
  }
  moments.onCloseSummary = closeHandSummary;
  // sang: posto → le carte del canto, con da quanto si vedono (P119)
  const sang: Record<number, SangShown> = {};
  for (let i = 0; i < view.players.length; i++) {
    const seat = view.players[i].seat;
    const entry = table.sang[seat];
    if (entry !== undefined) {
      sang[seat] = {
        seat: entry.event.seat,
        suit: entry.event.suit,
        points: entry.event.points,
        cards: entry.event.cards,
        shownFor: now - entry.at,
      };
    }
  }
  moments.sang = sang;
  moments.laidDown = table.laidDown;
  if (table.laidDown !== null) {
    moments.laidDownFor = now - table.laidDownAt;
  }
  if (view.mode !== '2v2') {
    return moments;
  }
  if (view.partner_hand !== null) {
    // picked: il consiglio vale finché la carta è ancora in mano al compagno
    let picked: Card | null = null;
    for (let i = 0; i < view.partner_hand.length; i++) {
      if (table.myAdvice !== null && sameCard(view.partner_hand[i], table.myAdvice)) {
        picked = table.myAdvice;
      }
    }
    let disabled = false;
    if (table.adviceSending || ending || (!table.demo && table.connection !== 'connected')) {
      disabled = true;
    }
    const partner: PartnerMoment = {
      picked: picked,
      disabled: disabled,
      shownFor: now - table.partnerSince,
      notice: table.partnerNotice,
    };
    moments.partner = partner;
  }
  if (!ending) {
    moments.advice = table.receivedAdvice;
  }
  return moments;
}

// aimed: le carte in volo a cui aimThrows ha già dato il punto di partenza. Un
// WeakSet è un insieme di oggetti che non li tiene in vita: quando React toglie
// l'elemento dalla pagina, sparisce anche da qui
const aimed: WeakSet<HTMLElement> = new WeakSet();

/**
 * P99, P107: dopo il disegno, per ogni carta appena entrata in volo dice al CSS
 * (card-throw di trick.css) da dove parte rispetto al suo posto sul tavolo:
 * spostamento, misura, rotazione iniziale, verso in cui gira e direzione in cui si
 * stacca (verso il centro). Senza il punto di partenza restano i valori di
 * trick.css: arriva dal suo lato. Come aimThrows di game.js.
 *
 * @param {HTMLElement} root l'elemento [data-table]
 *
 * In parole semplici:
 *   aimThrows(tableRef.current)
 *   Per misurare dove si posa, toglie per un attimo l'animazione (che così riparte
 *   da capo): per questo lo fa **una volta sola** per carta, appena nata, quando
 *   l'animazione non è ancora cominciata. game.js lo faceva a ogni ridisegno perché
 *   ricreava tutte le carte; React invece le tiene.
 */
function aimThrows(root: HTMLElement): void {
  const throws = getSnapshot().throws;
  const faces = root.querySelectorAll<HTMLElement>('.trick__card > [data-thrown]');
  for (let i = 0; i < faces.length; i++) {
    const face = faces[i];
    if (aimed.has(face)) {
      continue;
    }
    aimed.add(face);
    const entry = throws[`${face.dataset.suit}-${face.dataset.rank}`];
    if (entry === undefined || entry.from === null || face.offsetWidth === 0 || face.parentElement === null) {
      continue;
    }
    const from = entry.from;
    // Dove si posa: la carta senza l'animazione (il ritardo resta)
    face.style.animationName = 'none';
    const to = face.getBoundingClientRect();
    face.style.animationName = '';
    // Lo spostamento dell'animazione è girato con la casella della presa (un po'
    // ruotata) e ingrandito con la carta che vince (P76): si riporta nelle sue misure.
    // DOMMatrix legge la trasformazione della casella: a, b, c, d sono i numeri della
    // matrice 2x2 (rotazione e ingrandimento)
    const matrix = new DOMMatrix(getComputedStyle(face.parentElement).transform);
    let scale = parseFloat(getComputedStyle(face).scale);
    if (Number.isNaN(scale) || scale === 0) {
      scale = 1;
    }
    const det = (matrix.a * matrix.d - matrix.b * matrix.c) * scale;
    const sx = from.cx - (to.left + to.width / 2);
    const sy = from.cy - (to.top + to.height / 2);
    const dx = (matrix.d * sx - matrix.c * sy) / det;
    const dy = (matrix.a * sy - matrix.b * sx) / det;
    face.style.setProperty('--from-x', `${dx.toFixed(1)}px`);
    face.style.setProperty('--from-y', `${dy.toFixed(1)}px`);
    face.style.setProperty('--from-scale', (from.w / (face.offsetWidth * scale)).toFixed(3));
    // All'inizio com'era dov'è partita (dritta in mano, girata nel ventaglio), meno
    // la rotazione della casella
    const boxTilt = Math.atan2(matrix.b, matrix.a) * 180 / Math.PI;
    face.style.setProperty('--from-tilt', `${(from.tilt - boxTilt).toFixed(1)}deg`);
    // Gira verso il centro: da destra in senso antiorario, da sinistra in senso orario
    let turn = 14;
    if (dx > 0) {
      turn = -14;
    }
    face.style.setProperty('--from-turn', `${turn}deg`);
    // Si stacca di 16 px verso il suo posto, prima di volare
    let far = Math.hypot(dx, dy);
    if (far === 0) {
      far = 1;
    }
    face.style.setProperty('--lift-x', `${(-dx / far * 16).toFixed(1)}px`);
    face.style.setProperty('--lift-y', `${(-dy / far * 16).toFixed(1)}px`);
  }
}

/**
 * Le frasi da disegnare, oppure null finché l'elenco non arriva.
 *
 * @param {TableSnapshot} table la fotografia dello store
 * @param {number} now performance.now() di adesso
 * @returns {TablePhrasesState | null}
 */
function phrasesOf(table: TableSnapshot, now: number): TablePhrasesState | null {
  if (table.phrases === null || table.view === null) {
    return null;
  }
  const bubbles: Record<number, BubbleShown> = {};
  for (let i = 0; i < table.view.players.length; i++) {
    const seat = table.view.players[i].seat;
    const entry = table.bubbles[seat];
    if (entry !== undefined) {
      bubbles[seat] = { text: entry.text, shownFor: now - entry.since };
    }
  }
  return {
    list: table.phrases,
    open: table.phrasesOpen,
    disabled: now < table.phrasePausedUntil,
    openFor: now - table.phrasesOpenedAt,
    onToggle: togglePhrases,
    onPick: pickPhrase,
    bubbles: bubbles,
  };
}

/**
 * La pagina del tavolo.
 *
 * @returns {JSX.Element}
 *
 * In parole semplici:
 *   <GamePage />
 *   Disegna <main class="page page--game" data-page="game"> con il titolo nascosto
 *   "Partita a Cinquecento" e <div class="table" data-table>: dentro il messaggio
 *   ("Caricamento della partita…", "In attesa della partita…"), il tavolo, oppure il
 *   riquadro della partita interrotta.
 */
export function GamePage(): JSX.Element {
  // Gli hook (useState, useEffect, ...) si chiamano sempre in cima al componente,
  // mai dentro un if o un for: React li riconosce dall'ordine in cui arrivano.
  // params: i pezzi variabili dell'indirizzo; gameId è <codice> di /game/<codice>
  const params = useParams();
  // search: i parametri dopo il ?; useSearchParams restituisce due cose, i
  // parametri e la funzione per cambiarli (qui serve solo la prima)
  const [search] = useSearchParams();
  let gameId = '';
  if (params.gameId !== undefined) {
    gameId = params.gameId;
  }
  // demo: il valore di ?demo= ('1v1', '2v2'), oppure null nella partita vera
  const demo = search.get('demo');
  // table: la fotografia dello store, che fa ridisegnare la pagina quando cambia
  const table = useTable(gameId, demo);
  // tableRef: l'elemento <div data-table>. useRef è una "scatola" che resta uguale
  // tra un disegno e l'altro; React ci mette l'elemento dopo averlo disegnato
  const tableRef = useRef<HTMLDivElement | null>(null);

  /** Effetto: il titolo della scheda, come il blocco title di table.html. */
  function setTitle(): void {
    document.title = 'Partita · Cinquecento';
  }
  // []: una volta sola, all'apertura della pagina
  useEffect(setTitle, []);

  /**
   * Effetto nella prova: gli eventi demo:* sull'elemento [data-table]. Lo store li
   * riceve dentro flushSync, che fa ridisegnare React subito, prima di tornare a chi
   * ha mandato l'evento: come il tavolo Jinja, così un test che manda una vista e
   * poi guarda la pagina trova già il disegno nuovo.
   */
  function listenToDemo(): (() => void) | undefined {
    const element = tableRef.current;
    if (demo === null || element === null) {
      return undefined;
    }
    function onDemoState(event: Event): void {
      if (event instanceof CustomEvent) {
        const detail: unknown = event.detail;
        flushSync(function apply(): void {
          demoState(detail);
        });
      }
    }
    function onDemoSang(event: Event): void {
      if (event instanceof CustomEvent) {
        const detail: unknown = event.detail;
        flushSync(function apply(): void {
          demoSang(detail);
        });
      }
    }
    function onDemoPhrases(event: Event): void {
      if (event instanceof CustomEvent) {
        const detail: unknown = event.detail;
        flushSync(function apply(): void {
          demoPhrases(detail);
        });
      }
    }
    function onDemoPhrase(event: Event): void {
      if (event instanceof CustomEvent) {
        const detail: unknown = event.detail;
        flushSync(function apply(): void {
          demoPhrase(detail);
        });
      }
    }
    function stop(): void {
      if (element !== null) {
        element.removeEventListener('demo:state', onDemoState);
        element.removeEventListener('demo:sang', onDemoSang);
        element.removeEventListener('demo:phrases', onDemoPhrases);
        element.removeEventListener('demo:phrase', onDemoPhrase);
      }
    }
    element.addEventListener('demo:state', onDemoState);
    element.addEventListener('demo:sang', onDemoSang);
    element.addEventListener('demo:phrases', onDemoPhrases);
    element.addEventListener('demo:phrase', onDemoPhrase);
    return stop;
  }
  // [demo]: si rifà solo se cambia la prova
  useEffect(listenToDemo, [demo]);

  /** Effetto: l'elenco delle frasi aperto si chiude con Esc o toccando fuori (P56). */
  function watchPhrasesClose(): (() => void) | undefined {
    if (!table.phrasesOpen) {
      return undefined;
    }
    function onKey(event: KeyboardEvent): void {
      if (event.key !== 'Escape') {
        return;
      }
      closePhrases();
      // il fuoco torna al pulsante, come prima
      const button = document.querySelector<HTMLElement>('[data-phrases-button]');
      if (button !== null) {
        button.focus();
      }
    }
    function onPointer(event: PointerEvent): void {
      if (event.target instanceof Element && event.target.closest('[data-phrases-menu], [data-phrases-button]') !== null) {
        return;
      }
      closePhrases();
    }
    function stop(): void {
      document.removeEventListener('keydown', onKey);
      document.removeEventListener('pointerdown', onPointer);
    }
    document.addEventListener('keydown', onKey);
    document.addEventListener('pointerdown', onPointer);
    return stop;
  }
  // [table.phrasesOpen]: si ascolta solo mentre l'elenco è aperto
  useEffect(watchPhrasesClose, [table.phrasesOpen]);

  /**
   * Effetto dopo ogni disegno (P112): sul telefono l'elenco delle frasi comincia
   * subito sotto la tua riga (.table__me) e non si sposta più; la misura si prende
   * qui, prima che il browser mostri la pagina (useLayoutEffect, a differenza di
   * useEffect, gira prima di mostrarla), come placePhrasesMenu di game.js.
   */
  function placePhrasesMenu(): void {
    const element = tableRef.current;
    if (element === null || !window.matchMedia('(max-width: 639px)').matches) {
      return;
    }
    const menu = element.querySelector<HTMLElement>('[data-phrases-menu]');
    if (menu === null || menu.parentElement === null) {
      return;
    }
    const mine = menu.parentElement;
    const me = mine.querySelector('.table__me');
    if (me === null) {
      return;
    }
    let gap = parseFloat(getComputedStyle(mine).rowGap);
    if (Number.isNaN(gap)) {
      gap = 0;
    }
    const top = me.getBoundingClientRect().bottom - mine.getBoundingClientRect().top + gap;
    menu.style.setProperty('--phrases-phone-top', `${Math.round(top)}px`);
  }
  // nessun elenco tra quadre: dopo ogni disegno
  useLayoutEffect(placePhrasesMenu);

  /** Effetto dopo ogni disegno (P99, P107): il punto di partenza delle carte appena entrate in volo. */
  function aimNewThrows(): void {
    if (tableRef.current !== null) {
      aimThrows(tableRef.current);
    }
  }
  // nessun elenco tra quadre: dopo ogni disegno, prima che il browser mostri la pagina
  useLayoutEffect(aimNewThrows);

  // --- Il disegno ---

  const now = performance.now();
  // content: cosa sta dentro <div data-table>
  let content: JSX.Element;
  const shown = viewForTable(table, now);
  if (table.screen === 'gone') {
    content = <GoneNotice />;
  } else if (table.screen === 'table' && shown !== null) {
    content = (
      <Table
        view={shown}
        turnPaused={false}
        handlers={HANDLERS}
        status={table.status}
        moments={momentsOf(table, now)}
        phrases={phrasesOf(table, now)}
      />
    );
  } else {
    content = <p className="table__message" data-table-message="">{table.message}</p>;
  }

  // banner: l'avviso di connessione (P33), solo nella partita vera (la prova non si collega)
  let banner: JSX.Element | null = null;
  if (demo === null) {
    banner = <ConnectionBanner />;
  }
  // leaveDialog: la finestra di conferma di "Esci", mentre è aperta
  let leaveDialog: JSX.Element | null = null;
  if (table.confirmingLeave) {
    let message = 'La partita sarà persa per abbandono.';
    if (table.view !== null && table.view.mode === '2v2') {
      message = 'La partita sarà persa per abbandono, anche per il tuo compagno.';
    }
    leaveDialog = (
      <Modal title="Vuoi uscire dalla partita?" message={message} content={null} actions={LEAVE_ACTIONS}
        footer={null} onDone={answerLeave} />
    );
  }
  // demoUrlAttr e cardsReady: data-demo-url solo nella prova, data-cards-ready="1"
  // quando le immagini sono pronte (P79); undefined = niente attributo
  let demoUrlAttr: string | undefined = undefined;
  if (table.demoUrl !== null) {
    demoUrlAttr = table.demoUrl;
  }
  let cardsReady: string | undefined = undefined;
  if (table.cardsReady) {
    cardsReady = '1';
  }

  // <> ... </>: un contenitore che non diventa un elemento della pagina
  return (
    <>
      {banner}
      <main className="page page--game" data-page="game">
        <h1 className="visually-hidden">Partita a Cinquecento</h1>
        <div className="table" data-table="" data-game-id={gameId} data-demo-url={demoUrlAttr} data-cards-ready={cardsReady} ref={tableRef}>
          {content}
        </div>
      </main>
      {leaveDialog}
    </>
  );
}
