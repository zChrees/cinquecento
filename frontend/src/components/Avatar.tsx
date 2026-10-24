/**
 * Avatar di un utente (P43): l'immagine del set o, per chi non ne ha scelto uno,
 * l'iniziale del nome (stile in css/components/navbar.css, che vale per tutti gli
 * avatar).
 *
 * Cosa contiene:
 *   <Avatar username="Giulia" avatar="re_coppe" className="avatar" />
 *
 * Come la macro, non controlla l'elenco dei codici: il server salva solo codici
 * validi (app/services/avatars.py, P17), quindi basta sapere se c'è. (SeatAvatar.tsx,
 * al tavolo, invece lo controlla, perché lo usa anche con i dati finti di app/static/dev/.)
 * L'avatar è decorativo (aria-hidden): accanto c'è sempre il nome.
 *
 * DA DOVE ARRIVANO I DATI: da chi lo usa, per esempio la navbar con l'utente
 * della sessione (useSession).
 */

import type { JSX } from 'react';

// AvatarProps: cosa riceve il componente
interface AvatarProps {
  // il nome, per l'iniziale, per esempio 'Giulia'
  username: string;
  // il codice dell'avatar, per esempio 're_coppe', oppure null (allora l'iniziale)
  avatar: string | null;
  // le classi, per esempio 'avatar' o 'avatar avatar--big'
  className: string;
}

/**
 * L'avatar.
 *
 * @param {AvatarProps} props
 * @returns {JSX.Element}
 *
 * In parole semplici:
 *   <Avatar ... />
 *   Con un codice: <span class="avatar avatar--img"><img src="/static/img/avatars/re_coppe.svg"></span>.
 *   Senza: <span class="avatar">G</span>, l'iniziale maiuscola.
 */
export function Avatar(props: AvatarProps): JSX.Element {
  if (props.avatar === null || props.avatar === '') {
    return <span className={props.className} aria-hidden="true">{props.username.charAt(0).toUpperCase()}</span>;
  }
  return (
    <span className={`${props.className} avatar--img`} data-avatar={props.avatar} aria-hidden="true">
      <img
        className="avatar__img"
        src={`/static/img/avatars/${props.avatar}.svg`}
        alt=""
        draggable={false}
        decoding="sync"
      />
    </span>
  );
}
