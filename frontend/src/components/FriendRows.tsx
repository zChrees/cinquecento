/**
 * Il contenuto della lista del pannello amici (P46, passo 5b della migrazione):
 * richieste ricevute, amici divisi per stato, richieste mandate, bloccati. È la
 * versione React di renderList() e delle funzioni per le righe di
 * app/static/js/components/FriendsPanel.js, con lo stesso HTML, le stesse classi e
 * gli stessi data-* (stile in css/components/friends-panel.css).
 *
 * Cosa contiene:
 *   <FriendsBody overview={...} loadError="" busy={[...]} handlers={...} />
 *   e i pezzi che usa: MiniAvatar, Row, Group e una riga per tipo
 *   (RequestInRow, FriendRow, RequestOutRow, BlockedGroup)
 *
 * Questi componenti disegnano soltanto: le azioni (accetta, rifiuta, chatta, …)
 * le decide FriendsPanel.tsx, che le passa in handlers. Tutti i testi degli utenti
 * entrano come testo, mai come HTML (React li mette sempre come testo).
 *
 * DA DOVE ARRIVANO I DATI: overview è la risposta di GET /friends/ (contratto 2.2),
 * chiesta da FriendsPanel.tsx.
 */

import type { JSX } from 'react';
import type { Friend, FriendRequest, FriendsList, Presence } from '../types/api';
import type { UserRef } from '../types/common';
import { Avatar } from './Avatar';

// PRESENCE_LABEL: la scritta sotto il nome di un amico, per ogni stato.
// Record<Presence, string>: un testo per ogni valore di Presence (se ne manca uno,
// TypeScript lo segnala)
const PRESENCE_LABEL: Record<Presence, string> = {
  online: 'Online',
  in_game: 'In partita',
  offline: 'Offline',
};

// GROUPS: i tre gruppi di amici, nell'ordine in cui compaiono, con il titolo
const GROUPS: { presence: Presence; title: string }[] = [
  { presence: 'online', title: 'Online' },
  { presence: 'in_game', title: 'In partita' },
  { presence: 'offline', title: 'Offline' },
];

// FriendsHandlers: le azioni dei pulsanti della lista, decise da FriendsPanel.tsx.
// Ogni campo è una funzione: in C sarebbe un puntatore a funzione, per esempio
// void (*onAccept)(struct richiesta)
export interface FriendsHandlers {
  // "Accetta" e "Rifiuta" di una richiesta ricevuta
  onAccept: (request: FriendRequest) => void;
  onDecline: (request: FriendRequest) => void;
  // "Chatta" e "Altro" (rimuovi, blocca) di un amico
  onChat: (friend: Friend) => void;
  onMore: (friend: Friend) => void;
  // "Annulla" di una richiesta mandata
  onCancel: (request: FriendRequest) => void;
  // "Sblocca" di un utente bloccato
  onUnblock: (user: UserRef) => void;
  // "Riprova" quando la lista non è arrivata
  onRetry: () => void;
}

/**
 * Il numero del colore dell'iniziale (da 0 a 3), uguale per lo stesso nome.
 *
 * @param {string} name per esempio 'Giulia'
 * @returns {number}
 *
 * In parole semplici:
 *   colorIndex('Giulia')  →  la somma dei codici delle lettere, resto della divisione per 4
 *   (come colorIndex() di FriendsPanel.js: lo stesso nome ha sempre lo stesso colore).
 */
function colorIndex(name: string): number {
  let sum = 0;
  for (let i = 0; i < name.length; i++) {
    sum = sum + name.charCodeAt(i);
  }
  return sum % 4;
}

// MiniAvatarProps: cosa riceve l'avatar piccolo
interface MiniAvatarProps {
  // l'utente (nome e codice dell'avatar)
  user: UserRef;
  // il pallino dello stato (solo per gli amici), oppure null per nessun pallino
  presence: Presence | null;
}

