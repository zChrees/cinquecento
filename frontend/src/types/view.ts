/**
 * La vista di gioco: quello che il server manda con game:state a ogni giocatore
 * (docs/CONTRATTO-SOCKET.md, 3.3). Esempi completi: app/static/dev/vista_1v1.json
 * e vista_2v2.json (li controlla tests/frontend/test_tipi.py).
 *
 * Cosa contiene:
 *   GameView                 la vista: GameView1v1 oppure GameView2v2
 *   PlayerView, TrickPlay,   i pezzi della vista (giocatori, presa, canti, punti,
 *   Trick, LastTrick, ...    turno, mosse legali, risultato)
 *
 * DA DOVE ARRIVANO I DATI: app/game/engine/views.py costruisce la vista del
 * motore, app/realtime/room.py (view_for) aggiunge i campi della stanza
 * (game_id, version, rated, giocatori, tempi) e la manda con game:state.
 * La vista contiene solo quello che quel giocatore può vedere: mai le carte
 * degli altri (unica eccezione: partner_hand, nel 2v2).
 */

import type { Card, Suit } from './card';
import type { Mode, Team, TargetScore } from './common';

// PlayerRating: il rating di un giocatore nella modalità della partita (P88),
// letto quando la partita comincia e poi fermo
export interface PlayerRating {
  // il valore arrotondato, per esempio 1540
  value: number;
  // true per le prime 10 partite che contano (D9)
  provisional: boolean;
}

// PlayerView: un posto al tavolo, come lo vede chi riceve la vista
export interface PlayerView {
  // il posto, da 0, nell'ordine di gioco (contratto 3.1)
  seat: number;
  // la squadra del posto
  team: Team;
  // il numero dell'utente; 0 per tutte le CPU (D49)
  user_id: number;
  // il nome, per esempio 'Mario', 'CPU' o 'CPU 2'
  username: string;
  // il codice dell'avatar oppure null (iniziale del nome; per la CPU il robot)
  avatar: string | null;
  // il rating oppure null (sempre null per la CPU)
  rating: PlayerRating | null;
  // true solo per la CPU (P68)
  cpu: boolean;
  // quante carte ha in mano: solo il numero, mai le carte
  cards_in_hand: number;
  // se è collegato adesso (la CPU sempre)
  connected: boolean;
  // i secondi che restano per rientrare (o per arrivare al tavolo, P138) se è
  // scollegato, per esempio 48.0; null se è collegato
  reconnect_seconds_left: number | null;
}

// TrickPlay: una carta giocata in una presa, con chi l'ha giocata
export interface TrickPlay {
  // il posto di chi l'ha giocata
  seat: number;
  // la carta
  card: Card;
}

// Trick: la presa in corso
export interface Trick {
  // il posto di chi l'ha aperta
  leader_seat: number;
  // le carte giocate finora, nell'ordine in cui sono state giocate
  cards: TrickPlay[];
  // il posto della carta che vincerebbe la presa se finisse adesso (P75);
  // null quando sul tavolo non c'è nessuna carta
  winning_seat: number | null;
}

// LastTrick: una presa chiusa
export interface LastTrick {
  // chi l'ha presa
  winner_seat: number;
  // le carte, nell'ordine in cui sono state giocate
  cards: TrickPlay[];
}

// Sing: un canto (cantare 40 o cantare 20)
export interface Sing {
  // chi ha cantato
  seat: number;
  // il seme cantato
  suit: Suit;
  // 40 (il primo canto della mano, fissa la briscola) oppure 20
  points: 40 | 20;
}

// TeamTotal: i punti di una squadra (in scores e hand_points)
export interface TeamTotal {
  // la squadra
  team: Team;
  // i punti, per esempio 110
  total: number;
}

// HandTeamResult: il riepilogo di una mano finita, per una squadra
export interface HandTeamResult {
  // la squadra
  team: Team;
  // i punti delle carte prese
  card_points: number;
  // i punti dei canti
  sing_points: number;
  // il totale della mano (carte più canti)
  hand_total: number;
}

// SeatCards: le carte che restavano a un posto quando qualcuno ha calato
export interface SeatCards {
  // il posto
  seat: number;
  // le sue carte, ora scoperte per tutti
  cards: Card[];
}

// LaidDown: le carte calate (P84, "Cala le carte")
export interface LaidDown {
  // chi ha calato
  seat: number;
  // le carte che restavano a ogni posto, compresi gli avversari
  hands: SeatCards[];
  // i canti da 20 aggiunti dal server per il compagno (già contati in sing_points)
  sings: Sing[];
}

