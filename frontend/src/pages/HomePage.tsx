/**
 * La home (P22), passo 7 della migrazione: la versione React di
 * app/templates/main/index.html e js/pages/home.js, con lo stesso HTML, le stesse
 * classi e gli stessi data-* (stile in css/pages/home.css e
 * css/components/card-background.css). Finché non è finita sta su /prova-home
 * (solo sviluppo e test); al lotto 7d prende il posto di /.
 *
 * Lotto 7a (questo): la parte "ferma" della home.
 * - Le quattro carte-pulsante (Partita Veloce e Gioca con un amico, 1v1 e 2v2),
 *   che con il mouse si inclinano verso il puntatore. Senza login aprono "Accedi o
 *   registrati" (P40); con il login, per ora, un avviso: la carta-modal della
 *   modalità (ModeModal) arriva con il lotto 7b.
 * - Lo sfondo con la cascata di carte (CardBackground).
 * - "giocatori online": con il login da home:status (P44); senza login da
 *   GET /online ogni 15 secondi, solo con la scheda visibile (P82).
 * - L'avviso "Hai una partita in corso" con "Rientra" (ResumeBanner), da
 *   home:status, nello stesso spazio di "giocatori online". Con ?demo=rientro
 *   l'avviso è quello dei dati finti (si prova senza una partita vera).
 * Coda, CPU e inviti arrivano con i lotti 7b e 7c.
 *
 * Cosa contiene:
 *   <HomePage />   (routes.tsx, indirizzo /prova-home)
 *   PREVIEW_MESSAGE   l'avviso provvisorio delle carte-pulsante con il login (fino al 7b)
 *
 * DA DOVE ARRIVANO I DATI: chi è collegato da useSession (GET /api/auth/session);
 * home:status dal tempo reale (socket/, solo con il login); il numero senza login
 * da GET /online (api/home.ts); i dati finti da app/static/dev/home_esempio.json.
 */

import { useEffect, useState } from 'react';
import type { JSX, PointerEvent, ReactNode } from 'react';
import { useSearchParams } from 'react-router';
import { DEMO_RESUME, fetchDemoStatus, fetchOnlineCount } from '../api/home';
import { CardBackground } from '../components/CardBackground';
import { FlashList } from '../components/FlashList';
import { LoginPrompt } from '../components/LoginPrompt';
import { Navbar } from '../components/Navbar';
import { ResumeBanner, validResume } from '../components/ResumeBanner';
import { useSession } from '../session/SessionContext';
import { useSocketEvent } from '../socket/hooks';
import type { Mode } from '../types/common';
import type { HomeStatus } from '../types/events';
import { reduceMotion } from '../utils/motion';
import { useSessionFlashes } from './FormPage';

// PREVIEW_MESSAGE: cosa dice una carta-pulsante con il login, finché la carta-modal
// non c'è (lotto 7b; come l'avviso provvisorio di "Chatta" nel 5b)
export const PREVIEW_MESSAGE = 'La scelta della modalità arriva con il prossimo lotto della migrazione (7b).';

// ONLINE_POLL_MS: ogni quanto chi non ha fatto il login richiede il numero degli
// online (come ONLINE_POLL_MS di home.js, P82)
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
  // la sezione: 'veloce' o 'amico' (data-kind, come prima)
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
  // la funzione da chiamare al clic, con la sezione e la modalità della carta.
  // In C sarebbe un puntatore a funzione: void (*onOpen)(kind, mode)
  onOpen: (kind: TileKind, mode: Mode) => void;
}

/**
 * Dice se le carte-pulsante si possono inclinare sotto il mouse.
 *
 * @returns {boolean}
 *
 * In parole semplici:
 *   tiltAllowed()  →  true con un mouse vero e senza "riduci movimento"
 *   (sul telefono, con il dito, niente inclinazione: come initTilt di home.js)
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
  /** Clic: chiama props.onOpen con sezione e modalità. */
  function handleClick(): void {
    props.onOpen(props.kind, props.mode);
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

// HomeStatusListenerProps: cosa riceve l'ascoltatore di home:status
interface HomeStatusListenerProps {
  // la funzione da chiamare a ogni home:status. In C: void (*onStatus)(struct stato)
  onStatus: (status: HomeStatus) => void;
}

/**
 * Ascolta home:status. Non disegna niente.
 *
 * @param {HomeStatusListenerProps} props
 * @returns {null}
 *
 * In parole semplici:
 *   <HomeStatusListener onStatus={handleStatus} />
 *   È un componente a parte perché mettersi in ascolto apre il collegamento al
 *   tempo reale (on di socket/client.ts chiama connect): la home lo disegna solo
 *   con il login, così chi non ha fatto il login non si collega (come home.js).
 */
function HomeStatusListener(props: HomeStatusListenerProps): null {
  useSocketEvent('home:status', props.onStatus);
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

  /** Effetto: il titolo della scheda (prima lo scriveva base.html). */
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
   * Effetto senza login (P82): chiede il numero degli online a GET /online
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

  /** home:status: il numero degli online e la partita in corso (non con ?demo=rientro). */
  function handleStatus(next: HomeStatus): void {
    if (demo) {
      return;
    }
    setStatus(next);
  }

  /**
   * Clic su una carta-pulsante. Senza login: la finestra "Accedi o registrati".
   * Con il login: per ora l'avviso provvisorio (la carta-modal arriva con il 7b).
   * Finché la sessione non è arrivata non fa niente (non si sa ancora cosa aprire).
   */
  function handleOpenTile(kind: TileKind, mode: Mode): void {
    if (!session.loaded) {
      return;
    }
    if (!loggedIn) {
      setPromptOpen(true);
      return;
    }
    // kind e mode serviranno alla carta-modal (7b); oggi l'avviso è uguale per tutte
    setFlashes([{ kind: 'info', message: PREVIEW_MESSAGE }]);
    setFlashKey(flashKey + 1);
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

  // listener: l'ascolto di home:status, solo con il login e senza ?demo=rientro
  let listener: JSX.Element | null = null;
  if (loggedIn && !demo) {
    listener = <HomeStatusListener onStatus={handleStatus} />;
  }

  // prompt: la finestra "Accedi o registrati", solo mentre è aperta
  let prompt: JSX.Element | null = null;
  if (promptOpen) {
    prompt = <LoginPrompt onDone={handlePromptDone} />;
  }

  // demoState: data-demo-state="rientro" come nella home Jinja, solo con i dati finti
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
    </>
  );
}