/**
 * L'avatar piccolo di una riga, con il pallino dello stato.
 *
 * In parole semplici:
 *   <MiniAvatar user={amico} presence="online" />
 *   →  <span class="mini-avatar__wrap"><span class="mini-avatar mini-avatar--2">G</span>
 *      <span class="mini-avatar__status mini-avatar__status--online"></span></span>
 */
function MiniAvatar(props: MiniAvatarProps): JSX.Element {
  let status: JSX.Element | null = null;
  if (props.presence !== null) {
    status = <span className={`mini-avatar__status mini-avatar__status--${props.presence}`}></span>;
  }
  return (
    <span className="mini-avatar__wrap" aria-hidden="true">
      <Avatar
        username={props.user.username}
        avatar={props.user.avatar}
        className={`mini-avatar mini-avatar--${colorIndex(props.user.username)}`}
      />
      {status}
    </span>
  );
}

// RowProps: cosa riceve una riga della lista
interface RowProps {
  // l'utente della riga
  user: UserRef;
  // la scritta sotto il nome, per esempio 'Online' o 'In attesa di risposta'
  status: string;
  // il pallino dello stato (solo per gli amici), oppure null
  presence: Presence | null;
  // la classe in più della riga, per esempio 'friend--offline', oppure ''
  modifier: string;
  // un pezzo tra il nome e i pulsanti (il numero dei messaggi non letti), oppure null
  extra: JSX.Element | null;
  // i pulsanti della riga
  actions: JSX.Element[];
}

/**
 * Una riga della lista: avatar, nome, stato, pulsanti.
 *
 * In parole semplici:
 *   <Row user={...} status="Online" ... />
 *   →  <li class="friend" data-user-id="31"> avatar, nome e stato, pulsanti </li>
 */
function Row(props: RowProps): JSX.Element {
  let className = 'friend';
  if (props.modifier !== '') {
    className = `friend ${props.modifier}`;
  }
  return (
    <li className={className} data-user-id={props.user.user_id}>
      <MiniAvatar user={props.user} presence={props.presence} />
      <span className="friend__text">
        <span className="friend__name">{props.user.username}</span>
        <span className="friend__status">{props.status}</span>
      </span>
      {props.extra}
      <span className="friend__actions">{props.actions}</span>
    </li>
  );
}

// GroupKind: quale gruppo è, per scegliere il suo data-* (lo usano i test):
// 'requests-in' (richieste ricevute), 'requests-out' (mandate), oppure uno stato
// degli amici ('online', 'in_game', 'offline'). La | vuol dire "uno di questi valori".
type GroupKind = 'requests-in' | 'requests-out' | Presence;

// GroupProps: cosa riceve un gruppo della lista
interface GroupProps {
  // quale gruppo è
  kind: GroupKind;
  // il titolo, per esempio 'Online (3)'
  title: string;
  // le righe del gruppo
  items: JSX.Element[];
}

/**
 * Un gruppo della lista, con il titolo; senza righe non si disegna.
 *
 * In parole semplici:
 *   <Group kind="online" title="Online (3)" items={...} />
 *   →  <section class="friends-group" data-friends-group="online"><h3>…</h3><ul>…</ul></section>
 *   Le richieste hanno data-requests-in o data-requests-out al posto di data-friends-group.
 */
function Group(props: GroupProps): JSX.Element | null {
  if (props.items.length === 0) {
    return null;
  }
  const title = <h3 className="friends-group__title">{props.title}</h3>;
  const list = <ul className="friends-list">{props.items}</ul>;
  if (props.kind === 'requests-in') {
    return <section className="friends-group" data-requests-in="">{title}{list}</section>;
  }
  if (props.kind === 'requests-out') {
    return <section className="friends-group" data-requests-out="">{title}{list}</section>;
  }
  return <section className="friends-group" data-friends-group={props.kind}>{title}{list}</section>;
}

