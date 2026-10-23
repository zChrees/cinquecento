/**
 * La carta-modal della modalità (P22, dal prototipo P52): la versione React di
 * app/static/js/components/ModeModal.js, con lo stesso HTML e le stesse classi
 * (stile in css/components/mode-modal.css). La carta-pulsante toccata vola al
 * centro ingrandendosi e si gira; sulla faccia bianca ci sono titolo,
 * descrizione, punti per vincere (150, 300, 500), la scelta tra un giocatore e la
 * CPU, "In breve", "Lo sapevi?" e "Gioca".
 *
 * Con un amico (lotto 7c) al posto di "In breve", della scelta della CPU e di "Lo
 * sapevi?" c'è la lista degli amici online da invitare. Nel 1v1 un invito alla
 * volta; nel 2v2 fino a MAX_INVITES['2v2'] amici (P59), e "Gioca" si accende
 * appena uno ha accettato. Mentre c'è un invito aperto i punti sono fermi, perché
 * gli inviti portano già i punti scelti.
 *
 * Cosa contiene:
 *   <ModeModal kind="veloce" mode="1v1" tile={bottone} ratings={...} online={true}
 *              friends={...} invites={...} inviteNote={...}
 *              onPlay={...} onInvite={...} onDismiss={...} onClosed={...} />
 *   PlayChoice    cosa riceve onPlay: modalità, punti, CPU sì o no
 *   InviteEntry   un invito mandato e ancora aperto (lo tiene la pagina)
 *
 * Il modal non parla con il server: lo fa la pagina (HomePage.tsx).
 * - onPlay({ kind, mode, targetScore, cpu }): "Gioca". `cpu` è true se è scelta
 *   la CPU: "Avversario: CPU" nel 1v1 (P73), "Gioca con: CPU" nel 2v2 (P123).
 *   Il modal si chiude da solo.
 * - onInvite(friend, targetScore): "Invita" (contratto 5.3, invite:send). La pagina
 *   aggiorna invites e inviteNote con le risposte (invite:update).
 * - onDismiss(): il modal si chiude senza "Gioca" (X, Esc, tocco fuori): la pagina
 *   annulla gli inviti aperti (invite:cancel).
 * - onClosed(): il modal ha finito di chiudersi (dopo l'animazione); la pagina lo toglie.
 * - online (P33): senza connessione "Gioca" e "Invita" sono spenti.
 * Si chiude con X, Esc o un tocco fuori dalla carta. Con "riduci movimento"
 * compare e sparisce senza animazione.
 *
 * DA DOVE ARRIVANO I DATI: modalità e carta-pulsante da HomePage.tsx; il rating di
 * "In breve" da GET /api/stats/me e gli amici da GET /api/friends/ (HomePage.tsx); i testi
 * sono scritti qui.
 */

import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import type { ChangeEvent, JSX, MouseEvent, RefObject, SyntheticEvent } from 'react';
import type { Friend, Stats } from '../types/api';
import type { Mode, TargetScore } from '../types/common';
import { reduceMotion } from '../utils/motion';
import { Avatar } from './Avatar';

// TIMING_OPEN_MS e TIMING_CLOSE_MS: quanto durano il volo di apertura e quello di chiusura
const TIMING_OPEN_MS = 820;
const TIMING_CLOSE_MS = 620;

// ModalKind: la sezione della carta-pulsante. La | vuol dire "uno di questi
// valori" (come un enum del C): 'veloce' = Partita Veloce, 'amico' = Gioca con un amico
export type ModalKind = 'veloce' | 'amico';

// InviteEntry: un invito mandato e ancora aperto (la pagina tiene l'elenco)
export interface InviteEntry {
  // l'amico invitato
  friend: Friend;
  // 'pending' = in attesa della risposta, 'accepted' = ha accettato
  status: 'pending' | 'accepted';
  // il codice dell'invito dal server; null finché invite:send non ha risposto
  inviteId: string | null;
}

// MAX_INVITES: gli inviti aperti insieme per modalità (contratto 5.3; nel 2v2 P59:
// con chi invita il tavolo è pieno)
const MAX_INVITES: Record<Mode, number> = { '1v1': 1, '2v2': 3 };

