/**
 * Finestra nella pagina, al posto di alert / confirm (P19): la versione React di
 * app/static/js/components/Modal.js, con lo stesso HTML e le stesse classi
 * (stile in app/static/css/components/modal.css).
 *
 * Cosa contiene:
 *   <Modal title="..." actions={[...]} onDone={handleDone} />
 *
 * Per esempio:
 *   <Modal title="Nessuna connessione" message="Controlla la connessione..."
 *          actions={[{ label: 'Ok', value: 'ok', variant: 'primary' }]} onDone={handleDone} />
 *
 * La finestra si apre quando il componente compare. Si chiude con i pulsanti, con
 * la X, con Esc o toccando fuori (queste ultime tre valgono null, "Annulla"):
 * prima fa l'animazione di uscita, poi chiama onDone con il valore scelto, e chi
 * la usa la toglie dalla pagina. Dopo la prima scelta i pulsanti si spengono: un
 * doppio clic non conta due volte. Titolo e testo sono sempre testo, mai HTML.
 *
 * DA DOVE ARRIVANO I DATI: da chi la usa (per esempio LoginPrompt.tsx).
 */

import { useEffect, useId, useRef, useState } from 'react';
import type { AnimationEvent, JSX, MouseEvent, RefObject, SyntheticEvent } from 'react';
import { reduceMotion } from '../utils/motion';

// CLOSE_FALLBACK_MS: se l'animazione di uscita non parte (per esempio scheda in
// secondo piano), la finestra si chiude comunque dopo questo tempo (come Modal.js)
const CLOSE_FALLBACK_MS = 400;

// ModalAction: un pulsante della finestra
export interface ModalAction {
  // il testo del pulsante, per esempio 'Accedi'
  label: string;
  // il valore che riceve onDone se si sceglie questo pulsante, per esempio '/auth/login'
  value: string;
  // lo stile: 'primary' (pieno), 'ghost' (vuoto) o 'danger' (rosso)
  variant: 'primary' | 'ghost' | 'danger';
}

// ModalProps: cosa riceve il componente
interface ModalProps {
  // il titolo, per esempio 'Accedi o registrati per giocare'
  title: string;
  // il testo sotto il titolo; '' per niente
  message: string;
  // i pulsanti, nell'ordine in cui compaiono (il principale per ultimo); il primo
  // riceve il fuoco della tastiera
  actions: ModalAction[];
  // la riga in fondo, sotto i pulsanti (per esempio i crediti delle immagini), o null
  footer: JSX.Element | null;
  // la funzione da chiamare a finestra chiusa, con il valore scelto (null =
  // chiusa con X, Esc o tocco fuori). In C: void (*onDone)(char *value)
  onDone: (value: string | null) => void;
}

/**
 * La finestra.
 *
 * @param {ModalProps} props
 * @returns {JSX.Element}
 *
 * In parole semplici:
 *   <Modal ... />
 *   Disegna un <dialog> con titolo, testo, pulsanti e riga in fondo, e lo apre
 *   con showModal() (il browser mette la finestra sopra tutto e rende inerte il resto).
 */
