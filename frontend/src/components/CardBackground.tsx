/**
 * Lo sfondo della home (P22): una cascata di carte che cade dall'alto senza
 * fermarsi (stile in css/components/card-background.css).
 *
 * Carte di dorso e, di faccia, Assi, Tre (i carichi) e coppie Cavallo + Re a
 * ventaglio (cantare 40), dalle immagini di app/static/img/cards-bg/ (P40). Le
 * carte sono sempre le stesse a ogni apertura (numeri "casuali" fissi) e si
 * ricreano solo quando cambia la misura della finestra.
 *
 * Cosa contiene:
 *   <CardBackground />
 *
 * DA DOVE ARRIVANO I DATI: nessun dato dal server. Le misure vengono dalla
 * finestra (getBoundingClientRect) e da --bg-card-w di card-background.css.
 */

import { useEffect, useRef, useState } from 'react';
import type { CSSProperties, JSX, RefObject } from 'react';

// Le variabili CSS (--x, --dur, ...) dentro style={{ ... }}: TypeScript le conosce
// grazie a types/css.d.ts.

// IMG_BASE: la cartella delle immagini dello sfondo (data-img-base)
const IMG_BASE = '/static/img/cards-bg/';

// RESIZE_DELAY_MS: dopo un cambio di misura della finestra, quanto aspettare prima
// di ricreare le carte (mentre si trascina il bordo i cambi sono tanti)
const RESIZE_DELAY_MS = 120;

// FACES: le carte di faccia, a turno: ogni tanto una coppia Cavallo + Re
// ('pair:coppe'), poi Assi e Tre (il nome del file senza .webp)
const FACES: string[] = [
  'pair:coppe', 'asso-denari', 'tre-spade',
  'pair:bastoni', 'asso-coppe', 'tre-denari',
  'pair:spade', 'asso-bastoni', 'tre-coppe',
  'pair:denari', 'asso-spade', 'tre-bastoni',
];

// BgCard: una carta della cascata, già calcolata
interface BgCard {
  // il "nome" della carta per React (key), per esempio '4-dorso'
  key: string;
  // cosa cade: 'dorso', un file come 'asso-denari', oppure una coppia 'pair:coppe'
  kind: string;
  // la distanza: da 0,55 (lontana, piccola, lenta) a 1 (vicina)
  depth: number;
  // le variabili CSS della carta (posizione, durata, rotazione, luce)
  style: CSSProperties;
}

/**
 * Un numero "casuale" ma sempre uguale per la stessa carta.
 *
 * @param {number} i il numero della carta
 * @param {number} k quale numero di quella carta (posizione, durata, ...)
 * @returns {number} un numero tra 0 e 1
 *
 * In parole semplici:
 *   pseudoRandom(3, 21)  →  per esempio 0,4127, e lo stesso a ogni apertura
 *   Così lo sfondo non cambia ogni volta che si apre la pagina.
 */
function pseudoRandom(i: number, k: number): number {
  const x = Math.sin(i * 12.9898 + k * 78.233) * 43758.5453;
  return x - Math.floor(x);
}

/**
 * Calcola le carte della cascata per la misura attuale del contenitore.
 *
 * @param {HTMLElement} container il <div data-bg-cards> già nella pagina
 * @returns {BgCard[]} le carte, prima le lontane e poi le vicine; vuoto se non si può misurare
 *
 * In parole semplici:
 *   buildCards(div)  →  da 8 a 26 carte sparse su tutta la larghezza
 *   Le più piccole sembrano più lontane: cadono più lente, sono più scure e
 *   passano dietro alle grandi (sono piene, non trasparenti: chi sta davanti copre
 *   chi sta dietro). Nella pagina chi viene dopo sta davanti, per questo l'elenco
 *   è ordinato dalla più lontana alla più vicina.
 */
