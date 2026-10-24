/**
 * La home (P22), su / (stile in css/pages/home.css e
 * css/components/card-background.css).
 *
 * La parte "ferma" della home:
 * - Le quattro carte-pulsante (Partita Veloce e Gioca con un amico, 1v1 e 2v2),
 *   che con il mouse si inclinano verso il puntatore. Senza login aprono "Accedi o
 *   registrati" (P40).
 * - Lo sfondo con la cascata di carte (CardBackground).
 * - "giocatori online": con il login da home:status (P44); senza login da
 *   GET /api/online ogni 15 secondi, solo con la scheda visibile (P82).
 * - L'avviso "Hai una partita in corso" con "Rientra" (ResumeBanner), da
 *   home:status, nello stesso spazio di "giocatori online". Con ?demo=rientro
 *   l'avviso è quello dei dati finti (si prova senza una partita vera).
 *
 * La Partita Veloce:
 * - Con il login una carta della Partita Veloce apre la carta-modal (ModeModal).
 *   "Gioca" con "Giocatore" manda queue:join (con un request_id per clic) e apre
 *   la schermata di coda (QueueOverlay), che si aggiorna con queue:status (anche
 *   dalle altre schede dello stesso utente); "Annulla" manda queue:leave e la
 *   schermata si chiude con la risposta o con queue:left ("partner_left": un
 *   messaggio dice che il compagno è uscito). Con "CPU" manda cpu:start (P73, P123:
 *   niente coda). game:start porta al tavolo.
 * - "In breve" ha il rating vero, da GET /api/stats/me.
 * - Connessione (P33): senza connessione "Gioca" è spento; se la connessione cade
 *   la schermata di coda si chiude (chi resta senza schede esce dalla coda) e, se
 *   si è ancora in coda da un'altra scheda, al ritorno arriva queue:status e si riapre.
 *
 * Gli inviti a partita (P47, contratto 5.3):
 * - Con il login una carta "Gioca con un amico" apre la carta-modal con gli amici
 *   online (GET /api/friends/, riletta con friends:presence e friends:changed: vale solo
 *   l'ultima lettura partita, P65). "Invita" manda invite:send; invite:update
 *   aggiorna la carta; chiudere la carta con inviti aperti manda invite:cancel per
 *   ognuno; "Gioca" dopo l'accettazione manda invite:start (1v1: arriva
 *   game:start; 2v2: la risposta è lo stato della coda con compagno e avversari già
 *   noti, oppure con tre amici arriva game:start). Nel 2v2 gli inviti aperti
 *   possono essere fino a tre (P59).
 * - L'invito ricevuto si apre in una finestra (InviteDialog) con "Rifiuta" e
 *   "Accetta", e il suono dell'invito (P115).
 * - Connessione (P33, P83): senza connessione "Invita", "Accetta" e "Rifiuta" sono
 *   spenti; se cade, un invito mandato o ricevuto si considera annullato (il server
 *   annulla gli inviti di chi chiude tutte le schede). Al ritorno l'invito mandato
 *   rimasto aperto si annulla con invite:cancel e la lista degli amici si rilegge.
 *
 * Cosa contiene:
 *   <HomePage />   (routes.tsx, indirizzo /)
 *
 * DA DOVE ARRIVANO I DATI: chi è collegato da useSession (GET /api/auth/session);
 * home:status, la coda, gli inviti e game:start dal tempo reale (socket/, solo con
 * il login); il rating da GET /api/stats/me; gli amici da GET /api/friends/ (api/friends.ts);
 * il numero senza login da GET /api/online (api/home.ts); i dati finti da
 * app/static/dev/home_esempio.json.
 */

import { useEffect, useRef, useState } from 'react';
import type { JSX, MouseEvent, PointerEvent, ReactNode, RefObject } from 'react';
import { useNavigate, useSearchParams } from 'react-router';
import { DEMO_RESUME, fetchDemoStatus, fetchOnlineCount } from '../api/home';
import { CardBackground } from '../components/CardBackground';
import { FlashList } from '../components/FlashList';
import { LoginPrompt } from '../components/LoginPrompt';
import { ModeModal } from '../components/ModeModal';
import type { PlayChoice } from '../components/ModeModal';
import { Navbar } from '../components/Navbar';
import { QueueOverlay, queueKey } from '../components/QueueOverlay';
import { ResumeBanner, validResume } from '../components/ResumeBanner';
import { fetchStats } from '../components/StatsSheet';
import { useSession } from '../session/SessionContext';
import { send } from '../socket/client';
import type { ConnectionStatus } from '../socket/client';
import { useConnection, useSocketEvent } from '../socket/hooks';
import { fetchFriends } from '../api/friends';
import { InviteDialog } from '../components/InviteDialog';
import type { InviteDialogStatus, Reply } from '../components/InviteDialog';
import type { InviteEntry, ModalKind } from '../components/ModeModal';
import type { FlashKind, Friend, Stats } from '../types/api';
import type { Mode, TargetScore } from '../types/common';
import type { GameStart, HomeStatus, Invite, InviteUpdate, QueueLeft, QueueStatus } from '../types/events';
import { reduceMotion } from '../utils/motion';
import { newRequestId } from '../utils/requestId';
import { playSound } from '../utils/sounds';
import { useSessionFlashes } from './FormPage';

// IncomingInvite: l'invito ricevuto aperto in una finestra, con il suo stato
interface IncomingInvite {
  invite: Invite;
  status: InviteDialogStatus;
}

// OFFLINE_MESSAGE: "Gioca" senza rete
const OFFLINE_MESSAGE = 'Sei offline: potrai giocare appena torna la connessione.';

