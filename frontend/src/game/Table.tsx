/**
 * Il tavolo di gioco React (P21), costruito tutto dalla vista (contratto 3.3)
 * (stile in css/components/table.css, trick.css, hand-summary.css e
 * css/pages/game.css).
 *
 * Tu sei sempre in basso; gli altri si dispongono nell'ordine dei posti, verso
 * destra (D11): nel 1v1 l'avversario in alto; nel 2v2 a destra chi gioca dopo di
 * te, in alto il compagno, a sinistra chi gioca prima di te. Le loro carte coperte
 * (P70) sono ventagli agganciati al bordo dello schermo dal loro lato.
 *
 *   [Esci]        Punteggio      (P90: sotto 1024 px niente punteggio, Esci solo icona)
 *              (giocatore in alto)
 *   (sinistra)  presa · mazzo  (destra)
 *   [punti]       (tu)       [Frasi]
 *   pulsanti Canta · la tua mano
 *
 * Cosa contiene:
 *   positionFn(view)    la funzione posto → 'bottom' | 'right' | 'top' | 'left'
 *   NO_MOMENTS          i momenti del tavolo quando non c'è niente da mostrare
 *   <Table view={view} turnPaused={false} handlers={...} status="" moments={...} phrases={null} />
 *
 * La pagina non calcola regole: le carte giocabili sono legal.play, i canti
 * legal.sing e la calata legal.lay_down. I "momenti" del tavolo (presa appena
 * chiusa, riepilogo, canti, carte calate, lanci, P57 e P70) arrivano già decisi in
 * `moments`: qui si disegnano soltanto (GamePage.tsx parte da NO_MOMENTS e li
 * riempie dallo store).
 *
 * DA DOVE ARRIVANO I DATI (la catena delle chiamate):
 *   1. il server manda la vista con game:state (nella prova, la vista finta di
 *      app/static/dev/ e l'evento demo:state);
 *   2. GamePage.tsx la tiene, decide i momenti e disegna <Table>;
 *   3. Table passa i pezzi della vista ai componenti: Hand.tsx, Trick.tsx,
 *      Scoreboard.tsx, SingButtons.tsx, HandSummary.tsx, Timer.tsx, SeatAvatar.tsx,
 *      TablePhrases.tsx.
 */

import type { JSX } from 'react';
import { Link } from 'react-router';
import type { Card, Suit } from '../types/card';
import type { Phrase } from '../types/events';
import type { Advice, GameView, LaidDown, LastHand, LastTrick as LastTrickData, PlayerView, TeamTotal } from '../types/view';
import { CardView } from './CardView';
import { FIGURE_BASE, cardName, throwKey } from './cards';
import { EdgeHand, Hand, RevealedHand } from './Hand';
import type { HandAdvice, RevealedAdvise, Side } from './Hand';
import { HandSummary } from './HandSummary';
import { Scoreboard, myTeam } from './Scoreboard';
import { SeatAvatar } from './SeatAvatar';
import { SingButtons } from './SingButtons';
import { PhraseBubble, PhrasesButton, PhrasesMenu } from './TablePhrases';
import { Timer } from './Timer';
import { Deck, LastTrick, Trick, TrumpBadge } from './Trick';
import type { Position, PositionOf } from './Trick';
import { useStartDelay } from './useStartDelay';

// --- Tipi di quello che riceve il tavolo --------------------------------------

// TableHandlers: le funzioni della pagina che il tavolo chiama. Ognuna è un
// "puntatore a funzione" del C: il tavolo non sa cosa fanno, le chiama e basta
export interface TableHandlers {
  // carta della tua mano toccata
  onPlay: (card: Card) => void;
  // seme da cantare
  onSing: (suit: Suit) => void;
  // pulsante "Esci"
  onLeave: () => void;
  // P85: pulsante "Cala le carte", oppure null
  onLayDown: (() => void) | null;
  // P93: carta del compagno toccata (consiglio), oppure null
  onAdvise: ((card: Card) => void) | null;
}

// DealMoment: la distribuzione a inizio mano (P70)
export interface DealMoment {
  // millisecondi dall'inizio della mescolata, oppure null se la mescolata è finita
  shuffled: number | null;
  // le tue carte: carta ('coppe-10') → millisecondi da quando è partita
  mine: Record<string, number>;
  // gli altri: posto → per ogni carta i millisecondi da quando è partita
  seats: Record<number, (number | undefined)[]>;
}

// SangShown: le carte di un canto da mostrare accanto a chi ha cantato (D15)
export interface SangShown {
  // chi ha cantato
  seat: number;
  // il seme
  suit: Suit;
  // 40 oppure 20
  points: number;
  // Re e Cavallo del seme
  cards: Card[];
  // P119: millisecondi da quando si vedono (un ridisegno non fa ripartire l'entrata)
  shownFor: number;
}

// PartnerMoment: le carte del compagno scoperte (P93)
export interface PartnerMoment {
  // la carta che gli hai consigliato, oppure null
  picked: Card | null;
  // true se le sue carte sono spente (senza connessione, consiglio in viaggio, ...)
  disabled: boolean;
  // millisecondi da quando si vedono
  shownFor: number;
  // true finché c'è la scritta "Mazzo finito: ora vedi le carte di …"
  notice: boolean;
}

