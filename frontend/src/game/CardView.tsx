/**
 * Una carta siciliana al tavolo React (P20, P35): la faccia (l'immagine della carta
 * vera) oppure il dorso. È la versione React di Card() e CardBack() di
 * app/static/js/components/Card.js, con lo stesso HTML, le stesse classi e gli
 * stessi data-* (stile in css/components/card.css).
 *
 * Cosa contiene:
 *   <CardView card={{ suit: 'coppe', rank: 10 }} onPlay={null} ... />   carta da guardare
 *   <CardView card={...} onPlay={onPlay} playable={true} ... />          pulsante nella mano
 *   <CardBack extraClass="" style={undefined} />                         carta coperta
 *
 * La carta da guardare è un <div role="img">, quella da toccare un <button>: come
 * prima, un pulsante si può spegnere (disabled) quando la mossa non è ammessa.
 * Ogni carta ha data-suit e data-rank, che usano i test.
 *
 * DA DOVE ARRIVANO I DATI: le carte arrivano dalla vista del server; i componenti
 * del tavolo (Hand.tsx, Trick.tsx, Table.tsx) le passano qui una alla volta.
 */

import type { CSSProperties, JSX, ReactNode } from 'react';
import type { Card } from '../types/card';
import { BACK_URL, cardName, faceUrl } from './cards';

/**
 * Trasforma un sì/no in un attributo data-* senza valore.
 *
 * @param {boolean} on true se l'attributo ci deve essere
 * @returns {string | undefined} '' (attributo presente, vuoto) oppure undefined (assente)
 *
 * In parole semplici:
 *   dataFlag(true)    → ''          e React scrive data-advice=""
 *   dataFlag(false)   → undefined   e React non scrive l'attributo
 *   Card.js scriveva così i "segni" della carta (data-advice, data-dealt, ...),
 *   che i test cercano con [data-advice].
 */
export function dataFlag(on: boolean): string | undefined {
  if (on) {
    return '';
  }
  return undefined;
}

// CardViewProps: cosa riceve la carta scoperta
interface CardViewProps {
  // la carta, per esempio { suit: 'coppe', rank: 10 }
  card: Card;
  // la funzione da chiamare quando la tocchi (puntatore a funzione del C:
  // void (*onPlay)(struct carta)); null = carta da guardare soltanto
  onPlay: ((card: Card) => void) | null;
  // con onPlay: false = pulsante spento (mossa non ammessa adesso)
  playable: boolean;
  // classi in più dopo "card card--coppe", nell'ordine di Card.js, per esempio
  // 'card--advice card--dealt-mine'; '' se nessuna
  extraClass: string;
  // l'etichetta per i lettori di schermo al posto di quella normale ("Gioca Re di
  // coppe"), per esempio 'Consiglia a Giuseppe: Re di coppe'; null = quella normale
  label: string | null;
  // aria-pressed delle carte del compagno (P93): true se è quella consigliata,
  // false se no, null se la carta non è di quel ventaglio
  pressed: boolean | null;
  // i "segni" della carta, che diventano attributi data-* (per i test):
  // data-advice (consigliata a te, P93), data-dealt e data-drawn (distribuita o
  // pescata, P70), data-thrown (in volo, P70), data-advise-card e data-advised
  // (carte del compagno, P93)
  advice: boolean;
  dealt: boolean;
  drawn: boolean;
  thrown: boolean;
  adviseCard: boolean;
  advised: boolean;
  // valori calcolati per il CSS (ritardo dell'animazione, --i), oppure undefined
  style: CSSProperties | undefined;
  // quello che sta dentro la carta oltre all'immagine (la scritta "consiglio di
  // …", P93), oppure null
  children: ReactNode;
}

/**
 * La carta scoperta.
 *
 * @param {CardViewProps} props
 * @returns {JSX.Element}
 *
 * In parole semplici:
 *   <CardView card={{ suit: 'coppe', rank: 10 }} onPlay={null} ... />
 *   Senza onPlay: <div class="card card--coppe" role="img" aria-label="Re di coppe">
 *   con dentro l'immagine. Con onPlay: un <button aria-label="Gioca Re di coppe">,
 *   spento se playable è false; toccandolo chiama onPlay con la carta.
 */
