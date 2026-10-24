/**
 * La schermata di attesa in coda (P22; DECISIONI.md: "Attesa in coda a tutto
 * schermo", con il tempo trascorso, l'intervallo di rating e "Annulla"; stile in
 * css/components/queue-overlay.css).
 *
 * Si disegna dallo stato della coda del contratto (4, queue:status): { mode,
 * target_score, seconds_waiting, rating_range, partner, opponents }. La pagina non
 * calcola l'intervallo: lo manda il server, che lo allarga ogni 10 secondi (D16);
 * tra un invio e l'altro la schermata conta da sola i secondi.
 *
 * Cosa contiene:
 *   <QueueOverlay key={queueKey(queue)} queue={queue} cancelling={...} onCancel={...} />
 *   queueKey(queue)   il "nome" di una coda: modo, punti, compagno, avversari
 *   formatWait(83)    →  '1:23'
 *
 * P105: con un queue:status della stessa coda (stesso queueKey: l'intervallo si è
 * allargato) la schermata non si riapre, perché faceva un lampo: cambiano solo i
 * numeri dell'intervallo, che scorrono fino ai valori nuovi. Con una coda diversa
 * il key cambia e React ne disegna una nuova (si chiude e si riapre).
 * "Annulla" (o Esc) chiama onCancel; mentre cancelling è true il pulsante è spento.
 *
 * DA DOVE ARRIVANO I DATI: la coda da queue:join e queue:status (HomePage.tsx, con
 * socket/); i nomi e gli avatar di compagno e avversari dalla coda stessa.
 */

import { useEffect, useRef, useState } from 'react';
import type { JSX, RefObject, SyntheticEvent } from 'react';
import type { UserRef } from '../types/common';
import type { QueueStatus } from '../types/events';
import { reduceMotion } from '../utils/motion';
import { Avatar } from './Avatar';

// CARD_BACK: il dorso delle carte disegnate sopra il titolo
const CARD_BACK = '/static/img/cards-bg/dorso.webp';

// CARD_KEYS: le tre carte del dorso. key è il "nome" con cui React riconosce
// ogni elemento di un elenco tra un disegno e l'altro
const CARD_KEYS: string[] = ['prima', 'seconda', 'terza'];

// RANGE_MS: P105, in quanti millisecondi i numeri dell'intervallo arrivano ai valori nuovi
const RANGE_MS = 500;

// TICK_MS: ogni quanto si aggiorna il tempo trascorso
const TICK_MS = 1000;

// QueueOverlayProps: cosa riceve il componente
interface QueueOverlayProps {
  // lo stato della coda (queue:status o la risposta di queue:join)
  queue: QueueStatus;
  // true mentre "Annulla" aspetta la risposta del server (pulsante spento)
  cancelling: boolean;
  // la funzione da chiamare con "Annulla" o Esc. In C: void (*onCancel)(void)
  onCancel: () => void;
}

/**
 * I secondi come minuti:secondi.
 *
 * @param {number} seconds per esempio 83,4
 * @returns {string} per esempio '1:23'
 *
 * In parole semplici:
 *   formatWait(83)  →  '1:23';   formatWait(5)  →  '0:05';   formatWait(-2)  →  '0:00'
 */
export function formatWait(seconds: number): string {
  const total = Math.max(0, Math.floor(seconds));
  const minutes = Math.floor(total / 60);
  return `${minutes}:${String(total % 60).padStart(2, '0')}`;
}

/**
 * Il "nome" di una coda, per capire se un queue:status nuovo è la stessa coda.
 *
 * @param {QueueStatus} queue
 * @returns {string} per esempio '["1v1",500,null,[],true]'
 *
 * In parole semplici:
 *   queueKey(coda)
 *   Uguale se modo, punti, compagno, avversari e "c'è un intervallo" sono uguali
 *   (anche in data-queue-key). Cambiano solo i
 *   secondi e i numeri dell'intervallo: allora è la stessa coda.
 */
export function queueKey(queue: QueueStatus): string {
  let partner: number | null = null;
  if (queue.partner !== null) {
    partner = queue.partner.user_id;
  }
  const opponents: number[] = [];
  for (let i = 0; i < queue.opponents.length; i++) {
    opponents.push(queue.opponents[i].user_id);
  }
  return JSON.stringify([queue.mode, queue.target_score, partner, opponents, queue.rating_range !== null]);
}

/**
 * Il titolo della schermata.
 *
 * @param {QueueStatus} queue
 * @returns {string}
 *
 * In parole semplici:
 *   1v1 → 'Cerco un avversario…'; 2v2 da solo → 'Cerco compagno e avversari…';
 *   2v2 con un amico → 'Cerco gli avversari…'; gruppo di tre amici (P59) →
 *   'Cerco il quarto giocatore…'
 */
