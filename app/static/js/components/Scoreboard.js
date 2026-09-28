/**
 * Punteggio in alto al tavolo (P21): i punti delle mani già finite per la tua
 * squadra e per l'altra (scores della vista), il punteggio per vincere e il numero
 * della mano. Nel 1v1 le squadre hanno il nome dei giocatori ("Tu" e l'avversario),
 * nel 2v2 sono "Noi" e "Loro". Stile in css/components/scoreboard.css.
 */

import { el } from '../utils/dom.js';

function teamName(view, team, mine) {
  if (view.mode === '2v2') return mine ? 'Noi' : 'Loro';
  if (mine) return 'Tu';
  return view.players.find((player) => player.team === team)?.username ?? 'Avversario';
}

/**
 * @param {object} view la vista di gioco (contratto 3.3)
 * @returns {HTMLElement}
 */
export function Scoreboard(view) {
  const myTeam = view.players.find((player) => player.seat === view.you.seat).team;
  const ordered = [...view.scores].sort((a, b) => (a.team === myTeam ? -1 : b.team === myTeam ? 1 : 0));
  const teams = ordered.map((score) =>
    el('div', { class: `score${score.team === myTeam ? ' score--mine' : ''}`, data: { team: score.team } }, [
      el('span', { class: 'score__name', text: teamName(view, score.team, score.team === myTeam) }),
      el('span', { class: 'score__total', text: score.total }),
    ]),
  );
  const info = [`a ${view.target_score}`, `mano ${view.hand_number}`];
  if (!view.rated) info.push('amichevole');
  return el('div', { class: 'scoreboard', data: { scoreboard: '' }, attrs: { 'aria-label': 'Punteggio' } }, [
    el('div', { class: 'scoreboard__teams' }, [teams[0], el('span', { class: 'scoreboard__sep', text: '–', attrs: { 'aria-hidden': 'true' } }), teams[1]]),
    el('p', { class: 'scoreboard__info', text: info.join(' · ') }),
  ]);
}
