/**
 * Mano del giocatore (P20): le carte in fila dritta, affiancate, grandi quanto
 * permette lo schermo (a 360 px cinque carte stanno in una riga).
 *
 * Le mosse ammesse le decide il server (legal.play nella vista, contratto 3.3):
 * la mano rende giocabili solo quelle, le altre restano visibili ma spente.
 *
 * Questo file non disegna niente da solo: ogni funzione costruisce degli elementi
 * HTML (come document.createElement) e li restituisce; è la pagina (game.js) che
 * li mette sul tavolo. Le funzioni sono tre (Hand, EdgeHand e RevealedHand):
 *
 *   Hand(view.hand, { playable: view.legal.play, onPlay: function (card) { ... } })
 *   Hand(cards)                      // sola lettura (es. pagina di prova)
 *   EdgeHand(3, 'top', drawn, dealt) // P70: carte coperte di un avversario, dal bordo
 *   RevealedHand(cards, 'top', seat) // P85: le carte di un altro giocatore scoperte, dentro il tavolo
 *   Hand(view.hand, { ..., advice: { card, name } }) // P93: la carta consigliata dal compagno, segnata
 *
 * Una carta, qui, è un oggetto come { suit: 'coppe', rank: 10 }: è l'equivalente
 * di una struct del C con due campi.
 *
 * DA DOVE ARRIVANO I DATI (la catena delle chiamate):
 *
 *   1. il server manda la "vista" della partita con l'evento game:state
 *      (un oggetto con le tue carte, quelle giocabili, i giocatori, ...);
 *   2. game.js la riceve e chiama render(vista), che chiama
 *      Table(vista, ...) di components/Table.js;
 *   3. Table.js chiama le funzioni di questo file, passando pezzi della vista:
 *      Hand per le tue carte, EdgeHand o RevealedHand per quelle degli altri.
 *
 * Stile in css/components/hand.css.
 */

// hasValue sta in utils/dom.js (D52): dice se un valore non è né null né undefined.
import { el, hasValue } from '../utils/dom.js';
import { Card, CardBack, cardName, sameCard } from './Card.js';

/**
 * Le carte della tua mano, scoperte.
 *
 * @param {Array<{suit: string, rank: number}>} cards carte in mano, nell'ordine del server
 * @param {object} [options] impostazioni facoltative (si può non passare niente):
 * @param {Array<{suit: string, rank: number}>} [options.playable] carte giocabili (solo con onPlay)
 * @param {function} [options.onPlay] chiamata con la carta toccata
 * @param {object} [options.drawn] P70: carta ("coppe-10") → millisecondi da quando è stata pescata
 * @param {object} [options.dealt] P70: carta ("coppe-10") → millisecondi da quando è partita nella distribuzione
 * @param {object|null} [options.advice] P93: { card, name }, la carta che ti ha consigliato il compagno
 * @returns {HTMLElement}
 *
 * In parole semplici:
 *   Hand(cards, options)
 *   Costruisce la tua mano: un <div> con dentro una carta per ogni elemento di cards.
 *
 *   cards:   l'elenco delle tue carte, ognuna { suit: 'coppe', rank: 10 }.
 *            Arriva da Table.js, che passa view.hand (le tue carte nella vista
 *            mandata dal server).
 *   options: facoltativo. È un oggetto con dentro alcune impostazioni, tutte
 *            facoltative; serve a non avere una funzione con sette parametri in fila.
 *            Arriva da Table.js, che lo costruisce con i dati della vista e di game.js:
 *     playable - le carte che puoi giocare adesso (view.legal.play, deciso dal server)
 *     onPlay   - la funzione da chiamare quando tocchi una carta: è onPlay di
 *                game.js, che manda la carta al server. In C sarebbe un puntatore
 *                a funzione, void (*onPlay)(struct carta)
 *     drawn    - le carte che hai appena pescato, ognuna con da quanti
 *                millisecondi è partita l'animazione (calcolato da game.js)
 *     dealt    - come drawn, ma per le carte distribuite a inizio mano
 *     advice   - la carta che ti consiglia il compagno nel 2v2, con il suo nome,
 *                oppure null se non c'è nessun consiglio
 *
 *   Esempio di cosa può contenere options durante una partita:
 *     {
 *       playable: [{ suit: 'coppe', rank: 1 }, { suit: 'spade', rank: 3 }],
 *       onPlay:   onPlay,                    (la funzione di game.js)
 *       drawn:    { 'denari-7': 120 },       (pescata 120 ms fa: sta ancora volando)
 *       dealt:    {},                        (nessuna distribuzione in corso)
 *       advice:   { card: { suit: 'spade', rank: 3 }, name: 'Giuseppe' }
 *     }
 *   Quando invece si guardano le carte calate, Table.js chiama Hand(cards) senza
 *   options: le carte si vedono ma non si possono toccare.
 *
 *   Restituisce: il <div> della mano, che Table.js mette in fondo al tavolo.
 */
