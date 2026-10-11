/**
 * Avviso "Hai una partita in corso" con "Rientra" (P22; contratto 5.1,
 * home:status: resume = { game_id, url, mode, target_score } oppure null).
 * Sta nello spazio di "giocatori online" (home.css, .home__status), alto quanto
 * quella riga: tutto l'avviso è il collegamento al tavolo, "Rientra" è la pillola
 * dentro. Le carte-pulsante restano attive: se l'utente prova a giocare, risponde
 * il server.
 *
 *   slot.replaceChildren(ResumeBanner(resume));
 *
 * Il collegamento porta solo a una pagina del tavolo di questo sito (/game/...):
 * un indirizzo diverso non si mostra.
 */

import { el, icon } from '../utils/dom.js';

const GAME_URL = /^\/game\/[A-Za-z0-9_-]{1,64}$/;

/**
 * @param {object} resume  { game_id, url, mode, target_score }
 * @returns {HTMLElement|null}  null se l'indirizzo non è quello di un tavolo
 */
export function ResumeBanner(resume) {
  if (!resume || typeof resume.url !== 'string' || !GAME_URL.test(resume.url)) return null;
  return el('div', { class: 'resume', attrs: { role: 'status' }, data: { resume: resume.game_id } }, [
    el('a', {
      class: 'resume__link felt-text',
      attrs: { href: resume.url },
      data: { resumeLink: '' },
    }, [
      icon('playing_cards', 'resume__icon'),
      el('span', { class: 'resume__text' }, [
        el('strong', { text: 'Hai una partita in corso' }),
        el('span', { class: 'resume__detail', text: `${resume.mode} a ${resume.target_score} punti` }),
      ]),
      el('span', { class: 'resume__btn' }, [icon('login'), 'Rientra']),
    ]),
  ]);
}
