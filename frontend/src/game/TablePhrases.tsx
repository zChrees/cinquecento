/**
 * Le frasi del tavolo React (P56, D24; contratto 3.2): il pulsante, l'elenco e il
 * fumetto. È la versione React di app/static/js/components/TablePhrases.js, con lo
 * stesso HTML (stile in css/components/table-phrases.css).
 *
 * Cosa contiene:
 *   <PhrasesButton open={false} disabled={false} onToggle={onToggle} />   il pulsante sopra la mano, a destra (P71)
 *   <PhrasesMenu phrases={[...]} disabled={false} onPick={onPick} openFor={0} />   l'elenco, come pillole
 *   <PhraseBubble name="Turi" text="Bella!" shownFor={0} position="top" />  il fumetto accanto a chi ha parlato
 *
 * Il testo delle frasi e i nomi sono testo, mai HTML: React scrive sempre il testo
 * come testo. L'elenco è quello ricevuto dal server con game:phrases (la pagina
 * non ne tiene una copia sua, P56). Quando aprire, chiudere e spegnere lo decide
 * la pagina (GamePage.tsx).
 *
 * Passo 8a: qui c'è il disegno; le regole fini di game.js (fuoco e scorrimento che
 * restano dopo un ridisegno, P110) arrivano con il lotto 8f.
 *
 * DA DOVE ARRIVANO I DATI: l'elenco da game:phrases (nella prova dall'evento
 * demo:phrases), il fumetto da game:phrase (nella prova demo:phrase).
 */

import type { JSX } from 'react';
import type { Phrase } from '../types/events';
import type { Position } from './Trick';

// PhrasesButtonProps: cosa riceve il pulsante
interface PhrasesButtonProps {
  // true se l'elenco è aperto (aria-expanded, per i lettori di schermo)
  open: boolean;
  // true se il pulsante è spento (subito dopo una frase, o mentre parte)
  disabled: boolean;
  // la funzione della pagina che apre o chiude l'elenco
  onToggle: () => void;
}

/**
 * Il pulsante "Frasi".
 *
 * @param {PhrasesButtonProps} props
 * @returns {JSX.Element}
 *
 * In parole semplici:
 *   <PhrasesButton open={false} disabled={false} onToggle={onToggle} />
 *   Un pulsante con l'icona del fumetto e l'etichetta accessibile "Frasi" (su
 *   computer si vede anche la scritta).
 */
export function PhrasesButton(props: PhrasesButtonProps): JSX.Element {
  let expanded: 'true' | 'false' = 'false';
  if (props.open) {
    expanded = 'true';
  }
  return (
    <button
      className="btn btn--ghost btn--small phrases-button"
      data-phrases-button=""
      type="button"
      aria-label="Frasi"
      aria-expanded={expanded}
      aria-controls="table-phrases"
      disabled={props.disabled}
      onClick={props.onToggle}
    >
      <span className="icon" aria-hidden="true">chat_bubble</span>
      <span className="phrases-button__text" aria-hidden="true">Frasi</span>
    </button>
  );
}

// PhraseChoiceProps: cosa riceve una frase dell'elenco
interface PhraseChoiceProps {
  // la frase: { code, text }
  phrase: Phrase;
  // true se le frasi sono spente
  disabled: boolean;
  // la funzione della pagina da chiamare con il codice della frase scelta
  onPick: (code: string) => void;
}

/**
 * Una frase dell'elenco (un pulsante).
 *
 * @param {PhraseChoiceProps} props
 * @returns {JSX.Element}
 */
function PhraseChoice(props: PhraseChoiceProps): JSX.Element {
  /** Il tocco: passa il codice della frase alla pagina. */
  function handleClick(): void {
    props.onPick(props.phrase.code);
  }
  return (
    <button className="phrase" data-phrase-code={props.phrase.code} type="button" disabled={props.disabled} onClick={handleClick}>
      {props.phrase.text}
    </button>
  );
}

// PhrasesMenuProps: cosa riceve l'elenco
interface PhrasesMenuProps {
  // l'elenco di game:phrases, per esempio [{ code: 'bella', text: 'Bella!' }]
  phrases: Phrase[];
  // true se le frasi sono spente
  disabled: boolean;
  // la funzione della pagina da chiamare con il codice della frase scelta
  onPick: (code: string) => void;
  // P110: millisecondi da quando l'elenco è aperto: l'entrata riprende da lì
  // invece di ripartire a ogni ridisegno
  openFor: number;
}

/**
 * L'elenco delle frasi.
 *
 * @param {PhrasesMenuProps} props
 * @returns {JSX.Element}
 *
 * In parole semplici:
 *   <PhrasesMenu phrases={phrases} disabled={false} onPick={onPick} openFor={0} />
 *   Disegna <div class="phrases-menu" data-phrases-menu id="table-phrases"> con
 *   un pulsante per frase. Lo usa Table.tsx, dentro .table__mine.
 */
export function PhrasesMenu(props: PhrasesMenuProps): JSX.Element {
  // items: una frase per pulsante; la `key` (il "nome" con cui React riconosce lo
  // stesso pulsante tra un disegno e l'altro) è il codice della frase
  const items: JSX.Element[] = [];
  for (let i = 0; i < props.phrases.length; i++) {
    const phrase = props.phrases[i];
    items.push(<PhraseChoice key={phrase.code} phrase={phrase} disabled={props.disabled} onPick={props.onPick} />);
  }
  return (
    <div
      className="phrases-menu"
      data-phrases-menu=""
      id="table-phrases"
      role="group"
      aria-label="Frasi da mandare al tavolo"
      style={{ animationDelay: `${-Math.round(props.openFor)}ms` }}
    >
      {items}
    </div>
  );
}

// PhraseBubbleProps: cosa riceve il fumetto
interface PhraseBubbleProps {
  // chi ha parlato (lo leggono i lettori di schermo, non si vede)
  name: string;
  // il testo della frase
  text: string;
  // P130: millisecondi da quando il fumetto è comparso: l'entrata riprende da lì
  shownFor: number;
  // il posto al tavolo di chi ha parlato
  position: Position;
}

/**
 * Il fumetto accanto all'avatar di chi ha parlato.
 *
 * @param {PhraseBubbleProps} props
 * @returns {JSX.Element}
 *
 * In parole semplici:
 *   <PhraseBubble name="Turi" text="Bella!" shownFor={0} position="top" />
 *   Disegna <p class="phrase-bubble phrase-bubble--top" data-phrase-bubble> con
 *   "Turi: " nascosto (solo per i lettori di schermo) e il testo. Lo usa Table.tsx.
 */
export function PhraseBubble(props: PhraseBubbleProps): JSX.Element {
  return (
    <p
      className={`phrase-bubble phrase-bubble--${props.position}`}
      data-phrase-bubble=""
      role="status"
      style={{ animationDelay: `${-Math.round(props.shownFor)}ms` }}
    >
      <span className="visually-hidden">{`${props.name}: `}</span>
      {props.text}
    </p>
  );
}