export function Hand(cards, options) {
  // Se options non è stato passato, si usa un oggetto vuoto: così le righe sotto
  // possono leggere options.playable ecc. senza errori (leggere un campo di
  // undefined in JavaScript fa fermare il programma, come dereferenziare NULL in C).
  if (!hasValue(options)) {
    options = {};
  }

  // Le impostazioni non passate prendono un valore predefinito: niente carte
  // giocabili, niente gestore del tocco, niente animazioni, niente consiglio.
  // playable: array di carte, per esempio [{ suit: 'coppe', rank: 1 }]
  let playable = [];
  if (options.playable !== undefined) {
    playable = options.playable;
  }
  // onPlay: una funzione (onPlay di game.js) oppure null = carte non toccabili
  let onPlay = null;
  if (options.onPlay !== undefined) {
    onPlay = options.onPlay;
  }
  // drawn: oggetto "codice carta → millisecondi", per esempio { 'denari-7': 120 }
  let drawn = {};
  if (options.drawn !== undefined) {
    drawn = options.drawn;
  }
  // dealt: stessa forma di drawn, per la distribuzione
  let dealt = {};
  if (options.dealt !== undefined) {
    dealt = options.dealt;
  }
  // advice: { card: { suit, rank }, name: 'Giuseppe' } oppure null
  let advice = null;
  if (options.advice !== undefined) {
    advice = options.advice;
  }

  // items: l'array degli elementi HTML delle carte, uno per carta, nello stesso
  // ordine di cards. Alla fine diventano i figli del <div> della mano.
  const items = [];
  for (let i = 0; i < cards.length; i++) {
    // card: la carta numero i, per esempio { suit: 'coppe', rank: 10 }
    const card = cards[i];

    // item: l'elemento HTML di questa carta (un pulsante con l'immagine), creato
    // da Card() di Card.js. La carta si può toccare solo se la pagina ha passato
    // onPlay; in quel caso è accesa se è tra quelle giocabili, altrimenti si vede
    // ma è spenta.
    let item;
    if (onPlay) {
      // Si cerca la carta nell'elenco delle giocabili, come una ricerca lineare
      // in un array del C. sameCard confronta seme e valore.
      let isPlayable = false;
      for (let j = 0; j < playable.length; j++) {
        if (sameCard(playable[j], card)) {
          isPlayable = true;
          break;
        }
      }
      item = Card(card, { onPlay: onPlay, playable: isPlayable });
    } else {
      item = Card(card, {});
    }

    // P93: la carta consigliata dal compagno ha il bordo e l'etichetta "consiglio di …".
    // classList è l'elenco delle classi CSS dell'elemento; dataset sono i suoi
    // attributi data-* (qui data-advice), che usano i test per trovarla.
    if (advice && sameCard(advice.card, card)) {
      item.classList.add('card--advice');
      item.dataset.advice = '';
      // L'etichetta per i lettori di schermo diventa, per esempio,
      // "3 di spade, consigliata da Giuseppe".
      item.setAttribute('aria-label', `${item.getAttribute('aria-label')}, consigliata da ${advice.name}`);
      // label: la scritta "consiglio di Giuseppe" che si vede sopra la carta
      const label = el('span', {
        class: 'card__advice',
        text: `consiglio di ${advice.name}`,
        attrs: { 'aria-hidden': 'true' },
      });
      item.append(label);
    }

    // P70: la carta appena pescata, o distribuita a inizio mano, vola dal mazzo nella
    // mano. dealt e drawn dicono da quanti millisecondi è partita (negativo = parte
    // tra poco, e fino ad allora non si vede). Se la carta è in tutti e due vale dealt.
    // key: il codice della carta, per esempio 'coppe-10', che è la chiave usata
    // dentro drawn e dealt.
    const key = `${card.suit}-${card.rank}`;
    const wasDealt = hasValue(dealt[key]);
    const wasDrawn = hasValue(drawn[key]);
    // animationDelay negativo = l'animazione parte "già avanzata" di quei
    // millisecondi: così se la mano si ridisegna a metà volo, la carta non riparte
    // da capo.
    if (wasDealt) {
      item.classList.add('card--dealt-mine');
      item.dataset.dealt = '';
      item.style.animationDelay = `${Math.round(-dealt[key])}ms`;
    } else if (wasDrawn) {
      item.classList.add('card--drawn-mine');
      item.dataset.drawn = '';
      item.style.animationDelay = `${Math.round(-drawn[key])}ms`;
    }

    items.push(item);
  }

  // Il contenitore di tutte le carte. role e aria-label servono ai lettori di
  // schermo (chi non vede la pagina sente "Le tue carte"). data-count dice ai
  // test quante carte ci sono.
  return el('div', {
    class: 'hand',
    data: { hand: '', count: cards.length },
    attrs: { role: 'group', 'aria-label': 'Le tue carte' },
  }, items);
}

