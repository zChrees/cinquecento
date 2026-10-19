# Regole per scrivere e commentare il codice

Queste regole valgono per ogni file del progetto che si commenta o si riscrive. Lo scopo è che **Christian, Giuseppe e Antonio**, che sono principianti, capiscano ogni riga e sappiano spiegarla a un colloquio di lavoro. Il file di esempio, già scritto così, è `app/static/js/components/Hand.js`.

Sono state decise da Christian il 19/10/2026.

## 1. Lingua

- **Commenti in italiano**, semplici, come se si spiegasse a un compagno di corso.
- **Il codice resta in inglese** (nomi di variabili, funzioni, file), come prima.
- Un termine tecnico (per esempio `dataset`, `aria-label`, una variabile CSS) si spiega con una frase la prima volta che compare **in quel file**: chi apre un file non ha per forza letto gli altri.
- Dove aiuta, si fa un **paragone con il C** (puntatori a funzione, struct, NULL, ricerca lineare in un array).

## 2. In cima a ogni file

Un commento che dice:

1. **cosa fa il file**, in due o tre righe;
2. **cosa contiene**: l'elenco delle funzioni, con un esempio di chiamata per ciascuna;
3. **da dove arrivano i dati**: la catena delle chiamate, dal server (o dall'utente) fino a questo file.

Esempio (da `Hand.js`):

```js
 * DA DOVE ARRIVANO I DATI (la catena delle chiamate):
 *
 *   1. il server manda la "vista" della partita con l'evento game:state
 *      (un oggetto con le tue carte, quelle giocabili, i giocatori, ...);
 *   2. game.js la riceve e chiama render(vista), che chiama
 *      Table(vista, ...) di components/Table.js;
 *   3. Table.js chiama le funzioni di questo file, passando pezzi della vista:
 *      Hand per le tue carte, EdgeHand o RevealedHand per quelle degli altri.
```

## 3. Sopra ogni funzione: due blocchi

**Prima il blocco di documentazione standard**: JSDoc in JavaScript, docstring in Python. Si tiene perché l'editor lo legge e lo mostra passando il mouse sulla funzione.

**Poi il blocco "In parole semplici"**, che contiene:

- la **firma** della funzione, per esempio `Hand(cards, options)`;
- **cosa fa**, in una frase;
- **per ogni parametro**:
  - **cos'è** (un numero, un elenco, un oggetto con certi campi, una funzione…);
  - **cosa contiene**, con un **esempio concreto** di valore;
  - **da dove arriva**: chi chiama la funzione e da quale dato prende quel valore;
  - se è **facoltativo**, e cosa vale quando manca;
- **cosa restituisce** e chi lo usa;
- una **nota** se la funzione oggi non la chiama nessuno, o se ha un comportamento non ovvio.

Esempio (da `Hand.js`):

```js
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
 *     ...
 *
 *   Esempio di cosa può contenere options durante una partita:
 *     {
 *       playable: [{ suit: 'coppe', rank: 1 }, { suit: 'spade', rank: 3 }],
 *       onPlay:   onPlay,                    (la funzione di game.js)
 *       drawn:    { 'denari-7': 120 },       (pescata 120 ms fa: sta ancora volando)
 *       ...
 *     }
 *
 *   Restituisce: il <div> della mano, che Table.js mette in fondo al tavolo.
```

Gli esempi di valore devono essere **veri**: si controllano nel codice, o eseguendolo, prima di scriverli.

## 4. Dentro le funzioni

- **Commenti a blocchi**, non riga per riga: un commento sopra ogni gruppo di 3-6 righe che fanno una cosa sola. Leggendo solo i commenti si deve capire il racconto della funzione.
- **Ogni variabile di cui non è ovvio il contenuto** ha un commento con cosa contiene, e un esempio quando serve:

  ```js
  // key: il codice della carta, per esempio 'coppe-10', che è la chiave usata
  // dentro drawn e dealt.
  const key = `${card.suit}-${card.rank}`;
  ```

- Si spiega anche **il perché** di una riga non ovvia, non solo cosa fa:

  ```js
  // animationDelay negativo = l'animazione parte "già avanzata" di quei
  // millisecondi: così se la mano si ridisegna a metà volo, la carta non riparte
  // da capo.
  ```

- I riferimenti ai punti della scaletta (P70, P93, D46…) **si tengono**: servono a ritrovare il perché di una scelta in `docs/archivio/` e `DECISIONI.md`.

## 5. Niente zucchero sintattico

Si scrive tutto nella forma più esplicita, quella più vicina al C.

### JavaScript

| Si toglie | Si scrive invece |
|---|---|
| `array.map(...)`, `array.forEach(...)`, `array.filter(...)`, `array.some(...)`, `Array.from({ length: n }, ...)` | un ciclo `for (let i = 0; i < n; i++)` che riempie un array con `push` |
| arrow function `(x) => ...` | `function (x) { ... }` |
| `a ? b : c` (if su una riga) | `if (a) { ... } else { ... }` |
| `a ?? b` | `if` con un controllo esplicito su `null` e `undefined` |
| `a?.b` | `if (a && a.b)` |
| `x != null` (che controlla insieme null e undefined) | `hasValue(x)` |
| spread `...oggetto`, `...array` | si costruisce l'oggetto o l'array e si aggiungono i campi con `if` |
| destrutturazione `const { a, b } = obj` | `const a = obj.a;` riga per riga |
| valori predefiniti nella firma `function f(a, b = 1, { c = [] } = {})` | parametri semplici `function f(a, b, options)`; dentro, un `if (b === undefined) { b = 1; }` per ciascuno |
| `Boolean(x)` per trasformare in vero/falso | `let ok = false; if (x) { ok = true; }` |

`hasValue(value)` restituisce `false` se il valore è `null` o `undefined`, `true` altrimenti (anche per `0` e `''`). Per ora sta in `Hand.js`: va deciso se spostarla in `utils/dom.js` per usarla da tutti i file (D52 in `DA-DECIDERE.md`).

### Python

| Si toglie | Si scrive invece |
|---|---|
| list comprehension `[c for c in cards if ...]`, e quelle di dizionari e insiemi | un ciclo `for` che riempie la lista con `append` |
| generatori dentro le chiamate `sum(x for x in ...)`, `any(...)`, `all(...)` | un ciclo `for` con un accumulatore o un `break` |
| `a if cond else b` | `if cond: ... else: ...` |
| `lambda x: ...` | una funzione con `def` e un nome |
| walrus `:=` | l'assegnazione su una riga a parte |
| spacchettamenti complicati (`*args`, `**kwargs` dove non servono, `a, *b = ...`) | assegnazioni una per una |

### Cosa resta

- **f-string** in Python (`f"{count} carte"`) e **template literal** in JavaScript (`` `${count} carte` ``): si leggono già come una `printf`.

## 6. React e TypeScript

Il frontend nuovo (`frontend/`, piano in `docs/MIGRAZIONE-FRONTEND.md`) si scrive in **"stile esplicito"**: React e TypeScript normali, ma senza le forme compatte che li rendono difficili da leggere. Valgono tutte le regole sopra (sezioni 1-5): commenti in italiano, blocco "In parole semplici" sopra ogni componente e ogni funzione, da dove arriva ogni dato.

Esempio di riferimento:

```tsx
/**
 * Le carte della tua mano.
 *
 * In parole semplici:
 *   <Hand cards={...} playable={...} onPlay={...} />
 *   Disegna un <div> con dentro una carta per ogni elemento di props.cards.
 *   Lo usa Table.tsx, che gli passa i pezzi della vista mandata dal server.
 */

// HandProps: cosa riceve il componente. Ogni campo ha il suo tipo e il suo commento.
interface HandProps {
  // le tue carte, per esempio [{ suit: 'coppe', rank: 10 }]; da view.hand
  cards: Card[];
  // le carte che puoi giocare adesso; da view.legal.play (le decide il server)
  playable: Card[];
  // la funzione da chiamare quando tocchi una carta; è onPlay di game.tsx, che la
  // manda al server. In C sarebbe un puntatore a funzione: void (*onPlay)(struct carta)
  onPlay: (card: Card) => void;
}

export function Hand(props: HandProps): JSX.Element {
  // items: gli elementi delle carte, costruiti con un for prima del return
  const items: JSX.Element[] = [];
  for (let i = 0; i < props.cards.length; i++) {
    const card = props.cards[i];
    items.push(<CardView key={cardKey(card)} card={card} onPlay={props.onPlay} />);
  }

  // label: il testo per i lettori di schermo, deciso con un if prima del return
  let label = 'Le tue carte';
  if (props.cards.length === 0) {
    label = 'Nessuna carta';
  }

  return <div className="hand" aria-label={label}>{items}</div>;
}
```

### Componenti e JSX

| Si evita | Si scrive invece |
|---|---|
| `const Hand = ({ cards }) => ...` | `export function Hand(props: HandProps): JSX.Element { ... }`, con un nome |
| destrutturazione delle props `{ cards, onPlay }` | `props.cards`, `props.onPlay` |
| `.map(...)` dentro il JSX | un ciclo `for` **prima del `return`** che riempie un array, poi `{items}` nel JSX |
| `cond ? <A /> : <B />` e `cond && <A />` dentro il JSX | una variabile decisa con un `if` prima del `return` (`let banner = null; if (...) { banner = <Banner />; }`), poi `{banner}` |
| funzioni scritte dentro gli attributi `onClick={() => ...}` | una funzione con un nome dentro il componente (`function handleClick() { ... }`), poi `onClick={handleClick}` |
| spread delle props `<Card {...props} />` | ogni prop scritta una per una |

- **`key`**: ogni elemento di un elenco ha una `key` unica e stabile (per esempio `'coppe-10'`, mai l'indice `i`). È il "nome" con cui React riconosce lo stesso elemento tra un disegno e l'altro: si spiega con un commento la prima volta in ogni file.
- **`className`** al posto di `class`, e **gli stessi nomi di classi e di attributi `data-*`** del frontend di oggi: i test nel browser li usano.
- **`style={{ ... }}`** (le doppie graffe: un oggetto JavaScript dentro il JSX) solo per i valori calcolati, come le variabili CSS (`--i`, `--n`); si commenta ogni volta. Niente `style="..."` scritto nell'HTML (CSP).

### Hook (useState, useEffect, …)

- **`const [value, setValue] = useState(...)`** è l'**unica destrutturazione ammessa**: è il modo standard di React. Si commenta la prima volta in ogni file: `useState` restituisce due cose, il valore attuale e la funzione per cambiarlo (che fa ridisegnare il componente).
- **`useEffect`** riceve una funzione con un nome (`useEffect(listenToGame, [gameId])`), e la funzione di pulizia che restituisce ha anche lei un nome (`return stopListening;`). L'elenco tra quadre (le "dipendenze") si commenta: dice **quando** rieseguire l'effetto.
- Gli hook si chiamano sempre in cima al componente, mai dentro un `if` o un `for`: si scrive nel commento la prima volta.

### TypeScript

- **Tipi scritti** su ogni parametro e su ogni valore restituito, anche quando TypeScript li indovinerebbe da solo.
- **`interface`** per gli oggetti (props, vista, eventi), con un commento su **ogni campo**: cos'è, esempio, da dove arriva. È la struct del C.
- **Tipi a elenco** come `'top' | 'left' | 'right'`: si spiega che la `|` vuol dire "uno di questi valori" (come un `enum` del C).
- **Campi facoltativi** (`advice?: Advice`): si spiega che `?` vuol dire "può mancare", e cosa succede quando manca.
- **Niente `any`** (il tipo "qualsiasi cosa", che spegne i controlli), niente `!` per dire "fidati, non è null", niente `as` per forzare un tipo: se servono davvero, si spiega perché nel commento.
- **Il tipo di una funzione** (`(card: Card) => void`) si scrive così perché in TypeScript non c'è altro modo: è l'eccezione alla regola delle arrow function, e si commenta con il paragone del puntatore a funzione.
- I tipi del contratto stanno in `frontend/src/types/` e **copiano** `docs/CONTRATTO-SOCKET.md`, con gli stessi nomi dei campi (`legal`, `hand`, `cards_in_hand`, …).

### Regole del frontend

- **Niente regole del gioco in React**: le carte giocabili, i canti e la calata arrivano dal server (`legal.play`, `legal.sing`, `legal.lay_down`).
- **I componenti non usano Socket.IO direttamente**: passano da `frontend/src/socket/`.
- Dopo ogni modifica, il controllo è **`npx tsc --noEmit`** (TypeScript controlla i tipi di tutti i file senza produrre niente) al posto di `node --check`.

## 7. Cosa non si cambia mai

- **Nomi** di funzioni, variabili esportate, file, classi CSS, attributi `data-*`, eventi: i test e gli altri file li usano.
- **Il comportamento**: commentare e semplificare non deve cambiare niente di quello che vede l'utente.
- **I punti che i test leggono come testo**, per esempio il primo testo di ogni elenco in `ModeModal.js` (nome dell'icona), le durate in `game.js` confrontate con il CSS, `Card.js` eseguito con Node, i commenti di `favicon.svg` senza doppio trattino, `pianifica_backup.ps1` solo ASCII. I "Punti delicati" sono elencati in `CLAUDE.md`.
- **Le regole di sicurezza** (CSP): niente `onclick=` o `style="..."` nell'HTML, niente `setAttribute("style", …)` nel JS.

## 8. Semplificazioni

- Togliere lo zucchero si fa e basta. **Le semplificazioni di struttura** (unire o dividere funzioni, cambiare un algoritmo, togliere un pezzo) **si propongono prima**, spiegando perché, e si fanno solo dopo l'ok.
- Il **codice che non usa nessuno** si segnala nel commento della funzione e si propone di toglierlo (per esempio `HiddenHand` in `Hand.js`).

## 9. Come si lavora

- **Un lotto alla volta** (un gruppo di file legati), su un branch creato da `dev`.
- **Il JavaScript di adesso** (`app/static/js/`) non si commenta più: verrà sostituito dal frontend React, che si scrive già con queste regole (decisione del 19/10/2026 in `DECISIONI.md`). Fa eccezione `Hand.js`, già fatto come esempio. Il Python si commenta come scritto sopra.
- **I file degli altri due** si toccano solo con il loro ok. Le aree sono: Giuseppe motore e tempo reale, Antonio account, dati e amici, Christian interfaccia e documenti.
- Dopo ogni lotto si lanciano **solo i test della parte toccata**. Le suite complete si lanciano solo su richiesta.
- Se si cambiano solo i commenti, basta controllare che il file sia ancora valido (`node --check` per il JS, `python -m py_compile` per il Python).
- Fine riga **CRLF** (tranne gli script `.sh`, che restano LF).
- **Nessun commit, merge o push senza l'ok esplicito**, chiesto ogni volta.

## 10. Casi non ancora decisi

Se ne incontra uno, ci si ferma e si chiede:

- i **decoratori** di Python (`@app.route`, `@handler`, `@property`): servono a Flask e non si possono togliere, ma va deciso come spiegarli;
- **classi**, `with` e `try/except` in Python, `async`/`await` e le `Promise` in JavaScript: sono costrutti veri, non zucchero, ma vanno spiegati bene;
- dove mettere `hasValue` (vedi sezione 5, D52) e se togliere `HiddenHand` (D53): sono in `DA-DECIDERE.md`.