// TableMoments: i momenti del tavolo da mostrare adesso (P57, P70, P85, P93),
// decisi dalla pagina
export interface TableMoments {
  // la presa appena chiusa, oppure null
  lastTrick: LastTrickData | null;
  // millisecondi da quando la presa chiusa si vede
  lastTrickFor: number;
  // carta ('coppe-10') → millisecondi dal lancio, per le carte in volo
  thrown: Record<string, number>;
  // posto di un altro → millisecondi dalla sua pescata
  drawnSeats: Record<number, number>;
  // carta pescata da te → millisecondi dalla pescata
  drawnCards: Record<string, number>;
  // la distribuzione, oppure null
  deal: DealMoment | null;
  // P70: la parte della key delle carte che cambia a ogni distribuzione (dealRoundKey
  // dello store): all'inizio della distribuzione le carte sono elementi nuovi
  dealRound: string;
  // il riepilogo di fine mano da mostrare (last_hand), oppure null
  summary: LastHand | null;
  // P72: i punti della mano da mostrare al posto di hand_points, oppure null
  handPoints: TeamTotal[] | null;
  // il pulsante "Ok" del riepilogo, oppure null
  onCloseSummary: (() => void) | null;
  // posto → le carte del canto da mostrare
  sang: Record<number, SangShown>;
  // P85: le carte calate da mostrare adesso, oppure null
  laidDown: LaidDown | null;
  // P85: millisecondi da quando si vedono
  laidDownFor: number;
  // P93: le carte del compagno scoperte, oppure null
  partner: PartnerMoment | null;
  // P93: la carta che ti ha consigliato il compagno, oppure null
  advice: Advice | null;
}

// NO_MOMENTS: nessun momento da mostrare (per esempio alla prima vista)
export const NO_MOMENTS: TableMoments = {
  lastTrick: null,
  lastTrickFor: 0,
  thrown: {},
  drawnSeats: {},
  drawnCards: {},
  deal: null,
  dealRound: '',
  summary: null,
  handPoints: null,
  onCloseSummary: null,
  sang: {},
  laidDown: null,
  laidDownFor: 0,
  partner: null,
  advice: null,
};

// BubbleShown: il fumetto di una frase, con da quanto si vede (P130)
export interface BubbleShown {
  // il testo della frase
  text: string;
  // millisecondi da quando è comparso
  shownFor: number;
  // performance.now() di quando è comparso: la key del fumetto (una frase nuova
  // dello stesso posto è un elemento nuovo, con la sua entrata)
  since: number;
}

// TablePhrasesState: le frasi del tavolo (P56), decise dalla pagina
export interface TablePhrasesState {
  // l'elenco di game:phrases
  list: Phrase[];
  // true se l'elenco è aperto
  open: boolean;
  // true se pulsante e frasi sono spenti
  disabled: boolean;
  // P110: millisecondi da quando l'elenco è aperto
  openFor: number;
  // apre o chiude l'elenco
  onToggle: () => void;
  // frase scelta (il codice)
  onPick: (code: string) => void;
  // posto → il fumetto da mostrare
  bubbles: Record<number, BubbleShown>;
}

// --- Posti ----------------------------------------------------------------------

// POSITIONS: le posizioni in ordine di posto, partendo da te: nel 1v1 tu e
// l'avversario in alto; nel 2v2 tu, destra, alto (il compagno), sinistra
const POSITIONS_1V1: Position[] = ['bottom', 'top'];
const POSITIONS_2V2: Position[] = ['bottom', 'right', 'top', 'left'];

/**
 * La funzione che dice dove sta un posto, visto da te.
 *
 * @param {GameView} view la vista
 * @returns {PositionOf} posto → 'bottom' | 'right' | 'top' | 'left'
 *
 * In parole semplici:
 *   const positionOf = positionFn(view);   positionOf(2)   → 'top' (nel 2v2, se sei al posto 0)
 *   Conta quanti posti dopo di te sta quel giocatore, girando: (posto - tuo + n) % n.
 */
export function positionFn(view: GameView): PositionOf {
  const n = view.players.length;
  let names = POSITIONS_1V1;
  if (n === 4) {
    names = POSITIONS_2V2;
  }
  const mySeat = view.you.seat;

  /** La posizione di un posto. */
  function positionOf(seat: number): Position {
    return names[(seat - mySeat + n) % n];
  }
  return positionOf;
}

// --- Pezzi di un posto ------------------------------------------------------------

// SingBadgesProps: cosa ricevono le icone dei canti di un giocatore
interface SingBadgesProps {
  // la vista (i canti della mano: sings)
  view: GameView;
  // il posto del giocatore
  seat: number;
}

/**
 * I canti di un giocatore, come icone fisse accanto al nome (D15).
 *
 * @param {SingBadgesProps} props
 * @returns {JSX.Element | null} null se non ha cantato
 *
 * In parole semplici:
 *   <SingBadges view={view} seat={1} />
 *   Per ogni canto di quel posto: l'Asso del seme e il numero (40 o 20).
 */