/**
 * Carte coperte di un avversario al tavolo (P70): un ventaglio agganciato al bordo
 * dello schermo dal suo lato ('top', 'left' o 'right'), per metà fuori, aperto verso
 * il centro del tavolo. Il ventaglio si disegna "in piedi" e il CSS lo gira verso
 * il suo lato; l'angolo di ogni carta dipende dalla sua posizione (--i) e da quante
 * sono (--n).
 *
 * P70, pescata: con `drawn` (millisecondi da quando ha pescato; negativo = pesca tra
 * poco) l'ultima carta arriva dal centro del tavolo e le altre si allargano per farle
 * posto, partendo dal ventaglio di prima (--n-before). Il tempo diventa un ritardo
 * dell'animazione, così un ridisegno a metà non la fa ripartire.
 *
 * @param {number} count carte in mano (cards_in_hand)
 * @param {string} side 'top' | 'left' | 'right'
 * @param {number|null} [drawn] millisecondi dalla pescata, o null
 * @param {Array<number>|null} [dealt] P70, distribuzione: per ogni carta i millisecondi
 *   da quando è partita dal mazzo (negativi: parte tra poco e fino ad allora non si vede)
 * @returns {HTMLElement}
 *
 * In parole semplici:
 *   EdgeHand(count, side, drawn, dealt)
 *   Costruisce il ventaglio di carte coperte di un avversario, sul bordo dello schermo.
 *
 *   count: quante carte ha in mano. Arriva da Table.js, che passa
 *          player.cards_in_hand (il server non manda le carte degli altri, solo
 *          quante sono).
 *   side:  da che lato dello schermo sta: 'top' (in alto, l'avversario di fronte),
 *          'left' o 'right' (a sinistra o a destra, nel 2v2). Lo decide Table.js
 *          dalla posizione del giocatore al tavolo.
 *   drawn: facoltativo. Un numero: da quanti millisecondi ha pescato, per far volare
 *          l'ultima carta dal mazzo. null se non sta pescando. Lo calcola game.js
 *          (moments.drawnSeats) e lo passa Table.js.
 *   dealt: facoltativo. Un array di numeri, uno per carta: da quanti millisecondi
 *          ogni carta è partita nella distribuzione, per esempio [300, 150, -50]
 *          (l'ultima parte tra 50 ms). null se non si sta distribuendo. Lo calcola
 *          dealMoments di game.js (deal.seats) e lo passa Table.js.
 *
 *   Restituisce: il <div> del ventaglio.
 */
