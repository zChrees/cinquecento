/**
 * La navbar delle pagine della SPA (P40), con lo stesso HTML di
 * app/templates/partials/navbar.html (stile in components/navbar.css).
 *
 * - Senza login: icona generica e "Accedi", il logo, "Amici"; avatar e amici aprono
 *   la finestra "Accedi o registrati per giocare" (passo 4).
 * - Con il login: avatar e nome, che aprono il pannello statistiche (StatsSheet);
 *   il logo; "Amici" con il contatore, che apre il pannello amici (FriendsPanel, passo 5b).
 *   Solo con il login la pagina si collega al tempo reale: per questo anche l'avviso
 *   di connessione (ConnectionBanner, P33) sta qui (dal passo 6; prima nella pagina di prova).
 * - Finché non si sa chi è collegato (la sessione non è ancora arrivata) i due
 *   pulsanti ci sono ma non si vedono: così chi ha il login non vede per un attimo "Accedi".
 *
 * Cosa contiene:
 *   <Navbar />
 *
 * DA DOVE ARRIVANO I DATI: l'utente dalla sessione (useSession); le statistiche
 * da GET /api/stats/me, a ogni apertura del pannello (fetchStats di StatsSheet.tsx); il
 * contatore degli amici da FriendsPanel.tsx (GET /api/friends/).
 */

import { useRef, useState } from 'react';
import type { CSSProperties, JSX, RefObject } from 'react';
import { useSession } from '../session/SessionContext';
import type { Stats } from '../types/api';
import { Avatar } from './Avatar';
import { ConnectionBanner } from './ConnectionBanner';
import { FriendsPanel, useOpenFriendsPanel } from './FriendsPanel';
import { LoginPrompt } from './LoginPrompt';
import { Logo } from './Logo';
import { sheetControls } from './sheet';
import { LOADING_MESSAGE, StatsSheet, fetchStats } from './StatsSheet';

// HIDDEN: lo stile dei pulsanti finché non si sa chi è collegato. style={{...}}
// (le doppie graffe: un oggetto JavaScript dentro il JSX) imposta element.style,
// che la CSP permette; visibility hidden tiene lo spazio, così niente si sposta.
const HIDDEN: CSSProperties = { visibility: 'hidden' };

/**
 * La navbar.
 *
 * @returns {JSX.Element}
 *
 * In parole semplici:
 *   <Navbar />
 *   Disegna la barra in alto e, a seconda del login, la finestra "Accedi o
 *   registrati" oppure il pannello statistiche.
 */
