/**
 * Il riepilogo di fine mano del tavolo React (P57). È la versione React di
 * app/static/js/components/HandSummary.js, con lo stesso HTML (stile in
 * css/components/hand-summary.css).
 *
 * Cosa contiene:
 *   <HandSummary view={view} lastHand={view.last_hand} onClose={onClose} />
 *
 * Per ogni squadra: i punti delle carte prese, dei canti e il totale della mano;
 * sotto, il punteggio della partita. La tua squadra è sempre la prima colonna. Si
 * usa in due posti: sopra il centro del tavolo a inizio della mano nuova (con
 * "Ok", dal lotto 8c), e dentro il riquadro di fine partita (senza "Ok").
 *
 * DA DOVE ARRIVANO I DATI: dalla vista del server (last_hand, scores, players).
 */

import type { JSX } from 'react';
import type { GameView, HandTeamResult, LastHand } from '../types/view';
import { mineFirst, myTeam, teamName } from './Scoreboard';

// RowProps: cosa riceve una riga della tabella
interface RowProps {
  // la scritta a sinistra, per esempio 'Carte prese'
  label: string;
  // i valori delle due squadre, nell'ordine delle colonne
  values: number[];
  // la classe della riga, per esempio 'hand-summary__hand'; undefined se nessuna
  // (niente attributo class, come el() di utils/dom.js con una classe vuota)
  className: string | undefined;
}

/**
 * Una riga del riepilogo.
 *
 * @param {RowProps} props
 * @returns {JSX.Element}
 */
function Row(props: RowProps): JSX.Element {
  // cells: una cella per squadra; la `key` è la colonna (le colonne non cambiano posto)
  const cells: JSX.Element[] = [];
  for (let i = 0; i < props.values.length; i++) {
    cells.push(<td key={`col-${i}`}>{props.values[i]}</td>);
  }
  return (
    <tr className={props.className}>
      <th scope="row">{props.label}</th>
      {cells}
    </tr>
  );
}

// HandSummaryProps: cosa riceve il riepilogo
interface HandSummaryProps {
  // la vista, per i nomi delle squadre e il punteggio
  view: GameView;
  // il campo last_hand: { hand_number, teams: [...] }
  lastHand: LastHand;
  // la funzione per "Ok"; null = niente pulsante (riquadro di fine partita)
  onClose: (() => void) | null;
}

/**
 * Il riepilogo.
 *
 * @param {HandSummaryProps} props
 * @returns {JSX.Element}
 *
 * In parole semplici:
 *   <HandSummary view={view} lastHand={view.last_hand} onClose={null} />
 *   Disegna <section class="hand-summary" data-hand-summary data-hand-number="3">
 *   con il titolo "Mano 3 finita" e una tabella di quattro righe (Carte prese,
 *   Canti, Mano, Punteggio). Con onClose è un riquadro sopra il tavolo con "Ok".
 */
export function HandSummary(props: HandSummaryProps): JSX.Element {
  const view = props.view;
  const mine = myTeam(view);
  const teams: HandTeamResult[] = mineFirst(props.lastHand.teams, mine);

  // headers e le righe: una colonna per squadra, nello stesso ordine
  const headers: JSX.Element[] = [];
  const cardPoints: number[] = [];
  const singPoints: number[] = [];
  const handTotals: number[] = [];
  const totals: number[] = [];
  for (let i = 0; i < teams.length; i++) {
    const done = teams[i];
    const isMine = done.team === mine;
    // className: solo la colonna della tua squadra ha la classe; per le altre
    // undefined, cioè nessun attributo class (come prima)
    let className: string | undefined = undefined;
    if (isMine) {
      className = 'hand-summary__mine';
    }
    headers.push(<th key={`team-${done.team}`} className={className} scope="col">{teamName(view, done.team, isMine)}</th>);
    cardPoints.push(done.card_points);
    singPoints.push(done.sing_points);
    handTotals.push(done.hand_total);
    // il punteggio della partita di quella squadra (0 se manca)
    let total = 0;
    for (let j = 0; j < view.scores.length; j++) {
      if (view.scores[j].team === done.team) {
        total = view.scores[j].total;
      }
    }
    totals.push(total);
  }

  // titleId: lega il titolo alla sezione per i lettori di schermo (aria-labelledby)
  const titleId = `hand-summary-${props.lastHand.hand_number}`;
  let className = 'hand-summary';
  let close: JSX.Element | null = null;
  if (props.onClose !== null) {
    className = 'hand-summary hand-summary--overlay panel';
    close = (
      <button className="btn btn--primary btn--small hand-summary__close" data-hand-summary-close="" type="button" onClick={props.onClose}>
        Ok
      </button>
    );
  }

  return (
    <section className={className} data-hand-summary="" data-hand-number={props.lastHand.hand_number} role="status" aria-labelledby={titleId}>
      <h2 className="hand-summary__title" id={titleId}>{`Mano ${props.lastHand.hand_number} finita`}</h2>
      <table className="hand-summary__table">
        <thead>
          <tr>
            <td></td>
            {headers}
          </tr>
        </thead>
        <tbody>
          <Row label="Carte prese" values={cardPoints} className={undefined} />
          <Row label="Canti" values={singPoints} className={undefined} />
          <Row label="Mano" values={handTotals} className="hand-summary__hand" />
          <Row label="Punteggio" values={totals} className="hand-summary__total" />
        </tbody>
      </table>
      {close}
    </section>
  );
}