// Le props delle righe: la richiesta, l'amico o l'utente della riga, se i suoi
// pulsanti sono spenti (azione in corso) e le azioni
interface RequestRowProps {
  request: FriendRequest;
  busy: boolean;
  handlers: FriendsHandlers;
}

interface FriendRowProps {
  friend: Friend;
  busy: boolean;
  handlers: FriendsHandlers;
}

interface BlockedRowProps {
  user: UserRef;
  busy: boolean;
  handlers: FriendsHandlers;
}

/**
 * Una richiesta ricevuta: "Vuole essere tuo amico", con Accetta e Rifiuta.
 */
function RequestInRow(props: RequestRowProps): JSX.Element {
  const name = props.request.username;

  /** Clic su Accetta. */
  function handleAccept(): void {
    props.handlers.onAccept(props.request);
  }

  /** Clic su Rifiuta. */
  function handleDecline(): void {
    props.handlers.onDecline(props.request);
  }

  // actions: i pulsanti della riga (con sola icona: l'etichetta è aria-label).
  // key: il "nome" con cui React riconosce lo stesso pulsante tra un disegno e l'altro
  const actions: JSX.Element[] = [
    <button
      key="accept"
      className="icon-btn icon-btn--ok"
      type="button"
      aria-label={`Accetta la richiesta di ${name}`}
      data-accept={props.request.user_id}
      disabled={props.busy}
      onClick={handleAccept}
    >
      <span className="icon" aria-hidden="true">check</span>
    </button>,
    <button
      key="decline"
      className="icon-btn icon-btn--no"
      type="button"
      aria-label={`Rifiuta la richiesta di ${name}`}
      data-decline={props.request.user_id}
      disabled={props.busy}
      onClick={handleDecline}
    >
      <span className="icon" aria-hidden="true">close</span>
    </button>,
  ];
  return <Row user={props.request} status="Vuole essere tuo amico" presence={null} modifier="" extra={null} actions={actions} />;
}

/**
 * Un amico: lo stato, i messaggi non letti, Chatta e Altro.
 */
function FriendRow(props: FriendRowProps): JSX.Element {
  const name = props.friend.username;

  /** Clic su Chatta. */
  function handleChat(): void {
    props.handlers.onChat(props.friend);
  }

  /** Clic su Altro (rimuovi, blocca). */
  function handleMore(): void {
    props.handlers.onMore(props.friend);
  }

  // unread: il numero dei messaggi non letti, solo se ce ne sono
  let unread: JSX.Element | null = null;
  if (props.friend.unread > 0) {
    let words = ' messaggi non letti';
    if (props.friend.unread === 1) {
      words = ' messaggio non letto';
    }
    unread = (
      <span className="friend__unread" data-unread={props.friend.unread}>
        {String(props.friend.unread)}
        <span className="visually-hidden">{words}</span>
      </span>
    );
  }

  let modifier = '';
  if (props.friend.presence === 'offline') {
    modifier = 'friend--offline';
  }

  const actions: JSX.Element[] = [
    <button
      key="chat"
      className="icon-btn"
      type="button"
      aria-label={`Chatta con ${name}`}
      data-chat-open={props.friend.user_id}
      disabled={props.busy}
      onClick={handleChat}
    >
      <span className="icon" aria-hidden="true">chat</span>
    </button>,
    <button
      key="more"
      className="icon-btn"
      type="button"
      aria-label={`Altre azioni per ${name}`}
      data-friend-more={props.friend.user_id}
      disabled={props.busy}
      onClick={handleMore}
    >
      <span className="icon" aria-hidden="true">more_vert</span>
    </button>,
  ];
  return (
    <Row
      user={props.friend}
      status={PRESENCE_LABEL[props.friend.presence]}
      presence={props.friend.presence}
      modifier={modifier}
      extra={unread}
      actions={actions}
    />
  );
}

/**
 * Una richiesta mandata: "In attesa di risposta", con Annulla.
 */