export function Navbar(): JSX.Element {
  // session: chi è collegato (loaded false finché non si sa)
  const session = useSession();
  // useState restituisce il valore attuale e la funzione per cambiarlo, che fa
  // ridisegnare il componente (regole-codice.md, sezione 6). Gli hook si chiamano
  // sempre in cima al componente, mai dentro un if.
  // promptOpen: true mentre la finestra "Accedi o registrati" è aperta
  const [promptOpen, setPromptOpen] = useState<boolean>(false);
  // stats e statsMessage: il contenuto del pannello statistiche (la griglia, o un messaggio)
  const [stats, setStats] = useState<Stats | null>(null);
  const [statsMessage, setStatsMessage] = useState<string>('');
  // loadingStats: true mentre le statistiche sono in viaggio (un doppio clic non le chiede due volte)
  const loadingStats: RefObject<boolean> = useRef<boolean>(false);
  // statsRef: il <dialog> del pannello statistiche, disegnato da StatsSheet
  const statsRef: RefObject<HTMLDialogElement | null> = useRef<HTMLDialogElement>(null);
  const statsSheet = sheetControls(statsRef);
  // friendsBadge: il numero sul contatore degli amici (richieste ricevute + messaggi
  // non letti); lo manda FriendsPanel a ogni lista nuova
  const [friendsBadge, setFriendsBadge] = useState<number>(0);
  // openFriends: la funzione che apre il pannello amici
  const openFriends = useOpenFriendsPanel();

  /** Clic su avatar o amici senza login: apre la finestra. */
  function handleOpenPrompt(): void {
    setPromptOpen(true);
  }

  /** La finestra si è chiusa senza scegliere: si toglie. */
  function handlePromptDone(): void {
    setPromptOpen(false);
  }

  /**
   * Clic sull'avatar con il login: apre il pannello e ricarica le statistiche.
   * Mentre arrivano resta quello che c'era (o "Caricamento…" la prima volta).
   */
  async function handleOpenStats(): Promise<void> {
    statsSheet.open();
    if (loadingStats.current) {
      return;
    }
    loadingStats.current = true;
    if (stats === null && statsMessage === '') {
      setStatsMessage(LOADING_MESSAGE);
    }
    const result = await fetchStats();
    setStats(result.stats);
    setStatsMessage(result.message);
    loadingStats.current = false;
  }

  /** Clic su "Amici" con il login: apre il pannello amici. */
  function handleOpenFriends(): void {
    openFriends();
  }

  // buttonStyle: i pulsanti non si vedono finché la sessione non è arrivata
  let buttonStyle: CSSProperties | undefined = undefined;
  if (!session.loaded) {
    buttonStyle = HIDDEN;
  }

  // account, friends, extra: i due pulsanti e la finestra o il pannello,
  // decisi con un if prima del return (con o senza login)
  let account: JSX.Element;
  let friends: JSX.Element;
  let extra: JSX.Element | null = null;
  if (session.user !== null) {
    // friendsLabel, badgeText, badgeHidden: il contatore, solo se c'è qualche novità
    let friendsLabel = 'Amici';
    let badgeText = '';
    let badgeHidden = true;
    if (friendsBadge > 0) {
      friendsLabel = `Amici: ${friendsBadge} novità (richieste e messaggi)`;
      badgeText = String(friendsBadge);
      badgeHidden = false;
    }
    account = (
      <button
        className="navbar__account felt-text"
        type="button"
        data-open-stats=""
        aria-haspopup="dialog"
        aria-controls="stats"
        onClick={handleOpenStats}
      >
        <Avatar username={session.user.username} avatar={session.user.avatar} className="avatar" />
        <span className="navbar__label">{session.user.username}</span>
        <span className="visually-hidden">: apri le tue statistiche</span>
      </button>
    );
    friends = (
      <button
        className="navbar__friends felt-text"
        type="button"
        data-friends-button=""
        aria-label={friendsLabel}
        aria-haspopup="dialog"
        aria-controls="friends"
        data-friends-url="/api/friends/"
        onClick={handleOpenFriends}
      >
        <span className="icon" aria-hidden="true">group</span>
        <span className="navbar__label" aria-hidden="true">Amici</span>
        <span className="badge" aria-hidden="true" data-friends-badge="" hidden={badgeHidden}>{badgeText}</span>
      </button>
    );
    extra = (
      <>
        <StatsSheet
          user={session.user}
          dialogRef={statsRef}
          sheet={statsSheet}
          stats={stats}
          message={statsMessage}
        />
        <FriendsPanel onBadge={setFriendsBadge} />
        <ConnectionBanner />
      </>
    );
  } else {
    account = (
      <button
        className="navbar__account felt-text"
        type="button"
        data-login-prompt=""
        aria-haspopup="dialog"
        aria-label="Accedi o registrati"
        style={buttonStyle}
        onClick={handleOpenPrompt}
      >
        <span className="avatar" aria-hidden="true"><span className="icon">person</span></span>
        <span className="navbar__label" aria-hidden="true">Accedi</span>
      </button>
    );
    friends = (
      <button
        className="navbar__friends felt-text"
        type="button"
        data-login-prompt=""
        aria-haspopup="dialog"
        aria-label="Amici: accedi per vederli"
        style={buttonStyle}
        onClick={handleOpenPrompt}
      >
        <span className="icon" aria-hidden="true">group</span>
        <span className="navbar__label" aria-hidden="true">Amici</span>
        <span className="badge" aria-hidden="true" data-friends-badge="" hidden></span>
      </button>
    );
    if (promptOpen) {
      extra = <LoginPrompt onDone={handlePromptDone} />;
    }
  }

  // <> ... </>: un contenitore che non diventa un elemento della pagina; serve
  // perché un componente restituisce un solo pezzo (qui: barra più finestra)
  return (
    <>
      <header className="navbar" data-part="navbar">
        <div className="navbar__inner">
          {account}
          <Logo />
          {friends}
        </div>
      </header>
      {extra}
    </>
  );
}