// GAME_PREFIX: game:start porta solo a una pagina del tavolo di questo sito
const GAME_PREFIX = '/game/';

// ONLINE_POLL_MS: ogni quanto chi non ha fatto il login richiede il numero degli
// online (P82)
const ONLINE_POLL_MS = 15000;

// TILT_MAX: i gradi di inclinazione massima delle carte-pulsante sotto il mouse
const TILT_MAX = 10;

// TILT_PROPERTIES: le variabili CSS dell'inclinazione (home.css, .mode-tile)
const TILT_PROPERTIES: string[] = ['--rx', '--ry', '--gx', '--gy'];

// TileKind: che carta-pulsante è. La | vuol dire "uno di questi valori" (come un
// enum del C): 'veloce' = Partita Veloce, 'amico' = Gioca con un amico
type TileKind = 'veloce' | 'amico';

// ModeTileProps: cosa riceve una carta-pulsante
interface ModeTileProps {
  // la sezione: 'veloce' o 'amico' (data-kind)
  kind: TileKind;
  // la modalità: '1v1' o '2v2' (data-mode)
  mode: Mode;
  // il colore della carta: 'red', 'purple', 'yellow' o 'blue' (classe mode-tile--...)
  color: string;
  // il seme dell'Asso disegnato sulla carta: 'coppe', 'spade', 'denari' o 'bastoni'
  suit: string;
  // il nome dell'icona: 'person' (1v1) o 'groups' (2v2)
  icon: string;
  // la scritta piccola sotto, per esempio "Uno contro uno". ReactNode ("qualunque
  // cosa React sappia disegnare") perché "Sfida un amico" ha un a capo dentro
  sub: ReactNode;
  // la funzione da chiamare al clic, con la sezione, la modalità e il <button>
  // stesso (da lì parte il volo della carta-modal). In C sarebbe un puntatore a
  // funzione: void (*onOpen)(kind, mode, tile)
  onOpen: (kind: TileKind, mode: Mode, tile: HTMLButtonElement) => void;
}

/**
 * Dice se le carte-pulsante si possono inclinare sotto il mouse.
 *
 * @returns {boolean}
 *
 * In parole semplici:
 *   tiltAllowed()  →  true con un mouse vero e senza "riduci movimento"
 *   (sul telefono, con il dito, niente inclinazione)
 */
function tiltAllowed(): boolean {
  if (reduceMotion()) {
    return false;
  }
  return window.matchMedia('(hover: hover) and (pointer: fine)').matches;
}

/**
 * Una carta-pulsante.
 *
 * @param {ModeTileProps} props
 * @returns {JSX.Element}
 *
 * In parole semplici:
 *   <ModeTile kind="veloce" mode="1v1" color="red" suit="coppe" icon="person" sub="Uno contro uno" onOpen={...} />
 *   Un <button> con l'Asso, l'icona, "1v1" e la scritta piccola. Con il mouse la
 *   carta si inclina verso il puntatore e il riflesso di luce lo segue: le
 *   variabili --rx, --ry, --gx, --gy si scrivono direttamente sull'elemento
 *   (element.style.setProperty), a ogni movimento, senza ridisegnare la pagina.
 */
function ModeTile(props: ModeTileProps): JSX.Element {
  /** Clic: chiama props.onOpen con sezione, modalità e la carta stessa. */
  function handleClick(event: MouseEvent<HTMLButtonElement>): void {
    props.onOpen(props.kind, props.mode, event.currentTarget);
  }

  /** Il mouse si muove sulla carta: la inclina verso il puntatore. */
  function handlePointerMove(event: PointerEvent<HTMLButtonElement>): void {
    if (!tiltAllowed()) {
      return;
    }
    // tile: il <button> stesso (currentTarget è l'elemento che ascolta l'evento)
    const tile = event.currentTarget;
    const r = tile.getBoundingClientRect();
    // px e py: la posizione del puntatore sulla carta, da 0 a 1 in orizzontale e in verticale
    const px = Math.min(1, Math.max(0, (event.clientX - r.left) / r.width));
    const py = Math.min(1, Math.max(0, (event.clientY - r.top) / r.height));
    tile.style.setProperty('--ry', `${((px - 0.5) * 2 * TILT_MAX).toFixed(1)}deg`);
    tile.style.setProperty('--rx', `${((0.5 - py) * 2 * TILT_MAX).toFixed(1)}deg`);
    tile.style.setProperty('--gx', `${(px * 100).toFixed(0)}%`);
    tile.style.setProperty('--gy', `${(py * 100).toFixed(0)}%`);
  }

  /** Il mouse esce dalla carta: torna dritta. */
  function handlePointerLeave(event: PointerEvent<HTMLButtonElement>): void {
    for (let i = 0; i < TILT_PROPERTIES.length; i++) {
      event.currentTarget.style.removeProperty(TILT_PROPERTIES[i]);
    }
  }

  return (
    <button
      className={`mode-tile mode-tile--${props.color}`}
      type="button"
      data-tile=""
      data-kind={props.kind}
      data-mode={props.mode}
      aria-haspopup="dialog"
      onClick={handleClick}
      onPointerMove={handlePointerMove}
      onPointerLeave={handlePointerLeave}
    >
      <span className={`mode-tile__suit mode-tile__suit--${props.suit}`} aria-hidden="true"></span>
      <span className="icon mode-tile__icon" aria-hidden="true">{props.icon}</span>
      <span className="mode-tile__label">{props.mode}</span>
      <span className="mode-tile__sub">{props.sub}</span>
    </button>
  );
}

