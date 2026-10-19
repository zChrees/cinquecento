/**
 * Aprire e chiudere una finestra <dialog> della navbar (pannello statistiche, e
 * dal passo 5b il pannello amici), con l'animazione di uscita: la versione React
 * di closeDialog() e wireDialog() di app/static/js/core/layout.js.
 *
 * Cosa contiene:
 *   const sheet = sheetControls(dialogRef);
 *   sheet.open()               apre (showModal), se non è già aperta
 *   sheet.close()              chiude con l'animazione (is-closing, poi close())
 *   sheet.handleCancel         per onCancel del <dialog> (Esc)
 *   sheet.handleClick          per onClick del <dialog> (tocco fuori)
 *
 * Si chiude con Esc, toccando fuori dal riquadro e con i pulsanti che chiamano
 * close(). Con "riduci movimento", o se il CSS non ha un'animazione, si chiude subito.
 *
 * DA DOVE ARRIVANO I DATI: il <dialog> lo disegna il componente che usa l'hook e
 * lo mette in dialogRef (ref={dialogRef}).
 */

import type { MouseEvent, RefObject, SyntheticEvent } from 'react';
import { reduceMotion } from '../utils/motion';

// CLOSE_FALLBACK_MS: se l'animazione non parte (scheda in secondo piano), chiude comunque
const CLOSE_FALLBACK_MS = 400;

// Sheet: le funzioni che restituisce l'hook
export interface Sheet {
  open: () => void;
  close: () => void;
  handleCancel: (event: SyntheticEvent<HTMLDialogElement>) => void;
  handleClick: (event: MouseEvent<HTMLDialogElement>) => void;
}

/**
 * Le funzioni per aprire e chiudere il <dialog> di dialogRef.
 *
 * @param {RefObject<HTMLDialogElement | null>} dialogRef il <dialog> disegnato dal componente
 * @returns {Sheet}
 *
 * In parole semplici:
 *   const sheet = sheetControls(dialogRef);
 *   Le classi is-closing si cambiano direttamente sul <dialog> (come layout.js),
 *   senza ridisegnare il componente: il contenuto del pannello resta com'è.
 *   Non è un hook di React (non usa useState né useEffect): è una funzione
 *   normale, che si può chiamare dove si vuole.
 */
export function sheetControls(dialogRef: RefObject<HTMLDialogElement | null>): Sheet {
  /** Apre il pannello; un secondo clic mentre è aperto non fa niente. */
  function open(): void {
    const dialog = dialogRef.current;
    if (dialog !== null && !dialog.open) {
      dialog.showModal();
    }
  }

  /** Chiude con l'animazione di uscita. */
  function close(): void {
    const dialog = dialogRef.current;
    if (dialog === null || !dialog.open || dialog.classList.contains('is-closing')) {
      return;
    }
    // current: lo stesso <dialog>, in una costante che le funzioni qui sotto ricordano
    const current: HTMLDialogElement = dialog;

    /** Fine della chiusura. */
    function done(): void {
      current.classList.remove('is-closing');
      if (current.open) {
        current.close();
      }
    }

    if (reduceMotion()) {
      done();
      return;
    }
    current.classList.add('is-closing');
    if (getComputedStyle(current).animationName === 'none') {
      done();
      return;
    }

    /** Fine di un'animazione: conta solo quella del <dialog>, non dei suoi figli. */
    function handleEnd(event: AnimationEvent): void {
      if (event.target !== current) {
        return;
      }
      current.removeEventListener('animationend', handleEnd);
      done();
    }

    /** Il tempo di riserva: chiude se l'animazione non è finita. */
    function closeAnyway(): void {
      if (current.classList.contains('is-closing')) {
        current.removeEventListener('animationend', handleEnd);
        done();
      }
    }

    current.addEventListener('animationend', handleEnd);
    window.setTimeout(closeAnyway, CLOSE_FALLBACK_MS);
  }

  /** Esc: il browser chiuderebbe subito; lo fermiamo per far vedere l'animazione. */
  function handleCancel(event: SyntheticEvent<HTMLDialogElement>): void {
    event.preventDefault();
    close();
  }

  /**
   * Clic sul <dialog> stesso: se è fuori dal riquadro (sullo sfondo scuro) chiude.
   * Si misura il riquadro perché un clic sul bordo interno arriva anche lui al <dialog>.
   */
  function handleClick(event: MouseEvent<HTMLDialogElement>): void {
    const dialog = dialogRef.current;
    if (dialog === null || event.target !== dialog) {
      return;
    }
    const box = dialog.getBoundingClientRect();
    let inside = false;
    if (event.clientX >= box.left && event.clientX <= box.right && event.clientY >= box.top && event.clientY <= box.bottom) {
      inside = true;
    }
    if (!inside) {
      close();
    }
  }

  return { open: open, close: close, handleCancel: handleCancel, handleClick: handleClick };
}
