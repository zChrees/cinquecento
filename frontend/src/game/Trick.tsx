/**
 * Il centro del tavolo React: la presa in corso, la presa appena chiusa, il mazzo
 * e la briscola nell'angolo. È la versione React di
 * app/static/js/components/Trick.js (P21, P57, P70, P76, P102, P108), con lo stesso
 * HTML, le stesse classi e gli stessi data-* (stile in css/components/trick.css e
 * table.css).
 *
 * Cosa contiene:
 *   <Trick trick={view.trick} positionOf={positionOf} thrown={{}} />          la presa in corso
 *   <LastTrick lastTrick={...} positionOf={...} winnerText="Prendi tu" ... /> la presa appena chiusa (P57)
 *   <Deck deckCount={12} trump={null} shuffled={null} />                     il mazzo (o lo spazio vuoto)
 *   <TrumpBadge trump="coppe" />                                             la briscola nell'angolo (P102)
 *
 * Ogni carta della presa sta dal lato di chi l'ha giocata (in basso la tua, poi
 * destra, in alto e sinistra, come i posti); quella che sta vincendo (la dice il
 * server, trick.winning_seat, P75) è sollevata e bordata (P76).
 *
 * DA DOVE ARRIVANO I DATI: dalla vista del server (trick, last_trick, deck_count,
 * trump); i tempi delle animazioni (thrown, shownFor, shuffled) li decide la
 * pagina e li passa Table.tsx.
 */

import type { CSSProperties, JSX } from 'react';
import type { Card, Suit } from '../types/card';
import type { LastTrick as LastTrickData, Trick as TrickData } from '../types/view';
import { AWAY_DELAY_MS } from './animations';
import { CardBack, CardView } from './CardView';
import { FIGURE_BASE, cardName, throwKey } from './cards';

// Position: il posto di un giocatore visto da te ('bottom' sei tu)
export type Position = 'bottom' | 'right' | 'top' | 'left';

// PositionOf: il tipo di una funzione che dal posto (0-3) dà la posizione. In C
// sarebbe un puntatore a funzione: const char *(*positionOf)(int seat)
export type PositionOf = (seat: number) => Position;

// ThrownCardProps: cosa riceve una carta della presa
interface ThrownCardProps {
  // la carta
  card: Card;
  // P70: millisecondi dal lancio se sta volando (negativi: parte tra poco), oppure undefined
  thrown: number | undefined;
}

/**
 * Una carta dentro la presa; se è appena stata giocata vola al suo posto (P70).
 *
 * @param {ThrownCardProps} props
 * @returns {JSX.Element}
 *
 * In parole semplici:
 *   <ThrownCard card={{ suit: 'coppe', rank: 1 }} thrown={undefined} />
 *   Una carta da guardare. Con thrown ha la classe card--thrown, data-thrown e il
 *   ritardo negativo dell'animazione: un ridisegno a metà volo non la fa ripartire.
 */
function ThrownCard(props: ThrownCardProps): JSX.Element {
  let extraClass = '';
  let isThrown = false;
  let style: CSSProperties | undefined = undefined;
  if (props.thrown !== undefined) {
    extraClass = 'card--thrown';
    isThrown = true;
    style = { animationDelay: `${-Math.round(props.thrown)}ms` };
  }
  return (
    <CardView
      card={props.card}
      onPlay={null}
      playable={false}
      extraClass={extraClass}
      label={null}
      pressed={null}
      advice={false}
      dealt={false}
      drawn={false}
      thrown={isThrown}
      adviseCard={false}
      advised={false}
      style={style}
    >
      {null}
    </CardView>
  );
}

// TrickProps: cosa riceve la presa in corso
interface TrickProps {
  // il campo trick della vista: { leader_seat, cards: [{ seat, card }], winning_seat }
  trick: TrickData;
  // posto → 'bottom' | 'right' | 'top' | 'left'; la calcola Table.tsx
  positionOf: PositionOf;
  // P70: carta ('coppe-10') → millisecondi dal lancio, per le carte in volo; {} se nessuna
  thrown: Record<string, number>;
}

