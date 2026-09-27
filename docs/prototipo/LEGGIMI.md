# Prototipo della home (P52)

Prototipo statico della home, scritto da Claude il 27/09/2026 seguendo il prompt dell'utente, con la palette scelta: **Carretto siciliano**, su un **panno verde da tavolo** (ritocco dello stesso giorno). Serve **solo come riferimento grafico**: il server non lo usa.

## Come si apre

Doppio clic su `index.html`. Serve internet, perché font e icone arrivano da Google Fonts.

## Cosa si può provare

- **Avatar** (in alto a sinistra): apre, con un'animazione che parte dall'avatar, le statistiche (partite, vinte, perse, percentuale, rating 1v1 e 2v2), con i link Impostazioni ed Esci e, in fondo, la riga dei crediti delle immagini.
- **Amici** (in alto a destra): apre il pannello, che entra scorrendo da destra (a tutto schermo su telefono, laterale su computer) con la ricerca per username e l'invio della richiesta, le richieste ricevute (accetta o rifiuta), gli amici online e offline e la chat con ciascuno.
- **Partita Veloce 1v1 / 2v2**: modal con i punti per vincere (150, 300, 500) e "Gioca".
- **Gioca con un amico 1v1 / 2v2**: stesso modal più la lista degli amici online da invitare. "Gioca" resta disattivato finché l'amico non accetta: nel prototipo accetta da solo dopo 2 secondi.

Per aprire subito uno stato, aggiungi all'indirizzo `?apri=` seguito da `statistiche`, `amici`, `chat`, `veloce`, `amico` oppure `invito` (quest'ultimo invia subito l'invito e mostra l'accettazione). Esempio: `index.html?apri=invito`.

## Carte-pulsante

Ogni modalità è una **carta da gioco colorata in rilievo**, con le proporzioni di una carta siciliana (larghezza/altezza 0,61) e l'icona, "1v1" o "2v2" e il sottotitolo in bianco:

| Carta | Colore | Asso al centro | Sottotitolo |
|---|---|---|---|
| Partita Veloce 1v1 | rosso | coppe | Uno contro uno |
| Partita Veloce 2v2 | viola (`--purple`, `#7b3fc4`; era verde, ma si confondeva con il tavolo) | spade | A coppie |
| Gioca con un amico 1v1 | giallo | denari | Sfida un amico |
| Gioca con un amico 2v2 | blu | bastoni | Fai squadra |

Com'è fatta (`prototipo.css`, `.mode-tile`):
- **colore**: ogni carta ha il suo colore in `--tile`; il CSS ne ricava una versione chiara e una scura (`color-mix`) per la sfumatura dall'alto in basso e per lo spessore;
- **bordi**: un bordo esterno crema sottile (2 px), come il margine bianco di una carta vera, e dentro una cornice doppia sbalzata come l'Asso (niente fregi negli angoli);
- **superficie stampata**, nello stesso stile dell'Asso perché non stacchi dal resto: grana della carta, tratteggio fine a incisione, trama leggera a rombi (tipo maiolica), un medaglione di luce dietro l'Asso e i margini appena consumati. Queste velature sono leggere apposta, perché i **colori restino vivaci**: la parte alta della carta è schiarita solo del 8%;
- **disegni**: una luce dall'alto, l'**Asso del suo seme** grande al centro, **sbalzato**: chiaro, in grigio, con una luce sul bordo alto e un'ombra sotto, come un rilievo sulla superficie della carta;
- **3D**: sotto la carta c'è il suo spessore (una striscia scura piena di soli 2 px, per un 3D leggero) e un'ombra larga e morbida. Passandoci sopra la carta si solleva e lo spessore cresce; premendola scende e lo spessore si schiaccia;
- **scritte in rilievo**: icona, "1v1 / 2v2" e sottotitolo hanno un leggero rilievo con bordi netti, come il logo: lo spessore è nel colore scuro della carta stessa, più una linea scura alla base e un alone scuro leggero che le stacca dall'Asso dietro;
- **inclinazione**: con il mouse la carta si inclina verso il puntatore (fino a 10 gradi) e un riflesso di luce lo segue (script in `prototipo.js`, subito dopo il modal). Solo con un mouse vero: sul telefono e con "riduci movimento" la carta non si inclina.