// HomeListenerProps: cosa riceve l'ascoltatore del tempo reale. Ogni campo è una
// funzione da chiamare quando arriva l'evento (in C: un puntatore a funzione)
interface HomeListenerProps {
  // home:status: utenti online e partita in corso
  onStatus: (status: HomeStatus) => void;
  // queue:status: lo stato della coda (anche da un'altra scheda)
  onQueueStatus: (queue: QueueStatus) => void;
  // queue:left: si è usciti dalla coda (annullato, o il compagno è uscito)
  onQueueLeft: (left: QueueLeft) => void;
  // game:start: la partita è pronta, si va al tavolo
  onGameStart: (start: GameStart) => void;
  // lo stato della connessione, a ogni cambio ('connected', 'disconnected', ...)
  onConnection: (status: ConnectionStatus) => void;
  // friends:presence e friends:changed: la lista degli amici va riletta
  onFriendsChanged: () => void;
  // invite:received: un amico ti invita
  onInviteReceived: (invite: Invite) => void;
  // invite:update: un invito (mandato o ricevuto) ha cambiato stato
  onInviteUpdate: (update: InviteUpdate) => void;
}

/**
 * Ascolta il tempo reale della home. Non disegna niente.
 *
 * @param {HomeListenerProps} props
 * @returns {null}
 *
 * In parole semplici:
 *   <HomeListener onStatus={...} onQueueStatus={...} ... />
 *   È un componente a parte perché mettersi in ascolto apre il collegamento al
 *   tempo reale (on di socket/client.ts chiama connect): la home lo disegna solo
 *   con il login, così chi non ha fatto il login non si collega.
 */
function HomeListener(props: HomeListenerProps): null {
  useSocketEvent('home:status', props.onStatus);
  useSocketEvent('queue:status', props.onQueueStatus);
  useSocketEvent('queue:left', props.onQueueLeft);
  useSocketEvent('game:start', props.onGameStart);
  useSocketEvent('friends:presence', props.onFriendsChanged);
  useSocketEvent('friends:changed', props.onFriendsChanged);
  useSocketEvent('invite:received', props.onInviteReceived);
  useSocketEvent('invite:update', props.onInviteUpdate);
  // status: lo stato della connessione, aggiornato a ogni cambio
  const status = useConnection();

  /** Effetto a ogni cambio della connessione: lo dice alla pagina. */
  function report(): void {
    props.onConnection(status);
  }

  // [status]: si rifà quando lo stato della connessione cambia
  useEffect(report, [status]);

  // onStatus: la funzione della pagina, fissata in una costante per l'effetto qui sotto
  const onStatus = props.onStatus;

  /**
   * Effetto (contratto 5.1): con il collegamento aperto chiede lo stato
   * della home (home:refresh). home:status arriva solo al collegamento e ai
   * cambiamenti: tornando dal tavolo senza ricaricare la pagina il collegamento è
   * già aperto, e senza questa richiesta mancherebbero il numero degli online e
   * l'avviso di rientro. Una risposta arrivata dopo che la home è sparita si ignora.
   */
  function askStatus(): (() => void) | undefined {
    if (status !== 'connected') {
      return undefined;
    }
    let current = true;
    async function ask(): Promise<void> {
      const answer = await send('home:refresh', {});
      if (current && answer.ok) {
        onStatus(answer.data);
      }
    }
    ask();
    function stop(): void {
      current = false;
    }
    return stop;
  }
  // [status]: a ogni collegamento (anche quello già aperto quando la home compare)
  useEffect(askStatus, [status]);
  return null;
}

/**
 * La home.
 *
 * @returns {JSX.Element}
 *
 * In parole semplici:
 *   <HomePage />
 *   Disegna navbar, sfondo, "giocatori online" (o l'avviso di rientro) e le
 *   quattro carte-pulsante, più i messaggi in basso e, senza login, la finestra
 *   "Accedi o registrati" quando si tocca una carta.
 */
