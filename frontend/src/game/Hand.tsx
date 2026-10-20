/**
 * Le carte in mano al tavolo React: la tua mano, le carte coperte degli altri e
 * quelle scoperte (compagno o carte calate). È la versione React di
 * app/static/js/components/Hand.js (P20, P70, P85, P93), con lo stesso HTML, le
 * stesse classi e gli stessi data-* (stile in css/components/hand.css e table.css).
 *
 * Cosa contiene:
 *   <Hand cards={view.hand} playable={view.legal.play} onPlay={onPlay} ... />   la tua mano
 *   <EdgeHand count={3} side="top" drawn={null} dealt={null} />               carte coperte di un altro
 *   <RevealedHand cards={...} side="top" seat={2} ... />                      carte scoperte di un altro
 *
 * Le mosse ammesse le decide il server (legal.play della vista): la mano rende
 * giocabili solo quelle, le altre restano visibili ma spente.
 *
 * DA DOVE ARRIVANO I DATI (la catena delle chiamate):
 *   1. il server manda la vista con game:state (nella prova, la vista finta di
 *      app/static/dev/ e l'evento demo:state);
 *   2. GamePage.tsx la tiene e disegna <Table>;
 *   3. Table.tsx passa a questi componenti i pezzi della vista: view.hand per la
 *      tua mano, cards_in_hand o le carte scoperte per gli altri.
 */

import type { CSSProperties, JSX } from 'react';
import type { Card } from '../types/card';
import { CardBack, CardView } from './CardView';
import { cardName, sameCard, throwKey } from './cards';

// Side: il lato dello schermo di un altro giocatore. La | vuol dire "uno di questi
// valori e nessun altro", come un enum del C
export type Side = 'top' | 'left' | 'right';

// HandAdvice: la carta che ti ha consigliato il compagno (P93), con il suo nome
export interface HandAdvice {
  // la carta consigliata, una della tua mano
  card: Card;
  // il nome del compagno, per la scritta "consiglio di Giuseppe"
  name: string;
}

// HandProps: cosa riceve la tua mano
interface HandProps {
  // le tue carte, nell'ordine del server, per esempio [{ suit: 'coppe', rank: 10 }]; da view.hand
  cards: Card[];
  // le carte che puoi giocare adesso; da view.legal.play (le decide il server)
  playable: Card[];
  // la funzione da chiamare quando tocchi una carta (puntatore a funzione del C);
  // null = carte da guardare soltanto (per esempio le carte calate, P85)
  onPlay: ((card: Card) => void) | null;
  // P70: carta ('coppe-10') → millisecondi da quando è stata pescata, per esempio
  // { 'denari-7': 120 }; {} se nessuna. Record<string, number> è un oggetto con
  // chiavi di testo e numeri come valori
  drawn: Record<string, number>;
  // P70: come drawn, per le carte distribuite a inizio mano
  dealt: Record<string, number>;
  // P93: la carta consigliata dal compagno, oppure null
  advice: HandAdvice | null;
}

/**
 * La tua mano.
 *
 * @param {HandProps} props
 * @returns {JSX.Element}
 *
 * In parole semplici:
 *   <Hand cards={view.hand} playable={view.legal.play} onPlay={onPlay} drawn={{}} dealt={{}} advice={null} />
 *   Disegna <div class="hand" data-hand data-count="5"> con dentro una carta per
 *   ogni elemento di cards: un pulsante acceso se la carta è giocabile, spento se
 *   no. La carta consigliata dal compagno ha il bordo e la scritta "consiglio di …";
 *   quella appena pescata o distribuita vola dal mazzo (ritardo negativo
 *   dell'animazione, così un ridisegno a metà volo non la fa ripartire, P70).
 *   Lo usa Table.tsx, in fondo al tavolo.
 */