// FRIEND_DESC: la descrizione di "Gioca con un amico" (il 1v1 tra amici non conta
// per il rating; il 2v2 con un amico sì)
const FRIEND_DESC: Record<Mode, string> = {
  '1v1': 'Scegli i punti e invita un amico online: la partita parte appena accetta. Non conta per il rating.',
  '2v2': 'Invita fino a tre amici. Con uno siete in squadra, contro una coppia dalla coda; con più amici, squadre a sorte.',
};

// INVITE_TITLE e INVITE_HINT: il titolo della lista e il suggerimento di partenza
const INVITE_TITLE: Record<Mode, string> = { '1v1': 'Invita un amico da sfidare', '2v2': 'Invita da uno a tre amici' };
export const INVITE_HINT: Record<Mode, string> = {
  '1v1': "Potrai giocare quando l'amico avrà accettato.",
  '2v2': 'Potrai giocare appena un amico avrà accettato.',
};

// InviteLook: l'aspetto di "Invita" in uno stato: icona, testo e etichetta per i
// lettori di schermo (che dipende dal nome)
interface InviteLook {
  icon: string;
  text: string;
  label: (name: string) => string;
}

/** L'etichetta di "Invita" da fermo. */
function idleLabel(name: string): string {
  return `Invita ${name}`;
}

/** L'etichetta di "Invita" con l'invito in attesa. */
function pendingLabel(name: string): string {
  return `Invito a ${name} in attesa`;
}

/** L'etichetta di "Invita" dopo l'accettazione. */
function acceptedLabel(name: string): string {
  return `${name} ha accettato`;
}

// INVITE_LOOKS: i tre aspetti di "Invita" (come setInviteButton di ModeModal.js)
const INVITE_LOOKS: Record<'idle' | 'pending' | 'accepted', InviteLook> = {
  idle: { icon: 'send', text: 'Invita', label: idleLabel },
  pending: { icon: 'progress_activity', text: 'In attesa…', label: pendingLabel },
  accepted: { icon: 'check_circle', text: 'Ha accettato', label: acceptedLabel },
};

/**
 * Il colore dell'avatar con l'iniziale, sempre uguale per lo stesso nome.
 *
 * @param {string} name
 * @returns {number} da 0 a 3 (classe mini-avatar--0 ... --3)
 */
function colorIndex(name: string): number {
  let sum = 0;
  for (let i = 0; i < name.length; i++) {
    sum += name.charCodeAt(i);
  }
  return sum % 4;
}

// Opponent: con chi si gioca nella Partita Veloce: 'player' (la coda) o 'cpu'
type Opponent = 'player' | 'cpu';

// Fact: una riga di "In breve": il nome dell'icona e il testo
interface Fact {
  icon: string;
  text: string;
}

// PlayChoice: cosa riceve onPlay quando si preme "Gioca"
export interface PlayChoice {
  kind: ModalKind;
  mode: Mode;
  // i punti per vincere scelti
  targetScore: TargetScore;
  // true se si gioca contro la CPU (o in coppia con la CPU nel 2v2)
  cpu: boolean;
}

// Ratings: il rating dell'utente in ogni modalità (la parte "ratings" delle statistiche)
type Ratings = Stats['ratings'];

// QUICK_DESC: la descrizione della Partita Veloce per ogni modalità (solo regole e
// decisioni già prese: code separate per punteggio, il rating conta)
const QUICK_DESC: Record<Mode, string> = {
  '1v1': 'Entri in coda e ti troviamo un avversario del tuo livello. Una sfida secca, uno contro uno, carta dopo carta.',
  '2v2': 'Entri in coda da solo: ti troviamo un compagno e una coppia avversaria del vostro livello.',
};

// CPU_DESC e CPU_FACTS: i testi della partita contro la CPU (D43, non conta per il
// rating): 1v1 con "Avversario: CPU" (P73), 2v2 con "Gioca con: CPU", tu e CPU 1
// contro CPU 2 e CPU 3 (P123)
const CPU_DESC: Record<Mode, string> = {
  '1v1': 'Giochi subito contro il computer, senza coda: allenati quanto vuoi.',
  '2v2': 'Giochi subito in coppia con il computer, contro due computer: allenati quanto vuoi.',
};
const CPU_FACTS: Record<Mode, Fact[]> = {
  '1v1': [
    { icon: 'smart_toy', text: 'Parte subito, senza coda' },
    { icon: 'trending_up', text: 'Non conta per il rating' },
    { icon: 'timer', text: '15 secondi per ogni turno' },
  ],
  '2v2': [
    { icon: 'smart_toy', text: 'Parte subito, senza coda' },
    { icon: 'event_seat', text: 'CPU 1, la tua compagna, siede di fronte a te' },
    { icon: 'trending_up', text: 'Non conta per il rating' },
  ],
};

