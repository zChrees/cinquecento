/**
 * L'avviso in cima alla pagina sullo stato della connessione (P33; stile in
 * css/components/banner.css). Va nelle pagine con il login,
 * che si collegano al tempo reale.
 *
 * Cosa contiene:
 *   <ConnectionBanner />
 *
 * Quando compare:
 *   - collegati: niente;
 *   - al primo collegamento: solo se ci vogliono più di 3 secondi
 *     ("Collegamento al server in corso…");
 *   - la connessione è caduta e Socket.IO riprova: "Connessione persa: riprovo a
 *     collegarmi…" (sparisce da sola quando torna);
 *   - il server ha chiuso e non si riprova (per esempio "Esci" da un'altra scheda,
 *     P32), o il login non vale più: un errore con il pulsante "Ricarica";
 *   - mentre si lascia la pagina: niente (la connessione chiusa non è un problema).
 * L'avviso sta nel "top layer" (popover) quando il browser lo permette, così resta
 * sopra le finestre già aperte.
 *
 * DA DOVE ARRIVANO I DATI: lo stato della connessione da useConnection (socket/hooks.ts).
 */

import { useEffect, useRef, useState } from 'react';
import type { JSX, RefObject } from 'react';
import { useConnection } from '../socket/hooks';

// FIRST_CONNECT_MS: al primo collegamento l'avviso aspetta questo tempo
const FIRST_CONNECT_MS = 3000;

// I testi dell'avviso
const FIRST_CONNECT = 'Collegamento al server in corso…';
const LOST = 'Connessione persa: riprovo a collegarmi…';
const LOGGED_OUT = 'Non sei più collegato al tuo account: ricarica la pagina.';
const DISCONNECTED = 'Sei stato scollegato (per esempio sei uscito da un\'altra scheda): ricarica la pagina.';

/**
 * L'avviso.
 *
 * @returns {JSX.Element | null}
 *
 * In parole semplici:
 *   <ConnectionBanner />
 *   Decide il testo dallo stato della connessione e lo disegna; senza niente da
 *   dire non disegna niente (null).
 */
export function ConnectionBanner(): JSX.Element | null {
  // status: lo stato della connessione, che fa ridisegnare l'avviso quando cambia
  const status = useConnection();
  // useState restituisce il valore attuale e la funzione per cambiarlo, che fa
  // ridisegnare il componente (regole-codice.md, sezione 6)
  // slow: true se il primo collegamento ci mette più di FIRST_CONNECT_MS
  const [slow, setSlow] = useState<boolean>(false);
  // leaving: true mentre si lascia la pagina (evento beforeunload)
  const [leaving, setLeaving] = useState<boolean>(false);
  // everConnected: true dopo il primo collegamento riuscito. Un ref, non uno
  // stato: cambiarlo non deve ridisegnare niente
  const everConnected: RefObject<boolean> = useRef<boolean>(false);
  // bannerRef: l'avviso disegnato, per metterlo nel top layer (showPopover)
  const bannerRef: RefObject<HTMLDivElement | null> = useRef<HTMLDivElement>(null);
  if (status === 'connected') {
    everConnected.current = true;
  }

  /** Effetto: dopo FIRST_CONNECT_MS, se non si è ancora mai collegati, l'avviso può comparire. */
  function waitFirstConnect(): () => void {
    function markSlow(): void {
      setSlow(true);
    }

    const timer = window.setTimeout(markSlow, FIRST_CONNECT_MS);

    function stop(): void {
      window.clearTimeout(timer);
    }

    return stop;
  }

  // []: una volta sola, all'apertura della pagina
  useEffect(waitFirstConnect, []);

  /**
   * Effetto: si accorge di quando si lascia la pagina (beforeunload) e di quando
   * ci si torna con "indietro" (pageshow).
   */
  function followLeaving(): () => void {
    function handleBeforeUnload(): void {
      setLeaving(true);
    }

    function handlePageShow(): void {
      setLeaving(false);
    }

    window.addEventListener('beforeunload', handleBeforeUnload);
    window.addEventListener('pageshow', handlePageShow);

    function stop(): void {
      window.removeEventListener('beforeunload', handleBeforeUnload);
      window.removeEventListener('pageshow', handlePageShow);
    }

    return stop;
  }

  // []: una volta sola
  useEffect(followLeaving, []);

  // text e error: cosa dire, deciso con degli if prima del return ('' = niente)
  let text = '';
  let error = false;
  if (leaving || status === 'connected') {
    text = '';
  } else if (status === 'connecting') {
    if (everConnected.current) {
      text = LOST;
    } else if (slow) {
      text = FIRST_CONNECT;
    }
  } else if (status === 'not_logged_in') {
    text = LOGGED_OUT;
    error = true;
  } else {
    text = DISCONNECTED;
    error = true;
  }

  /**
   * Effetto: mette l'avviso nel top layer, sopra i <dialog> aperti, se il browser
   * lo permette (showPopover). Si rifà quando cambia il testo (un avviso nuovo).
   */
  function raise(): void {
    const banner = bannerRef.current;
    if (banner !== null && typeof banner.showPopover === 'function' && !banner.matches(':popover-open')) {
      banner.showPopover();
    }
  }

  // [text]: dopo ogni cambio di testo
  useEffect(raise, [text]);

  if (text === '') {
    return null;
  }

  /** "Ricarica": ricarica la pagina, che si ricollega da capo. */
  function handleReload(): void {
    window.location.reload();
  }

  // kind, role, icon, action: le parti che cambiano tra attesa ed errore
  let kind = 'waiting';
  let role = 'status';
  let icon = <span className="icon banner__spin" aria-hidden="true">progress_activity</span>;
  let action: JSX.Element | null = null;
  if (error) {
    kind = 'error';
    role = 'alert';
    icon = <span className="icon" aria-hidden="true">error</span>;
    action = (
      <button className="btn btn--small banner__action" type="button" data-banner-action="" onClick={handleReload}>
        Ricarica
      </button>
    );
  }

  // key={text}: con un testo nuovo React crea un avviso nuovo (e toglie
  // il vecchio), così il lettore di schermo lo legge
  return (
    <div key={text} ref={bannerRef} className={`banner banner--${kind}`} role={role} data-banner={kind} popover="manual">
      {icon}
      <span className="banner__text">{text}</span>
      {action}
    </div>
  );
}