function SingBadges(props: SingBadgesProps): JSX.Element | null {
  const badges: JSX.Element[] = [];
  for (let i = 0; i < props.view.sings.length; i++) {
    const sing = props.view.sings[i];
    if (sing.seat !== props.seat) {
      continue;
    }
    // label: per esempio "Ha cantato 40 a coppe"; con role="img" i lettori di
    // schermo la leggono (P34)
    const label = `Ha cantato ${sing.points} a ${sing.suit}`;
    // la `key` (il "nome" con cui React riconosce lo stesso elemento tra un disegno
    // e l'altro) è il seme: un seme si canta una volta sola per mano
    badges.push(
      <span key={sing.suit} className={`sing-badge sing-badge--${sing.suit}`} data-sing-seat={props.seat} data-suit={sing.suit} role="img" title={label} aria-label={label}>
        <img className="sing-badge__img" src={`${FIGURE_BASE}asso-${sing.suit}-figura.webp`} alt="" draggable={false} />
        <span aria-hidden="true">{sing.points}</span>
      </span>,
    );
  }
  if (badges.length === 0) {
    return null;
  }
  return <div className="seat__sings">{badges}</div>;
}

// SangCardsProps: cosa ricevono le carte di un canto
interface SangCardsProps {
  // il canto da mostrare
  sang: SangShown;
  // il posto di chi ha cantato, visto da te
  position: Position;
}

/**
 * Re e Cavallo appena cantati (game:sang, D15), accanto a chi ha cantato.
 *
 * @param {SangCardsProps} props
 * @returns {JSX.Element}
 */
function SangCards(props: SangCardsProps): JSX.Element {
  // delay: l'entrata delle carte, fissata al primo disegno (useStartDelay)
  const delay = useStartDelay(`${-Math.round(props.sang.shownFor)}ms`);
  const cards: JSX.Element[] = [];
  for (let i = 0; i < props.sang.cards.length; i++) {
    const card = props.sang.cards[i];
    cards.push(
      <CardView key={throwKey(card)} card={card} onPlay={null} playable={false} extraClass="" label={null} pressed={null}
        advice={false} dealt={false} drawn={false} thrown={false} adviseCard={false} advised={false} style={undefined}>
        {null}
      </CardView>,
    );
  }
  // aria-hidden: lo annuncia già la riga di stato
  return (
    <div className={`sang sang--${props.position}`} data-sang-seat={props.sang.seat} data-suit={props.sang.suit} data-points={props.sang.points} aria-hidden="true">
      <div className="sang__cards" style={{ animationDelay: delay }}>{cards}</div>
      <span className="sang__points">{`Canta ${props.sang.points}`}</span>
    </div>
  );
}

// HandPointsProps: cosa ricevono i punti di una squadra nella mano in corso
interface HandPointsProps {
  // i punti: { team, total }
  points: TeamTotal;
  // la frase per i lettori di schermo, per esempio 'I tuoi punti in questa mano'
  label: string;
}

/**
 * I punti di una squadra nella mano in corso (P72, D44): sul telefono solo il
 * numero, da 1024 px "N punti" (la parola si nasconde in table.css).
 *
 * @param {HandPointsProps} props
 * @returns {JSX.Element}
 */
function HandPoints(props: HandPointsProps): JSX.Element {
  const text = `${props.label}: ${props.points.total}`;
  return (
    <span className="hand-points" data-hand-points={props.points.total} data-team={props.points.team} role="img" aria-label={text} title={text}>
      <span className="hand-points__total">{props.points.total}</span>
      <span className="hand-points__word" aria-hidden="true"> punti</span>
    </span>
  );
}

// RatingProps: cosa riceve la pillola del rating
interface RatingProps {
  // il giocatore (campo rating della vista, P88)
  player: PlayerView;
}

/**
 * P89: il rating del giocatore in una pillola accanto al nome (solo da computer,
 * table.css); tratteggiata se è ancora provvisorio.
 *
 * @param {RatingProps} props
 * @returns {JSX.Element | null} null per la CPU e per chi non ha il rating
 */
function Rating(props: RatingProps): JSX.Element | null {
  const rating = props.player.rating;
  if (rating === null) {
    return null;
  }
  let className = 'seat__rating';
  let title = `Rating ${rating.value}`;
  let provisional: string | undefined = undefined;
  let provisionalText: JSX.Element | null = null;
  if (rating.provisional) {
    className = 'seat__rating seat__rating--provisional';
    title = `Rating ${rating.value}, provvisorio`;
    provisional = '';
    provisionalText = <span className="visually-hidden">, provvisorio</span>;
  }
  return (
    <span className={className} data-rating={rating.value} data-provisional={provisional} title={title}>
      <span className="visually-hidden">rating </span>
      {String(rating.value)}
      {provisionalText}
    </span>
  );
}

// SeatProps: cosa riceve un posto
interface SeatProps {
  // la vista
  view: GameView;
  // il giocatore di quel posto
  player: PlayerView;
  // dove sta, visto da te
  position: Position;
  // true se il tavolo è in pausa (l'anello del tempo resta fermo, P132)
  turnPaused: boolean;
  // le carte del suo canto da mostrare, oppure null
  sang: SangShown | null;
  // il suo fumetto, oppure null
  phrase: BubbleShown | null;
  // i punti della mano da mostrare accanto (P72), oppure null
  points: JSX.Element | null;
}