export function CardView(props: CardViewProps): JSX.Element {
  // className: le classi, quelle di sempre e poi quelle in più
  let className = `card card--${props.card.suit}`;
  if (props.extraClass !== '') {
    className = `${className} ${props.extraClass}`;
  }

  // pressed: aria-pressed come testo ('true' o 'false'), o niente
  let pressed: 'true' | 'false' | undefined = undefined;
  if (props.pressed === true) {
    pressed = 'true';
  } else if (props.pressed === false) {
    pressed = 'false';
  }

  // face: l'immagine. alt="" perché il nome lo dà l'etichetta della carta: per i
  // lettori di schermo l'immagine è solo decorativa
  const face = <img className="card__face" src={faceUrl(props.card)} alt="" draggable={false} />;

  // Carta da guardare soltanto
  if (props.onPlay === null) {
    let label = cardName(props.card);
    if (props.label !== null) {
      label = props.label;
    }
    return (
      <div
        className={className}
        data-suit={props.card.suit}
        data-rank={props.card.rank}
        data-advice={dataFlag(props.advice)}
        data-dealt={dataFlag(props.dealt)}
        data-drawn={dataFlag(props.drawn)}
        data-thrown={dataFlag(props.thrown)}
        data-advise-card={dataFlag(props.adviseCard)}
        data-advised={dataFlag(props.advised)}
        role="img"
        aria-label={label}
        aria-pressed={pressed}
        style={props.style}
      >
        {face}
        {props.children}
      </div>
    );
  }

  // Carta da toccare
  let label = `Gioca ${cardName(props.card)}`;
  if (props.label !== null) {
    label = props.label;
  }
  // onPlay: la funzione della pagina; qui la si "fissa" in una costante perché
  // TypeScript sappia che dentro handleClick non è null
  const onPlay = props.onPlay;
  const card = props.card;

  /** Il tocco sulla carta: la passa alla pagina. */
  function handleClick(): void {
    onPlay(card);
  }

  return (
    <button
      className={className}
      data-suit={props.card.suit}
      data-rank={props.card.rank}
      data-advice={dataFlag(props.advice)}
      data-dealt={dataFlag(props.dealt)}
      data-drawn={dataFlag(props.drawn)}
      data-thrown={dataFlag(props.thrown)}
      data-advise-card={dataFlag(props.adviseCard)}
      data-advised={dataFlag(props.advised)}
      type="button"
      aria-label={label}
      aria-pressed={pressed}
      disabled={!props.playable}
      style={props.style}
      onClick={handleClick}
    >
      {face}
      {props.children}
    </button>
  );
}

// CardBackProps: cosa riceve la carta coperta
interface CardBackProps {
  // classi in più dopo "card card--back", per esempio 'card--dealt' o
  // 'deck__half deck__half--left'; '' se nessuna
  extraClass: string;
  // valori calcolati per il CSS (--i, ritardo dell'animazione), oppure undefined
  style: CSSProperties | undefined;
}

/**
 * La carta coperta (il dorso): carte degli avversari e mazzo.
 *
 * @param {CardBackProps} props
 * @returns {JSX.Element}
 *
 * In parole semplici:
 *   <CardBack extraClass="" style={undefined} />
 *   Disegna <div class="card card--back" data-back role="img" aria-label="Carta
 *   coperta"> con dentro l'immagine del dorso.
 */
export function CardBack(props: CardBackProps): JSX.Element {
  let className = 'card card--back';
  if (props.extraClass !== '') {
    className = `${className} ${props.extraClass}`;
  }
  return (
    <div className={className} data-back="" role="img" aria-label="Carta coperta" style={props.style}>
      <img className="card__back" src={BACK_URL} alt="" draggable={false} />
    </div>
  );
}