function RequestOutRow(props: RequestRowProps): JSX.Element {
  /** Clic su Annulla. */
  function handleCancel(): void {
    props.handlers.onCancel(props.request);
  }

  const actions: JSX.Element[] = [
    <button
      key="cancel"
      className="btn btn--ghost"
      type="button"
      aria-label={`Annulla la richiesta a ${props.request.username}`}
      data-cancel-request={props.request.user_id}
      disabled={props.busy}
      onClick={handleCancel}
    >
      Annulla
    </button>,
  ];
  return <Row user={props.request} status="In attesa di risposta" presence={null} modifier="" extra={null} actions={actions} />;
}

/**
 * Un utente bloccato: "Bloccato", con Sblocca.
 */
function BlockedRow(props: BlockedRowProps): JSX.Element {
  /** Clic su Sblocca. */
  function handleUnblock(): void {
    props.handlers.onUnblock(props.user);
  }

  const actions: JSX.Element[] = [
    <button
      key="unblock"
      className="btn btn--ghost"
      type="button"
      aria-label={`Sblocca ${props.user.username}`}
      data-unblock={props.user.user_id}
      disabled={props.busy}
      onClick={handleUnblock}
    >
      Sblocca
    </button>,
  ];
  return <Row user={props.user} status="Bloccato" presence={null} modifier="" extra={null} actions={actions} />;
}

// FriendsBodyProps: cosa riceve il contenuto della lista
interface FriendsBodyProps {
  // l'ultima risposta di GET /friends/, oppure null se non è ancora arrivata (o è fallita)
  overview: FriendsList | null;
  // il messaggio d'errore dell'ultima lettura, oppure '' (allora "Caricamento…")
  loadError: string;
  // gli user_id delle righe con un'azione in corso: i loro pulsanti sono spenti
  busy: number[];
  // le azioni dei pulsanti
  handlers: FriendsHandlers;
}

/**
 * Il contenuto della lista (dentro <div data-friends-body>).
 *
 * @param {FriendsBodyProps} props
 * @returns {JSX.Element}
 *
 * In parole semplici:
 *   <FriendsBody overview={overview} loadError="" busy={[]} handlers={handlers} />
 *   Senza lista: "Caricamento…", oppure l'errore con "Riprova". Con la lista, in
 *   ordine: richieste ricevute, amici online, in partita, offline (o "Non hai
 *   ancora amici"), richieste mandate, bloccati. Un gruppo vuoto non si disegna.
 */
export function FriendsBody(props: FriendsBodyProps): JSX.Element {
  if (props.overview === null) {
    return <FriendsMessage loadError={props.loadError} onRetry={props.handlers.onRetry} />;
  }
  const overview: FriendsList = props.overview;

  // sections: i pezzi della lista, nell'ordine in cui compaiono.
  // key: il "nome" con cui React riconosce lo stesso pezzo tra un disegno e l'altro
  // (qui il nome del gruppo, o lo user_id per le righe), così non lo ricrea.
  const sections: JSX.Element[] = [];

  // Richieste ricevute
  const requestsIn: JSX.Element[] = [];
  for (let i = 0; i < overview.requests_in.length; i++) {
    const request = overview.requests_in[i];
    requestsIn.push(
      <RequestInRow key={request.user_id} request={request} busy={isBusy(props.busy, request.user_id)} handlers={props.handlers} />,
    );
  }
  sections.push(<Group key="in" kind="requests-in" title="Richieste di amicizia" items={requestsIn} />);

  // Amici: un gruppo per stato, nell'ordine di GROUPS, con quanti sono nel titolo
  for (let g = 0; g < GROUPS.length; g++) {
    const items: JSX.Element[] = [];
    for (let i = 0; i < overview.friends.length; i++) {
      const friend = overview.friends[i];
      if (friend.presence === GROUPS[g].presence) {
        items.push(<FriendRow key={friend.user_id} friend={friend} busy={isBusy(props.busy, friend.user_id)} handlers={props.handlers} />);
      }
    }
    sections.push(
      <Group key={GROUPS[g].presence} kind={GROUPS[g].presence} title={`${GROUPS[g].title} (${items.length})`} items={items} />,
    );
  }
  if (overview.friends.length === 0) {
    sections.push(<p key="no-friends" className="friends-empty">Non hai ancora amici: cerca uno username qui sopra.</p>);
  }

  // Richieste mandate
  const requestsOut: JSX.Element[] = [];
  for (let i = 0; i < overview.requests_out.length; i++) {
    const request = overview.requests_out[i];
    requestsOut.push(
      <RequestOutRow key={request.user_id} request={request} busy={isBusy(props.busy, request.user_id)} handlers={props.handlers} />,
    );
  }
  sections.push(<Group key="out" kind="requests-out" title="Richieste mandate" items={requestsOut} />);

  // Bloccati
  if (overview.blocked.length > 0) {
    sections.push(<BlockedGroup key="blocked" blocked={overview.blocked} busy={props.busy} handlers={props.handlers} />);
  }

  // <> ... </>: un contenitore che non diventa un elemento della pagina
  return <>{sections}</>;
}

