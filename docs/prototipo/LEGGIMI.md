# Prototipo della home (P52)

Prototipo statico della home, scritto da Claude il 27/09/2026 seguendo il prompt dell'utente, con la palette scelta: **Carretto siciliano**, su un **panno verde da tavolo** (ritocco dello stesso giorno). Serve **solo come riferimento grafico**: il server non lo usa.

## Come si apre

Doppio clic su `index.html`. Serve internet, perché font e icone arrivano da Google Fonts.

## Cosa si può provare

- **Avatar** (in alto a sinistra): apre, con un'animazione che parte dall'avatar, le statistiche (partite, vinte, perse, percentuale, rating 1v1 e 2v2), con i link Impostazioni ed Esci e, in fondo, la riga dei crediti delle immagini.
- **Amici** (in alto a destra): apre il pannello, che entra scorrendo da destra (a tutto schermo su telefono, laterale su computer) con la ricerca per username e l'invio della richiesta, le richieste ricevute (accetta o rifiuta), gli amici online e offline e la chat con ciascuno.
- **Partita Veloce 1v1 / 2v2**: la carta toccata vola al centro dello schermo e si gira; sulla sua faccia c'è il modal, con i punti per vincere (150, 300, 500) e "Gioca" (vedi "Modal a forma di carta").
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
- **bordi**: una cornice doppia sbalzata come l'Asso, dentro la carta (niente fregi negli angoli); nessun bordo attorno;
- **superficie stampata**, nello stesso stile dell'Asso perché non stacchi dal resto: grana della carta, tratteggio fine a incisione, trama leggera a rombi (tipo maiolica), un medaglione di luce dietro l'Asso e i margini appena consumati. Queste velature sono leggere apposta, perché i **colori restino vivaci**: la parte alta della carta è schiarita solo del 8%;
- **disegni**: una luce dall'alto, l'**Asso del suo seme** grande al centro, ridotto a una **sagoma in rilievo** (27/09/2026): niente dettagli del disegno, solo la forma, così si riconosce il seme (coppa, spada, aquila con la moneta, bastone) senza il realismo della stampa. La sagoma è appena più chiara della carta, con una luce sul bordo alto e un'ombra sotto, come uno sbalzo sulla superficie. È fatta solo con CSS sulla stessa immagine: `brightness(0) invert(1)` la rende tutta bianca, due `drop-shadow` fanno luce e ombra e `mix-blend-mode: soft-light` la fonde con il colore della carta;
- **3D**: lo spessore della carta è un **bordo crema pieno visibile solo in basso** (2 px, `--edge`; era 4, ridotto il 27/09/2026 per un 3D più leggero), come il taglio di una carta vera; sotto quel bordo **non c'è nient'altro** (niente striscia scura né ombre: 27/09/2026). Passandoci sopra la carta si solleva e lo spessore cresce (3 px); premendola scende e lo spessore si schiaccia (1 px);
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

**La pagina non scorre mai**, né su telefono né su computer: è alta esattamente quanto lo schermo, e `html` e `body` hanno `overflow: hidden` e `overscroll-behavior: none` (niente "rimbalzo" su telefono). Nel modal-carta l'unica cosa che scorre è la lista degli amici da invitare. Le carte-pulsante si rimpiccioliscono sugli schermi bassi: la loro altezza massima (`--tile-h` in `prototipo.css`) è lo schermo meno navbar, "giocatori online", titoli e spazi.