export function HomePage(): JSX.Element {
  // Gli hook si chiamano sempre in cima al componente, mai dentro un if.
  // session: chi è collegato (loaded false finché non si sa)
  const session = useSession();
  // searchParams: la parte dopo ? dell'indirizzo (per ?demo=rientro). È uno
  // dei due valori che dà useSearchParams; il secondo (per cambiarla) non serve
  const searchParams = useSearchParams()[0];
  const demo = searchParams.get('demo') === DEMO_RESUME;
  // useState restituisce due cose: il valore attuale e la funzione per cambiarlo,
  // che fa ridisegnare il componente (regole-codice.md, sezione 6).
  // flashes: i messaggi in basso (quelli lasciati dal server, poi gli avvisi della pagina)
  const [flashes, setFlashes] = useSessionFlashes();
  // flashKey: cambia a ogni avviso nuovo, così la lista si ridisegna da capo e
  // l'avviso ricompare anche se il testo è lo stesso di prima
  const [flashKey, setFlashKey] = useState<number>(0);
  // status: l'ultimo home:status ({ online_count, resume }); null finché non arriva
  const [status, setStatus] = useState<HomeStatus | null>(null);
  // promptOpen: true mentre la finestra "Accedi o registrati" è aperta
  const [promptOpen, setPromptOpen] = useState<boolean>(false);
  // loggedIn: true con il login (false anche finché la sessione non è arrivata)
  const loggedIn = session.user !== null;
  // flashCount: il numero dell'ultimo avviso (il key della lista dei messaggi);
  // un ref perché si legge anche dopo un await, quando flashKey può essere vecchio
  const flashCount: RefObject<number> = useRef<number>(0);
  // ratings: il rating dell'utente, per "In breve"; null finché non arriva
  const [ratings, setRatings] = useState<Stats['ratings'] | null>(null);
  // modal: la carta-modal aperta (sezione, modalità e carta-pulsante toccata), oppure null
  const [modal, setModal] = useState<{ kind: ModalKind; mode: Mode; tile: HTMLButtonElement } | null>(null);
  // queue: la coda in cui si è, oppure null. queueRef: lo stesso valore, letto
  // dalle funzioni che rispondono al server (dopo un await il valore di useState
  // di quel disegno può essere vecchio; il ref ha sempre l'ultimo)
  const [queue, setQueue] = useState<QueueStatus | null>(null);
  const queueRef: RefObject<QueueStatus | null> = useRef<QueueStatus | null>(null);
  // cancelling: true mentre "Annulla" aspetta la risposta del server
  const [cancelling, setCancelling] = useState<boolean>(false);
  // connection: lo stato della connessione al tempo reale (solo con il login)
  const [connection, setConnection] = useState<ConnectionStatus>('connecting');
  // joining: queue:join o cpu:start in attesa di risposta (niente doppio invio)
  const joining: RefObject<boolean> = useRef<boolean>(false);
  // starting: è arrivato game:start, si sta andando al tavolo
  const starting: RefObject<boolean> = useRef<boolean>(false);
  // navigate: cambia pagina dentro la SPA, senza ricaricare (verso il tavolo)
  const navigate = useNavigate();
  // wasOnline: la pagina è già stata collegata almeno una volta
  const wasOnline: RefObject<boolean> = useRef<boolean>(false);
  // friends: gli amici (GET /api/friends/), per la lista da invitare
  const [friends, setFriends] = useState<Friend[]>([]);
  // friendsRequest: il numero dell'ultima lettura della lista partita (P65: le
  // risposte possono arrivare in un altro ordine, e vale solo quella dell'ultima)
  const friendsRequest: RefObject<number> = useRef<number>(0);
  // invites: gli inviti mandati e ancora aperti (nella carta-modal). invitesRef: lo
  // stesso elenco, letto dalle funzioni che rispondono al server (come queueRef)
  const [invites, setInvites] = useState<InviteEntry[]>([]);
  const invitesRef: RefObject<InviteEntry[]> = useRef<InviteEntry[]>([]);
  // inviteNote: il suggerimento sotto la lista degli amici; null = quello di partenza
  const [inviteNote, setInviteNote] = useState<string | null>(null);
  // sending: gli amici con invite:send in attesa di risposta (user_id)
  const sending: RefObject<Set<number>> = useRef<Set<number>>(new Set<number>());
  // cancelAfterSend: la carta si è chiusa prima della risposta: si annullano appena arriva
  const cancelAfterSend: RefObject<Set<number>> = useRef<Set<number>>(new Set<number>());
  // staleInvites: inviti mandati rimasti aperti mentre mancava la connessione
  // (si annullano al ritorno)
  const staleInvites: RefObject<string[]> = useRef<string[]>([]);
  // incoming: l'invito ricevuto aperto in una finestra, oppure null. incomingRef:
  // lo stesso valore, per le funzioni che rispondono al server
  const [incoming, setIncoming] = useState<IncomingInvite | null>(null);
  const incomingRef: RefObject<IncomingInvite | null> = useRef<IncomingInvite | null>(null);

  /** Effetto: il titolo della scheda. */
  function setTitle(): void {
    document.title = 'Cinquecento';
  }

  // []: una volta sola, all'apertura della pagina
  useEffect(setTitle, []);

  /** Effetto per ?demo=rientro: prende lo stato finto con la partita in corso. */
  function loadDemo(): () => void {
    // active: false se la pagina sparisce prima della risposta
    let active = true;

    async function read(): Promise<void> {
      const demoStatus = await fetchDemoStatus();
      if (active && demoStatus !== null) {
        setStatus(demoStatus);
      }
    }

    function stop(): void {
      active = false;
    }

    if (demo) {
      read();
    }
    return stop;
  }

  // [demo]: si rifà solo se cambia ?demo=
  useEffect(loadDemo, [demo]);

  /**
   * Effetto senza login (P82): chiede il numero degli online a GET /api/online
   * all'apertura e poi ogni ONLINE_POLL_MS, solo finché la scheda è visibile;
   * tornando sulla scheda lo richiede subito. Con il login il numero arriva con
   * home:status, e con ?demo=rientro valgono solo i dati finti.
   */
  function pollOnline(): () => void {
    // active: false quando l'effetto si ferma (pagina chiusa, login cambiato)
    let active = true;
    // timer: la prossima richiesta in attesa (0 = nessuna)
    let timer = 0;

    async function load(): Promise<void> {
      window.clearTimeout(timer);
      if (document.hidden) {
        return;
      }
      const answer = await fetchOnlineCount();
      if (!active) {
        return;
      }
      if (answer.ok) {
        setStatus({ online_count: answer.data.online_count, resume: null });
      }
      // senza risposta resta il numero di prima; si riprova al giro dopo
      window.clearTimeout(timer);
      if (!document.hidden) {
        timer = window.setTimeout(load, ONLINE_POLL_MS);
      }
    }

    function handleVisibility(): void {
      if (document.hidden) {
        window.clearTimeout(timer);
      } else {
        load();
      }
    }

    function stop(): void {
      active = false;
      window.clearTimeout(timer);
      document.removeEventListener('visibilitychange', handleVisibility);
    }

    if (!session.loaded || loggedIn || demo) {
      return stop;
    }
    document.addEventListener('visibilitychange', handleVisibility);
    load();
    return stop;
  }

  // [session.loaded, loggedIn, demo]: si rifà quando arriva la sessione (e si
  // sa se c'è il login) o se cambia ?demo=
  useEffect(pollOnline, [session.loaded, loggedIn, demo]);

  /** Effetto con il login: chiede il rating per "In breve" (GET /api/stats/me), una volta. */
  function loadRatings(): () => void {
    // active: false se la pagina sparisce prima della risposta
    let active = true;

    async function read(): Promise<void> {
      const result = await fetchStats();
      if (active && result.stats !== null) {
        setRatings(result.stats.ratings);
      }
    }

    function stop(): void {
      active = false;
    }

    if (loggedIn) {
      read();
    }
    return stop;
  }

  // [loggedIn]: si rifà quando arriva la sessione con il login
  useEffect(loadRatings, [loggedIn]);

  /**
   * Un messaggio in basso (stesso aspetto di quelli del server).
   *
   * @param {FlashKind} kind 'info', 'error' o 'success'
   * @param {string} message il testo
   *
   * In parole semplici:
   *   showMessage('error', 'Sei già in coda.')
   *   Prende il posto del messaggio di prima e ricompare anche se il testo è lo stesso.
   */
  function showMessage(kind: FlashKind, message: string): void {
    flashCount.current = flashCount.current + 1;
    setFlashes([{ kind: kind, message: message }]);
    setFlashKey(flashCount.current);
  }

  /** Mostra la schermata di coda (risposta di queue:join, o queue:status). */
  function showQueue(next: QueueStatus): void {
    if (starting.current) {
      return;
    }
    queueRef.current = next;
    setQueue(next);
  }

  /** Chiude la schermata di coda. */
  function closeQueue(): void {
    queueRef.current = null;
    setQueue(null);
    setCancelling(false);
  }

  /** "Gioca" con "Giocatore": entra in coda (contratto 4, queue:join). */
  async function joinQueue(mode: Mode, targetScore: TargetScore): Promise<void> {
    if (joining.current || queueRef.current !== null || starting.current) {
      return;
    }
    joining.current = true;
    const answer = await send('queue:join', { request_id: newRequestId(), mode: mode, target_score: targetScore });
    joining.current = false;
    if (!answer.ok) {
      showMessage('error', answer.error.message);
      return;
    }
    showQueue(answer.data);
  }

  /**
   * "Gioca" con "CPU" (P73, contratto 4.1; P123 con mode '2v2'): niente coda,
   * arriva subito game:start.
   */
  async function startCpu(mode: Mode, targetScore: TargetScore): Promise<void> {
    if (joining.current || queueRef.current !== null || starting.current) {
      return;
    }
    joining.current = true;
    const answer = await send('cpu:start', { request_id: newRequestId(), mode: mode, target_score: targetScore });
    joining.current = false;
    if (!answer.ok) {
      showMessage('error', answer.error.message);
    }
  }

  /** "Gioca" nella carta-modal. */
  function handlePlay(choice: PlayChoice): void {
    if (!navigator.onLine) {
      showMessage('error', OFFLINE_MESSAGE);
      return;
    }
    if (choice.kind === 'amico') {
      startInvite();
    } else if (choice.cpu) {
      startCpu(choice.mode, choice.targetScore);
    } else {
      joinQueue(choice.mode, choice.targetScore);
    }
  }

  /** La carta-modal ha finito di chiudersi: si toglie, con i suoi inviti. */
  function handleModalClosed(): void {
    setModal(null);
    changeInvites([]);
    setInviteNote(null);
  }

  // ------------------------------------------------------------
  // Inviti mandati (P47, contratto 5.3)
  // ------------------------------------------------------------

  /** Cambia l'elenco degli inviti aperti (lo stato e il ref insieme). */
  function changeInvites(next: InviteEntry[]): void {
    invitesRef.current = next;
    setInvites(next);
  }

  /**
   * Cerca l'invito aperto a un amico.
   *
   * @param {number} friendId l'user_id dell'amico
   * @returns {InviteEntry | null}
   */
  function inviteOf(friendId: number): InviteEntry | null {
    for (let i = 0; i < invitesRef.current.length; i++) {
      if (invitesRef.current[i].friend.user_id === friendId) {
        return invitesRef.current[i];
      }
    }
    return null;
  }

  /**
   * Cambia un invito aperto: lo sostituisce con `changed`, oppure lo toglie se
   * `changed` è null.
   */
  function replaceInvite(friendId: number, changed: InviteEntry | null): void {
    const next: InviteEntry[] = [];
    for (let i = 0; i < invitesRef.current.length; i++) {
      const entry = invitesRef.current[i];
      if (entry.friend.user_id !== friendId) {
        next.push(entry);
      } else if (changed !== null) {
        next.push(changed);
      }
    }
    changeInvites(next);
  }

  /**
   * Il suggerimento quando un amico accetta (nel 2v2 si possono aspettare gli altri).
   *
   * @returns {string} per esempio 'Giulia ha accettato: puoi giocare!'
   */
  function acceptedHint(): string {
    const names: string[] = [];
    let waiting = false;
    for (let i = 0; i < invitesRef.current.length; i++) {
      if (invitesRef.current[i].status === 'accepted') {
        names.push(invitesRef.current[i].friend.username);
      } else {
        waiting = true;
      }
    }
    let who = `${names.join(' e ')} hanno accettato`;
    if (names.length === 1) {
      who = `${names[0]} ha accettato`;
    }
    if (waiting) {
      return `${who}: puoi giocare subito (chi non ha ancora risposto resta fuori) o aspettare gli altri.`;
    }
    // Quattro amici al tavolo: come il 1v1 tra amici, non conta per il rating (P59)
    if (names.length === 3) {
      return `${who}: puoi giocare! Tra quattro amici non conta per il rating.`;
    }
    return `${who}: puoi giocare!`;
  }

  /**
   * Il risultato di un invito mandato (invite:update): "accepted", "declined",
   * "expired" o "cancelled". Gli stati di amici senza un invito aperto si ignorano.
   *
   * @param {number} friendId l'amico
   * @param {string} status lo stato nuovo
   */
  function applyInviteStatus(friendId: number, status: string): void {
    const entry = inviteOf(friendId);
    if (entry === null) {
      return;
    }
    const name = entry.friend.username;
    if (status === 'accepted') {
      replaceInvite(friendId, { friend: entry.friend, status: 'accepted', inviteId: entry.inviteId });
      setInviteNote(acceptedHint());
      return;
    }
    let note = '';
    if (status === 'declined') {
      note = `${name} ha rifiutato l'invito. Puoi invitare un altro amico.`;
    } else if (status === 'expired') {
      note = `${name} non ha risposto in tempo. Puoi invitare un altro amico.`;
    } else if (status === 'cancelled') {
      note = `L'invito a ${name} è stato annullato.`;
    } else {
      return;
    }
    replaceInvite(friendId, null);
    setInviteNote(note);
  }

  /** "Invita" nella carta-modal: invite:send, con un request_id. */
  async function handleInvite(friend: Friend, targetScore: TargetScore): Promise<void> {
    if (modal === null) {
      return;
    }
    if (!navigator.onLine) {
      setInviteNote('Sei offline: potrai invitare appena torna la connessione.');
      return;
    }
    const mode = modal.mode;
    const added: InviteEntry[] = [];
    for (let i = 0; i < invitesRef.current.length; i++) {
      added.push(invitesRef.current[i]);
    }
    added.push({ friend: friend, status: 'pending', inviteId: null });
    changeInvites(added);
    setInviteNote(`Invito inviato a ${friend.username}. Aspettiamo che accetti…`);

    sending.current.add(friend.user_id);
    cancelAfterSend.current.delete(friend.user_id);
    const answer = await send('invite:send', {
      request_id: newRequestId(), user_id: friend.user_id, mode: mode, target_score: targetScore,
    });
    sending.current.delete(friend.user_id);
    if (answer.ok && cancelAfterSend.current.delete(friend.user_id)) {
      // la carta si è chiusa prima della risposta
      send('invite:cancel', { invite_id: answer.data.invite_id });
      return;
    }
    if (!answer.ok) {
      showMessage('error', answer.error.message);
      applyInviteStatus(friend.user_id, 'cancelled');   // si può invitare di nuovo
      return;
    }
    const entry = inviteOf(friend.user_id);
    if (entry !== null) {
      replaceInvite(friend.user_id, { friend: friend, status: entry.status, inviteId: answer.data.invite_id });
    }
  }

  /** La carta-modal si chiude senza "Gioca": gli inviti aperti si annullano (invite:cancel). */
  function handleModalDismiss(): void {
    for (let i = 0; i < invitesRef.current.length; i++) {
      const entry = invitesRef.current[i];
      if (sending.current.has(entry.friend.user_id)) {
        cancelAfterSend.current.add(entry.friend.user_id);
      }
      if (entry.inviteId !== null) {
        send('invite:cancel', { invite_id: entry.inviteId });
      }
    }
    changeInvites([]);
  }

  /**
   * "Gioca" con un amico dopo l'accettazione: invite:start. Nel 2v2 vale qualunque
   * invito accettato: il server avvia tutto il gruppo (P59).
   */
  async function startInvite(): Promise<void> {
    let id: string | null = null;
    for (let i = 0; i < invitesRef.current.length; i++) {
      if (invitesRef.current[i].status === 'accepted' && id === null) {
        id = invitesRef.current[i].inviteId;
      }
    }
    if (id === null) {
      return;
    }
    const answer = await send('invite:start', { invite_id: id });
    if (!answer.ok) {
      showMessage('error', answer.error.message);
      return;
    }
    // 2v2 con uno o due amici: in coda; altrimenti arriva game:start
    if ('data' in answer) {
      showQueue(answer.data);
    }
  }

  // ------------------------------------------------------------
  // Inviti ricevuti (InviteDialog)
  // ------------------------------------------------------------

  /** Cambia l'invito ricevuto aperto (lo stato e il ref insieme). */
  function changeIncoming(next: IncomingInvite | null): void {
    incomingRef.current = next;
    setIncoming(next);
  }

  /** invite:received: si apre la finestra (al posto di un'altra eventuale), con il suono. */
  function handleInviteReceived(invite: Invite): void {
    if (starting.current || typeof invite.invite_id !== 'string') {
      return;
    }
    playSound('invite', 0);   // P115
    changeIncoming({ invite: invite, status: invite.status });
  }

  /** invite:update: un invito mandato (carta-modal) o ricevuto (finestra) è cambiato. */
  function handleInviteUpdate(update: InviteUpdate): void {
    for (let i = 0; i < invitesRef.current.length; i++) {
      const entry = invitesRef.current[i];
      if (entry.inviteId === update.invite_id && update.status !== 'started') {
        applyInviteStatus(entry.friend.user_id, update.status);
      }
    }
    const current = incomingRef.current;
    if (current !== null && current.invite.invite_id === update.invite_id) {
      changeIncoming({ invite: current.invite, status: update.status });
    }
  }

  /** "Accetta" nella finestra dell'invito ricevuto. */
  function handleAcceptInvite(): Promise<Reply> {
    const current = incomingRef.current;
    if (current === null) {
      return Promise.resolve({ ok: false, error: { code: 'not_found', message: "L'invito non c'è più." } });
    }
    return send('invite:accept', { invite_id: current.invite.invite_id });
  }

  /** "Rifiuta" nella finestra dell'invito ricevuto. */
  function handleDeclineInvite(): Promise<Reply> {
    const current = incomingRef.current;
    if (current === null) {
      return Promise.resolve({ ok: true });
    }
    return send('invite:decline', { invite_id: current.invite.invite_id });
  }

  /** La finestra dell'invito ricevuto si è chiusa: si toglie. */
  function handleIncomingClosed(): void {
    changeIncoming(null);
  }

  // ------------------------------------------------------------
  // Amici (GET /api/friends/)
  // ------------------------------------------------------------

  /** Rilegge la lista degli amici; vale solo la risposta dell'ultima lettura partita (P65). */
  async function loadFriends(): Promise<void> {
    friendsRequest.current = friendsRequest.current + 1;
    const mine = friendsRequest.current;
    const answer = await fetchFriends();
    if (!answer.ok || mine !== friendsRequest.current) {
      // senza lista nuova resta quella di prima
      return;
    }
    setFriends(answer.data.friends);
  }

  /** Effetto con il login: la prima lettura della lista degli amici. */
  function firstFriends(): void {
    if (loggedIn) {
      loadFriends();
    }
  }

  // [loggedIn]: si rifà quando arriva la sessione con il login
  useEffect(firstFriends, [loggedIn]);

  /** "Annulla" nella schermata di coda: queue:leave, e si chiude con la risposta. */
  async function handleCancelQueue(): Promise<void> {
    setCancelling(true);
    const answer = await send('queue:leave', {});
    if (!answer.ok) {
      showMessage('error', answer.error.message);
      setCancelling(false);
      return;
    }
    closeQueue();
  }

  /** queue:left: fuori dalla coda; se è uscito il compagno, lo dice un messaggio. */
  function handleQueueLeft(left: QueueLeft): void {
    const current = queueRef.current;
    if (left.reason === 'partner_left' && current !== null) {
      // group: gruppo di tre amici (P59)
      const group = current.opponents.length > 0;
      if (group) {
        showMessage('info', 'Un amico del tuo gruppo è uscito dalla coda.');
      } else {
        showMessage('info', 'Il tuo compagno è uscito dalla coda.');
      }
    }
    closeQueue();
  }

  /**
   * game:start: si va al tavolo (solo un indirizzo /game/... di questo sito). Dal
   * senza ricaricare la pagina (navigate di React Router): il tavolo è una
   * pagina della SPA e il collegamento al tempo reale resta aperto.
   */
  function handleGameStart(start: GameStart): void {
    if (typeof start.url !== 'string' || !start.url.startsWith(GAME_PREFIX)) {
      return;
    }
    starting.current = true;
    navigate(start.url);
  }

  /**
   * Un cambio della connessione (P33). Chi resta senza schede esce dalla coda
   * (DECISIONI.md, P28): la schermata si chiude, e se si è ancora in coda (un'altra
   * scheda aperta) al ritorno arriva queue:status e la schermata si riapre.
   */
  function handleConnection(now: ConnectionStatus): void {
    setConnection(now);
    if (now === 'connected') {
      // al ritorno: gli inviti rimasti aperti si annullano, le presenze si rileggono
      const stale = staleInvites.current;
      staleInvites.current = [];
      for (let i = 0; i < stale.length; i++) {
        send('invite:cancel', { invite_id: stale[i] });
      }
      if (wasOnline.current) {
        loadFriends();
      }
      wasOnline.current = true;
      return;
    }
    if (!wasOnline.current) {
      return;
    }
    if (queueRef.current !== null) {
      closeQueue();
    }
    // Gli inviti mandati si considerano annullati (al ritorno si annullano davvero)
    const open = invitesRef.current;
    for (let i = 0; i < open.length; i++) {
      // id: il codice dell'invito; null se invite:send non aveva ancora risposto
      const id = open[i].inviteId;
      if (id !== null) {
        staleInvites.current.push(id);
      }
      applyInviteStatus(open[i].friend.user_id, 'cancelled');
    }
    // P83: anche l'invito ricevuto il server lo annulla, ma l'avviso non arriverebbe
    // mai: senza questo, dopo "Accetta" si resterebbe ad aspettare per sempre
    const current = incomingRef.current;
    if (current !== null && (current.status === 'pending' || current.status === 'accepted')) {
      changeIncoming({ invite: current.invite, status: 'connection_lost' });
    }
  }

  /** home:status: il numero degli online e la partita in corso (non con ?demo=rientro). */
  function handleStatus(next: HomeStatus): void {
    if (demo) {
      return;
    }
    setStatus(next);
  }

  /**
   * Clic su una carta-pulsante. Senza login: la finestra "Accedi o registrati".
   * Con il login: la carta-modal. Finché la sessione non è arrivata non fa niente
   * (non si sa ancora cosa aprire); in coda o con la carta-modal già aperta nemmeno.
   */
  function handleOpenTile(kind: TileKind, mode: Mode, tile: HTMLButtonElement): void {
    if (!session.loaded) {
      return;
    }
    if (!loggedIn) {
      setPromptOpen(true);
      return;
    }
    if (queueRef.current !== null || modal !== null) {
      return;
    }
    setModal({ kind: kind, mode: mode, tile: tile });
  }

  /** La finestra "Accedi o registrati" si è chiusa senza scegliere. */
  function handlePromptDone(): void {
    setPromptOpen(false);
  }

  // banner: l'avviso di rientro, solo se home:status ha una partita in corso con
  // un indirizzo valido; deciso con un if prima del return
  let banner: JSX.Element | null = null;
  if (status !== null && status.resume !== null && validResume(status.resume)) {
    banner = <ResumeBanner resume={status.resume} />;
  }

  // "giocatori online" sta nello stesso spazio: nascosto mentre c'è l'avviso di
  // rientro, e finché il numero non arriva
  let onlineHidden = true;
  let onlineCount = '';
  let onlineLabel = 'giocatori online';
  if (status !== null && banner === null) {
    onlineHidden = false;
    onlineCount = String(status.online_count);
  }
  // P120: "1 giocatore online", al singolare
  if (status !== null && status.online_count === 1) {
    onlineLabel = 'giocatore online';
  }

  // listener: l'ascolto del tempo reale, solo con il login (con ?demo=rientro
  // home:status si ignora in handleStatus, ma la coda funziona)
  let listener: JSX.Element | null = null;
  if (loggedIn) {
    listener = (
      <HomeListener
        onStatus={handleStatus}
        onQueueStatus={showQueue}
        onQueueLeft={handleQueueLeft}
        onGameStart={handleGameStart}
        onConnection={handleConnection}
        onFriendsChanged={loadFriends}
        onInviteReceived={handleInviteReceived}
        onInviteUpdate={handleInviteUpdate}
      />
    );
  }

  // modeModal: la carta-modal, solo mentre è aperta
  let modeModal: JSX.Element | null = null;
  if (modal !== null) {
    modeModal = (
      <ModeModal
        kind={modal.kind}
        mode={modal.mode}
        tile={modal.tile}
        ratings={ratings}
        online={connection === 'connected'}
        friends={friends}
        invites={invites}
        inviteNote={inviteNote}
        onPlay={handlePlay}
        onInvite={handleInvite}
        onDismiss={handleModalDismiss}
        onClosed={handleModalClosed}
      />
    );
  }

  // inviteDialog: la finestra dell'invito ricevuto, solo mentre c'è. key: l'id
  // dell'invito, così un invito nuovo è una finestra nuova
  let inviteDialog: JSX.Element | null = null;
  if (incoming !== null) {
    inviteDialog = (
      <InviteDialog
        key={incoming.invite.invite_id}
        invite={incoming.invite}
        status={incoming.status}
        online={connection === 'connected'}
        onAccept={handleAcceptInvite}
        onDecline={handleDeclineInvite}
        onClosed={handleIncomingClosed}
      />
    );
  }

  // queueOverlay: la schermata di coda, solo in coda. key: con una coda diversa
  // (queueKey) React ne disegna una nuova; con la stessa aggiorna solo i numeri (P105)
  let queueOverlay: JSX.Element | null = null;
  if (queue !== null) {
    queueOverlay = (
      <QueueOverlay key={queueKey(queue)} queue={queue} cancelling={cancelling} onCancel={handleCancelQueue} />
    );
  }

  // prompt: la finestra "Accedi o registrati", solo mentre è aperta
  let prompt: JSX.Element | null = null;
  if (promptOpen) {
    prompt = <LoginPrompt onDone={handlePromptDone} />;
  }

  // demoState: data-demo-state="rientro", solo con i dati finti
  let demoState: string | undefined = undefined;
  if (demo) {
    demoState = DEMO_RESUME;
  }

  // "Sfida un amico" va a capo sul telefono (mode-tile__br, home.css)
  const challengeSub = (
    <>
      Sfida<br className="mode-tile__br" /> un amico
    </>
  );

  // <> ... </>: un contenitore che non diventa un elemento della pagina
  return (
    <>
      <Navbar />
      <main className="page home" data-page="home">
        <p className="visually-hidden" data-stato="ok">ok</p>
        {/* P34: titolo principale per i lettori di schermo (nella pagina lo fa il logo della navbar) */}
        <h1 className="visually-hidden">Cinquecento: scegli come giocare</h1>

        <CardBackground />

        <div className="home__view" data-home="" data-demo-state={demoState}>
          <div className="home__status" data-status-slot="">
            <p className="online felt-text" data-online="" hidden={onlineHidden}>
              <span className="online__dot" aria-hidden="true"></span>
              <span>
                <strong data-online-count="">{onlineCount}</strong>{' '}
                <span data-online-label="">{onlineLabel}</span>
              </span>
            </p>
            <div className="home__resume" data-resume-slot="" hidden={banner === null}>{banner}</div>
          </div>

          <div className="home__sections">
            <section className="mode-section" aria-labelledby="titolo-veloce">
              <h2 className="mode-section__title felt-text" id="titolo-veloce">
                <span className="icon" aria-hidden="true">bolt</span>Partita Veloce
              </h2>
              <div className="mode-section__tiles">
                <ModeTile kind="veloce" mode="1v1" color="red" suit="coppe" icon="person" sub="Uno contro uno" onOpen={handleOpenTile} />
                <ModeTile kind="veloce" mode="2v2" color="purple" suit="spade" icon="groups" sub="A coppie" onOpen={handleOpenTile} />
              </div>
            </section>

            <section className="mode-section" aria-labelledby="titolo-amico">
              <h2 className="mode-section__title felt-text" id="titolo-amico">
                <span className="icon" aria-hidden="true">favorite</span>Gioca con un amico
              </h2>
              <div className="mode-section__tiles">
                <ModeTile kind="amico" mode="1v1" color="yellow" suit="denari" icon="person" sub={challengeSub} onOpen={handleOpenTile} />
                <ModeTile kind="amico" mode="2v2" color="blue" suit="bastoni" icon="groups" sub="Fai squadra" onOpen={handleOpenTile} />
              </div>
            </section>
          </div>
        </div>
      </main>
      <FlashList key={flashKey} flashes={flashes} />
      {listener}
      {prompt}
      {modeModal}
      {queueOverlay}
      {inviteDialog}
    </>
  );
}