/**
 * Dice se la riga di un utente ha un'azione in corso.
 *
 * In parole semplici:
 *   isBusy([31, 44], 31)  →  true
 */
function isBusy(busy: number[], userId: number): boolean {
  for (let i = 0; i < busy.length; i++) {
    if (busy[i] === userId) {
      return true;
    }
  }
  return false;
}

// BlockedGroupProps: cosa riceve il gruppo dei bloccati
interface BlockedGroupProps {
  blocked: UserRef[];
  busy: number[];
  handlers: FriendsHandlers;
}

/**
 * Il gruppo dei bloccati, chiuso all'inizio (si apre toccando il titolo).
 *
 * In parole semplici:
 *   <BlockedGroup blocked={...} ... />
 *   →  <details class="friends-group friends-group--blocked" data-blocked>
 *        <summary>Bloccati (2)</summary><ul>…</ul></details>
 *   Aperto o chiuso lo ricorda il browser (l'attributo open del <details>): React
 *   non lo tocca, quindi resta aperto anche quando la lista si rilegge.
 */
function BlockedGroup(props: BlockedGroupProps): JSX.Element {
  const items: JSX.Element[] = [];
  for (let i = 0; i < props.blocked.length; i++) {
    const user = props.blocked[i];
    items.push(<BlockedRow key={user.user_id} user={user} busy={isBusy(props.busy, user.user_id)} handlers={props.handlers} />);
  }
  return (
    <details className="friends-group friends-group--blocked" data-blocked="">
      <summary className="friends-group__title">
        <span className="icon" aria-hidden="true">chevron_right</span>
        {`Bloccati (${props.blocked.length})`}
      </summary>
      <ul className="friends-list">{items}</ul>
    </details>
  );
}

// FriendsMessageProps: cosa riceve il messaggio al posto della lista
interface FriendsMessageProps {
  // l'errore dell'ultima lettura, oppure '' (allora "Caricamento…" e niente "Riprova")
  loadError: string;
  // la funzione di "Riprova"
  onRetry: () => void;
}

/**
 * Il messaggio al posto della lista: "Caricamento…", oppure l'errore con "Riprova".
 */
function FriendsMessage(props: FriendsMessageProps): JSX.Element {
  let text = 'Caricamento…';
  let retry: JSX.Element | null = null;
  if (props.loadError !== '') {
    text = props.loadError;
    retry = (
      <button className="btn btn--ghost btn--small" type="button" onClick={props.onRetry}>
        <span className="icon" aria-hidden="true">refresh</span>Riprova
      </button>
    );
  }
  return (
    <div className="friends-message" data-friends-message="">
      <p>{text}</p>
      {retry}
    </div>
  );
}