// OPPONENT_WORDS: P123, la scelta si chiama "Avversario" nel 1v1 e "Gioca con" nel 2v2
const OPPONENT_LEGEND: Record<Mode, string> = { '1v1': 'Avversario', '2v2': 'Gioca con' };
const PLAYER_WORD: Record<Mode, string> = { '1v1': 'Giocatore', '2v2': 'Giocatori' };

// TIPS: consigli dal regolamento (docs/REGOLE-GIOCO.md), uno diverso a ogni apertura
const TIPS: string[] = [
  'Il primo canto della mano vale 40 e fa diventare briscola quel seme; i canti dopo valgono 20.',
  'Per cantare servono Re e Cavallo dello stesso seme, nel tuo turno e prima di giocare la carta.',
  "Non c'è obbligo di rispondere al seme: puoi giocare qualsiasi carta.",
  "L'Asso vale 11 punti e il Tre 10: sono i carichi, le carte più forti.",
  'Se il Re o il Cavallo di un seme viene giocato, quel seme non si può più cantare.',
  'A mazzo finito puoi cantare solo se hai ancora almeno 3 carte in mano.',
  "Ogni mano vale 120 punti di carte, più i canti. L'ultima presa non dà punti in più.",
  "All'inizio della mano non c'è briscola: la decide il primo canto.",
];

// TARGETS: i punti per vincere, con la parola sotto
const TARGETS: { value: TargetScore; word: string }[] = [
  { value: 150, word: 'Breve' },
  { value: 300, word: 'Media' },
  { value: 500, word: 'Classica' },
];

// lastTip: il consiglio dell'apertura di prima (variabile del modulo: vale per
// tutta la scheda), così due aperture di fila non mostrano lo stesso
let lastTip = -1;

/**
 * Il consiglio di "Lo sapevi?" per questa apertura.
 *
 * @returns {string}
 *
 * In parole semplici:
 *   pickTip()  →  un consiglio a caso di TIPS, mai lo stesso della volta prima
 */
function pickTip(): string {
  let tip = Math.floor(Math.random() * TIPS.length);
  if (tip === lastTip) {
    tip = (tip + 1) % TIPS.length;
  }
  lastTip = tip;
  return TIPS[tip];
}

/**
 * Il rating da scrivere tra parentesi in "In breve".
 *
 * @param {Ratings | null} ratings il rating di ogni modalità, oppure null se non è arrivato
 * @param {Mode} mode
 * @returns {string} per esempio ' (1540)' o ' (1500, provvisorio)'; '' senza rating
 */
function ratingText(ratings: Ratings | null, mode: Mode): string {
  if (ratings === null) {
    return '';
  }
  const rating = ratings[mode];
  if (rating.provisional) {
    return ` (${rating.value}, provvisorio)`;
  }
  return ` (${rating.value})`;
}

/**
 * Le righe di "In breve" della coda (con "Giocatore" scelto).
 *
 * @param {Mode} mode
 * @param {Ratings | null} ratings
 * @returns {Fact[]}
 */
function quickFacts(mode: Mode, ratings: Ratings | null): Fact[] {
  if (mode === '1v1') {
    return [
      { icon: 'person_search', text: 'Avversario scelto in base al rating' },
      { icon: 'trending_up', text: `Conta per il tuo rating 1v1${ratingText(ratings, '1v1')}` },
      { icon: 'timer', text: '15 secondi per ogni turno' },
    ];
  }
  return [
    { icon: 'handshake', text: 'Compagno e avversari arrivano dalla coda' },
    { icon: 'event_seat', text: 'Il compagno siede di fronte a te' },
    { icon: 'trending_up', text: `Conta per il tuo rating 2v2${ratingText(ratings, '2v2')}` },
  ];
}