/**
 * La presa in corso.
 *
 * @param {TrickProps} props
 * @returns {JSX.Element}
 *
 * In parole semplici:
 *   <Trick trick={view.trick} positionOf={positionOf} thrown={{}} />
 *   Disegna <div class="trick" data-trick data-count="2"> con una casella per
 *   carta (trick__card--top, ...). L'etichetta per i lettori di schermo dice le
 *   carte e quale sta vincendo.
 */
export function Trick(props: TrickProps): JSX.Element {
  const trick = props.trick;
  // cards e names: le caselle delle carte e i loro nomi, in ordine di gioco
  const cards: JSX.Element[] = [];
  const names: string[] = [];
  let winningName: string | null = null;
  for (let i = 0; i < trick.cards.length; i++) {
    const play = trick.cards[i];
    const key = throwKey(play.card);
    names.push(cardName(play.card));
    // P76: la carta che sta vincendo
    let className = `trick__card trick__card--${props.positionOf(play.seat)}`;
    let winning: string | undefined = undefined;
    if (play.seat === trick.winning_seat) {
      className = `${className} trick__card--winner`;
      winning = '';
      winningName = cardName(play.card);
    }
    cards.push(
      <div key={key} className={className} data-trick-seat={play.seat} data-winning={winning}>
        <ThrownCard card={play.card} thrown={props.thrown[key]} />
      </div>,
    );
  }

  // label: per esempio "Presa in corso: 7 di denari, 3 di denari. Sta vincendo: 3 di denari"
  let label = 'Presa in corso: nessuna carta';
  if (trick.cards.length > 0) {
    label = `Presa in corso: ${names.join(', ')}`;
    if (winningName !== null) {
      label = `${label}. Sta vincendo: ${winningName}`;
    }
  }
  return (
    <div className="trick" data-trick="" data-count={trick.cards.length} role="group" aria-label={label}>
      {cards}
    </div>
  );
}

// LastTrickProps: cosa riceve la presa appena chiusa
interface LastTrickProps {
  // il campo last_trick: { winner_seat, cards: [{ seat, card }] }
  lastTrick: LastTrickData;
  // posto → posizione
  positionOf: PositionOf;
  // per esempio "Prende Turi" oppure "Prendi tu"
  winnerText: string;
  // P70: millisecondi da quando la presa chiusa si vede
  shownFor: number;
  // P70: carta → millisecondi dal lancio (la carta che l'ha chiusa)
  thrown: Record<string, number>;
}

/**
 * La presa appena chiusa (P57), per un momento al posto della presa vuota: dopo
 * AWAY_DELAY_MS le carte scivolano verso chi ha preso.
 *
 * @param {LastTrickProps} props
 * @returns {JSX.Element}
 *
 * In parole semplici:
 *   <LastTrick lastTrick={view.last_trick} positionOf={...} winnerText="Prendi tu" shownFor={200} thrown={{}} />
 *   Disegna <div class="trick trick--closed trick--to-bottom" data-last-trick>
 *   con le carte e la scritta di chi prende. Quando e per quanto si vede lo decide
 *   la pagina (dal lotto 8c).
 */
export function LastTrick(props: LastTrickProps): JSX.Element {
  const winner = props.lastTrick.winner_seat;
  // awayDelay: l'uscita comincia AWAY_DELAY_MS dopo che la presa si vede, anche dopo un ridisegno
  const awayDelay = `${Math.round(AWAY_DELAY_MS - props.shownFor)}ms`;
  const cards: JSX.Element[] = [];
  const names: string[] = [];
  for (let i = 0; i < props.lastTrick.cards.length; i++) {
    const play = props.lastTrick.cards[i];
    const key = throwKey(play.card);
    names.push(cardName(play.card));
    let className = `trick__card trick__card--${props.positionOf(play.seat)}`;
    if (play.seat === winner) {
      className = `${className} trick__card--winner`;
    }
    cards.push(
      <div key={key} className={className} data-trick-seat={play.seat} style={{ animationDelay: awayDelay }}>
        <ThrownCard card={play.card} thrown={props.thrown[key]} />
      </div>,
    );
  }
  const label = `${props.winnerText}: ${names.join(', ')}`;
  return (
    <div
      className={`trick trick--closed trick--to-${props.positionOf(winner)}`}
      data-last-trick=""
      data-winner-seat={winner}
      data-count={props.lastTrick.cards.length}
      role="group"
      aria-label={label}
    >
      {cards}
      <span className="trick__winner" aria-hidden="true" style={{ animationDelay: awayDelay }}>{props.winnerText}</span>
    </div>
  );
}