/**
 * Un giocatore al tavolo: avatar (con l'anello del tempo se tocca a lui), nome, stato.
 *
 * @param {SeatProps} props
 * @returns {JSX.Element}
 *
 * In parole semplici:
 *   <Seat view={view} player={view.players[1]} position="top" ... />
 *   Disegna <section class="seat seat--top" data-seat="1" data-position="top">
 *   con l'avatar, il nome (più "(tu)" per te), la pillola del rating, sotto
 *   "compagno" o "scollegato · 48 s", le icone dei canti e le carte appena cantate.
 */
function Seat(props: SeatProps): JSX.Element {
  const view = props.view;
  const player = props.player;
  let isTurn = false;
  if (view.turn !== null && view.turn.seat === player.seat) {
    isTurn = true;
  }
  const isMe = player.seat === view.you.seat;
  let partner = false;
  if (view.mode === '2v2' && !isMe && player.team === myTeam(view)) {
    partner = true;
  }

  // notes: "compagno", "scollegato · 48 s" (i secondi arrotondati per eccesso)
  const notes: string[] = [];
  if (partner) {
    notes.push('compagno');
  }
  if (!player.connected) {
    if (player.reconnect_seconds_left === null) {
      notes.push('scollegato');
    } else {
      notes.push(`scollegato · ${Math.ceil(player.reconnect_seconds_left)} s`);
    }
  }

  // P72: in alto i punti stanno a sinistra dell'avatar, per non alzare il posto;
  // negli altri posti sopra l'avatar
  const pointsBeside = props.position === 'top';
  let pointsInAvatar: JSX.Element | null = null;
  let pointsAbove: JSX.Element | null = null;
  if (pointsBeside) {
    pointsInAvatar = props.points;
  } else {
    pointsAbove = props.points;
  }

  let timer: JSX.Element | null = null;
  if (isTurn && view.turn !== null) {
    // key: P132, l'anello si ricrea a ogni vista nuova e quando la pausa finisce:
    // l'animazione parte dai secondi di quel momento (cambiarli a metà la farebbe saltare)
    timer = <Timer key={`timer-${view.version}-${String(props.turnPaused)}`} turn={view.turn} paused={props.turnPaused} />;
  }
  let bubble: JSX.Element | null = null;
  if (props.phrase !== null) {
    bubble = (
      <PhraseBubble key={`bubble-${props.phrase.since}`} name={player.username} text={props.phrase.text}
        shownFor={props.phrase.shownFor} position={props.position} />
    );
  }
  let name = player.username;
  if (isMe) {
    name = `${player.username} (tu)`;
  }
  let note: JSX.Element | null = null;
  if (notes.length > 0) {
    note = <span className="seat__note">{notes.join(' · ')}</span>;
  }
  let sang: JSX.Element | null = null;
  if (props.sang !== null) {
    // key: un canto nuovo (un altro seme) è un elemento nuovo, con la sua entrata
    sang = <SangCards key={`${props.sang.suit}-${props.sang.points}`} sang={props.sang} position={props.position} />;
  }

  // className e label: di turno e scollegato cambiano classe ed etichetta
  let className = `seat seat--${props.position}`;
  let label = player.username;
  if (isTurn) {
    className = `${className} seat--turn`;
    label = `${player.username}, di turno`;
  }
  if (!player.connected) {
    className = `${className} seat--offline`;
  }
  let turn = 'no';
  if (isTurn) {
    turn = 'yes';
  }

  return (
    <section className={className} data-seat={player.seat} data-position={props.position} data-team={player.team} data-turn={turn} aria-label={label}>
      {pointsAbove}
      <span className="seat__avatar">
        {pointsInAvatar}
        <SeatAvatar player={player} />
        {timer}
        {bubble}
      </span>
      <div className="seat__label">
        <span className="seat__title">
          <span className="seat__name">{name}</span>
          <Rating player={player} />
        </span>
        {note}
      </div>
      <SingBadges view={view} seat={player.seat} />
      {sang}
    </section>
  );
}

// --- Riquadri e scritte -------------------------------------------------------------

// ResultProps: cosa riceve il riquadro di fine partita
interface ResultProps {
  // la vista, con result non null
  view: GameView;
}

/**
 * Il riquadro di fine partita (result della vista). Se la partita è finita a punti,
 * sotto c'è il riepilogo dell'ultima mano (P57); dopo un abbandono no, perché
 * last_hand sarebbe quello di una mano precedente.
 *
 * @param {ResultProps} props
 * @returns {JSX.Element | null}
 */
