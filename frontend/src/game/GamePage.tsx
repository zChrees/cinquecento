/**
 * La pagina del tavolo React: /game/<codice>?ui=react (passo 8 della migrazione,
 * docs/MIGRAZIONE-FRONTEND.md, "Piano del passo 8"). È la versione React di
 * app/templates/game/table.html e di app/static/js/pages/game.js, con lo stesso
 * HTML: <main class="page page--game">, il titolo nascosto e
 * <div class="table" data-table data-game-id ...> con dentro il tavolo.
 *
 * Cosa contiene:
 *   <GamePage />   (routes.tsx, indirizzo /game/:gameId)
 *
 * Lotto 8a (questo): il tavolo si raggiunge e si disegna "fermo" da una vista.
 *   - Prova: con ?demo=1v1 o ?demo=2v2 carica la vista finta di app/static/dev/ e
 *     non si collega al server. Come la prova di game.js accetta gli eventi del
 *     browser "demo:state" (una vista nuova), "demo:phrases" (l'elenco delle
 *     frasi) e "demo:phrase" (una frase detta) sull'elemento [data-table], per i
 *     test e per provare dalla console. Una carta, un canto o un consiglio scelti
 *     nella prova scrivono solo una frase nella riga di stato.
 *   - Partita vera: per ora "In attesa della partita…". Il collegamento
 *     (game:join, game:state, le mosse) arriva con il lotto 8b, i momenti del
 *     tavolo (presa chiusa, riepilogo, canti, lanci, ...) con 8c–8e: fino ad allora
 *     <Table> riceve NO_MOMENTS.
 * Al tavolo niente navbar: tutto lo schermo va al gioco.
 *
 * DA DOVE ARRIVANO I DATI (la catena delle chiamate):
 *   1. il browser apre /game/prova?demo=1v1&ui=react; Flask (app/blueprints/game/
 *      routes.py) controlla l'indirizzo e manda la pagina della SPA;
 *   2. React Router (routes.tsx) disegna questa pagina, che legge il codice della
 *      partita e ?demo= dall'indirizzo;
 *   3. la pagina chiede la vista finta con fetch e la passa a <Table> (Table.tsx).
 */

import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import type { JSX } from 'react';
import { useParams, useSearchParams } from 'react-router';
import type { Card, Suit } from '../types/card';
import type { Phrase } from '../types/events';
import type { GameView } from '../types/view';
import { BUBBLE_MS, PHRASE_PAUSE_MS, TIMER_SLACK_MS } from './animations';
import { cardName, sameCard } from './cards';
import { NO_MOMENTS, Table } from './Table';
import type { BubbleShown, PartnerMoment, TableHandlers, TableMoments, TablePhrasesState } from './Table';

// DEMO_VIEWS: le viste finte della prova, come DEMO_VIEWS di app/blueprints/game/routes.py
const DEMO_VIEWS: Record<string, string> = {
  '1v1': '/static/dev/vista_1v1.json',
  '2v2': '/static/dev/vista_2v2.json',
};

// I messaggi al posto del tavolo, gli stessi di table.html e game.js
const LOADING = 'Caricamento della partita…';
const WAITING = 'In attesa della partita…';
const DEMO_FAILED = 'Non riesco a caricare la partita di prova.';

// BubbleEntry: un fumetto che si vede adesso (P56)
interface BubbleEntry {
  // il testo della frase
  text: string;
  // performance.now() di quando è comparso (P130: un ridisegno non rifà l'entrata)
  since: number;
}

/**
 * Il messaggio al posto del tavolo.
 *
 * @param {{ text: string }} props il testo
 * @returns {JSX.Element}
 */
function TableMessage(props: { text: string }): JSX.Element {
  return <p className="table__message" data-table-message="">{props.text}</p>;
}