// TrumpBadgeProps: cosa riceve la briscola nell'angolo
interface TrumpBadgeProps {
  // il seme di briscola, per esempio 'coppe'
  trump: Suit;
}

/**
 * La briscola nell'angolo (P102, P108): Cavallo e Re del seme, a ventaglio.
 *
 * @param {TrumpBadgeProps} props
 * @returns {JSX.Element}
 *
 * In parole semplici:
 *   <TrumpBadge trump="coppe" />
 *   Disegna <div class="trump-badge" data-trump-badge="coppe" aria-label="Briscola:
 *   coppe"> con le due immagini. È l'unico posto dove si vede la briscola; il nome
 *   lo leggono i lettori di schermo. Lo usa Table.tsx, accanto al tabellone.
 */
export function TrumpBadge(props: TrumpBadgeProps): JSX.Element {
  return (
    <div className="trump-badge" data-trump-badge={props.trump} role="img" aria-label={`Briscola: ${props.trump}`}>
      <img className="trump-badge__card" src={`${FIGURE_BASE}cavallo-${props.trump}.webp`} alt="" draggable={false} />
      <img className="trump-badge__card" src={`${FIGURE_BASE}re-${props.trump}.webp`} alt="" draggable={false} />
    </div>
  );
}

// DeckProps: cosa riceve il mazzo
interface DeckProps {
  // le carte rimaste nel mazzo; da deck_count
  deckCount: number;
  // il seme di briscola, oppure null finché nessuno ha cantato 40: serve solo a
  // sapere se a mazzo finito resta lo spazio vuoto
  trump: Suit | null;
  // P70: millisecondi dall'inizio della mescolata a inizio mano, oppure null
  shuffled: number | null;
}

/**
 * Il mazzo coperto con le carte rimaste; a mazzo finito, con la briscola, uno
 * spazio vuoto della stessa misura (P77, P102), così presa e tavolo non si spostano.
 *
 * @param {DeckProps} props
 * @returns {JSX.Element | null}
 *
 * In parole semplici:
 *   <Deck deckCount={12} trump={null} shuffled={null} />
 *   Con carte: <div class="deck" data-deck-count="12" aria-label="Mazzo: 12 carte">
 *   con il dorso e il numero. Durante la mescolata (P70) due mezzi mazzi si aprono
 *   ai lati e si richiudono. Senza carte: lo spazio vuoto se c'è la briscola,
 *   altrimenti niente (null). Lo usa Table.tsx, al centro.
 */
export function Deck(props: DeckProps): JSX.Element | null {
  if (props.deckCount <= 0) {
    if (props.trump === null) {
      return null;
    }
    // La carta coperta è invisibile (deck__slot) e tiene solo il posto
    return (
      <div className="deck deck--empty" data-deck-empty="" aria-hidden="true">
        <CardBack extraClass="deck__slot" style={undefined} />
      </div>
    );
  }

  // riffle: i due mezzi mazzi della mescolata, solo mentre si mescola
  const riffle: JSX.Element[] = [];
  let shuffling: string | undefined = undefined;
  if (props.shuffled !== null) {
    shuffling = '';
    const delay = `${Math.round(-props.shuffled)}ms`;
    riffle.push(<CardBack key="half-left" extraClass="deck__half deck__half--left" style={{ animationDelay: delay }} />);
    riffle.push(<CardBack key="half-right" extraClass="deck__half deck__half--right" style={{ animationDelay: delay }} />);
  }
  return (
    <div className="deck" data-deck-count={props.deckCount} data-shuffling={shuffling} role="img" aria-label={`Mazzo: ${props.deckCount} carte`}>
      <CardBack extraClass="" style={undefined} />
      {riffle}
      <span className="deck__count" aria-hidden="true">{props.deckCount}</span>
    </div>
  );
}