/**
 * Una posizione della carta grande durante il volo.
 *
 * @param {number} dx spostamento orizzontale dal centro, in px
 * @param {number} dy spostamento verticale dal centro, in px
 * @param {number} sx rimpicciolimento in larghezza (1 = misura piena)
 * @param {number} sy rimpicciolimento in altezza (diverso da sx solo sul telefono,
 *                    dove la carta grande è più alta del normale)
 * @param {number} turn rotazione in gradi (180 = sul retro, 0 = sulla faccia)
 * @param {string} easing come si muove fino alla posizione successiva
 * @returns {Keyframe}
 */
function frame(dx: number, dy: number, sx: number, sy: number, turn: number, easing: string): Keyframe {
  return { transform: `translate(${dx}px, ${dy}px) scale(${sx}, ${sy}) rotateY(${turn}deg)`, easing: easing };
}

// ModeModalProps: cosa riceve il componente
interface ModeModalProps {
  // la sezione: 'veloce' o 'amico'
  kind: ModalKind;
  // la modalità: '1v1' o '2v2'
  mode: Mode;
  // la carta-pulsante toccata: punto di partenza del volo, colore e retro della carta grande
  tile: HTMLElement;
  // il rating dell'utente, per "In breve"; null finché non arriva
  ratings: Ratings | null;
  // P33: false senza connessione ("Gioca" e "Invita" spenti)
  online: boolean;
  // gli amici (GET /api/friends/): si invitano quelli online. La lista si prende
  // all'apertura e resta quella (come ModeModal.js)
  friends: Friend[];
  // gli inviti mandati e ancora aperti (li tiene la pagina)
  invites: InviteEntry[];
  // il suggerimento sotto la lista; null = quello di partenza (INVITE_HINT)
  inviteNote: string | null;
  // "Gioca": la scelta fatta. In C: void (*onPlay)(struct scelta)
  onPlay: (choice: PlayChoice) => void;
  // "Invita": l'amico e i punti scelti. In C: void (*onInvite)(amico, punti)
  onInvite: (friend: Friend, targetScore: TargetScore) => void;
  // chiusura senza "Gioca": la pagina annulla gli inviti aperti. In C: void (*onDismiss)(void)
  onDismiss: () => void;
  // il modal si è chiuso del tutto. In C: void (*onClosed)(void)
  onClosed: () => void;
}

/**
 * La carta-modal.
 *
 * @param {ModeModalProps} props
 * @returns {JSX.Element}
 *
 * In parole semplici:
 *   <ModeModal kind="veloce" mode="2v2" tile={bottone} ... />
 *   Appena compare apre il <dialog> (showModal) e fa il volo dalla carta-pulsante
 *   al centro; chiudendo fa il volo al contrario e poi chiama props.onClosed.
 *   Il volo si fa con element.animate (le animazioni del browser), sugli elementi
 *   veri della pagina presi con i ref, come in ModeModal.js.
 */
