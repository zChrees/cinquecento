/**
 * Il pannello statistiche (P40, P30): si apre dall'avatar della navbar (stile
 * in css/components/stats-panel.css).
 *
 * Cosa contiene:
 *   <StatsSheet user={...} dialogRef={...} sheet={...} />
 *   <StatsGrid stats={...} />   la griglia: partite, vinte, perse, vittorie, rating 1v1 e 2v2
 *
 * In fondo: "Impostazioni", "Esci" (POST /api/auth/logout con il codice CSRF, non un
 * link: un altro sito non può far uscire l'utente) e i crediti delle immagini.
 *
 * DA DOVE ARRIVANO I DATI: GET /api/stats/me (contratto 2.1), chiesto a ogni apertura
 * del pannello; l'utente dalla sessione (useSession, nella navbar); il codice CSRF
 * lo mette postJson (api/client.ts).
 */

import { useState } from 'react';
import type { FormEvent, JSX, RefObject } from 'react';
import { getJson, postJson } from '../api/client';
import type { AuthDone, LogoutBody, ModeRating, Stats } from '../types/api';
import type { UserRef } from '../types/common';
import { Avatar } from './Avatar';
import { Credits } from './LoginPrompt';
import type { Sheet } from './sheet';

// I messaggi al posto della griglia
export const LOADING_MESSAGE = 'Caricamento…';
const OFFLINE = 'Sei offline: le statistiche arrivano appena torna la connessione.';
const NOT_AVAILABLE = 'Statistiche non disponibili. Riprova tra poco.';

// StatProps: una casella della griglia
interface StatProps {
  // l'etichetta, per esempio 'Vinte' (anche in data-stat, per i test)
  label: string;
  // il valore da mostrare, per esempio '71' o '55%'
  value: string;
  // la classe in più, per esempio 'stat--win', oppure ''
  modifier: string;
  // la nota piccola sotto il valore, per esempio 'provvisorio', oppure ''
  note: string;
}

/**
 * Una casella delle statistiche.
 *
 * In parole semplici:
 *   <Stat label="Vinte" value="71" modifier="stat--win" note="" />
 *   →  <div class="stat stat--win" data-stat="Vinte"><dt>Vinte</dt><dd>71</dd></div>
 */
function Stat(props: StatProps): JSX.Element {
  let className = 'stat';
  if (props.modifier !== '') {
    className = `stat ${props.modifier}`;
  }
  let note: JSX.Element | null = null;
  if (props.note !== '') {
    note = <small className="stat__note">{props.note}</small>;
  }
  return (
    <div className={className} data-stat={props.label}>
      <dt>{props.label}</dt>
      <dd>{props.value}{note}</dd>
    </div>
  );
}

/**
 * La nota del rating: 'provvisorio' per le prime 10 partite (D9), altrimenti niente.
 */
function provisionalNote(rating: ModeRating): string {
  if (rating.provisional) {
    return 'provvisorio';
  }
  return '';
}

// StatsGridProps: cosa riceve la griglia
interface StatsGridProps {
  // i dati di GET /api/stats/me
  stats: Stats;
}

/**
 * La griglia delle statistiche.
 *
 * In parole semplici:
 *   <StatsGrid stats={stats} />
 *   La percentuale di vittorie è '—' per chi non ha ancora giocato (win_rate null).
 */
export function StatsGrid(props: StatsGridProps): JSX.Element {
  let winRate = '—';
  if (props.stats.win_rate !== null) {
    winRate = `${props.stats.win_rate}%`;
  }
  const rating1v1 = props.stats.ratings['1v1'];
  const rating2v2 = props.stats.ratings['2v2'];
  return (
    <dl className="stats-grid">
      <Stat label="Partite" value={String(props.stats.games)} modifier="" note="" />
      <Stat label="Vinte" value={String(props.stats.wins)} modifier="stat--win" note="" />
      <Stat label="Perse" value={String(props.stats.losses)} modifier="stat--lose" note="" />
      <Stat label="Vittorie" value={winRate} modifier="" note="" />
      <Stat label="Rating 1v1" value={String(rating1v1.value)} modifier="" note={provisionalNote(rating1v1)} />
      <Stat label="Rating 2v2" value={String(rating2v2.value)} modifier="" note={provisionalNote(rating2v2)} />
    </dl>
  );
}

