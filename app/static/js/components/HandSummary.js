/**
 * Riepilogo di fine mano (P57), dal campo last_hand della vista (contratto 3.3):
 * per ogni squadra i punti delle carte prese (nascosti durante la mano, decisione
 * di P8), dei canti e il totale della mano; sotto, il punteggio della partita.
 * La tua squadra è sempre la prima colonna. Nel 1v1 le squadre hanno il nome dei
 * giocatori ("Tu" e l'avversario), nel 2v2 sono "Noi" e "Loro", come nel punteggio.
 *
 * Si usa in due posti: sopra il centro del tavolo a inizio della mano nuova (con
 * il pulsante "Ok"), e dentro il riquadro di fine partita (senza "Ok").
 * Stile in css/components/hand-summary.css.
 */

import { el } from '../utils/dom.js';

/** Nome della squadra, come in Scoreboard.js. */
function teamName(view, team, mine) {
  if (view.mode === '2v2') return mine ? 'Noi' : 'Loro';
  if (mine) return 'Tu';
  return view.players.find((player) => player.team === team)?.username ?? 'Avversario';
}

function row(label, values, className = '') {
  return el('tr', { class: className }, [
    el('th', { text: label, attrs: { scope: 'row' } }),
    ...values.map((value) => el('td', { text: value })),
  ]);
}

/**
 * @param {object} view la vista di gioco (serve per i nomi e il punteggio)
 * @param {object} lastHand il campo last_hand ({hand_number, teams: [...]})
 * @param {object} [options]
 * @param {function} [options.onClose] se c'è, il riquadro ha il pulsante "Ok"
 * @returns {HTMLElement}
 */
export function HandSummary(view, lastHand, { onClose = null } = {}) {
  const myTeam = view.players.find((player) => player.seat === view.you.seat).team;
  const teams = [...lastHand.teams].sort((a, b) => (a.team === myTeam ? -1 : b.team === myTeam ? 1 : 0));
  const totals = teams.map((done) => view.scores.find((score) => score.team === done.team)?.total ?? 0);
  const titleId = `hand-summary-${lastHand.hand_number}`;

  const table = el('table', { class: 'hand-summary__table' }, [
    el('thead', {}, el('tr', {}, [
      el('td'),
      ...teams.map((done) => el('th', {
        class: done.team === myTeam ? 'hand-summary__mine' : '',
        text: teamName(view, done.team, done.team === myTeam),
        attrs: { scope: 'col' },
      })),
    ])),
    el('tbody', {}, [
      row('Carte prese', teams.map((done) => done.card_points)),
      row('Canti', teams.map((done) => done.sing_points)),
      row('Mano', teams.map((done) => done.hand_total), 'hand-summary__hand'),
      row('Punteggio', totals, 'hand-summary__total'),
    ]),
  ]);

  return el('section', {
    class: `hand-summary${onClose ? ' hand-summary--overlay panel' : ''}`,
    data: { handSummary: '', handNumber: lastHand.hand_number },
    attrs: { role: 'status', 'aria-labelledby': titleId },
  }, [
    el('h2', { class: 'hand-summary__title', text: `Mano ${lastHand.hand_number} finita`, attrs: { id: titleId } }),
    table,
    onClose
      ? el('button', {
        class: 'btn btn--primary btn--small hand-summary__close',
        text: 'Ok',
        data: { handSummaryClose: '' },
        attrs: { type: 'button' },
        on: { click: onClose },
      })
      : null,
  ]);
}