/**
 * Tiene solo le frasi ben fatte di un elenco arrivato da fuori.
 *
 * @param {unknown} data i dati dell'evento, per esempio { phrases: [{ code, text }] }
 * @returns {Phrase[] | null} le frasi, oppure null se i dati non sono un elenco
 *
 * In parole semplici:
 *   goodPhrases({ phrases: [{ code: 'bella', text: 'Bella!' }, 5] })   → [{ code: 'bella', text: 'Bella!' }]
 *   Come onPhrases di game.js: una voce senza codice o testo si salta. "unknown"
 *   vuol dire "non sappiamo ancora com'è fatto": TypeScript obbliga a controllarlo
 *   prima di usarlo.
 */
function goodPhrases(data: unknown): Phrase[] | null {
  if (data === null || typeof data !== 'object' || !('phrases' in data) || !Array.isArray(data.phrases)) {
    return null;
  }
  const list: Phrase[] = [];
  for (let i = 0; i < data.phrases.length; i++) {
    const item: unknown = data.phrases[i];
    if (item !== null && typeof item === 'object' && 'code' in item && 'text' in item
      && typeof item.code === 'string' && typeof item.text === 'string') {
      list.push({ code: item.code, text: item.text });
    }
  }
  return list;
}

/**
 * La pagina del tavolo.
 *
 * @returns {JSX.Element}
 *
 * In parole semplici:
 *   <GamePage />
 *   Disegna <main class="page page--game" data-page="game"> con il titolo nascosto
 *   "Partita a Cinquecento" e <div class="table" data-table>: dentro, finché non c'è
 *   una vista, il messaggio ("Caricamento della partita…"); poi il tavolo.
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
  // demo e demoUrl: con ?demo=1v1 o 2v2 la vista finta da caricare; null fuori dalla prova
  const demo = search.get('demo');
  let demoUrl: string | null = null;
  if (demo !== null && DEMO_VIEWS[demo] !== undefined) {
    demoUrl = DEMO_VIEWS[demo];
  }
  const isDemo = demo !== null;

  // useState restituisce due cose: il valore attuale e la funzione per cambiarlo,
  // che fa ridisegnare la pagina (regole-codice.md, sezione 6).
  // view: la vista da disegnare, oppure null finché non arriva
  const [view, setView] = useState<GameView | null>(null);
  // message: il testo al posto del tavolo finché non c'è la vista
  let firstMessage = WAITING;
  if (isDemo) {
    firstMessage = LOADING;
  }
  const [message, setMessage] = useState<string>(firstMessage);
  // status: la riga sotto la mano (per esempio "Prova: hai scelto Re di coppe...")
  const [status, setStatus] = useState<string>('');
  // myAdvice: P93, la carta del compagno che gli hai consigliato, oppure null
  const [myAdvice, setMyAdvice] = useState<Card | null>(null);
  // phrases: P56, l'elenco delle frasi, oppure null finché non arriva (niente pulsante)
  const [phrases, setPhrases] = useState<Phrase[] | null>(null);
  // phrasesOpen e phrasesOpenedAt: l'elenco aperto, e da quando (P110)
  const [phrasesOpen, setPhrasesOpen] = useState<boolean>(false);
  const [phrasesOpenedAt, setPhrasesOpenedAt] = useState<number>(0);
  // phrasePausedUntil: performance.now() fino a cui il pulsante resta spento
  const [phrasePausedUntil, setPhrasePausedUntil] = useState<number>(0);
  // bubbles: posto → il fumetto che si vede
  const [bubbles, setBubbles] = useState<Record<number, BubbleEntry>>({});
  // redraws: un contatore che serve solo a far ridisegnare la pagina (per
  // esempio alla fine della pausa delle frasi, che non cambia altri valori): il
  // valore non si legge, conta solo che cambi. "void redraws" lo nomina senza
  // farne niente, per dire che la variabile non usata è voluta
  const [redraws, setRedraws] = useState<number>(0);
  void redraws;

  // tableRef: l'elemento <div data-table>, per ascoltare gli eventi della prova.
  // useRef è una "scatola" che resta uguale tra un disegno e l'altro
  const tableRef = useRef<HTMLDivElement | null>(null);
  // viewRef e phrasesRef: la vista e le frasi di adesso, per gli ascoltatori degli
  // eventi, che sono registrati una volta sola e altrimenti vedrebbero i valori
  // del primo disegno
  const viewRef = useRef<GameView | null>(null);
  viewRef.current = view;
  const phrasesRef = useRef<Phrase[] | null>(null);
  phrasesRef.current = phrases;
  // timersRef: i timer da fermare quando la pagina sparisce
  const timersRef = useRef<number[]>([]);

  /** Effetto: il titolo della scheda, come il blocco title di table.html. */
  function setTitle(): void {
    document.title = 'Partita · Cinquecento';
  }
  // []: una volta sola, all'apertura della pagina
  useEffect(setTitle, []);

  /**
   * Fa ridisegnare la pagina tra `ms` millisecondi (più TIMER_SLACK_MS: setTimeout
   * a volte scatta un po' prima, P91).
   */
  function redrawAfter(ms: number): void {
    function redraw(): void {
      setRedraws(next);
    }
    function next(count: number): number {
      return count + 1;
    }
    timersRef.current.push(window.setTimeout(redraw, ms + TIMER_SLACK_MS));
  }

  /**
   * Il fumetto di una frase accanto a chi ha parlato, per BUBBLE_MS (P56).
   *
   * @param {number} seat il posto di chi ha parlato
   * @param {string} text il testo della frase
   */
  function showBubble(seat: number, text: string): void {
    const entry: BubbleEntry = { text: text, since: performance.now() };
    function add(current: Record<number, BubbleEntry>): Record<number, BubbleEntry> {
      const copy: Record<number, BubbleEntry> = Object.assign({}, current);
      copy[seat] = entry;
      return copy;
    }
    // remove: toglie il fumetto, ma solo se nel frattempo non ne è arrivato un altro
    function remove(current: Record<number, BubbleEntry>): Record<number, BubbleEntry> {
      if (current[seat] !== entry) {
        return current;
      }
      const copy: Record<number, BubbleEntry> = Object.assign({}, current);
      delete copy[seat];
      return copy;
    }
    function hide(): void {
      setBubbles(remove);
    }
    setBubbles(add);
    timersRef.current.push(window.setTimeout(hide, BUBBLE_MS));
  }

  /** Effetto: nella prova, carica la vista finta e ascolta gli eventi demo:*. */
  function startDemo(): (() => void) | undefined {
    const table = tableRef.current;
    if (!isDemo || table === null) {
      return undefined;
    }
    // active: false se la pagina sparisce prima che arrivi la vista
    let active = true;

    async function load(): Promise<void> {
      if (demoUrl === null) {
        setMessage(DEMO_FAILED);
        return;
      }
      try {
        const response = await fetch(demoUrl, { headers: { Accept: 'application/json' } });
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        // la vista finta, che si fida del file come la pagina si fida del server
        const loaded: GameView = await response.json();
        if (active) {
          setView(loaded);
        }
      } catch {
        if (active) {
          setMessage(DEMO_FAILED);
        }
      }
    }

    /** demo:state: una vista nuova; una più vecchia di quella mostrata si ignora. */
    function onDemoState(event: Event): void {
      if (!(event instanceof CustomEvent)) {
        return;
      }
      // next: la vista mandata dal test (detail dell'evento), come una mandata dal server
      const next: GameView = event.detail;
      function keepNewer(current: GameView | null): GameView {
        if (current !== null && next.version < current.version) {
          return current;
        }
        return next;
      }
      setView(keepNewer);
    }

    /** demo:phrases: l'elenco delle frasi. */
    function onDemoPhrases(event: Event): void {
      if (!(event instanceof CustomEvent)) {
        return;
      }
      const list = goodPhrases(event.detail);
      if (list !== null) {
        setPhrases(list);
      }
    }

    /** demo:phrase: una frase detta { seat, code }; il testo si prende dall'elenco. */
    function onDemoPhrase(event: Event): void {
      if (!(event instanceof CustomEvent) || event.detail === null || typeof event.detail !== 'object') {
        return;
      }
      const seat: unknown = event.detail.seat;
      const code: unknown = event.detail.code;
      const list = phrasesRef.current;
      const current = viewRef.current;
      if (list === null || current === null || typeof seat !== 'number' || current.players[seat] === undefined) {
        return;
      }
      for (let i = 0; i < list.length; i++) {
        if (list[i].code === code) {
          showBubble(seat, list[i].text);
          return;
        }
      }
    }

    function stop(): void {
      active = false;
      if (table !== null) {
        table.removeEventListener('demo:state', onDemoState);
        table.removeEventListener('demo:phrases', onDemoPhrases);
        table.removeEventListener('demo:phrase', onDemoPhrase);
      }
    }

    table.addEventListener('demo:state', onDemoState);
    table.addEventListener('demo:phrases', onDemoPhrases);
    table.addEventListener('demo:phrase', onDemoPhrase);
    load();
    return stop;
  }
  // [demoUrl]: si rifà solo se cambia la vista finta (cioè cambiando indirizzo)
  useEffect(startDemo, [demoUrl]);

  /** Effetto: alla chiusura della pagina si fermano tutti i timer. */
  function watchTimers(): () => void {
    function stopTimers(): void {
      for (let i = 0; i < timersRef.current.length; i++) {
        window.clearTimeout(timersRef.current[i]);
      }
      timersRef.current = [];
    }
    return stopTimers;
  }
  // []: una volta sola
  useEffect(watchTimers, []);

  /** Effetto: l'elenco delle frasi aperto si chiude con Esc o toccando fuori (P56). */
  function watchPhrasesClose(): (() => void) | undefined {
    if (!phrasesOpen) {
      return undefined;
    }
    function onKey(event: KeyboardEvent): void {
      if (event.key !== 'Escape') {
        return;
      }
      setPhrasesOpen(false);
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
      setPhrasesOpen(false);
    }
    function stop(): void {
      document.removeEventListener('keydown', onKey);
      document.removeEventListener('pointerdown', onPointer);
    }
    document.addEventListener('keydown', onKey);
    document.addEventListener('pointerdown', onPointer);
    return stop;
  }
  // [phrasesOpen]: si ascolta solo mentre l'elenco è aperto
  useEffect(watchPhrasesClose, [phrasesOpen]);

  /**
   * Effetto dopo ogni disegno (P112): sul telefono l'elenco delle frasi comincia
   * subito sotto la tua riga (.table__me) e non si sposta più; la misura si prende
   * qui, prima che il browser mostri la pagina (useLayoutEffect, a differenza di
   * useEffect, gira prima di mostrarla), come placePhrasesMenu di game.js.
   */
  function placePhrasesMenu(): void {
    const table = tableRef.current;
    if (table === null || !window.matchMedia('(max-width: 639px)').matches) {
      return;
    }
    const menu = table.querySelector<HTMLElement>('[data-phrases-menu]');
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

  // --- Le funzioni che il tavolo chiama (TableHandlers) ---

  /** Una carta della tua mano toccata. */
  function onPlay(card: Card): void {
    if (isDemo) {
      setStatus(`Prova: hai scelto ${cardName(card)}. In partita la carta va al server.`);
    }
    // Partita vera: game:play_card arriva con il lotto 8b
  }

  /** Un pulsante "Canta" toccato. */
  function onSing(suit: Suit): void {
    if (isDemo) {
      setStatus(`Prova: vuoi cantare a ${suit}. In partita il canto va al server.`);
    }
  }

  /** "Cala le carte" (P85). */
  function onLayDown(): void {
    if (isDemo) {
      setStatus('Prova: vuoi calare le carte. In partita la richiesta va al server.');
    }
  }

  /**
   * Una carta del compagno toccata (P93): la consigli; toccando quella già
   * consigliata il consiglio si toglie.
   */
  function onAdvise(card: Card): void {
    let next: Card | null = card;
    if (myAdvice !== null && sameCard(myAdvice, card)) {
      next = null;
    }
    if (isDemo) {
      setMyAdvice(next);
      if (next === null) {
        setStatus('Prova: consiglio tolto.');
      } else {
        setStatus(`Prova: consigli ${cardName(next)}. In partita il consiglio va al compagno.`);
      }
    }
  }

  /**
   * "Esci". A partita finita, o nella prova, si torna alla home. Nella partita vera
   * la conferma e game:leave arrivano con il lotto 8b.
   */
  function onLeave(): void {
    if (isDemo || (view !== null && view.status === 'finished')) {
      window.location.assign('/');
    }
  }

  /** Apre o chiude l'elenco delle frasi. */
  function onTogglePhrases(): void {
    setPhrasesOpen(!phrasesOpen);
    setPhrasesOpenedAt(performance.now());
  }

  /** Una frase scelta: nella prova mostra subito il proprio fumetto, senza server. */
  function onPickPhrase(code: string): void {
    if (view === null || phrases === null || performance.now() < phrasePausedUntil) {
      return;
    }
    setPhrasesOpen(false);
    if (!isDemo) {
      return; // Partita vera: game:send_phrase arriva con il lotto 8f
    }
    setPhrasePausedUntil(performance.now() + PHRASE_PAUSE_MS);
    redrawAfter(PHRASE_PAUSE_MS);
    for (let i = 0; i < phrases.length; i++) {
      if (phrases[i].code === code) {
        showBubble(view.you.seat, phrases[i].text);
      }
    }
  }

  // --- Il disegno ---

  let content: JSX.Element;
  if (view === null) {
    content = <TableMessage text={message} />;
  } else {
    const now = performance.now();
    // moments: nel lotto 8a nessun momento, tranne le carte del compagno scoperte
    // (P93) e il consiglio ricevuto, che sono campi della vista
    const moments: TableMoments = Object.assign({}, NO_MOMENTS);
    if (view.mode === '2v2') {
      if (view.partner_hand !== null) {
        // picked: il consiglio vale finché la carta è ancora in mano al compagno
        let picked: Card | null = null;
        for (let i = 0; i < view.partner_hand.length; i++) {
          if (myAdvice !== null && sameCard(view.partner_hand[i], myAdvice)) {
            picked = myAdvice;
          }
        }
        // shownFor: alla prima vista le carte sono già lì, l'entrata è finita
        // (come game.js, che conta dall'apertura della pagina)
        const partner: PartnerMoment = { picked: picked, disabled: false, shownFor: now, notice: false };
        moments.partner = partner;
      }
      moments.advice = view.advice;
    }
    // shownPhrases: le frasi per il tavolo, oppure null finché l'elenco non arriva
    let shownPhrases: TablePhrasesState | null = null;
    if (phrases !== null) {
      const shownBubbles: Record<number, BubbleShown> = {};
      for (let i = 0; i < view.players.length; i++) {
        const seat = view.players[i].seat;
        if (bubbles[seat] !== undefined) {
          shownBubbles[seat] = { text: bubbles[seat].text, shownFor: now - bubbles[seat].since };
        }
      }
      shownPhrases = {
        list: phrases,
        open: phrasesOpen,
        disabled: now < phrasePausedUntil,
        openFor: now - phrasesOpenedAt,
        onToggle: onTogglePhrases,
        onPick: onPickPhrase,
        bubbles: shownBubbles,
      };
    }
    const handlers: TableHandlers = {
      onPlay: onPlay,
      onSing: onSing,
      onLeave: onLeave,
      onLayDown: onLayDown,
      onAdvise: onAdvise,
    };
    content = (
      <Table
        view={view}
        turnPaused={false}
        handlers={handlers}
        status={status}
        moments={moments}
        phrases={shownPhrases}
      />
    );
  }

  // demoUrlAttr: data-demo-url solo nella prova (undefined = niente attributo)
  let demoUrlAttr: string | undefined = undefined;
  if (demoUrl !== null) {
    demoUrlAttr = demoUrl;
  }
  return (
    <main className="page page--game" data-page="game">
      <h1 className="visually-hidden">Partita a Cinquecento</h1>
      <div className="table" data-table="" data-game-id={gameId} data-demo-url={demoUrlAttr} ref={tableRef}>
        {content}
      </div>
    </main>
  );
}
