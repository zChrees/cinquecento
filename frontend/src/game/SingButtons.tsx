/**
 * I pulsanti "Canta 40" / "Canta 20" del tavolo React (P21), e accanto "Cala le
 * carte" (P85). È la versione React di app/static/js/components/SingButtons.js,
 * con lo stesso HTML (stile in css/components/table.css).
 *
 * Cosa contiene:
 *   <SingButtons suits={view.legal.sing} sings={view.sings} onSing={onSing} canLayDown={false} onLayDown={null} />
 *
 * Un pulsante per ogni seme che puoi cantare adesso (legal.sing, deciso dal
 * server: turno, prima della carta, Re e Cavallo in mano, ...). Il numero sul
 * pulsante segue il contratto: il primo canto della mano vale 40, i successivi 20
 * (sings vuoto = 40). Serve solo all'etichetta: i punti li decide il server.
 *
 * DA DOVE ARRIVANO I DATI: dalla vista del server (legal.sing, sings,
 * legal.lay_down), passati da Table.tsx; onSing e onLayDown sono della pagina.
 */

import type { JSX } from 'react';
import type { Suit } from '../types/card';
import type { Sing } from '../types/view';

// SingButtonProps: cosa riceve un pulsante di canto
interface SingButtonProps {
  // il seme da cantare
  suit: Suit;
  // 40 oppure 20
  points: number;
  // la funzione della pagina da chiamare con il seme (puntatore a funzione del C)
  onSing: (suit: Suit) => void;
}

/**
 * Un pulsante "Canta 40 a coppe".
 *
 * @param {SingButtonProps} props
 * @returns {JSX.Element}
 */
function SingButton(props: SingButtonProps): JSX.Element {
  /** Il tocco: passa il seme alla pagina. */
  function handleClick(): void {
    props.onSing(props.suit);
  }
  return (
    <button className="btn btn--primary btn--small sing-button" data-sing-button="" data-suit={props.suit} type="button" onClick={handleClick}>
      <span className="icon" aria-hidden="true">campaign</span>
      {`Canta ${props.points} a ${props.suit}`}
    </button>
  );
}

// SingButtonsProps: cosa riceve la riga dei pulsanti
interface SingButtonsProps {
  // i semi cantabili adesso; da legal.sing (vuoto se non puoi cantare)
  suits: Suit[];
  // i canti della mano in corso; da sings della vista
  sings: Sing[];
  // la funzione della pagina che manda il canto
  onSing: (suit: Suit) => void;
  // P85: true se adesso puoi calare le carte; da legal.lay_down
  canLayDown: boolean;
  // P85: la funzione della pagina per "Cala le carte", oppure null
  onLayDown: (() => void) | null;
}

/**
 * La riga dei pulsanti dei canti.
 *
 * @param {SingButtonsProps} props
 * @returns {JSX.Element}
 *
 * In parole semplici:
 *   <SingButtons suits={['coppe']} sings={[]} onSing={onSing} canLayDown={false} onLayDown={null} />
 *   Disegna <div class="sing-buttons" data-sing-buttons> con dentro
 *   "Canta 40 a coppe". La riga c'è sempre, anche vuota: tiene il suo spazio
 *   (P117). Lo usa Table.tsx, sopra la tua mano.
 */
export function SingButtons(props: SingButtonsProps): JSX.Element {
  // points: 40 se nessuno ha ancora cantato in questa mano, altrimenti 20
  let points = 20;
  if (props.sings.length === 0) {
    points = 40;
  }

  // buttons: un pulsante per seme; la `key` (il "nome" con cui React riconosce lo
  // stesso pulsante tra un disegno e l'altro) è il seme
  const buttons: JSX.Element[] = [];
  for (let i = 0; i < props.suits.length; i++) {
    buttons.push(<SingButton key={props.suits[i]} suit={props.suits[i]} points={points} onSing={props.onSing} />);
  }
  if (props.canLayDown && props.onLayDown !== null) {
    buttons.push(
      <button key="lay-down" className="btn btn--primary btn--small lay-down-button" data-lay-down-button="" type="button" onClick={props.onLayDown}>
        <span className="icon" aria-hidden="true">playing_cards</span>
        Cala le carte
      </button>,
    );
  }
  return <div className="sing-buttons" data-sing-buttons="">{buttons}</div>;
}