export function EdgeHand(count, side, drawn, dealt) {
  // Gli ultimi due parametri sono facoltativi: se chi chiama non li passa valgono
  // undefined, e qui li trasformiamo in null, cioè "nessuna animazione".
  if (drawn === undefined) {
    drawn = null;
  }
  if (dealt === undefined) {
    dealt = null;
  }

  // items: un dorso per ogni carta. --i è una variabile CSS: il foglio di stile la
  // legge per calcolare l'angolo della carta nel ventaglio (la carta 0 è la prima
  // a sinistra).
  const items = [];
  for (let i = 0; i < count; i++) {
    // back: l'elemento HTML del dorso, creato da CardBack di Card.js
    const back = CardBack();
    back.style.setProperty('--i', i);

    if (dealt && hasValue(dealt[i])) {
      // Distribuzione: ogni carta vola dal mazzo con il suo ritardo (dealt[i]).
      back.classList.add('card--dealt');
      back.style.animationDelay = `${Math.round(-dealt[i])}ms`;
    } else if (hasValue(drawn)) {
      // Pescata: l'ultima carta (indice count - 1) arriva, le altre si spostano
      // per farle posto. Tutte con lo stesso ritardo (drawn).
      if (i === count - 1) {
        back.classList.add('card--drawn');
      } else {
        back.classList.add('card--making-room');
      }
      back.style.animationDelay = `${Math.round(-drawn)}ms`;
    }

    items.push(back);
  }

  // data: gli attributi data-* del ventaglio, per esempio
  // { edgeHand: 'top', count: 5, drawing: '' } diventa
  // data-edge-hand="top" data-count="5" data-drawing="".
  // data-drawing e data-dealing ci sono solo durante la pescata e la distribuzione.
  const data = { edgeHand: side, count: count };
  if (hasValue(drawn)) {
    data.drawing = '';
  }
  if (dealt) {
    data.dealing = '';
  }

  // hand: il <div> del ventaglio, con dentro i dorsi
  const hand = el('div', {
    class: `edge-hand edge-hand--${side}`,
    data: data,
    attrs: { role: 'group', 'aria-label': `${count} carte coperte` },
  }, items);

  // Quante carte ci sono ora (--n) e quante ce n'erano prima della pescata
  // (--n-before, almeno 1): il CSS le usa per calcolare quanto aprire il ventaglio.
  hand.style.setProperty('--n', count);
  hand.style.setProperty('--n-before', Math.max(count - 1, 1));
  return hand;
}

/**
 * Le carte di un altro giocatore scoperte (P85, carte calate): il suo ventaglio entra
 * dal bordo nel tavolo finché le carte si vedono intere e dritte, anche quello in
 * alto (non capovolto), un po' più aperto del ventaglio coperto. Copre per un momento
 * nome e avatar di quel giocatore. Stile in css/components/table.css.
 *
 * P93: le carte del compagno (partner_hand) usano lo stesso ventaglio, un po' più
 * grande e con le carte che si toccano per consigliargli quale giocare (`advise`).
 * P123: con la CPU compagna (`advise.onPick` null) lo stesso ventaglio, ma le carte
 * non si toccano: la CPU non riceve consigli (D49).
 *
 * @param {Array<{suit: string, rank: number}>} cards le sue carte
 * @param {string} side 'top' | 'left' | 'right'
 * @param {number} seat il suo posto (data-revealed-seat, per i test)
 * @param {string} [label] etichetta per i lettori di schermo
 * @param {object|null} [advise] P93, solo per il compagno
 * @param {function|null} advise.onPick chiamata con la carta toccata (null: niente consiglio)
 * @param {object|null} advise.picked la carta che hai consigliato, segnata
 * @param {boolean} advise.disabled carte spente (per esempio senza connessione)
 * @param {string} advise.name il nome del compagno, per le etichette
 * @returns {HTMLElement}
 *
 * In parole semplici:
 *   RevealedHand(cards, side, seat, label, advise)
 *   Costruisce il ventaglio delle carte di un altro giocatore, scoperte. Si usa in
 *   due casi: quando qualcuno "cala le carte" (tutti vedono le sue carte) e, nel
 *   2v2, per le carte del tuo compagno, che vedi sempre.
 *
 *   cards:  le sue carte, ognuna { suit: 'coppe', rank: 10 }. Le passa Table.js:
 *           le carte calate, oppure quelle del compagno (partner_hand nella vista).
 *   side:   da che lato dello schermo sta: 'top', 'left' o 'right' (vedi EdgeHand).
 *   seat:   il numero del suo posto al tavolo (0, 1, 2 o 3); finisce
 *           nell'attributo data-revealed-seat, che usano i test.
 *   label:  facoltativo. Il testo per i lettori di schermo, per esempio
 *           "Carte di Giuseppe". Se manca: "Carte scoperte".
 *   advise: facoltativo, solo per le carte del compagno. È un oggetto con:
 *     onPick   - la funzione da chiamare quando tocchi una sua carta per
 *                consigliargliela (onAdvise di game.js, che lo manda al server);
 *                null se il compagno è la CPU, che non riceve consigli
 *     picked   - la carta che gli hai già consigliato, oppure null
 *     disabled - true se le carte vanno spente (per esempio senza connessione)
 *     name     - il nome del compagno, per le etichette
 *   Esempio:
 *     { onPick: onAdvise, picked: { suit: 'denari', rank: 1 }, disabled: false, name: 'Giuseppe' }
 *
 *   Restituisce: il <div> del ventaglio.
 */