function Result(props: ResultProps): JSX.Element | null {
  const view = props.view;
  if (view.result === null) {
    return null;
  }
  const winner = view.result.winner_team;
  const reason = view.result.reason;
  let title = 'Pareggio';
  if (winner !== null) {
    if (winner === myTeam(view)) {
      title = 'Hai vinto!';
    } else {
      title = 'Hai perso';
    }
  }
  let text = 'La partita è finita.';
  if (reason === 'abandon') {
    text = 'La partita è finita per abbandono.';
  }
  let summary: JSX.Element | null = null;
  if (reason === 'score' && view.last_hand !== null && view.last_hand.hand_number === view.hand_number) {
    summary = <HandSummary view={view} lastHand={view.last_hand} onClose={null} />;
  }
  return (
    <div className="table__result panel" data-result={reason} role="status">
      <h2>{title}</h2>
      <p>{text}</p>
      {summary}
      {/* discover="none": senza, React Router aggiunge l'attributo data-discover, che
          qui non serve */}
      <Link className="btn btn--primary" to="/" discover="none">Torna alla home</Link>
    </div>
  );
}

/**
 * Il nome di un posto, oppure un testo di riserva se il posto non c'è.
 *
 * @param {GameView} view la vista
 * @param {number} seat il posto
 * @param {string} fallback il testo se il posto non c'è, per esempio 'un giocatore'
 * @returns {string}
 */
function nameOf(view: GameView, seat: number, fallback: string): string {
  for (let i = 0; i < view.players.length; i++) {
    if (view.players[i].seat === seat) {
      return view.players[i].username;
    }
  }
  return fallback;
}

/**
 * "Prendi tu", "Prende Turi".
 *
 * @param {GameView} view la vista
 * @param {number} seat chi ha preso
 * @returns {string}
 */
function winnerText(view: GameView, seat: number): string {
  if (seat === view.you.seat) {
    return 'Prendi tu';
  }
  return `Prende ${nameOf(view, seat, 'un giocatore')}`;
}

// PartnerNoticeProps: cosa riceve la scritta delle carte del compagno
interface PartnerNoticeProps {
  // il nome del compagno
  name: string;
  // millisecondi da quando si vede (P119: un ridisegno non fa ripartire l'entrata)
  shownFor: number;
}

/**
 * P93: la scritta quando le carte del compagno si scoprono.
 *
 * @param {PartnerNoticeProps} props
 * @returns {JSX.Element}
 */
function PartnerNotice(props: PartnerNoticeProps): JSX.Element {
  // delay: l'entrata della scritta, fissata al primo disegno (useStartDelay)
  const delay = useStartDelay(`${-Math.round(props.shownFor)}ms`);
  return (
    <p className="partner-notice" data-partner-notice="" role="status" style={{ animationDelay: delay }}>
      {`Mazzo finito: ora vedi le carte di ${props.name}`}
    </p>
  );
}

// LaidDownNoticeProps: cosa riceve la scritta delle carte calate
interface LaidDownNoticeProps {
  // la vista
  view: GameView;
  // le carte calate (last_hand.laid_down)
  laid: LaidDown;
  // posto → posizione
  positionOf: PositionOf;
  // millisecondi da quando si vede
  shownFor: number;
}

/**
 * P85: la scritta al centro mentre si vedono le carte calate. Per i lettori di
 * schermo dice anche le carte di tutti.
 *
 * @param {LaidDownNoticeProps} props
 * @returns {JSX.Element}
 */
function LaidDownNotice(props: LaidDownNoticeProps): JSX.Element {
  // delay: l'entrata della scritta, fissata al primo disegno (useStartDelay)
  const delay = useStartDelay(`${-Math.round(props.shownFor)}ms`);
  const view = props.view;
  let text = `${nameOf(view, props.laid.seat, 'Un giocatore')} cala le carte`;
  if (props.laid.seat === view.you.seat) {
    text = 'Hai calato le carte';
  }
  // cards: per esempio "tu: Asso di coppe, Re di coppe" per ogni posto con carte
  const cards: string[] = [];
  for (let i = 0; i < props.laid.hands.length; i++) {
    const hand = props.laid.hands[i];
    if (hand.cards.length === 0) {
      continue;
    }
    let who = nameOf(view, hand.seat, 'un giocatore');
    if (hand.seat === view.you.seat) {
      who = 'tu';
    }
    const names: string[] = [];
    for (let j = 0; j < hand.cards.length; j++) {
      names.push(cardName(hand.cards[j]));
    }
    cards.push(`${who}: ${names.join(', ')}`);
  }
  return (
    <div
      className={`laid-down laid-down--from-${props.positionOf(props.laid.seat)}`}
      data-laid-down=""
      data-laid-down-seat={props.laid.seat}
      role="status"
      aria-label={`${text}. ${cards.join('; ')}`}
    >
      <span className="laid-down__text" aria-hidden="true" style={{ animationDelay: delay }}>{text}</span>
    </div>
  );
}

// --- Il tavolo ------------------------------------------------------------------------

// TableProps: cosa riceve il tavolo
interface TableProps {
  // la vista da disegnare. Quando le mosse non sono permesse (mossa in viaggio,
  // senza connessione, fine mano) la pagina passa la vista con legal vuoto
  view: GameView;
  // true se il tavolo è in pausa: l'anello del tempo resta pieno e fermo (P132)
  turnPaused: boolean;
  // le funzioni della pagina
  handlers: TableHandlers;
  // il messaggio sotto la mano (per esempio la risposta del server), '' se nessuno
  status: string;
  // i momenti da mostrare adesso (NO_MOMENTS se nessuno)
  moments: TableMoments;
  // le frasi del tavolo, oppure null finché l'elenco non arriva
  phrases: TablePhrasesState | null;
}