function titleFor(queue: QueueStatus): string {
  if (queue.mode === '1v1') {
    return 'Cerco un avversario…';
  }
  if (queue.opponents.length > 0) {
    return 'Cerco il quarto giocatore…';
  }
  if (queue.partner !== null) {
    return 'Cerco gli avversari…';
  }
  return 'Cerco compagno e avversari…';
}

/**
 * La prima parte della riga piccola in alto.
 *
 * @param {QueueStatus} queue
 * @returns {string} 'Con gli amici', 'Con un amico' oppure 'Partita Veloce'
 */
function sectionFor(queue: QueueStatus): string {
  if (queue.opponents.length > 0) {
    return 'Con gli amici';
  }
  if (queue.partner !== null) {
    return 'Con un amico';
  }
  return 'Partita Veloce';
}

// RangeNumberProps: cosa riceve un numero dell'intervallo
interface RangeNumberProps {
  // il valore a cui arrivare, per esempio 1340
  value: number;
  // quale dei due: 'min' (data-range-min) o 'max' (data-range-max)
  side: 'min' | 'max';
}

/**
 * Un numero dell'intervallo, che scorre fino al valore nuovo (P105).
 *
 * @param {RangeNumberProps} props
 * @returns {JSX.Element}
 *
 * In parole semplici:
 *   <RangeNumber value={1340} side="min" />
 *   → <span data-range-min="1340">1340</span>. Quando value cambia, l'attributo
 *   ha subito il valore nuovo e il testo ci arriva in mezzo secondo, rallentando
 *   alla fine; con "riduci movimento" subito.
 */
function RangeNumber(props: RangeNumberProps): JSX.Element {
  // useState restituisce due cose: il valore attuale e la funzione per cambiarlo,
  // che fa ridisegnare il componente (regole-codice.md, sezione 6).
  // shown: il numero scritto adesso
  const [shown, setShown] = useState<number>(props.value);
  // shownRef: lo stesso numero, letto dall'effetto senza aspettare un disegno
  const shownRef: RefObject<number> = useRef<number>(props.value);

  /** Effetto quando cambia il valore: fa scorrere il numero. */
  function slide(): () => void {
    // frame: la prossima chiamata di requestAnimationFrame (0 = nessuna)
    let frame = 0;
    const from = shownRef.current;
    const to = props.value;

    function show(value: number): void {
      shownRef.current = value;
      setShown(value);
    }

    function step(now: number): void {
      const t = Math.min(1, (now - start) / RANGE_MS);
      // eased: da 0 a 1, veloce all'inizio e lento alla fine
      const eased = 1 - (1 - t) ** 3;
      show(Math.round(from + (to - from) * eased));
      if (t < 1) {
        frame = requestAnimationFrame(step);
      }
    }

    function stop(): void {
      cancelAnimationFrame(frame);
    }

    const start = performance.now();
    if (from === to || reduceMotion()) {
      show(to);
    } else {
      frame = requestAnimationFrame(step);
    }
    return stop;
  }

  // [props.value]: si rifà a ogni valore nuovo (un valore arrivato a metà
  // ferma lo scorrimento di prima con stop, e riparte da dove era)
  useEffect(slide, [props.value]);

  if (props.side === 'min') {
    return <span data-range-min={props.value}>{shown}</span>;
  }
  return <span data-range-max={props.value}>{shown}</span>;
}

// PlayersLineProps: cosa riceve la riga di compagno o avversari
interface PlayersLineProps {
  // i giocatori, con nome e avatar
  players: UserRef[];
  // il testo, per esempio 'In squadra con Giulia'
  text: string;
}

/**
 * Gli avatar (P43) e il testo di "In squadra con Giulia" o "Contro Giulia e Salvo".
 *
 * @param {PlayersLineProps} props
 * @returns {JSX.Element[]} gli elementi da mettere dentro il <p>
 */
function playersLine(props: PlayersLineProps): JSX.Element[] {
  const items: JSX.Element[] = [];
  for (let i = 0; i < props.players.length; i++) {
    const player = props.players[i];
    // key: l'id dell'utente, unico nella riga
    items.push(<Avatar key={player.user_id} username={player.username} avatar={player.avatar} className="avatar" />);
  }
  items.push(<span key="testo">{props.text}</span>);
  return items;
}

/**
 * La schermata.
 *
 * @param {QueueOverlayProps} props
 * @returns {JSX.Element}
 *
 * In parole semplici:
 *   <QueueOverlay key={queueKey(queue)} queue={queue} cancelling={false} onCancel={handleCancel} />
 *   Un <dialog> a tutto schermo aperto con showModal() appena compare; quando la
 *   pagina lo toglie, si chiude. Il tempo riparte da queue.seconds_waiting a ogni
 *   stato nuovo del server.
 */