export function Hand(props: HandProps): JSX.Element {
  // items: le carte, costruite con un for prima del return
  const items: JSX.Element[] = [];
  for (let i = 0; i < props.cards.length; i++) {
    // card: la carta numero i, per esempio { suit: 'coppe', rank: 10 }
    const card = props.cards[i];
    // key: il codice della carta, per esempio 'coppe-10'. È anche la `key` di
    // React: il "nome" con cui React riconosce la stessa carta tra un disegno e
    // l'altro (se la riconosce, riusa l'elemento invece di crearne uno nuovo)
    const key = throwKey(card);

    // isPlayable: la carta è tra quelle giocabili (ricerca lineare, come in C)
    let isPlayable = false;
    for (let j = 0; j < props.playable.length; j++) {
      if (sameCard(props.playable[j], card)) {
        isPlayable = true;
        break;
      }
    }

    // classes: le classi in più, nell'ordine di Hand.js (prima il consiglio, poi
    // la distribuzione o la pescata)
    const classes: string[] = [];
    let label: string | null = null;
    let adviceLabel: JSX.Element | null = null;
    let isAdvice = false;
    if (props.advice !== null && sameCard(props.advice.card, card)) {
      // P93: per esempio "Gioca 3 di spade, consigliata da Giuseppe"
      isAdvice = true;
      classes.push('card--advice');
      let base = cardName(card);
      if (props.onPlay !== null) {
        base = `Gioca ${base}`;
      }
      label = `${base}, consigliata da ${props.advice.name}`;
      adviceLabel = <span className="card__advice" aria-hidden="true">{`consiglio di ${props.advice.name}`}</span>;
    }

    // P70: distribuita o pescata. Il ritardo negativo fa partire l'animazione
    // "già avanzata" di quei millisecondi. Se la carta è in tutti e due vale dealt.
    let style: CSSProperties | undefined = undefined;
    let isDealt = false;
    let isDrawn = false;
    const dealtFor = props.dealt[key];
    const drawnFor = props.drawn[key];
    if (dealtFor !== undefined) {
      isDealt = true;
      classes.push('card--dealt-mine');
      style = { animationDelay: `${Math.round(-dealtFor)}ms` };
    } else if (drawnFor !== undefined) {
      isDrawn = true;
      classes.push('card--drawn-mine');
      style = { animationDelay: `${Math.round(-drawnFor)}ms` };
    }

    items.push(
      <CardView
        key={key}
        card={card}
        onPlay={props.onPlay}
        playable={isPlayable}
        extraClass={classes.join(' ')}
        label={label}
        pressed={null}
        advice={isAdvice}
        dealt={isDealt}
        drawn={isDrawn}
        thrown={false}
        adviseCard={false}
        advised={false}
        style={style}
      >
        {adviceLabel}
      </CardView>,
    );
  }

  // role e aria-label servono ai lettori di schermo; data-count dice ai test
  // quante carte ci sono
  return (
    <div className="hand" data-hand="" data-count={props.cards.length} role="group" aria-label="Le tue carte">
      {items}
    </div>
  );
}

// EdgeHandProps: cosa riceve il ventaglio coperto di un altro giocatore
interface EdgeHandProps {
  // quante carte ha in mano (il server manda solo il numero); da cards_in_hand
  count: number;
  // il suo lato dello schermo
  side: Side;
  // P70: millisecondi da quando ha pescato (negativo: pesca tra poco), oppure null
  drawn: number | null;
  // P70: per ogni carta, millisecondi da quando è partita nella distribuzione,
  // per esempio [300, 150, -50]; null se non si sta distribuendo. Un posto può
  // essere vuoto (undefined): quella carta non sta volando
  dealt: (number | undefined)[] | null;
}

/**
 * Le carte coperte di un altro giocatore (P70): un ventaglio agganciato al bordo
 * dello schermo dal suo lato, per metà fuori.
 *
 * @param {EdgeHandProps} props
 * @returns {JSX.Element}
 *
 * In parole semplici:
 *   <EdgeHand count={4} side="top" drawn={null} dealt={null} />
 *   Disegna <div class="edge-hand edge-hand--top" data-edge-hand="top"
 *   data-count="4"> con un dorso per carta. Il CSS gira ogni dorso con le
 *   variabili --i (la sua posizione), --n (quante sono) e --n-before (quante
 *   erano prima della pescata). Lo usa Table.tsx, per ogni altro giocatore.
 */
export function EdgeHand(props: EdgeHandProps): JSX.Element {
  // items: un dorso per ogni carta
  const items: JSX.Element[] = [];
  for (let i = 0; i < props.count; i++) {
    // style: --i, la posizione nel ventaglio (style={{ ... }} si usa solo per
    // valori calcolati come questo), più il ritardo dell'animazione se vola
    const style: CSSProperties = { '--i': String(i) };
    let extraClass = '';
    let dealtFor: number | undefined = undefined;
    if (props.dealt !== null) {
      dealtFor = props.dealt[i];
    }
    if (dealtFor !== undefined) {
      // Distribuzione: ogni carta vola dal mazzo con il suo ritardo
      extraClass = 'card--dealt';
      style.animationDelay = `${Math.round(-dealtFor)}ms`;
    } else if (props.drawn !== null) {
      // Pescata: l'ultima carta arriva, le altre si spostano per farle posto
      if (i === props.count - 1) {
        extraClass = 'card--drawn';
      } else {
        extraClass = 'card--making-room';
      }
      style.animationDelay = `${Math.round(-props.drawn)}ms`;
    }
    // key: i dorsi sono tutti uguali, quindi qui il "nome" è il loro posto nel
    // ventaglio (back-0, back-1, ...): è proprio la posizione a distinguerli
    items.push(<CardBack key={`back-${i}`} extraClass={extraClass} style={style} />);
  }

  // drawing e dealing: data-drawing e data-dealing solo durante pescata e distribuzione
  let drawing: string | undefined = undefined;
  if (props.drawn !== null) {
    drawing = '';
  }
  let dealing: string | undefined = undefined;
  if (props.dealt !== null) {
    dealing = '';
  }
  // style: quante carte ci sono ora e quante prima della pescata (almeno 1)
  const style: CSSProperties = {
    '--n': String(props.count),
    '--n-before': String(Math.max(props.count - 1, 1)),
  };

  return (
    <div
      className={`edge-hand edge-hand--${props.side}`}
      data-edge-hand={props.side}
      data-count={props.count}
      data-drawing={drawing}
      data-dealing={dealing}
      role="group"
      aria-label={`${props.count} carte coperte`}
      style={style}
    >
      {items}
    </div>
  );
}

