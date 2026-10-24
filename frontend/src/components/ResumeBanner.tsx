/**
 * L'avviso "Hai una partita in corso" con "Rientra" (P22; stile in
 * css/pages/home.css, .resume).
 *
 * Sta nello spazio di "giocatori online" (.home__status), alto quanto quella riga:
 * tutto l'avviso è il collegamento al tavolo, "Rientra" è la pillola dentro. Le
 * carte-pulsante restano attive: se l'utente prova a giocare, risponde il server.
 *
 * Cosa contiene:
 *   <ResumeBanner resume={status.resume} />
 *   validResume(resume)   true se l'indirizzo è quello di un tavolo di questo sito
 *
 * DA DOVE ARRIVANO I DATI: resume di home:status (contratto 5.1), che la home
 * riceve dal server (oppure dai dati finti con ?demo=rientro).
 */

import type { JSX } from 'react';
import { Link } from 'react-router';
import type { Resume } from '../types/events';

// GAME_URL: la forma dell'indirizzo di un tavolo, per esempio /game/a1b2c3d4.
// Un indirizzo diverso non si mostra: il collegamento porta solo a questo sito.
const GAME_URL = /^\/game\/[A-Za-z0-9_-]{1,64}$/;

// ResumeBannerProps: cosa riceve il componente
interface ResumeBannerProps {
  // la partita in corso: { game_id, url, mode, target_score }; da home:status
  resume: Resume;
}

/**
 * Dice se l'avviso si può mostrare.
 *
 * @param {Resume | null} resume la partita in corso, oppure null
 * @returns {boolean}
 *
 * In parole semplici:
 *   validResume({ url: '/game/a1b2c3d4', ... })  →  true
 *   validResume({ url: 'https://altro.sito/', ... })  →  false
 *   validResume(null)  →  false
 *   La home lo chiede prima di disegnare l'avviso, perché quando c'è l'avviso
 *   "giocatori online" si nasconde (stanno nello stesso spazio).
 */
export function validResume(resume: Resume | null): boolean {
  if (resume === null) {
    return false;
  }
  if (typeof resume.url !== 'string') {
    return false;
  }
  return GAME_URL.test(resume.url);
}

/**
 * L'avviso.
 *
 * @param {ResumeBannerProps} props
 * @returns {JSX.Element}
 *
 * In parole semplici:
 *   <ResumeBanner resume={resume} />
 *   →  "Hai una partita in corso · 1v1 a 500 punti · Rientra", un collegamento al
 *   tavolo (props.resume.url). Chi lo usa controlla prima validResume.
 *   Il collegamento è un <Link> di React Router: nella pagina è lo
 *   stesso <a href>, ma toccandolo si va al tavolo senza ricaricare (il tavolo è
 *   una pagina della SPA, e il collegamento al tempo reale resta aperto).
 */
export function ResumeBanner(props: ResumeBannerProps): JSX.Element {
  // detail: la riga piccola, per esempio "1v1 a 500 punti"
  const detail = `${props.resume.mode} a ${props.resume.target_score} punti`;

  return (
    <div className="resume" role="status" data-resume={props.resume.game_id}>
      {/* discover="none": senza, React Router aggiunge l'attributo data-discover, che
          qui non serve */}
      <Link className="resume__link felt-text" to={props.resume.url} data-resume-link="" discover="none">
        <span className="icon resume__icon" aria-hidden="true">playing_cards</span>
        <span className="resume__text">
          <strong>Hai una partita in corso</strong>
          <span className="resume__detail">{detail}</span>
        </span>
        <span className="resume__btn">
          <span className="icon" aria-hidden="true">login</span>
          Rientra
        </span>
      </Link>
    </div>
  );
}