La carta gialla usa un giallo più carico (`--yellow-card`, `#e9a000`) del giallo dei dettagli (`--yellow`, `#ffc21a`), con un'ombra sotto le scritte, perché il testo bianco si legga. Il contrasto resta comunque più basso di quello delle altre carte.

## Sfondo

Il fondo della pagina è un **panno verde da tavolo** con profondità:
- **luce da lampada**: una pozza di luce calda sopra il centro del tavolo; il verde è più chiaro lì e sempre più scuro verso i bordi (`--felt-light`, `--felt`, `--felt-dark`, `--felt-edge`);
- **trama del feltro**: fibre fini, un po' allungate, chiare e scure (riquadro di 220 px che si ripete), più macchie ampie e irregolari appena più scure (riquadro di 900 px), come un tessuto vero.

Trama e macchie sono piccoli SVG di rumore scritti dentro il CSS, senza immagini in più. Il filtro SVG copre esattamente il 100% del riquadro: così il rumore si ripete senza cuciture visibili.

Sopra il panno c'è una **cascata di carte che cade dall'alto**, senza fermarsi mai (script in `prototipo.js`, parte "Sfondo"):
- due carte su cinque cadono **di dorso** (`img/dorso.webp`, vedi "Immagini e licenze"); le altre sono di faccia, a turno una **coppia Cavallo + Re** (a ventaglio, come in mano a chi canta 40, che cade tutta insieme), un **Asso** e un **Tre** (i carichi);
- le carte hanno misure diverse: le più piccole sembrano più lontane, quindi cadono più lente, sono un po' più scure (`--shade`) e passano dietro alle più grandi;
- le carte sono **piene, non trasparenti**: quando due si incrociano, la più grande (più vicina) copre la più piccola (più lontana);
- mentre cadono girano piano su se stesse e si spostano un po' di lato;
- all'apertura della pagina la cascata è già a metà (ogni carta parte da un punto diverso del suo giro);
- passano **dietro** a tutto (navbar, titoli, "giocatori online", carte-pulsante);
- il numero di carte dipende dalla larghezza dello schermo: 8 su telefono, 16 a 1280 px, 24 a 1920 px;
- con **"riduci movimento"** attivo nel sistema la cascata resta ferma, con le carte sparse sullo schermo.

Spostamenti, rotazioni e velocità sono "casuali" ma sempre uguali, quindi lo sfondo non cambia a ogni apertura. La cascata si ricrea (e riparte) solo quando cambia la misura della finestra.

Misura delle carte più vicine: 60 px su telefono, 84 px su tablet, 104 px su computer; le più lontane sono al 55%.

Carte della cascata, contate il 27/09/2026: a 360×640 8 carte (3 dorsi, 2 coppie, 2 Assi, 1 Tre); a 1440×900 18 carte (7 dorsi, 4 coppie, 4 Assi, 3 Tre); a 1920×1080 24 carte (10 dorsi, 5 coppie, 5 Assi, 4 Tre).

## Layout

**La pagina non scorre mai**, né su telefono né su computer: è alta esattamente quanto lo schermo. Le carte-pulsante si rimpiccioliscono sugli schermi bassi: la loro altezza massima (`--tile-h` in `prototipo.css`) è lo schermo meno navbar, "giocatori online", titoli e spazi.

- **Telefono** (fino a 639 px): sulla carta gialla il sottotitolo va a capo, "Sfida" e sotto "un amico" (su una riga uscirebbe dalla cornice); navbar con avatar, "Cinquecento" e amici (icona degli amici più grande, 30 px); le due sezioni una sotto l'altra, ciascuna con due carte affiancate; "giocatori online" **in fondo alla pagina**, centrato. Gli elementi sono **più distanziati** che sugli altri schermi (22 px tra sezioni e "giocatori online", 26 px tra le due sezioni, 20 px tra le due carte, 14 px sotto i titoli); `--tile-h` sottrae anche questi spazi, così la pagina non scorre. Misurato il 27/09/2026 a 360×640, 375×667, 390×844 e 412×915: nessuno scorrimento, almeno 24 px tra l'ultima carta e "giocatori online".
- **A tutte le misure** i titoli "Partita Veloce" e "Gioca con un amico" sono **centrati sopra le loro due carte**.
- **Vetro liquido**: "giocatori online" e i due titoli sono sulla stessa pillola di vetro di avatar e amici (variabili `--glass-*` in `prototipo.css`), con il testo color crema e, nei titoli, l'icona (fulmine e cuore) bianca sul vetro come l'icona degli amici, senza più il cerchio giallo; il puntino "online" è un verde più chiaro (`--online-glass`) per staccarsi dal vetro.
- **Telefono in orizzontale** (altezza fino a 520 px): le quattro carte su una sola fila.
- **Tablet** (da 640 px): carte larghe al massimo 220 px, sezioni centrate. Da 900 px le due sezioni sono affiancate.
- **Computer** (da 1024 px): navbar con le scritte "Mario" e "Amici", carte più grandi e più distanziate.