// RevealedAdvise: le carte del compagno (P93), che si toccano per consigliargli
export interface RevealedAdvise {
  // la funzione da chiamare con la carta toccata; null se il compagno è la CPU,
  // che non riceve consigli (P123, D49)
  onPick: ((card: Card) => void) | null;
  // la carta che gli hai già consigliato, oppure null
  picked: Card | null;
  // true se le carte vanno spente (per esempio senza connessione)
  disabled: boolean;
  // il nome del compagno, per le etichette
  name: string;
}

// RevealedHandProps: cosa riceve il ventaglio scoperto
interface RevealedHandProps {
  // le sue carte
  cards: Card[];
  // il suo lato dello schermo
  side: Side;
  // il suo posto (data-revealed-seat, per i test)
  seat: number;
  // l'etichetta per i lettori di schermo, per esempio 'Carte di Giuseppe'
  label: string;
  // P93: solo per il compagno; null per le carte calate (P85)
  advise: RevealedAdvise | null;
  // il ritardo dell'entrata, per esempio '-1200ms' (P119: un ridisegno non la fa ripartire)
  delay: string;
}

/**
 * Le carte di un altro giocatore scoperte, dentro il tavolo (P85 carte calate, P93
 * carte del compagno).
 *
 * @param {RevealedHandProps} props
 * @returns {JSX.Element}
 *
 * In parole semplici:
 *   <RevealedHand cards={view.partner_hand} side="top" seat={2} label="Carte di Salvo" advise={...} delay="0ms" />
 *   Disegna <div class="revealed-hand revealed-hand--top" data-revealed-seat="2">
 *   con le carte scoperte. Con advise (il compagno) il ventaglio è un po' più
 *   grande e, se il compagno è una persona, ogni carta è un pulsante che gliela
 *   consiglia (aria-pressed dice quale è già consigliata). Lo usa Table.tsx.
 */
export function RevealedHand(props: RevealedHandProps): JSX.Element {
  // pickable: le carte si toccano (c'è un compagno vero a cui consigliare)
  let pickable = false;
  if (props.advise !== null && props.advise.onPick !== null) {
    pickable = true;
  }

  // items: le carte, nello stesso ordine di cards
  const items: JSX.Element[] = [];
  for (let i = 0; i < props.cards.length; i++) {
    const card = props.cards[i];
    // style: --i, la posizione nel ventaglio, per l'angolo della carta
    const style: CSSProperties = { '--i': String(i) };

    if (pickable && props.advise !== null) {
      // picked: questa è la carta già consigliata
      let picked = false;
      if (props.advise.picked !== null && sameCard(props.advise.picked, card)) {
        picked = true;
      }
      let extraClass = '';
      if (picked) {
        extraClass = 'card--advised';
      }
      items.push(
        <CardView
          key={throwKey(card)}
          card={card}
          onPlay={props.advise.onPick}
          playable={!props.advise.disabled}
          extraClass={extraClass}
          label={`Consiglia a ${props.advise.name}: ${cardName(card)}`}
          pressed={picked}
          advice={false}
          dealt={false}
          drawn={false}
          thrown={false}
          adviseCard={true}
          advised={picked}
          style={style}
        >
          {null}
        </CardView>,
      );
    } else {
      // Carta da guardare soltanto
      items.push(
        <CardView
          key={throwKey(card)}
          card={card}
          onPlay={null}
          playable={false}
          extraClass=""
          label={null}
          pressed={null}
          advice={false}
          dealt={false}
          drawn={false}
          thrown={false}
          adviseCard={false}
          advised={false}
          style={style}
        >
          {null}
        </CardView>,
      );
    }
  }

  // className: il ventaglio del compagno ha la classe in più, che lo fa più grande
  let className = `revealed-hand revealed-hand--${props.side}`;
  if (props.advise !== null) {
    className = `${className} revealed-hand--partner`;
  }
  // style: quante carte ci sono (apertura del ventaglio) e il ritardo dell'entrata
  const style: CSSProperties = { '--n': String(props.cards.length), animationDelay: props.delay };

  return (
    <div
      className={className}
      data-revealed-hand={props.side}
      data-revealed-seat={props.seat}
      data-count={props.cards.length}
      role="group"
      aria-label={props.label}
      style={style}
    >
      {items}
    </div>
  );
}
