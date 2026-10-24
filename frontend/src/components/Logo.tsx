/**
 * Il logo della navbar (P40, P42): due carte di dorso che ogni tanto si girano e
 * mostrano Cavallo e Re di un seme, poi tornano sul dorso; al giro dopo tocca al
 * seme successivo. Con "riduci movimento" restano ferme sul dorso
 * (stile in app/static/css/components/navbar.css).
 *
 * Cosa contiene:
 *   <Logo />
 *
 * DA DOVE ARRIVANO I DATI: nessuno; le immagini sono in app/static/img/cards-bg/.
 */

import { useEffect, useRef } from 'react';
import type { JSX, RefObject } from 'react';
import { reduceMotion } from '../utils/motion';

// IMG_BASE: la cartella delle immagini delle carte del logo
const IMG_BASE = '/static/img/cards-bg/';
// LOGO_SUITS: i semi, nell'ordine in cui si mostrano
const LOGO_SUITS: string[] = ['coppe', 'denari', 'spade', 'bastoni'];
// I tempi del giro, in millisecondi:
// BACK_MS sul dorso, FRONT_MS scoperte, STAGGER_MS tra la prima e la seconda
// carta, FLIP_MS la durata della girata (deve restare uguale al CSS)
const BACK_MS = 3000;
const FRONT_MS = 2600;
const STAGGER_MS = 180;
const FLIP_MS = 900;

/**
 * L'indirizzo dell'immagine di una figura.
 *
 * In parole semplici:
 *   imageOf('re', 'coppe')  →  '/static/img/cards-bg/re-coppe.webp'
 */
function imageOf(who: string, suit: string): string {
  return `${IMG_BASE}${who}-${suit}.webp`;
}

/**
 * Il logo.
 *
 * @returns {JSX.Element}
 *
 * In parole semplici:
 *   <Logo />
 *   Disegna il link alla home con le due carte e la scritta. Le carte si girano
 *   cambiando le loro classi direttamente nel DOM (is-flipping, is-front), non
 *   con lo stato di React: così il logo non si ridisegna a ogni girata.
 */
export function Logo(): JSX.Element {
  // markRef: il <span> con le due carte, che React mette in markRef.current dopo
  // averlo disegnato. Serve per trovare le carte e le loro facce.
  const markRef: RefObject<HTMLSpanElement | null> = useRef<HTMLSpanElement>(null);

  /**
   * Effetto: carica prima tutte le figure (così il giro non scatta), poi fa
   * partire i giri. La funzione di pulizia ferma tutti i timer se il logo sparisce.
   */
  function animate(): () => void {
    // timers: i timer avviati, da fermare nella pulizia
    const timers: number[] = [];
    // stopped: true dopo la pulizia, così una girata in arrivo non fa niente
    let stopped = false;

    function stop(): void {
      stopped = true;
      for (let i = 0; i < timers.length; i++) {
        window.clearTimeout(timers[i]);
      }
    }

    const mark = markRef.current;
    if (mark === null || reduceMotion()) {
      return stop;
    }
    const cards = mark.querySelectorAll<HTMLElement>('.logo__card');
    if (cards.length !== 2) {
      return stop;
    }
    // faces: le immagini davanti delle due carte, per cambiare la figura
    const faces: HTMLImageElement[] = [];
    for (let i = 0; i < cards.length; i++) {
      const face = cards[i].querySelector<HTMLImageElement>('.logo__face--front');
      if (face === null) {
        return stop;
      }
      faces.push(face);
    }

    /** Aspetta ms millisecondi e poi chiama action, se il logo c'è ancora. */
    function later(ms: number, action: () => void): void {
      function run(): void {
        if (!stopped) {
          action();
        }
      }

      timers.push(window.setTimeout(run, ms));
    }

    /** Gira una carta: verso la faccia (front true) o verso il dorso. */
    function flip(card: HTMLElement, front: boolean): void {
      card.classList.add('is-flipping');
      card.classList.toggle('is-front', front);

      function endFlip(): void {
        card.classList.remove('is-flipping');
      }

      later(FLIP_MS, endFlip);
    }

    /** Un giro completo con il seme numero index. */
    function cycle(index: number): void {
      const suit = LOGO_SUITS[index % LOGO_SUITS.length];
      // Le facce si cambiano mentre si vede il dorso, quindi il cambio non si nota
      faces[0].src = imageOf('cavallo', suit);
      faces[1].src = imageOf('re', suit);

      function showFront(): void {
        flip(cards[0], true);

        function flipSecond(): void {
          flip(cards[1], true);
        }

        later(STAGGER_MS, flipSecond);
        later(FLIP_MS + FRONT_MS, showBack);
      }

      function showBack(): void {
        flip(cards[0], false);

        function flipSecondBack(): void {
          flip(cards[1], false);
        }

        function nextCycle(): void {
          cycle(index + 1);
        }

        later(STAGGER_MS, flipSecondBack);
        later(FLIP_MS + STAGGER_MS, nextCycle);
      }

      later(BACK_MS, showFront);
    }

    // loading: il caricamento di tutte le figure; decode() finisce quando
    // l'immagine è pronta da mostrare (un errore si ignora: il giro parte lo stesso)
    const loading: Promise<void>[] = [];
    for (let i = 0; i < LOGO_SUITS.length; i++) {
      const whos = ['cavallo', 're'];
      for (let j = 0; j < whos.length; j++) {
        const image = new Image();
        image.src = imageOf(whos[j], LOGO_SUITS[i]);
        loading.push(image.decode().catch(ignoreError));
      }
    }

    function ignoreError(): void {
      // un'immagine che non si carica non ferma il logo
    }

    function startCycles(): void {
      if (!stopped) {
        cycle(0);
      }
    }

    Promise.all(loading).then(startCycles);
    return stop;
  }

  // []: una volta sola, quando il logo compare
  useEffect(animate, []);

  return (
    <a className="logo" href="/" aria-label="Cinquecento, torna alla home">
      <span className="logo__mark" aria-hidden="true" data-logo-cards="" data-img-base={IMG_BASE} ref={markRef}>
        <span className="logo__card">
          <span className="logo__flip">
            <img className="logo__face logo__face--back" src={`${IMG_BASE}dorso.webp`} alt="" />
            <img className="logo__face logo__face--front" src={`${IMG_BASE}cavallo-coppe.webp`} alt="" />
          </span>
        </span>
        <span className="logo__card">
          <span className="logo__flip">
            <img className="logo__face logo__face--back" src={`${IMG_BASE}dorso.webp`} alt="" />
            <img className="logo__face logo__face--front" src={`${IMG_BASE}re-coppe.webp`} alt="" />
          </span>
        </span>
      </span>
      <span className="logo__text">Cinque<b>cento</b></span>
    </a>
  );
}