export function ModeModal(props: ModeModalProps): JSX.Element {
  // Gli hook si chiamano sempre in cima al componente, mai dentro un if.
  // I ref: gli elementi veri della pagina, che React mette in .current dopo averli
  // disegnati (null prima). Servono per showModal, le misure e le animazioni.
  const dialogRef: RefObject<HTMLDialogElement | null> = useRef<HTMLDialogElement>(null);
  const flipRef: RefObject<HTMLDivElement | null> = useRef<HTMLDivElement>(null);
  const backRef: RefObject<HTMLDivElement | null> = useRef<HTMLDivElement>(null);
  const bodyRef: RefObject<HTMLDivElement | null> = useRef<HTMLDivElement>(null);
  // busy: true durante un volo (niente doppi clic, niente chiusura a metà)
  const busy: RefObject<boolean> = useRef<boolean>(false);
  // closing: true quando la chiusura è partita (si chiude una volta sola)
  const closing: RefObject<boolean> = useRef<boolean>(false);
  // playedRef: true dopo "Gioca" (letto da closeModal, che parte nello stesso clic,
  // prima che lo stato played sia ridisegnato)
  const playedRef: RefObject<boolean> = useRef<boolean>(false);
  // useState restituisce due cose: il valore attuale e la funzione per cambiarlo,
  // che fa ridisegnare il componente (regole-codice.md, sezione 6).
  // target: i punti scelti (500 all'apertura)
  const [target, setTarget] = useState<TargetScore>(500);
  // opponent: con chi si gioca ('player' all'apertura)
  const [opponent, setOpponent] = useState<Opponent>('player');
  // played: true dopo "Gioca" (il pulsante si spegne: niente doppio clic)
  const [played, setPlayed] = useState<boolean>(false);
  // isClosing: la classe is-closing del <dialog> durante il volo di chiusura
  const [isClosing, setIsClosing] = useState<boolean>(false);
  // tip: il consiglio di questa apertura. useState con una funzione: React la
  // chiama solo al primo disegno, così il consiglio non cambia a ogni disegno
  const [tip] = useState<string>(pickTip);
  // friends: gli amici presi all'apertura (useState tiene il primo valore e non
  // segue i cambi di props.friends: la lista resta quella, come in ModeModal.js)
  const [friends] = useState<Friend[]>(props.friends);

  /**
   * Fa il volo: aprendo dalla carta-pulsante al centro, chiudendo al contrario.
   *
   * @param {boolean} opening true per l'apertura
   * @returns {void}
   *
   * In parole semplici:
   *   flip(true)
   *   Il retro della carta grande è una copia della carta-pulsante alla sua misura
   *   vera, ingrandita fino alla carta grande (così all'inizio è identica
   *   all'originale). A metà la carta è di taglio, già vicina al centro e quasi
   *   grande. Aprendo prima si stacca e gira con calma, poi rallenta arrivando al
   *   centro; chiudendo parte piano e poi accelera verso il suo posto. Con "riduci
   *   movimento" niente volo.
   */
  function flip(opening: boolean): void {
    const dialog = dialogRef.current;
    const flipBox = flipRef.current;
    const back = backRef.current;
    const body = bodyRef.current;
    if (dialog === null || flipBox === null || back === null || body === null) {
      return;
    }
    if (reduceMotion() || typeof flipBox.animate !== 'function') {
      if (!opening) {
        dialog.close();
      }
      return;
    }
    busy.current = true;
    const tile = props.tile;

    // Il retro: la copia della carta-pulsante. Si costruisce a mano (cloneNode,
    // come in ModeModal.js) dentro un <div> che React disegna vuoto: React non
    // tocca figli che non ha messo lui
    const copy = document.createElement('div');
    copy.className = tile.className;
    for (let i = 0; i < tile.childNodes.length; i++) {
      copy.append(tile.childNodes[i].cloneNode(true));
    }
    copy.style.width = `${tile.offsetWidth}px`;
    copy.style.height = `${tile.offsetHeight}px`;
    copy.style.transform = `scale(${dialog.clientWidth / tile.offsetWidth}, ${dialog.clientHeight / tile.offsetHeight})`;
    back.replaceChildren(copy);

    // Partenza: sopra la carta-pulsante, alla sua misura, girata sul retro
    const from = tile.getBoundingClientRect();
    const to = dialog.getBoundingClientRect();
    const dx = from.left + from.width / 2 - (to.left + to.width / 2);
    const dy = from.top + from.height / 2 - (to.top + to.height / 2);
    const sx = tile.offsetWidth / dialog.clientWidth;
    const sy = tile.offsetHeight / dialog.clientHeight;
    const start = frame(dx, dy, sx, sy, 180, 'cubic-bezier(0.45, 0, 0.55, 1)');
    let middleEasing = 'cubic-bezier(0.45, 0, 0.55, 1)';
    if (opening) {
      middleEasing = 'cubic-bezier(0.15, 0.6, 0.3, 1)';
    }
    const middle = frame(dx * 0.35, dy * 0.35, sx + (1 - sx) * 0.72, sy + (1 - sy) * 0.72, 90, middleEasing);
    const center = frame(0, 0, 1, 1, 0, 'cubic-bezier(0.6, 0, 0.9, 0.5)');

    tile.style.visibility = 'hidden';
    setIsClosing(!opening);

    let frames: Keyframe[] = [center, middle, start];
    let duration = TIMING_CLOSE_MS;
    if (opening) {
      frames = [start, middle, center];
      duration = TIMING_OPEN_MS;
    }
    const animation = flipBox.animate(frames, { duration: duration, fill: 'both' });

    // Il contenuto della faccia compare con un attimo di ritardo, quando la carta è quasi girata
    if (opening) {
      for (let i = 0; i < body.children.length; i++) {
        body.children[i].animate(
          [{ opacity: 0, transform: 'translateY(10px)' }, { opacity: 1, transform: 'none' }],
          { duration: 320, delay: TIMING_OPEN_MS * 0.45 + i * 50, easing: 'ease-out', fill: 'backwards' },
        );
      }
    }

    /** Il volo è finito: chiudendo si chiude il <dialog>. */
    function handleFinished(): void {
      if (!opening && dialog !== null) {
        dialog.close();
      }
      animation.cancel();
      busy.current = false;
    }

    animation.finished.then(handleFinished, handleFinished);
  }

  /**
   * Effetto all'apertura: il colore della carta (--tile della carta-pulsante),
   * showModal e il volo. È un "layout effect": parte prima che il browser
   * mostri la pagina, così non si vede per un attimo la carta grande ferma al centro.
   */
  function openModal(): void {
    const dialog = dialogRef.current;
    if (dialog === null || dialog.open) {
      return;
    }
    dialog.style.setProperty('--tile', getComputedStyle(props.tile).getPropertyValue('--tile'));
    dialog.showModal();
    flip(true);
  }

  // []: una volta sola, quando il modal compare
  useLayoutEffect(openModal, []);

  /** Effetto: quando il modal sparisce, la carta-pulsante torna visibile. */
  function showTileAgain(): () => void {
    const tile = props.tile;

    function restore(): void {
      tile.style.visibility = '';
    }

    return restore;
  }

  // [props.tile]: legato alla carta-pulsante di questa apertura
  useEffect(showTileAgain, [props.tile]);

  /**
   * Chiude il modal (X, Esc, tocco fuori, "Gioca"): il volo al contrario, poi close.
   * Senza "Gioca" la pagina annulla gli inviti aperti (onDismiss).
   */
  function closeModal(): void {
    if (busy.current || closing.current) {
      return;
    }
    closing.current = true;
    if (!playedRef.current) {
      props.onDismiss();
    }
    flip(false);
  }

  /** Il <dialog> si è chiuso del tutto (evento "close"): la pagina toglie il modal. */
  function handleClose(): void {
    setIsClosing(false);
    props.tile.style.visibility = '';
    props.onClosed();
  }

  /** Esc: il browser chiuderebbe subito; lo fermiamo per far vedere il ritorno della carta. */
  function handleEscape(event: SyntheticEvent<HTMLDialogElement>): void {
    event.preventDefault();
    closeModal();
  }

  /** Un clic sul <dialog> stesso, fuori dalla carta: chiude. */
  function handleDialogClick(event: MouseEvent<HTMLDialogElement>): void {
    const dialog = dialogRef.current;
    if (dialog === null || event.target !== dialog) {
      return;
    }
    const r = dialog.getBoundingClientRect();
    const inside = event.clientX >= r.left && event.clientX <= r.right
      && event.clientY >= r.top && event.clientY <= r.bottom;
    if (!inside) {
      closeModal();
    }
  }

  /** Una scelta dei punti. */
  function handleTargetChange(event: ChangeEvent<HTMLInputElement>): void {
    for (let i = 0; i < TARGETS.length; i++) {
      if (String(TARGETS[i].value) === event.target.value) {
        setTarget(TARGETS[i].value);
      }
    }
  }

  /** La scelta tra "Giocatore" e "CPU". */
  function handleOpponentChange(event: ChangeEvent<HTMLInputElement>): void {
    if (event.target.value === 'cpu') {
      setOpponent('cpu');
    } else {
      setOpponent('player');
    }
  }

  // quick: Partita Veloce; withFriend: Gioca con un amico
  const quick = props.kind === 'veloce';
  const withFriend = props.kind === 'amico';

  // accepted: c'è almeno un amico che ha accettato; invitesFull: inviti aperti al
  // massimo (gli altri "Invita" sono fermi)
  let accepted = false;
  for (let i = 0; i < props.invites.length; i++) {
    if (props.invites[i].status === 'accepted') {
      accepted = true;
    }
  }
  const invitesFull = props.invites.length >= MAX_INVITES[props.mode];

  // playReady: "Gioca" si potrebbe premere (connessione a parte): con un amico solo
  // dopo che ha accettato
  const playReady = quick || accepted;

  /** "Gioca": manda la scelta alla pagina e chiude. */
  function handlePlay(): void {
    if (playedRef.current || !playReady || !props.online || busy.current || closing.current) {
      return;
    }
    playedRef.current = true;
    setPlayed(true);
    closeModal();
    props.onPlay({ kind: props.kind, mode: props.mode, targetScore: target, cpu: quick && opponent === 'cpu' });
  }

  /**
   * "Invita" su una riga.
   *
   * @param {Friend} friend l'amico della riga
   */
  function handleInvite(friend: Friend): void {
    if (busy.current || closing.current || invitesFull) {
      return;
    }
    for (let i = 0; i < props.invites.length; i++) {
      if (props.invites[i].friend.user_id === friend.user_id) {
        return;
      }
    }
    props.onInvite(friend, target);
  }

  // cpu: true con la CPU scelta (solo nella Partita Veloce); kicker, desc e facts:
  // i testi, decisi con un if prima del return
  const cpu = quick && opponent === 'cpu';
  let kicker = 'Partita Veloce';
  let desc = QUICK_DESC[props.mode];
  let facts: Fact[] = quickFacts(props.mode, props.ratings);
  if (cpu) {
    desc = CPU_DESC[props.mode];
    facts = CPU_FACTS[props.mode];
  }
  if (withFriend) {
    kicker = 'Gioca con un amico';
    desc = FRIEND_DESC[props.mode];
    facts = [];
  }

  // inviteRows: una riga per amico online, oppure "Nessun amico online"
  const inviteRows: JSX.Element[] = [];
  if (withFriend) {
    for (let i = 0; i < friends.length; i++) {
      const friend = friends[i];
      if (friend.presence !== 'online') {
        continue;
      }
      // state: 'idle', 'pending' o 'accepted', dall'invito aperto (se c'è)
      let state: 'idle' | 'pending' | 'accepted' = 'idle';
      for (let j = 0; j < props.invites.length; j++) {
        if (props.invites[j].friend.user_id === friend.user_id) {
          state = props.invites[j].status;
        }
      }
      const look = INVITE_LOOKS[state];

      /** "Invita" di questa riga (una funzione per riga: sa di quale amico è). */
      function handleRowInvite(): void {
        handleInvite(friend);
      }

      // key: l'id dell'amico, unico nella lista
      inviteRows.push(
        <li className="invite__item" data-user-id={friend.user_id} data-state={state} key={friend.user_id}>
          <span className="mini-avatar__wrap" aria-hidden="true">
            <Avatar
              username={friend.username}
              avatar={friend.avatar}
              className={`mini-avatar mini-avatar--${colorIndex(friend.username)}`}
            />
            <span className="mini-avatar__status"></span>
          </span>
          <span className="invite__name">{friend.username}</span>
          <button
            className="invite__btn"
            type="button"
            data-invite-user={friend.user_id}
            data-state={state}
            aria-label={look.label(friend.username)}
            disabled={state !== 'idle' || invitesFull || !props.online}
            onClick={handleRowInvite}
          >
            <span className="icon" aria-hidden="true">{look.icon}</span>
            {look.text}
          </button>
        </li>,
      );
    }
    if (inviteRows.length === 0) {
      inviteRows.push(<li className="invite__empty" key="vuota">Nessun amico online in questo momento.</li>);
    }
  }

  // inviteTitle e inviteHint: i testi della sezione degli amici (vuoti nella Partita Veloce)
  let inviteTitle = '';
  let inviteHint = '';
  if (withFriend) {
    inviteTitle = INVITE_TITLE[props.mode];
    inviteHint = INVITE_HINT[props.mode];
    if (props.inviteNote !== null) {
      inviteHint = props.inviteNote;
    }
  }

  // targetOptions: i tre punti. key: il "nome" con cui React riconosce ogni
  // elemento di un elenco tra un disegno e l'altro (qui il valore, unico)
  const targetOptions: JSX.Element[] = [];
  for (let i = 0; i < TARGETS.length; i++) {
    targetOptions.push(
      <label className="target__option" key={TARGETS[i].value}>
        <input
          type="radio"
          name="target"
          value={TARGETS[i].value}
          checked={target === TARGETS[i].value}
          disabled={props.invites.length > 0}
          onChange={handleTargetChange}
        />
        <span><b>{TARGETS[i].value}</b><small>{TARGETS[i].word}</small></span>
      </label>,
    );
  }

  // factItems: le righe di "In breve" (key: il nome dell'icona, diverso in ogni riga)
  const factItems: JSX.Element[] = [];
  for (let i = 0; i < facts.length; i++) {
    factItems.push(
      <li key={facts[i].icon}>
        <span className="icon" aria-hidden="true">{facts[i].icon}</span>
        <span>{facts[i].text}</span>
      </li>,
    );
  }

  // dialogClass: con la classe is-closing durante il volo di chiusura
  let dialogClass = 'mode-modal';
  if (isClosing) {
    dialogClass = 'mode-modal is-closing';
  }

  return (
    <dialog
      className={dialogClass}
      id="mode-modal"
      aria-labelledby="mode-title"
      data-mode-modal=""
      data-opponent={opponent}
      data-kind={props.kind}
      ref={dialogRef}
      onCancel={handleEscape}
      onClose={handleClose}
      onClick={handleDialogClick}
    >
      <div className="mode-modal__flip" ref={flipRef}>
        <div className="mode-modal__back" aria-hidden="true" ref={backRef}></div>
        <div className="mode-modal__face">
          <button className="icon-btn mode-modal__close" type="button" aria-label="Chiudi" onClick={closeModal}>
            <span className="icon" aria-hidden="true">close</span>
          </button>
          <div className="mode-modal__body" ref={bodyRef}>
            <div className="mode-modal__head">
              <p className="mode-modal__kicker">{kicker}</p>
              <h2 className="mode-modal__title" id="mode-title">{props.mode}</h2>
            </div>
            <p className="mode-modal__desc" data-modal-desc="">{desc}</p>
            <fieldset className="target">
              <legend className="target__legend">Punti per vincere</legend>
              <div className="target__options">{targetOptions}</div>
              <p className="target__note" aria-live="polite" hidden={cpu || withFriend}>{`Incontri solo chi ha scelto ${target} punti.`}</p>
            </fieldset>
            <fieldset className="target opponent" data-opponent="" hidden={withFriend}>
              <legend className="target__legend">{OPPONENT_LEGEND[props.mode]}</legend>
              <div className="target__options">
                <label className="target__option">
                  <input type="radio" name="opponent" value="player" checked={!cpu} onChange={handleOpponentChange} />
                  <span className="opponent__choice">
                    <span className="icon" aria-hidden="true">person</span>
                    <b data-opponent-word="player">{PLAYER_WORD[props.mode]}</b>
                  </span>
                </label>
                <label className="target__option">
                  <input type="radio" name="opponent" value="cpu" checked={cpu} onChange={handleOpponentChange} />
                  <span className="opponent__choice">
                    <span className="icon" aria-hidden="true">smart_toy</span>
                    <b data-opponent-word="cpu">CPU</b>
                  </span>
                </label>
              </div>
            </fieldset>
            <section className="mode-modal__facts" aria-labelledby="facts-title" hidden={withFriend}>
              <h3 className="mode-modal__section-title" id="facts-title">In breve</h3>
              <ul className="facts">{factItems}</ul>
            </section>
            {/* Gli amici da invitare: solo con un amico (nella Partita Veloce è nascosta, come in ModeModal.js) */}
            <section className="invite" hidden={quick}>
              <h3 className="invite__title">{inviteTitle}</h3>
              <ul className="invite__list" data-invite-list="">{inviteRows}</ul>
              <p className="invite__hint" aria-live="polite" data-invite-hint="">{inviteHint}</p>
            </section>
            <aside className="mode-modal__tip" hidden={withFriend}>
              <span className="icon" aria-hidden="true">lightbulb</span>
              <p><strong>Lo sapevi?</strong> <span>{tip}</span></p>
            </aside>
            <button
              className="btn btn--primary btn--big"
              type="button"
              data-play=""
              disabled={played || !playReady || !props.online}
              onClick={handlePlay}
            >
              <span className="icon" aria-hidden="true">play_arrow</span>
              Gioca
            </button>
          </div>
        </div>
      </div>
    </dialog>
  );
}