export function QueueOverlay(props: QueueOverlayProps): JSX.Element {
  // Gli hook si chiamano sempre in cima al componente, mai dentro un if.
  // dialogRef: il <dialog> della pagina (null prima che React lo disegni)
  const dialogRef: RefObject<HTMLDialogElement | null> = useRef<HTMLDialogElement>(null);
  // seconds: i secondi di attesa scritti adesso
  const [seconds, setSeconds] = useState<number>(props.queue.seconds_waiting);

  /** Effetto: apre la schermata quando compare, la chiude quando sparisce. */
  function open(): () => void {
    const dialog = dialogRef.current;
    if (dialog !== null && !dialog.open) {
      dialog.showModal();
    }

    function close(): void {
      if (dialog !== null && dialog.open) {
        dialog.close();
      }
    }

    return close;
  }

  // []: una volta sola, quando la schermata compare
  useEffect(open, []);

  /** Effetto a ogni stato nuovo della coda: il tempo riparte da quello del server. */
  function count(): () => void {
    // since: quando è arrivato questo stato (millisecondi)
    const since = Date.now();
    const base = props.queue.seconds_waiting;

    function tick(): void {
      setSeconds(base + (Date.now() - since) / 1000);
    }

    function stop(): void {
      window.clearInterval(timer);
    }

    setSeconds(base);
    const timer = window.setInterval(tick, TICK_MS);
    return stop;
  }

  // [props.queue]: si rifà quando arriva uno stato nuovo (un oggetto nuovo)
  useEffect(count, [props.queue]);

  /** "Annulla": una volta sola, finché la pagina non riaccende il pulsante. */
  function handleCancel(): void {
    if (props.cancelling) {
      return;
    }
    props.onCancel();
  }

  /** Esc: il browser chiuderebbe la schermata da solo; vale invece come "Annulla". */
  function handleEscape(event: SyntheticEvent<HTMLDialogElement>): void {
    event.preventDefault();
    handleCancel();
  }

  const queue = props.queue;

  // range: la riga dell'intervallo; senza intervallo va bene qualunque avversario
  let range: JSX.Element = <>Va bene qualunque avversario</>;
  let hint: JSX.Element | null = null;
  if (queue.rating_range !== null) {
    range = (
      <>
        Avversari con rating tra <RangeNumber value={queue.rating_range.min} side="min" /> e{' '}
        <RangeNumber value={queue.rating_range.max} side="max" />
      </>
    );
    hint = <p className="queue-overlay__hint felt-text">L'intervallo si allarga mentre aspetti.</p>;
  }

  // partner e opponents: le righe di compagno e avversari, solo se ci sono
  let partner: JSX.Element | null = null;
  if (queue.partner !== null) {
    const line = playersLine({ players: [queue.partner], text: `In squadra con ${queue.partner.username}` });
    partner = <p className="queue-overlay__partner felt-text" data-queue-partner={queue.partner.user_id}>{line}</p>;
  }
  let opponents: JSX.Element | null = null;
  if (queue.opponents.length > 0) {
    const names: string[] = [];
    const ids: number[] = [];
    for (let i = 0; i < queue.opponents.length; i++) {
      names.push(queue.opponents[i].username);
      ids.push(queue.opponents[i].user_id);
    }
    const line = playersLine({ players: queue.opponents, text: `Contro ${names.join(' e ')}` });
    opponents = <p className="queue-overlay__partner felt-text" data-queue-opponents={ids.join(' ')}>{line}</p>;
  }

  // cards: le tre carte di dorso sopra il titolo
  const cards: JSX.Element[] = [];
  for (let i = 0; i < CARD_KEYS.length; i++) {
    cards.push(<img key={CARD_KEYS[i]} src={CARD_BACK} alt="" />);
  }

  return (
    <dialog
      className="queue-overlay"
      aria-labelledby="queue-title"
      data-queue-overlay=""
      data-mode={queue.mode}
      data-target-score={queue.target_score}
      data-queue-key={queueKey(queue)}
      ref={dialogRef}
      onCancel={handleEscape}
    >
      <div className="queue-overlay__body">
        <div className="queue-overlay__cards" aria-hidden="true">{cards}</div>
        <p className="queue-overlay__kicker felt-text">{`${sectionFor(queue)} · ${queue.mode} · ${queue.target_score} punti`}</p>
        <h2 className="queue-overlay__title felt-text" id="queue-title">{titleFor(queue)}</h2>
        <p className="queue-overlay__time felt-text">
          <span className="visually-hidden">In attesa da </span>
          <span data-queue-seconds="">{formatWait(seconds)}</span>
        </p>
        <p className="queue-overlay__range felt-text" data-queue-range="">{range}</p>
        {hint}
        {partner}
        {opponents}
        <button
          className="btn btn--ghost queue-overlay__cancel"
          type="button"
          data-queue-cancel=""
          disabled={props.cancelling}
          onClick={handleCancel}
        >
          <span className="icon" aria-hidden="true">close</span>
          Annulla
        </button>
      </div>
    </dialog>
  );
}