export function Modal(props: ModalProps): JSX.Element {
  // dialogRef: il <dialog> vero della pagina, che React mette in dialogRef.current
  // dopo averlo disegnato (null prima). Serve per chiamare showModal() e close().
  const dialogRef: RefObject<HTMLDialogElement | null> = useRef<HTMLDialogElement>(null);
  // chosen: il valore scelto, conservato mentre si fa l'animazione di uscita
  const chosen: RefObject<string | null> = useRef<string | null>(null);
  // finished: true dopo la chiamata a onDone, che così parte una volta sola
  // (l'animazione finita e il tempo di riserva potrebbero arrivare tutti e due)
  const finished: RefObject<boolean> = useRef<boolean>(false);
  // useState restituisce due cose: il valore attuale e la funzione per cambiarlo,
  // che fa ridisegnare il componente (regole-codice.md, sezione 6). Gli hook si
  // chiamano sempre in cima al componente, mai dentro un if.
  // closing: true dall'istante della scelta (pulsanti spenti, animazione di uscita)
  const [closing, setClosing] = useState<boolean>(false);
  // titleId: un identificatore unico per collegare il titolo al <dialog>
  // (aria-labelledby: il lettore di schermo legge il titolo all'apertura)
  const titleId = useId();

  /**
   * Effetto all'apertura: apre il <dialog>. La funzione di pulizia lo chiude se
   * il componente sparisce.
   */
  function openDialog(): () => void {
    const dialog = dialogRef.current;
    if (dialog !== null && !dialog.open) {
      dialog.showModal();
    }

    function closeDialog(): void {
      if (dialog !== null && dialog.open) {
        dialog.close();
      }
    }

    return closeDialog;
  }

  // []: una volta sola, quando la finestra compare
  useEffect(openDialog, []);

  /**
   * Effetto durante la chiusura: se l'animazione non finisce entro
   * CLOSE_FALLBACK_MS, chiude comunque.
   */
  function closeAnyway(): (() => void) | undefined {
    if (!closing) {
      return undefined;
    }
    const timer = window.setTimeout(done, CLOSE_FALLBACK_MS);

    function stopTimer(): void {
      window.clearTimeout(timer);
    }

    return stopTimer;
  }

  // [closing]: si rifà quando closing cambia (cioè quando parte la chiusura)
  useEffect(closeAnyway, [closing]);

  /** Fine della chiusura: chiude il <dialog> e avvisa chi usa la finestra. */
  function done(): void {
    if (finished.current) {
      return;
    }
    finished.current = true;
    const dialog = dialogRef.current;
    if (dialog !== null && dialog.open) {
      dialog.close();
    }
    props.onDone(chosen.current);
  }

  /**
   * Una scelta (pulsante, X, Esc, tocco fuori): conta solo la prima. Con "riduci
   * movimento" chiude subito, altrimenti parte l'animazione di uscita (is-closing).
   */
  function finish(value: string | null): void {
    if (closing) {
      return;
    }
    chosen.current = value;
    if (reduceMotion()) {
      done();
      return;
    }
    setClosing(true);
  }

  /** Esc: il browser chiuderebbe subito; lo fermiamo per far vedere l'animazione. */
  function handleCancel(event: SyntheticEvent<HTMLDialogElement>): void {
    event.preventDefault();
    finish(null);
  }

  /** Tocco fuori dalla finestra: il clic arriva al <dialog> stesso (lo sfondo). */
  function handleBackdropClick(event: MouseEvent<HTMLDialogElement>): void {
    if (event.target === dialogRef.current) {
      finish(null);
    }
  }

  /** Fine di un'animazione: se è quella di uscita del <dialog>, la finestra si chiude. */
  function handleAnimationEnd(event: AnimationEvent<HTMLDialogElement>): void {
    if (closing && event.target === dialogRef.current) {
      done();
    }
  }

  /** La X in alto. */
  function handleClose(): void {
    finish(null);
  }

  // buttons: i pulsanti delle scelte, costruiti con un for prima del return.
  // key: il "nome" con cui React riconosce lo stesso pulsante tra un disegno e
  // l'altro (qui il testo, che è unico nella finestra).
  const buttons: JSX.Element[] = [];
  for (let i = 0; i < props.actions.length; i++) {
    const action = props.actions[i];

    /** Clic su questo pulsante: la scelta è il suo valore. */
    function handleChoice(): void {
      finish(action.value);
    }

    buttons.push(
      <button
        key={action.label}
        className={`btn btn--${action.variant}`}
        type="button"
        autoFocus={i === 0}
        disabled={closing}
        onClick={handleChoice}
      >
        {action.label}
      </button>,
    );
  }

  // body: il testo sotto il titolo, solo se c'è
  let body: JSX.Element | null = null;
  if (props.message !== '') {
    body = <p className="dialog__body">{props.message}</p>;
  }

  // className: con is-closing parte l'animazione di uscita (modal.css)
  let className = 'dialog';
  if (closing) {
    className = 'dialog is-closing';
  }

  return (
    <dialog
      ref={dialogRef}
      className={className}
      aria-labelledby={titleId}
      data-animated=""
      data-modal=""
      onCancel={handleCancel}
      onClick={handleBackdropClick}
      onAnimationEnd={handleAnimationEnd}
    >
      <div className="dialog__head">
        <h2 className="dialog__title" id={titleId}>{props.title}</h2>
        <button className="icon-btn" type="button" aria-label="Chiudi" disabled={closing} onClick={handleClose}>
          <span className="icon" aria-hidden="true">close</span>
        </button>
      </div>
      {body}
      <div className="dialog__actions">{buttons}</div>
      {props.footer}
    </dialog>
  );
}