// StatsSheetProps: cosa riceve il pannello
interface StatsSheetProps {
  // l'utente collegato (nome e avatar in cima al pannello)
  user: UserRef;
  // il <dialog>: lo disegna questo componente, la navbar lo apre
  dialogRef: RefObject<HTMLDialogElement | null>;
  // le funzioni per chiuderlo con l'animazione (sheet.ts)
  sheet: Sheet;
  // il contenuto: la griglia, oppure un messaggio (caricamento, offline, errore)
  stats: Stats | null;
  // il messaggio al posto della griglia quando stats è null
  message: string;
}

/**
 * Il pannello.
 *
 * @param {StatsSheetProps} props
 * @returns {JSX.Element}
 *
 * In parole semplici:
 *   <StatsSheet ... />
 *   Il <dialog> resta sempre nella pagina (chiuso), come in navbar.html: la navbar
 *   lo apre con showModal().
 */
export function StatsSheet(props: StatsSheetProps): JSX.Element {
  // useState restituisce il valore attuale e la funzione per cambiarlo, che fa
  // ridisegnare il componente (regole-codice.md, sezione 6)
  // leaving: true dopo il primo invio di "Esci" (niente doppio invio)
  const [leaving, setLeaving] = useState<boolean>(false);

  /**
   * Invio di "Esci": senza rete non parte; al primo invio il pulsante si spegne.
   *
   * In parole semplici:
   *   Il modulo non va al server da solo (preventDefault): la richiesta
   *   POST /api/auth/logout la manda postJson, con il codice CSRF. Se va bene si
   *   ricarica la home (window.location.assign), come faceva il modulo di prima:
   *   la pagina riparte da zero, senza collegamento né dati dell'utente uscito.
   *   Se non va (rete caduta, errore del server) il pulsante si riaccende.
   */
  async function handleLogout(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!navigator.onLine || leaving) {
      return;
    }
    setLeaving(true);
    // body: nessun dato, solo la richiesta
    const body: LogoutBody = {};
    const answer = await postJson<LogoutBody, AuthDone>('/api/auth/logout', body);
    if (answer.ok) {
      window.location.assign(answer.data.redirect);
      return;
    }
    setLeaving(false);
  }

  /** La X in alto. */
  function handleClose(): void {
    props.sheet.close();
  }

  // body: la griglia, oppure il messaggio
  let body: JSX.Element = <p className="sheet__message">{props.message}</p>;
  if (props.stats !== null) {
    body = <StatsGrid stats={props.stats} />;
  }

  return (
    <dialog
      className="sheet"
      id="stats"
      aria-labelledby="stats-title"
      data-animated=""
      data-stats-url="/api/stats/me"
      ref={props.dialogRef}
      onCancel={props.sheet.handleCancel}
      onClick={props.sheet.handleClick}
    >
      <div className="sheet__head">
        <Avatar username={props.user.username} avatar={props.user.avatar} className="avatar avatar--big" />
        <div>
          <h2 className="sheet__title" id="stats-title">{props.user.username}</h2>
          <p className="sheet__subtitle">Le tue statistiche</p>
        </div>
        <button className="icon-btn" type="button" data-close="" aria-label="Chiudi" onClick={handleClose}>
          <span className="icon" aria-hidden="true">close</span>
        </button>
      </div>
      <div data-stats-body="" aria-live="polite">{body}</div>
      <div className="sheet__links">
        <a className="sheet__link" href="/profile/settings">
          <span className="icon" aria-hidden="true">settings</span>Impostazioni
        </a>
        <form className="sheet__logout" onSubmit={handleLogout}>
          <button className="sheet__link" type="submit" data-logout="" disabled={leaving}>
            <span className="icon" aria-hidden="true">logout</span>Esci
          </button>
        </form>
      </div>
      <Credits />
    </dialog>
  );
}

/**
 * Chiede le statistiche e restituisce cosa mostrare.
 *
 * @returns {Promise<{ stats: Stats | null; message: string }>}
 *
 * In parole semplici:
 *   const result = await fetchStats();
 *   Le statistiche, oppure null con il messaggio da mostrare al loro posto.
 */
export async function fetchStats(): Promise<{ stats: Stats | null; message: string }> {
  const answer = await getJson<Stats>('/api/stats/me');
  if (answer.ok) {
    return { stats: answer.data, message: '' };
  }
  if (answer.error.code === 'no_connection') {
    return { stats: null, message: OFFLINE };
  }
  return { stats: null, message: NOT_AVAILABLE };
}
