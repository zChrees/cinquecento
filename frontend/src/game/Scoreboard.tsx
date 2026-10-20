/**
 * Il punteggio in alto al tavolo React (P21): i punti delle mani già finite per la
 * tua squadra e per l'altra, il punteggio per vincere e il numero della mano. È la
 * versione React di app/static/js/components/Scoreboard.js, con lo stesso HTML
 * (stile in css/components/scoreboard.css).
 *
 * Cosa contiene:
 *   teamName(view, 1, false)   'Loro' nel 2v2, il nome dell'avversario nel 1v1
 *   <Scoreboard view={view} />
 *
 * Nel 1v1 le squadre hanno il nome dei giocatori ("Tu" e l'avversario), nel 2v2
 * sono "Noi" e "Loro". La tua squadra è sempre la prima.
 *
 * DA DOVE ARRIVANO I DATI: dalla vista del server (scores, target_score,
 * hand_number, rated); Table.tsx passa la vista intera.
 */

import type { JSX } from 'react';
import type { Team } from '../types/common';
import type { GameView, TeamTotal } from '../types/view';

/**
 * Il nome di una squadra, come in Scoreboard.js e HandSummary.js.
 *
 * @param {GameView} view la vista
 * @param {Team} team la squadra, 0 o 1
 * @param {boolean} mine true se è la tua squadra
 * @returns {string} 'Noi', 'Loro', 'Tu', oppure il nome dell'avversario
 *
 * In parole semplici:
 *   teamName(view, 1, false)
 *   Nel 2v2 'Noi' o 'Loro'. Nel 1v1 'Tu' per la tua squadra, altrimenti il nome
 *   del giocatore di quella squadra ('Avversario' se non c'è). La usano anche
 *   HandSummary.tsx e il riquadro di fine partita.
 */
export function teamName(view: GameView, team: Team, mine: boolean): string {
  if (view.mode === '2v2') {
    if (mine) {
      return 'Noi';
    }
    return 'Loro';
  }
  if (mine) {
    return 'Tu';
  }
  for (let i = 0; i < view.players.length; i++) {
    if (view.players[i].team === team) {
      return view.players[i].username;
    }
  }
  return 'Avversario';
}

/**
 * La tua squadra nella vista.
 *
 * @param {GameView} view la vista
 * @returns {Team} 0 oppure 1
 *
 * In parole semplici:
 *   myTeam(view)   → la squadra del giocatore che sta al tuo posto (view.you.seat)
 */
export function myTeam(view: GameView): Team {
  for (let i = 0; i < view.players.length; i++) {
    if (view.players[i].seat === view.you.seat) {
      return view.players[i].team;
    }
  }
  throw new Error('Il tuo posto non è nella vista.');
}

/**
 * Mette per prima la tua squadra.
 *
 * @param {T[]} list un elenco con un campo team, per esempio view.scores
 * @param {Team} mine la tua squadra
 * @returns {T[]} un elenco nuovo, con la tua squadra per prima
 *
 * In parole semplici:
 *   mineFirst([{ team: 1, total: 20 }, { team: 0, total: 30 }], 0)
 *   → [{ team: 0, total: 30 }, { team: 1, total: 20 }]
 *   <T extends { team: Team }> vuol dire "qualunque oggetto che abbia un campo
 *   team": la usa anche HandSummary.tsx con i suoi oggetti.
 */
export function mineFirst<T extends { team: Team }>(list: T[], mine: Team): T[] {
  const ordered: T[] = [];
  for (let i = 0; i < list.length; i++) {
    if (list[i].team === mine) {
      ordered.push(list[i]);
    }
  }
  for (let i = 0; i < list.length; i++) {
    if (list[i].team !== mine) {
      ordered.push(list[i]);
    }
  }
  return ordered;
}

// ScoreboardProps: cosa riceve il punteggio
interface ScoreboardProps {
  // la vista di gioco
  view: GameView;
}

/**
 * Il punteggio.
 *
 * @param {ScoreboardProps} props
 * @returns {JSX.Element}
 *
 * In parole semplici:
 *   <Scoreboard view={view} />
 *   Disegna <div class="scoreboard" data-scoreboard> con le due squadre separate
 *   da un trattino e sotto "a 300 · mano 1" (più "amichevole" se la partita non
 *   conta per il rating). Lo usa Table.tsx, nell'angolo in alto a destra.
 */
export function Scoreboard(props: ScoreboardProps): JSX.Element {
  const view = props.view;
  const mine = myTeam(view);
  const ordered: TeamTotal[] = mineFirst(view.scores, mine);

  // teams: le due squadre; la `key` (il "nome" con cui React riconosce lo stesso
  // elemento tra un disegno e l'altro) è il numero della squadra
  const teams: JSX.Element[] = [];
  for (let i = 0; i < ordered.length; i++) {
    const score = ordered[i];
    const isMine = score.team === mine;
    let className = 'score';
    if (isMine) {
      className = 'score score--mine';
    }
    teams.push(
      <div key={`team-${score.team}`} className={className} data-team={score.team}>
        <span className="score__name">{teamName(view, score.team, isMine)}</span>
        <span className="score__total">{score.total}</span>
      </div>,
    );
  }

  // info: per esempio "a 300 · mano 1 · amichevole"
  const info: string[] = [`a ${view.target_score}`, `mano ${view.hand_number}`];
  if (!view.rated) {
    info.push('amichevole');
  }
  return (
    <div className="scoreboard" data-scoreboard="" aria-label="Punteggio">
      <div className="scoreboard__teams">
        {teams[0]}
        <span className="scoreboard__sep" aria-hidden="true">–</span>
        {teams[1]}
      </div>
      <p className="scoreboard__info">{info.join(' · ')}</p>
    </div>
  );
}