function buildCards(container: HTMLElement): BgCard[] {
  // cardW: la larghezza di una carta vicina, da --bg-card-w del CSS (60 px)
  const cardW = parseFloat(getComputedStyle(container).getPropertyValue('--bg-card-w'));
  const area = container.getBoundingClientRect();
  if (!cardW || !area.width) {
    return [];
  }
  const count = Math.max(8, Math.min(26, Math.round((area.width / cardW) * 1.3)));
  const cards: BgCard[] = [];
  // faces: quante carte di faccia sono già uscite (per prendere la prossima di FACES)
  let faces = 0;
  for (let i = 0; i < count; i++) {
    // rnd(k): il k-esimo numero "casuale" di questa carta
    function rnd(k: number): number {
      return pseudoRandom(i + 1, k + 20);
    }

    const depth = 0.55 + rnd(1) * 0.45;
    // Due carte su cinque cadono di dorso, alternate a quelle di faccia
    const back = i % 5 === 1 || i % 5 === 3;
    let kind = 'dorso';
    if (!back) {
      kind = FACES[faces % FACES.length];
      faces += 1;
    }
    const dur = (9 + rnd(4) * 5) / depth;
    const r0 = (rnd(6) * 2 - 1) * 40;
    let turn = 1;
    if (rnd(7) < 0.5) {
      turn = -1;
    }
    const r1 = r0 + turn * (90 + rnd(8) * 180);
    // style: le variabili lette da card-background.css. style={{ ... }} si usa
    // solo per valori calcolati come questi (regole-codice.md, sezione 6)
    const style: CSSProperties = {
      '--bg-card-w': `${(cardW * depth).toFixed(1)}px`,
      '--x': `${(((i + 0.2 + rnd(3) * 0.6) / count) * area.width).toFixed(1)}px`,
      // posizione da ferma, senza animazioni ("riduci movimento")
      '--y': `${(rnd(10) * area.height).toFixed(1)}px`,
      '--dur': `${dur.toFixed(2)}s`,
      '--delay': `${(-rnd(5) * dur).toFixed(2)}s`,
      '--r0': `${r0.toFixed(1)}deg`,
      '--r1': `${r1.toFixed(1)}deg`,
      '--drift': `${((rnd(9) * 2 - 1) * cardW * 1.2).toFixed(1)}px`,
      // luce: 0,67 per le lontane, 0,85 per le vicine
      '--shade': (0.45 + depth * 0.4).toFixed(2),
    };
    cards.push({ key: `${i}-${kind}`, kind: kind, depth: depth, style: style });
  }

  /** Per l'ordinamento: prima la più lontana (depth più piccolo). */
  function byDepth(a: BgCard, b: BgCard): number {
    return a.depth - b.depth;
  }

  cards.sort(byDepth);
  return cards;
}

// FallingCardProps: cosa riceve una carta della cascata
interface FallingCardProps {
  // la carta calcolata da buildCards
  card: BgCard;
}

/**
 * Una carta che cade: un'immagine, oppure una coppia Cavallo + Re.
 *
 * @param {FallingCardProps} props
 * @returns {JSX.Element}
 *
 * In parole semplici:
 *   <FallingCard card={card} />
 *   → <img class="bg-fall" src=".../asso-denari.webp">, oppure per 'pair:coppe'
 *     <span class="bg-fall bg-pair"> con cavallo-coppe e re-coppe.
 *   alt="" perché è solo decorazione (tutto lo sfondo è aria-hidden).
 */
function FallingCard(props: FallingCardProps): JSX.Element {
  if (props.card.kind.startsWith('pair:')) {
    // suit: il seme della coppia, per esempio 'coppe' da 'pair:coppe'
    const suit = props.card.kind.slice(5);
    return (
      <span className="bg-fall bg-pair" style={props.card.style}>
        <img src={`${IMG_BASE}cavallo-${suit}.webp`} alt="" />
        <img src={`${IMG_BASE}re-${suit}.webp`} alt="" />
      </span>
    );
  }
  return <img className="bg-fall" src={`${IMG_BASE}${props.card.kind}.webp`} alt="" style={props.card.style} />;
}

/**
 * La cascata.
 *
 * @returns {JSX.Element}
 *
 * In parole semplici:
 *   <CardBackground />
 *   Al primo disegno il contenitore è vuoto (le carte si calcolano sulle sue
 *   misure, che ci sono solo quando è nella pagina); subito dopo l'effetto lo
 *   misura e lo riempie, e lo rifà quando cambia la misura della finestra.
 */
export function CardBackground(): JSX.Element {
  // Gli hook si chiamano sempre in cima al componente, mai dentro un if.
  // containerRef: il <div> dello sfondo, per misurarlo (null finché non c'è)
  const containerRef: RefObject<HTMLDivElement | null> = useRef<HTMLDivElement>(null);
  // useState restituisce due cose: il valore attuale e la funzione per cambiarlo,
  // che fa ridisegnare il componente (regole-codice.md, sezione 6).
  // cards: le carte da disegnare
  const [cards, setCards] = useState<BgCard[]>([]);

  /** Effetto: riempie lo sfondo e lo ricrea quando cambia la misura della finestra. */
  function fill(): () => void {
    // timer: il ricalcolo in attesa dopo un cambio di misura (0 = nessuno)
    let timer = 0;

    function measure(): void {
      if (containerRef.current !== null) {
        setCards(buildCards(containerRef.current));
      }
    }

    function handleResize(): void {
      window.clearTimeout(timer);
      timer = window.setTimeout(measure, RESIZE_DELAY_MS);
    }

    function stop(): void {
      window.clearTimeout(timer);
      window.removeEventListener('resize', handleResize);
    }

    measure();
    window.addEventListener('resize', handleResize);
    return stop;
  }

  // []: una volta sola, quando lo sfondo compare
  useEffect(fill, []);

  // items: un elemento per carta. key è il "nome" con cui React riconosce la
  // stessa carta tra un disegno e l'altro: il numero della carta nella cascata
  // e cosa mostra (per esempio '4-dorso')
  const items: JSX.Element[] = [];
  for (let i = 0; i < cards.length; i++) {
    items.push(<FallingCard key={cards[i].key} card={cards[i]} />);
  }

  return (
    <div className="bg-deco" aria-hidden="true" data-bg-cards="" data-img-base={IMG_BASE} ref={containerRef}>
      {items}
    </div>
  );
}