/**
 * Il tavolo.
 *
 * @param {TableProps} props
 * @returns {JSX.Element}
 *
 * In parole semplici:
 *   <Table view={view} turnPaused={false} handlers={handlers} status="" moments={NO_MOMENTS} phrases={null} />
 *   Disegna <div class="table__inner" data-mode="1v1" data-version="19"
 *   data-status="playing"> con, in ordine: i ventagli degli altri, la barra in
 *   alto (Esci, briscola, punteggio), il tavolo (gli altri posti, presa e mazzo,
 *   riepilogo), la tua parte (punti, tu, frasi, canti, mano, riga di stato) e, a
 *   partita finita, il riquadro del risultato. Lo usa GamePage.tsx.
 */
export function Table(props: TableProps): JSX.Element {
  const view = props.view;
  const moments = props.moments;
  const positionOf = positionFn(view);

  // laidHands: P85, mentre si vedono le carte calate, posto → le sue carte
  let laidHands: Record<number, Card[]> | null = null;
  if (moments.laidDown !== null) {
    laidHands = {};
    for (let i = 0; i < moments.laidDown.hands.length; i++) {
      laidHands[moments.laidDown.hands[i].seat] = moments.laidDown.hands[i].cards;
    }
  }
  let bubbles: Record<number, BubbleShown> = {};
  if (props.phrases !== null) {
    bubbles = props.phrases.bubbles;
  }

  // me e others: il tuo posto e quelli degli altri, nell'ordine dei posti
  let me: PlayerView = view.players[0];
  const others: PlayerView[] = [];
  for (let i = 0; i < view.players.length; i++) {
    if (view.players[i].seat === view.you.seat) {
      me = view.players[i];
    } else {
      others.push(view.players[i]);
    }
  }

  // mate e mateCards: P93, nel 2v2, a mazzo finito con la briscola, le carte del
  // compagno (partner_hand) si vedono. view.mode === '2v2' serve anche a TypeScript:
  // solo dopo questo controllo sa che la vista ha partner_hand
  let mate: PlayerView | null = null;
  let mateCards: Card[] | null = null;
  if (view.mode === '2v2') {
    for (let i = 0; i < others.length; i++) {
      if (others[i].team === me.team) {
        mate = others[i];
      }
    }
    if (moments.laidDown === null && mate !== null && view.partner_hand !== null && view.partner_hand.length > 0) {
      mateCards = view.partner_hand;
    }
  }
  // adviceFrom: chi ti ha dato il consiglio (P93), oppure null
  let handAdvice: HandAdvice | null = null;
  if (moments.advice !== null) {
    for (let i = 0; i < view.players.length; i++) {
      if (view.players[i].seat === moments.advice.seat) {
        handAdvice = { card: moments.advice.card, name: view.players[i].username };
      }
    }
  }

  // P72 (D44): i punti della mano in corso; i tuoi sopra la tua mano, quelli degli
  // avversari una volta sola, accanto all'avversario in alto (1v1) o a quello a sinistra (2v2)
  let handPoints: TeamTotal[] = view.hand_points;
  if (moments.handPoints !== null) {
    handPoints = moments.handPoints;
  }
  let myPoints: TeamTotal | null = null;
  let theirPoints: TeamTotal | null = null;
  for (let i = 0; i < handPoints.length; i++) {
    if (handPoints[i].team === me.team) {
      if (myPoints === null) {
        myPoints = handPoints[i];
      }
    } else if (theirPoints === null) {
      theirPoints = handPoints[i];
    }
  }
  let theirSide: Position = 'top';
  if (view.mode === '2v2') {
    theirSide = 'left';
  }
  let theirSeat: PlayerView | null = null;
  for (let i = 0; i < others.length; i++) {
    if (theirSeat === null && positionOf(others[i].seat) === theirSide) {
      theirSeat = others[i];
    }
  }
  // points: posto → i punti da mostrare accanto a quel posto
  const points: Record<number, JSX.Element> = {};
  if (myPoints !== null) {
    let label = 'I tuoi punti in questa mano';
    if (view.mode === '2v2') {
      label = 'Punti della tua squadra in questa mano';
    }
    points[me.seat] = <HandPoints points={myPoints} label={label} />;
  }
  if (theirPoints !== null && theirSeat !== null) {
    let label = `Punti di ${theirSeat.username} in questa mano`;
    if (view.mode === '2v2') {
      label = 'Punti degli avversari in questa mano';
    }
    points[theirSeat.seat] = <HandPoints points={theirPoints} label={label} />;
  }

  // --- La barra in alto: "Esci", la briscola (solo quando c'è) e il punteggio ---
  let trumpBadge: JSX.Element | null = null;
  if (view.trump !== null) {
    trumpBadge = <TrumpBadge trump={view.trump} />;
  }
  const topbar = (
    <header className="table__top">
      <button className="btn btn--ghost btn--small table__leave" data-leave="" type="button" onClick={props.handlers.onLeave}>
        <span className="icon" aria-hidden="true">logout</span>
        <span className="table__leave-text">Esci</span>
      </button>
      <div className="table__corner">
        {trumpBadge}
        <Scoreboard view={view} />
      </div>
    </header>
  );

  // --- Il tavolo: gli altri posti, il centro (presa e mazzo), il riepilogo ---
  const seats: JSX.Element[] = [];
  for (let i = 0; i < others.length; i++) {
    const player = others[i];
    seats.push(
      <Seat
        key={`seat-${player.seat}`}
        view={view}
        player={player}
        position={positionOf(player.seat)}
        turnPaused={props.turnPaused}
        sang={sangOf(moments, player.seat)}
        phrase={bubbleOf(bubbles, player.seat)}
        points={pointsOf(points, player.seat)}
      />,
    );
  }
  let laidNotice: JSX.Element | null = null;
  let center: JSX.Element | null = null;
  if (moments.laidDown !== null) {
    laidNotice = <LaidDownNotice view={view} laid={moments.laidDown} positionOf={positionOf} shownFor={moments.laidDownFor} />;
  } else if (moments.lastTrick !== null) {
    // key: una presa chiusa diversa è un elemento nuovo, con la sua uscita
    center = (
      <LastTrick
        key={trickKey(moments.lastTrick)}
        lastTrick={moments.lastTrick}
        positionOf={positionOf}
        winnerText={winnerText(view, moments.lastTrick.winner_seat)}
        shownFor={moments.lastTrickFor}
        thrown={moments.thrown}
      />
    );
  } else {
    center = <Trick trick={view.trick} positionOf={positionOf} thrown={moments.thrown} />;
  }
  let shuffled: number | null = null;
  if (moments.deal !== null) {
    shuffled = moments.deal.shuffled;
  }
  let summary: JSX.Element | null = null;
  if (moments.summary !== null) {
    summary = <HandSummary view={view} lastHand={moments.summary} onClose={moments.onCloseSummary} />;
  }
  let partnerNotice: JSX.Element | null = null;
  if (mateCards !== null && mate !== null && moments.partner !== null && moments.partner.notice) {
    partnerNotice = <PartnerNotice name={mate.username} shownFor={moments.partner.shownFor} />;
  }
  const board = (
    <div className={`table__board table__board--${view.mode}`}>
      {seats}
      <div className="table__center">
        {laidNotice}
        {center}
        <Deck deckCount={view.deck_count} trump={view.trump} shuffled={shuffled} />
      </div>
      {summary}
      {partnerNotice}
    </div>
  );

  // --- La tua parte: sopra la mano i tuoi punti a sinistra, tu al centro, le
  // frasi a destra (P71, P72, P77); poi elenco delle frasi, canti, mano, stato ---
  let phrasesButton: JSX.Element | null = null;
  let phrasesMenu: JSX.Element | null = null;
  if (props.phrases !== null) {
    phrasesButton = <PhrasesButton open={props.phrases.open} disabled={props.phrases.disabled} onToggle={props.phrases.onToggle} />;
    if (props.phrases.open) {
      // P101: l'elenco sta in .table__mine: sul telefono copre solo la zona sotto
      // la tua riga, da computer è il pannello di lato (P80)
      phrasesMenu = <PhrasesMenu phrases={props.phrases.list} disabled={props.phrases.disabled} onPick={props.phrases.onPick} openFor={props.phrases.openFor} />;
    }
  }
  // hand: P85, mentre si vedono le carte calate la tua mano è quella della calata
  let hand: JSX.Element;
  if (laidHands !== null) {
    let laidMine: Card[] = [];
    if (laidHands[me.seat] !== undefined) {
      laidMine = laidHands[me.seat];
    }
    hand = <Hand cards={laidMine} playable={[]} onPlay={null} drawn={{}} dealt={{}} advice={null} round="" />;
  } else {
    let dealtMine: Record<string, number> = {};
    if (moments.deal !== null) {
      dealtMine = moments.deal.mine;
    }
    hand = (
      <Hand
        cards={view.hand}
        playable={view.legal.play}
        onPlay={props.handlers.onPlay}
        drawn={moments.drawnCards}
        dealt={dealtMine}
        advice={handAdvice}
        round={moments.dealRound}
      />
    );
  }
  const mine = (
    <div className="table__mine">
      <div className="table__me">
        <div className="table__me-side">{pointsOf(points, me.seat)}</div>
        <Seat
          view={view}
          player={me}
          position="bottom"
          turnPaused={props.turnPaused}
          sang={sangOf(moments, me.seat)}
          phrase={bubbleOf(bubbles, me.seat)}
          points={null}
        />
        {phrasesButton}
      </div>
      {phrasesMenu}
      <SingButtons
        suits={view.legal.sing}
        sings={view.sings}
        onSing={props.handlers.onSing}
        canLayDown={view.legal.lay_down}
        onLayDown={props.handlers.onLayDown}
      />
      {hand}
      <p className="table__status" data-table-status="" role="status" aria-live="polite">{props.status}</p>
    </div>
  );

  // --- I ventagli degli altri (P70): coperti dal bordo dello schermo; P85 scoperti
  // mentre si vedono le carte calate; P93 scoperti quelli del compagno ---
  const edgeHands: JSX.Element[] = [];
  for (let i = 0; i < others.length; i++) {
    const player = others[i];
    const side = sideOf(positionOf(player.seat));
    const key = `hand-${player.seat}`;
    if (laidHands !== null) {
      const cards = laidHands[player.seat];
      if (cards !== undefined && cards.length > 0) {
        // key: le carte calate sono un ventaglio diverso da quello del compagno, con la sua entrata
        edgeHands.push(
          <RevealedHand key={`laid-${key}`} cards={cards} side={side} seat={player.seat} label={`Carte di ${player.username}`}
            advise={null} delay={`${-Math.round(moments.laidDownFor)}ms`} />,
        );
      }
      continue;
    }
    if (mateCards !== null && mate !== null && player.seat === mate.seat) {
      // P123 (D49): la CPU compagna non riceve consigli, le sue carte non si toccano
      let onPick: ((card: Card) => void) | null = props.handlers.onAdvise;
      if (player.cpu) {
        onPick = null;
      }
      let picked: Card | null = null;
      let disabled = props.handlers.onAdvise === null;
      let shownFor = 0;
      if (moments.partner !== null) {
        picked = moments.partner.picked;
        if (moments.partner.disabled) {
          disabled = true;
        }
        shownFor = moments.partner.shownFor;
      }
      const advise: RevealedAdvise = { onPick: onPick, picked: picked, disabled: disabled, name: player.username };
      edgeHands.push(
        <RevealedHand key={key} cards={mateCards} side={side} seat={player.seat} label={`Carte di ${player.username}`}
          advise={advise} delay={`${-Math.round(shownFor)}ms`} />,
      );
      continue;
    }
    let drawn: number | null = null;
    if (moments.drawnSeats[player.seat] !== undefined) {
      drawn = moments.drawnSeats[player.seat];
    }
    let dealt: (number | undefined)[] | null = null;
    if (moments.deal !== null) {
      dealt = null;
      if (moments.deal.seats[player.seat] !== undefined) {
        dealt = moments.deal.seats[player.seat];
      }
    }
    edgeHands.push(<EdgeHand key={key} count={player.cards_in_hand} side={side} drawn={drawn} dealt={dealt} round={moments.dealRound} />);
  }

  // A fine partita il riquadro arriva dopo che si è vista l'ultima presa (o le carte calate, P85)
  let result: JSX.Element | null = null;
  if (view.result !== null && moments.lastTrick === null && moments.laidDown === null) {
    result = <Result view={view} />;
  }
  // P93: con le carte del compagno scoperte il compagno si sposta per non stare sotto il ventaglio
  let className = 'table__inner';
  if (mateCards !== null) {
    className = 'table__inner table__inner--mate-cards';
  }
  return (
    <div className={className} data-mode={view.mode} data-version={view.version} data-status={view.status}>
      {edgeHands}
      {topbar}
      {board}
      {mine}
      {result}
    </div>
  );
}

