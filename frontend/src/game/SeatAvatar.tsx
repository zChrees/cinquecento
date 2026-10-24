/**
 * L'avatar di un giocatore al tavolo React (P43, P73): l'immagine del set,
 * l'iniziale del nome o il robot della CPU (stile in
 * css/components/navbar.css, che vale per tutti gli avatar).
 *
 * Cosa contiene:
 *   AVATAR_CODES                      i codici degli avatar del set
 *   <SeatAvatar player={player} />    l'avatar di un posto
 *
 * A differenza di components/Avatar.tsx (navbar, amici: il server salva solo
 * codici validi), al tavolo un codice fuori elenco mostra l'iniziale:
 * i giocatori arrivano anche dalle viste finte di app/static/dev/, dove
 * Giulia ha 'cavallo_spade', che non c'è. Per questo qui c'è una copia dell'elenco
 * (scelta del 20/10/2026, passo 8a): l'altra è in app/services/avatars.py;
 * tests/frontend/test_avatar.py controlla che siano uguali. Un codice nuovo va
 * aggiunto in tutti e due i posti.
 *
 * DA DOVE ARRIVANO I DATI: dal giocatore nella vista (players[i]: username,
 * avatar, cpu); lo passa Table.tsx.
 */

import type { JSX } from 'react';
import type { PlayerView } from '../types/view';

// AVATAR_CODES: i codici del set, nello stesso ordine di app/services/avatars.py.
// "readonly" vuol dire che l'elenco non si può cambiare mentre il programma gira
export const AVATAR_CODES: readonly string[] = [
  'coppe', 'denari', 'spade', 'bastoni',
  're_coppe', 're_denari', 're_spade', 're_bastoni',
  'cavallo_coppe', 'cavallo_bastoni', 'fante_denari', 'fante_spade',
];

/**
 * Dice se un codice è del set.
 *
 * @param {string | null} code il codice, per esempio 're_coppe', oppure null
 * @returns {boolean}
 *
 * In parole semplici:
 *   knownAvatar('re_coppe')        → true
 *   knownAvatar('cavallo_spade')   → false (non è del set: si mostra l'iniziale)
 *   knownAvatar(null)              → false
 */
export function knownAvatar(code: string | null): boolean {
  if (code === null) {
    return false;
  }
  for (let i = 0; i < AVATAR_CODES.length; i++) {
    if (AVATAR_CODES[i] === code) {
      return true;
    }
  }
  return false;
}

// SeatAvatarProps: cosa riceve l'avatar
interface SeatAvatarProps {
  // il giocatore, dalla vista: servono username, avatar e cpu
  player: PlayerView;
}

/**
 * L'avatar di un posto.
 *
 * @param {SeatAvatarProps} props
 * @returns {JSX.Element}
 *
 * In parole semplici:
 *   <SeatAvatar player={view.players[1]} />
 *   La CPU: <span class="avatar avatar--cpu" data-cpu> con l'icona del robot.
 *   Un codice del set: <span class="avatar avatar--img" data-avatar="denari"> con
 *   l'immagine. Altrimenti l'iniziale maiuscola del nome. Sempre aria-hidden:
 *   accanto c'è il nome.
 */
export function SeatAvatar(props: SeatAvatarProps): JSX.Element {
  const player = props.player;
  if (player.cpu) {
    return (
      <span className="avatar avatar--cpu" data-cpu="" aria-hidden="true">
        <span className="icon" aria-hidden="true">smart_toy</span>
      </span>
    );
  }
  if (!knownAvatar(player.avatar)) {
    return <span className="avatar" aria-hidden="true">{player.username.charAt(0).toUpperCase()}</span>;
  }
  // decoding="sync": il tavolo si ridisegna spesso, e un'immagine decodificata dopo
  // si vedrebbe vuota per un attimo (P70)
  return (
    <span className="avatar avatar--img" data-avatar={player.avatar} aria-hidden="true">
      <img className="avatar__img" src={`/static/img/avatars/${player.avatar}.svg`} alt="" draggable={false} decoding="sync" />
    </span>
  );
}