export function RevealedHand(cards, side, seat, label, advise) {
  // Parametri facoltativi: etichetta generica e nessun consiglio.
  if (label === undefined) {
    label = 'Carte scoperte';
  }
  if (advise === undefined) {
    advise = null;
  }

  // pickable: true se le carte si possono toccare, cioè se c'è un consiglio da
  // dare (il compagno è una persona vera, non la CPU).
  // "advise && advise.onPick" funziona come in C "p != NULL && p->onPick != NULL":
  // se advise è null la seconda parte non viene nemmeno guardata.
  let pickable = false;
  if (advise && advise.onPick) {
    pickable = true;
  }

  // items: l'elemento HTML di ogni carta, nello stesso ordine di cards
  const items = [];
  for (let i = 0; i < cards.length; i++) {
    // card: la carta numero i, per esempio { suit: 'coppe', rank: 10 }
    const card = cards[i];

    // face: l'elemento HTML della carta scoperta, creato da Card() di Card.js
    let face;
    if (pickable) {
      // Carta da toccare: è accesa se non è tutto spento (per esempio senza rete).
      face = Card(card, { onPlay: advise.onPick, playable: !advise.disabled });

      // picked: true se questa è la carta che hai già consigliato. Resta segnata
      // (aria-pressed = pulsante premuto, per i lettori di schermo).
      let picked = false;
      if (advise.picked && sameCard(advise.picked, card)) {
        picked = true;
      }
      // Per esempio "Consiglia a Giuseppe: Asso di denari".
      face.setAttribute('aria-label', `Consiglia a ${advise.name}: ${cardName(card)}`);
      if (picked) {
        face.setAttribute('aria-pressed', 'true');
      } else {
        face.setAttribute('aria-pressed', 'false');
      }
      face.dataset.adviseCard = '';
      if (picked) {
        face.classList.add('card--advised');
        face.dataset.advised = '';
      }
    } else {
      // Carta da guardare soltanto.
      face = Card(card);
    }

    // --i: la posizione della carta nel ventaglio, che il CSS usa per l'angolo
    face.style.setProperty('--i', i);
    items.push(face);
  }

  // className: le classi CSS del ventaglio, per esempio
  // "revealed-hand revealed-hand--top revealed-hand--partner".
  // Il ventaglio del compagno ha la classe in più, che lo fa un po' più grande.
  let className = `revealed-hand revealed-hand--${side}`;
  if (advise) {
    className = className + ' revealed-hand--partner';
  }

  // hand: il <div> del ventaglio, con dentro le carte
  const hand = el('div', {
    class: className,
    data: { revealedHand: side, revealedSeat: seat, count: cards.length },
    attrs: { role: 'group', 'aria-label': label },
  }, items);
  // --n: quante carte ci sono, per calcolare l'apertura del ventaglio
  hand.style.setProperty('--n', cards.length);
  return hand;
}