/**
 * Un nome che riconosce una presa chiusa: chi ha preso e le carte, in ordine.
 *
 * @param {LastTrickData} trick la presa
 * @returns {string} per esempio '1:coppe-1,denari-3'
 */
function trickKey(trick: LastTrickData): string {
  const cards: string[] = [];
  for (let i = 0; i < trick.cards.length; i++) {
    cards.push(throwKey(trick.cards[i].card));
  }
  return `${trick.winner_seat}:${cards.join(',')}`;
}

/**
 * Le carte del canto di un posto da mostrare, oppure null.
 *
 * @param {TableMoments} moments i momenti
 * @param {number} seat il posto
 * @returns {SangShown | null}
 */
function sangOf(moments: TableMoments, seat: number): SangShown | null {
  if (moments.sang[seat] !== undefined) {
    return moments.sang[seat];
  }
  return null;
}

/**
 * Il fumetto di un posto, oppure null.
 *
 * @param {Record<number, BubbleShown>} bubbles posto → fumetto
 * @param {number} seat il posto
 * @returns {BubbleShown | null}
 */
function bubbleOf(bubbles: Record<number, BubbleShown>, seat: number): BubbleShown | null {
  if (bubbles[seat] !== undefined) {
    return bubbles[seat];
  }
  return null;
}

/**
 * I punti della mano da mostrare accanto a un posto, oppure null.
 *
 * @param {Record<number, JSX.Element>} points posto → punti
 * @param {number} seat il posto
 * @returns {JSX.Element | null}
 */
function pointsOf(points: Record<number, JSX.Element>, seat: number): JSX.Element | null {
  if (points[seat] !== undefined) {
    return points[seat];
  }
  return null;
}

/**
 * Il lato dello schermo di un altro giocatore.
 *
 * @param {Position} position la sua posizione, vista da te
 * @returns {Side} 'top' | 'left' | 'right'
 * @throws {Error} se la posizione è 'bottom' (sei tu: non hai un ventaglio sul bordo)
 *
 * In parole semplici:
 *   sideOf('top')   → 'top'
 *   Position ha un valore in più di Side ('bottom'): questa funzione lo esclude con
 *   un controllo vero, invece di "forzare" il tipo (regole-codice.md, sezione 6).
 */
function sideOf(position: Position): Side {
  if (position === 'bottom') {
    throw new Error('Il tuo posto non ha un ventaglio sul bordo.');
  }
  return position;
}