// LastHand: il riepilogo dell'ultima mano finita
export interface LastHand {
  // il numero di quella mano
  hand_number: number;
  // i punti di ogni squadra
  teams: HandTeamResult[];
  // la presa che ha chiuso la mano (P58: la mano nuova parte con last_trick a null)
  last_trick: LastTrick;
  // null se la mano è finita giocando; le carte calate se qualcuno ha calato
  laid_down: LaidDown | null;
}

// Turn: di chi è il turno e quanto tempo gli resta
export interface Turn {
  // il posto di chi deve giocare
  seat: number;
  // la durata del turno in secondi (15, P94)
  seconds_total: number;
  // i secondi che restano adesso, per esempio 12.5; durante le pause del tavolo
  // resta uguale a seconds_total. La pagina conta alla rovescia da sola.
  seconds_left: number;
}

// Legal: le tue mosse ammesse adesso, decise dal server (la pagina non calcola regole)
export interface Legal {
  // le carte che puoi giocare; vuota quando non è il tuo turno
  play: Card[];
  // i semi che puoi cantare; vuota quando non è il tuo turno
  sing: Suit[];
  // true se adesso puoi calare le carte (P84)
  lay_down: boolean;
}

// Advice: il consiglio del compagno (P92, solo nel 2v2)
export interface Advice {
  // chi ha dato il consiglio
  seat: number;
  // la carta consigliata, una della tua mano
  card: Card;
}

// GameResult: come è finita la partita
export interface GameResult {
  // 'score' (qualcuno è arrivato ai punti) oppure 'abandon' (qualcuno è uscito)
  reason: 'score' | 'abandon';
  // la squadra che ha vinto, oppure null per il pareggio
  winner_team: Team | null;
  // i posti di chi ha abbandonato (vuoto se la partita è finita ai punti)
  abandoned_seats: number[];
  // i punti finali di ogni squadra
  scores: TeamTotal[];
}

// GameViewBase: i campi che ci sono in tutte e due le modalità
export interface GameViewBase {
  // il codice della stanza, per esempio 'e5f6a7b8' (non è il numero nel database)
  game_id: string;
  // il numero della vista: sale a ogni cambiamento; le mosse lo rimandano al
  // server, che rifiuta quelle fatte su una vista vecchia (stale_state)
  version: number;
  // modalità; GameView1v1 e GameView2v2 qui sotto la fissano a un solo valore
  mode: Mode;
  // i punti per vincere
  target_score: TargetScore;
  // false quando la partita non conta per il rating: 1v1 contro un amico (D36),
  // 2v2 tra quattro amici, partite contro la CPU
  rated: boolean;
  // se si sta giocando o se è finita
  status: 'playing' | 'finished';
  // il numero della mano, da 1
  hand_number: number;
  // il posto del mazziere
  dealer_seat: number;
  // il tuo posto
  you: { seat: number };
  // tutti i posti, nell'ordine
  players: PlayerView[];
  // le tue carte
  hand: Card[];
  // la presa in corso
  trick: Trick;
  // l'ultima presa chiusa; null a inizio mano
  last_trick: LastTrick | null;
  // il seme di briscola; null finché nessuno ha cantato 40
  trump: Suit | null;
  // le carte rimaste nel mazzo
  deck_count: number;
  // i canti della mano in corso, in ordine
  sings: Sing[];
  // i punti delle mani già finite, per squadra
  scores: TeamTotal[];
  // i punti della mano in corso, per squadra (P67)
  hand_points: TeamTotal[];
  // il riepilogo dell'ultima mano finita; null nella prima mano
  last_hand: LastHand | null;
  // il turno; null a partita finita
  turn: Turn | null;
  // le tue mosse ammesse
  legal: Legal;
  // null durante la partita; com'è finita, a partita finita
  result: GameResult | null;
}

// GameView1v1: la vista del 1v1. "extends" vuol dire "tutti i campi di
// GameViewBase, più questi": qui mode può essere solo '1v1', e i campi del
// 2v2 (partner_hand, advice) non ci sono proprio.
export interface GameView1v1 extends GameViewBase {
  mode: '1v1';
}

// GameView2v2: la vista del 2v2, con i due campi in più
export interface GameView2v2 extends GameViewBase {
  mode: '2v2';
  // le carte del compagno, quando ci sono insieme la briscola e il mazzo finito
  // (D46); altrimenti null
  partner_hand: Card[] | null;
  // il consiglio che ti ha dato il compagno, oppure null
  advice: Advice | null;
}

// GameView: la vista che arriva con game:state, una delle due. Per leggere
// partner_hand bisogna prima controllare view.mode === '2v2': dopo quel
// controllo TypeScript sa che la vista è una GameView2v2.
export type GameView = GameView1v1 | GameView2v2;