- **Telefono** (fino a 639 px): sulla carta gialla il sottotitolo va a capo, "Sfida" e sotto "un amico" (su una riga uscirebbe dalla cornice); navbar con avatar, "Cinquecento" e amici (icona degli amici più grande, 30 px); le due sezioni una sotto l'altra, ciascuna con due carte affiancate; "giocatori online" **in fondo alla pagina**, centrato. Gli elementi sono **più distanziati** che sugli altri schermi (22 px tra sezioni e "giocatori online", 26 px tra le due sezioni, 20 px tra le due carte, 14 px sotto i titoli); `--tile-h` sottrae anche questi spazi, così la pagina non scorre. Misurato il 27/09/2026 a 360×640, 375×667, 390×844 e 412×915: nessuno scorrimento, almeno 24 px tra l'ultima carta e "giocatori online".
- **A tutte le misure** i titoli "Partita Veloce" e "Gioca con un amico" sono **centrati sopra le loro due carte**.
- **Scritte sul tavolo, senza fondo**: "giocatori online" e i due titoli, come avatar e amici, stanno direttamente sul panno, scritti come il nome "Cinquecento" (vedi sotto); l'icona dei titoli (fulmine e cuore) ha lo stesso rilievo; il puntino "online" è un verde più chiaro (`--online-light`).
- **Telefono in orizzontale** (altezza fino a 520 px): le quattro carte su una sola fila.
- **Tablet** (da 640 px): carte larghe al massimo 220 px, sezioni centrate. Da 900 px le due sezioni sono affiancate.
- **Computer** (da 1024 px): navbar con le scritte "Mario" e "Amici", avatar e icona degli amici più grandi (avatar 58 px invece di 42, icona 40 px invece di 24) e navbar più alta (84 px invece di 64, con 12 px di spazio in alto: l'avatar sta a 19 px dal bordo superiore; le carte-pulsante hanno 20 px in meno di altezza massima, così la pagina non scorre), carte più grandi e più distanziate. La navbar è **larga quanto lo schermo**: avatar a sinistra e amici a destra stanno vicino ai bordi, a una distanza pari al 2% della larghezza della finestra, tra 16 e 32 px (`--navbar-side`; circa 20 px a 1024, 29 px a 1440, 32 px a 1920); il pannello statistiche si apre sotto l'avatar, alla stessa distanza.

La **navbar è completamente trasparente**: niente fondo, sfocatura né ombra sotto tutta la barra. Avatar e amici **non hanno fondo** (27/09/2026: tolti il vetro liquido e poi il "panno cucito", che non convincevano): si agisce solo sulle scritte, che sono **come il nome "Cinquecento"** del logo. Lettere color crema (`--on-navbar`) in Fredoka 700; lo stesso **leggero rilievo** bruno a strati netti di mezzo pixel del logo, con la linea scura alla base; in più un **contorno scuro sottile e sfumato** attorno alle lettere, che le stacca dalle carte chiare della cascata quando passano dietro, e un'ombra corta (tutto nella variabile `--relief-text`). Dietro ogni scritta c'è un **alone scuro morbido**, lo stesso del logo (`::before`). Lo stesso trattamento vale per "giocatori online", per i due titoli e per le icone accanto (amici, fulmine, cuore). Provato il 27/09/2026 con carte ferme proprio dietro le scritte, a 1440×900 e 390×844: si leggono anche sul bianco delle carte.

**Passandoci sopra** (o arrivandoci con la tastiera) avatar e amici si alzano un po'; l'**avatar** si ingrandisce, si inclina e il suo anello giallo si illumina; l'**icona degli amici** oscilla come un saluto e il contatore rimbalza.

**Logo**: due carte vere a ventaglio, di dorso (lo stesso dorso della cascata), che si aprono un po' passandoci sopra con il mouse. **Ogni tanto si girano**: dopo 3 secondi di dorso ruotano in 3D (la seconda un attimo dopo la prima, 0,9 s ciascuna, sollevandosi un po') e mostrano **Cavallo e Re dello stesso seme**; restano scoperte circa 2,6 secondi e tornano sul dorso; al giro dopo tocca al seme successivo (coppe → denari → spade → bastoni → di nuovo coppe). Le figure si cambiano mentre si vede il dorso e sono precaricate, così il giro non scatta; con "riduci movimento" le carte restano ferme sul dorso. Script in `prototipo.js`, parte "Logo". Accanto alle carte, il nome in due toni: "Cinque" color crema e "cento" giallo, in Fredoka. È **in risalto**: lettere con un **leggero rilievo** e **bordi netti** (Fredoka 700; lo spessore è di 1,5 px, fatto di tre strati pieni a mezzo pixel l'uno dall'altro, più scuri della lettera: bruno per "Cinque", ambra per "cento"; poi una linea scura netta alla base e un'ombra morbida corta e leggera, che non sfuma i bordi) e un alone scuro morbido dietro, che lo stacca dal panno e dalle carte che passano. Misura: nome 1,7 rem su telefono e 2,2 rem su computer; anche a 360 px restano circa 25 px di spazio da avatar e amici. È solo CSS: nessuna immagine. Il logo definitivo in SVG resta per P42.

## Animazioni

- **Pannello statistiche**: si apre ingrandendosi dall'angolo dell'avatar (0,22 s) e si chiude rimpicciolendosi e sfumando (0,16 s).
- **Pannello amici**: entra scorrendo da destra (0,3 s) ed esce allo stesso modo (0,22 s).
- Lo sfondo scuro dietro i due pannelli compare e scompare sfumando.
- La chiusura è animata con la X, con Esc e toccando fuori: lo script aggiunge `.is-closing` e chiude il pannello a fine animazione. Le finestre animate hanno l'attributo `data-animated`.
- Con "riduci movimento" attivo nel sistema, niente animazioni: i pannelli e il modal della modalità si aprono e si chiudono subito.

### Modal a forma di carta

Il modal della modalità è una **carta da gioco grande** al centro dello schermo. Da tablet in su ha le proporzioni di una carta siciliana (alta al massimo 760 px e comunque dentro lo schermo: 464 × 760 px a 1440×900). Su **telefono** la carta con le proporzioni vere sarebbe bassa, perché è limitata dalla larghezza: lì è larga quanto lo schermo meno 32 px e alta quanto lo schermo meno 32 px, al massimo 760 (358 × 760 px a 390×844, 328 × 608 px a 360×640).

- **Faccia**: **bianca**, con una **cornice doppia sottile** nel colore della carta toccata (rossa, viola, gialla o blu), come il bordo di una carta da gioco. I titoletti, le icone e i riquadri chiari prendono lo stesso colore (una versione scura per le scritte, una molto chiara per i fondi). Dentro la cornice c'è **tutto il modal**, dall'alto in basso, ogni parte al suo posto e senza sovrapposizioni:
  - la **X** nell'**angolo in alto a destra** della carta;
  - "Partita Veloce" o "Gioca con un amico" e il titolo "1v1 / 2v2";
  - una **descrizione** di due o tre righe di cosa succede in quella modalità (con un amico dice anche se la partita conta per il rating: 1v1 no, 2v2 sì, D36);
  - **Punti per vincere**: 150, 300, 500, con sotto una parola (Breve, Media, Classica); nella Partita Veloce anche una riga che cambia con la scelta ("Incontri solo chi ha scelto 500 punti.": le code sono separate per punteggio, D35);
  - solo nella Partita Veloce, **In breve**: tre righe con un'icona (come si trovano avversari e compagno, dove siede il compagno, se conta per il rating e il rating attuale, 30 secondi per turno);
  - solo con un amico, la lista degli **amici da invitare**, che prende **tutto lo spazio rimasto** nella carta (niente "In breve", per darle più spazio);
  - solo nella Partita Veloce, **Lo sapevi?**: un consiglio preso dal regolamento (`docs/REGOLE-GIOCO.md`: canti, carichi, briscola…), diverso a ogni apertura;
  - il pulsante **Gioca**, sempre dentro la carta.

  **Cosa entra dipende dall'altezza vera della carta** (non dello schermo): la faccia è un contenitore CSS (`container: carta / size`) e le regole `@container` tolgono le parti meno importanti quando la carta è più bassa. Restano sempre titolo, punti, amici da invitare e Gioca. Partita Veloce: fino a 700 px di altezza della carta sparisce "Lo sapevi?", fino a 540 "In breve", fino a 480 la descrizione. Con un amico: fino a 560 spariscono la descrizione e la frase sotto la lista. Sotto i 600 px gli spazi si stringono, sotto i 420 (telefono in orizzontale) anche la scritta sopra il titolo e la frase dei punti spariscono e le misure diminuiscono. **Telefono in orizzontale** (altezza fino a 520 px): la carta è larga fino a 520 px e alta quasi quanto lo schermo.

  **La carta non scorre mai**: la faccia sta ferma (`overflow: hidden`) e ogni parte ha la sua misura e non si schiaccia. L'unica parte elastica è la **lista degli amici da invitare**, che **scorre al suo interno** (con il dito o con la rotellina) e mostra sempre almeno un amico e mezzo, così si capisce che scorre; lo scorrimento non passa mai alla pagina (`overscroll-behavior: contain`). Per provarlo il prototipo ha 5 amici invitabili (aggiunti Carmelo, Agata e Ninni). Testi in `prototipo.js` (`modeTexts`, `ruleTips`); il rating è finto (1540 e 1482, come nel pannello statistiche).
- **Retro**: una copia esatta della carta-pulsante toccata. Su telefono, durante il volo, la carta cambia anche forma, dalle proporzioni della carta-pulsante a quelle della carta grande.
- **Apertura** (0,82 s): la carta-pulsante sparisce dal suo posto e la carta grande parte esattamente sopra di lei, rimpicciolita e girata sul retro. Nella prima metà si stacca e gira con calma fino a mettersi di taglio, già vicina al centro; nella seconda mostra la faccia e rallenta arrivando al centro a grandezza piena. Il contenuto della faccia compare sfumando dal basso, un pezzo dopo l'altro, quando la carta è quasi girata. Lo sfondo scuro compare sfumando.
- **Chiusura** (0,62 s), con la X, con Esc, toccando fuori o con "Gioca": lo stesso percorso al contrario; la carta si rigira sul retro, torna al suo posto e ridiventa la carta-pulsante.
- Durante l'animazione i clic in più non fanno niente (niente doppie aperture).

Script in `prototipo.js`, parte "Modal della modalità" (animazioni Web Animations, `element.animate`); stile in `prototipo.css` (`.modal`, `.modal__flip`, `.modal__back`, `.modal__face`). Provato il 27/09/2026 in Chrome a tempo reale: apertura, chiusura con X, Esc e tocco fuori, doppio clic; le quattro modalità, ciascuna a 17 misure di schermo (da 1920×1080 a 667×375, compresi portatili con la barra del browser come 1366×657 e 1536×730, tablet e telefoni in verticale e in orizzontale): in tutti i 68 casi ogni parte, Gioca compreso, sta dentro la cornice, nessuna tocca la successiva e la X non copre il titolo (misurato con uno script). Provato anche, con la rotellina e trascinando con il dito, a 1440×900, 390×844, 360×640 e 844×390: pagina e faccia della carta non si spostano mai, la lista degli amici sì.

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
| **Fredoka** | nome "Cinquecento"; "Mario" e "Amici" nella navbar (su computer); "giocatori online"; iniziale dell'avatar; "1v1 / 2v2" sulle carte-pulsante; titoli "Partita Veloce" e "Gioca con un amico"; titolo del modal; scelta 150 / 300 / 500; nome nel pannello statistiche; numeri delle statistiche; titolo "Amici" e nome dell'amico in cima alla chat |
| **Nunito** | sottotitoli delle carte-pulsante; scritta sopra il titolo del modal; "Punti per vincere"; lista inviti; pulsanti "Gioca", "Invita", "Invia"; etichette delle statistiche; "Impostazioni" ed "Esci"; ricerca, titoletti e nomi nel pannello amici; messaggi della chat; lettere degli avatar piccoli; contatore delle notifiche; messaggi brevi in basso |
| **Material Symbols Rounded** | tutte le icone |

## Cose che le pagine vere NON riprendono

- I parametri `?apri=` e l'accettazione automatica dell'invito dopo 2 secondi.
- Il codice dello sfondo, che nelle pagine vere va nel componente `js/components/CardBackground.js` (P22); le immagini vanno in `app/static/img/cards-bg/` già con P40, perché le usa anche il logo.
- I dati finti (Mario, 24 online, amici, messaggi, rating): nelle pagine vere arrivano dal server.
- Lo script classico: le pagine vere usano moduli ES, che però non partono aprendo un file con un doppio clic.