La **navbar è completamente trasparente**: niente fondo, sfocatura né ombra sotto tutta la barra. Avatar e amici stanno su una **pillola di vetro liquido** ("liquid glass"): le carte della cascata che passano dietro si vedono sfocate e scurite da una tinta verde (`backdrop-filter`), così icone e scritte bianche restano leggibili su qualunque carta; in più un riflesso chiaro in alto a sinistra, un bordo sottile di luce, un'ombra interna in basso per lo spessore del vetro e un'ombra sotto e il nome ha uno spessore e un'ombra che lo staccano dal panno; con scritte e icone color crema (`--on-navbar`). Un'ombra leggera sotto le scritte le tiene leggibili quando dietro passa una carta.

**Passandoci sopra** (o arrivandoci con la tastiera) la pillola si alza un po'; l'**avatar** si ingrandisce, si inclina e il suo anello giallo si illumina; l'**icona degli amici** oscilla come un saluto e il contatore rimbalza.

**Logo**: due carte vere a ventaglio, di dorso (lo stesso dorso della cascata), che si aprono un po' passandoci sopra con il mouse. **Ogni tanto si girano**: dopo 3 secondi di dorso ruotano in 3D (la seconda un attimo dopo la prima, 0,9 s ciascuna, sollevandosi un po') e mostrano **Cavallo e Re dello stesso seme**; restano scoperte circa 2,6 secondi e tornano sul dorso; al giro dopo tocca al seme successivo (coppe → denari → spade → bastoni → di nuovo coppe). Le figure si cambiano mentre si vede il dorso e sono precaricate, così il giro non scatta; con "riduci movimento" le carte restano ferme sul dorso. Script in `prototipo.js`, parte "Logo". Accanto alle carte, il nome in due toni: "Cinque" color crema e "cento" giallo, in Fredoka. È **in risalto**: lettere con un **leggero rilievo** e **bordi netti** (Fredoka 700; lo spessore è di 1,5 px, fatto di tre strati pieni a mezzo pixel l'uno dall'altro, più scuri della lettera: bruno per "Cinque", ambra per "cento"; poi una linea scura netta alla base e un'ombra morbida corta e leggera, che non sfuma i bordi) e un alone scuro morbido dietro, che lo stacca dal panno e dalle carte che passano. Misura: nome 1,7 rem su telefono e 2,2 rem su computer; anche a 360 px restano circa 25 px di spazio da avatar e amici. È solo CSS: nessuna immagine. Il logo definitivo in SVG resta per P42.

## Animazioni

- **Pannello statistiche**: si apre ingrandendosi dall'angolo dell'avatar (0,22 s) e si chiude rimpicciolendosi e sfumando (0,16 s).
- **Pannello amici**: entra scorrendo da destra (0,3 s) ed esce allo stesso modo (0,22 s).
- Lo sfondo scuro dietro i due pannelli compare e scompare sfumando.
- La chiusura è animata con la X, con Esc e toccando fuori: lo script aggiunge `.is-closing` e chiude il pannello a fine animazione. Le finestre animate hanno l'attributo `data-animated`; il modal della modalità non ce l'ha e si chiude subito come prima.
- Con "riduci movimento" attivo nel sistema, niente animazioni: i pannelli si aprono e si chiudono subito.

Controllato il 27/09/2026 a 360×640, 375×667, 390×844, 412×915, 768×1024, 844×390, 1280×720, 1440×900 e 1920×1080: in tutti i casi il contenuto è alto quanto lo schermo e l'ultima carta-pulsante resta dentro.

## Scelte di interpretazione

- Nel 2v2 "Gioca con un amico" l'amico invitato è il **compagno di squadra**; gli avversari arrivano dal matchmaking. Nel 1v1 l'amico invitato è l'avversario.
- Si invita un amico alla volta; gli amici "In partita" non compaiono tra quelli invitabili.
- Solo tema chiaro: il tema scuro è rimandato alla fine della scaletta (P53).

## Immagini e licenze

| File | Cosa | Fonte | Licenza |
|---|---|---|---|
| `img/seme-denari.svg` | Seme di denari: era accanto al nome "Cinquecento", ora non è più usato (il logo è in CSS) | Wikimedia Commons, file `Seme_denari_carte_siciliane.svg`, autore Florixc | **Pubblico dominio** |
| `img/asso-<seme>-figura.webp` (4 semi) | Asso al centro delle carte-pulsante: la figura dell'Asso **scontornata** (sfondo bianco e buchi bianchi resi trasparenti, tranne la moneta del denaro; tolte le macchioline della scansione), ritagliata e portata al doppio della misura | Ricavate da `img/asso-<seme>.webp`, quindi dalle scansioni di Matsoftware | **CC BY-SA 3.0**, come le carte da cui vengono |
| `img/cavallo-<seme>.webp`, `img/re-<seme>.webp`, `img/asso-<seme>.webp`, `img/tre-<seme>.webp` (4 semi ciascuno) | Carte di faccia della cascata, ritagliate dalle scansioni e portate a 200 × 326 px | Wikimedia Commons, file `Carte_da_gioco_siciliane_-_<seme>.jpg`, autore Matsoftware | **CC BY-SA 3.0**: si possono usare citando l'autore e la licenza; i ritagli restano sotto la stessa licenza |
| `img/dorso.webp` | Dorso delle carte della cascata: disegno a cubi, ritagliato, portato a 200 × 326 px e colorato di rosso su crema (l'originale è in bianco e nero) | Wikimedia Commons, file `Carte_Napoletane_retro.jpg`, autore Trocche100 (it.wikipedia). È il dorso delle **carte napoletane**: su Commons non c'è un dorso di carte siciliane con licenza libera, e questo disegno a cubi è quello classico dei mazzi regionali italiani | **Pubblico dominio**: nessun obbligo di citazione |

Da ricordare per le pagine vere: le immagini CC BY-SA richiedono una **riga di crediti** visibile nel sito: va in fondo al pannello statistiche, come nel prototipo ("Immagini delle carte: Matsoftware, CC BY-SA 3.0, da Wikimedia Commons": le carte della cascata e gli Assi delle carte-pulsante, con il collegamento alla licenza).

## Risorse esterne

| Risorsa | Da dove | Uso | Licenza |
|---|---|---|---|
| Font **Fredoka** (500, 600, 700) | Google Fonts | Titoli e numeri (vedi tabella sotto) | SIL Open Font License |
| Font **Nunito** (400, 600, 700, 800) | Google Fonts | Tutto il resto del testo | SIL Open Font License |
| Icone **Material Symbols Rounded** | Google Fonts | Icone dell'interfaccia (niente emoji) | Apache 2.0 |

### Dove si usa ogni font

| Font | Dove |
|---|---|
| **Fredoka** | nome "Cinquecento"; iniziale dell'avatar; "1v1 / 2v2" sulle carte-pulsante; titoli "Partita Veloce" e "Gioca con un amico"; titolo del modal; scelta 150 / 300 / 500; nome nel pannello statistiche; numeri delle statistiche; titolo "Amici" e nome dell'amico in cima alla chat |
| **Nunito** | "giocatori online"; sottotitoli delle carte-pulsante; "Mario" e "Amici" nella navbar (su computer); scritta sopra il titolo del modal; "Punti per vincere"; lista inviti; pulsanti "Gioca", "Invita", "Invia"; etichette delle statistiche; "Impostazioni" ed "Esci"; ricerca, titoletti e nomi nel pannello amici; messaggi della chat; lettere degli avatar piccoli; contatore delle notifiche; messaggi brevi in basso |
| **Material Symbols Rounded** | tutte le icone |

## Cose che le pagine vere NON riprendono

- I parametri `?apri=` e l'accettazione automatica dell'invito dopo 2 secondi.
- Il codice dello sfondo, che nelle pagine vere va nel componente `js/components/CardBackground.js` e le immagini in `app/static/img/cards-bg/` (P22).
- I dati finti (Mario, 24 online, amici, messaggi): nelle pagine vere arrivano dal server.
- Lo script classico: le pagine vere usano moduli ES, che però non partono aprendo un file con un doppio clic.
