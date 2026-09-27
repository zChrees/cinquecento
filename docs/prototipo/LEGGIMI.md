# Prototipo della home (P52)

Prototipo statico della home, scritto da Claude il 27/09/2026 seguendo il prompt dell'utente, con la palette scelta: **Carretto siciliano**. Serve **solo come riferimento grafico**: il server non lo usa.

## Come si apre

Doppio clic su `index.html`. Serve internet, perché font e icone arrivano da Google Fonts.

## Cosa si può provare

- **Avatar** (in alto a sinistra): apre le statistiche (partite, vinte, perse, percentuale, rating 1v1 e 2v2), con i link Impostazioni ed Esci.
- **Amici** (in alto a destra): apre il pannello (a tutto schermo su telefono, laterale su computer) con la ricerca per username e l'invio della richiesta, le richieste ricevute (accetta o rifiuta), gli amici online e offline e la chat con ciascuno.
- **Partita Veloce 1v1 / 2v2**: modal con i punti per vincere (150, 300, 500) e "Gioca".
- **Gioca con un amico 1v1 / 2v2**: stesso modal più la lista degli amici online da invitare. "Gioca" resta disattivato finché l'amico non accetta: nel prototipo accetta da solo dopo 2 secondi.

Per aprire subito uno stato, aggiungi all'indirizzo `?apri=` seguito da `statistiche`, `amici`, `chat`, `veloce`, `amico` oppure `invito` (quest'ultimo invia subito l'invito e mostra l'accettazione). Esempio: `index.html?apri=invito`.

## Carte-pulsante

Ogni modalità è una **carta da gioco colorata** con le proporzioni di una carta siciliana (larghezza/altezza 0,61), una cornice interna come il bordo stampato, l'icona, "1v1" o "2v2" e il sottotitolo, tutto in bianco:

| Carta | Colore | Sottotitolo |
|---|---|---|
| Partita Veloce 1v1 | rosso | Uno contro uno |
| Partita Veloce 2v2 | verde | A coppie |
| Gioca con un amico 1v1 | giallo | Sfida un amico |
| Gioca con un amico 2v2 | blu | Fai squadra |

La carta gialla usa un giallo più carico (`--yellow-card`, `#e9a000`) del giallo dei dettagli (`--yellow`, `#ffc21a`), con un'ombra sotto le scritte, perché il testo bianco si legga. Il contrasto resta comunque più basso di quello delle altre carte.

## Sfondo

Carte siciliane vere negli **spazi vuoti** della pagina:
- **Cavallo e Re di tutti e quattro i semi**, sempre in coppia (a ventaglio, come in mano a chi canta 40);
- tutti gli **Assi** e tutti i **Tre** (i carichi).

Regole (script in `prototipo.js`, parte "Sfondo"):
- le carte **non vanno dietro** le carte-pulsante, i titoli e "giocatori online": lo script misura dove sono e lascia libere quelle zone;
- **eccezione, sugli schermi con poco spazio** (di solito i telefoni): se dopo il primo giro le carte coprono meno del 45% dello spazio libero, un secondo giro mette altre carte anche **dietro le carte-pulsante**, purché ognuna resti visibile almeno per un terzo e spunti nello spazio vuoto. Titoli e "giocatori online" restano sempre liberi;
- le carte **non si sovrappongono mai** fra loro: solo Cavallo e Re di una coppia stanno uno sopra l'altro;
- dietro la **navbar trasparente** le carte sono ammesse e si vedono sfocate;
- le carte possono uscire dallo schermo al massimo per il 40%, così "spuntano" dai bordi;
- lo script prova i punti dello schermo in ordine di precedenza: prima le carte a misura piena (coppie in circa un punto su tre, poi Assi e Tre), poi al 75%, infine carte singole al 55% solo nei buchi stretti;
- spostamenti e rotazioni sono "casuali" ma sempre uguali per lo stesso punto, quindi lo sfondo non cambia ogni volta;
- lo sfondo si ricalcola quando la finestra cambia misura e quando titoli e carte si spostano (per esempio quando arrivano i font da Google).

Misura delle carte a piena grandezza: 60 px su telefono, 84 px su tablet, 104 px su computer.

Parte dello spazio libero coperta dalle carte, misurata il 27/09/2026: 43–53% sui telefoni (360×640, 375×667, 390×844, 412×915), 55% con il telefono in orizzontale (844×390), 50% su tablet (768×1024), 48–56% su computer (1280×720, 1440×900, 1920×1080).

## Layout

**La pagina non scorre mai**, né su telefono né su computer: è alta esattamente quanto lo schermo. Le carte-pulsante si rimpiccioliscono sugli schermi bassi: la loro altezza massima (`--tile-h` in `prototipo.css`) è lo schermo meno navbar, "giocatori online", titoli e spazi.

- **Telefono**: navbar con avatar, "Briscola" e amici; giocatori online al centro; le due sezioni una sotto l'altra, ciascuna con due carte affiancate.
- **Telefono in orizzontale** (altezza fino a 520 px): le quattro carte su una sola fila.
- **Tablet** (da 640 px): carte larghe al massimo 220 px, sezioni centrate. Da 900 px le due sezioni sono affiancate.
- **Computer** (da 1024 px): navbar con le scritte "Mario" e "Amici", carte più grandi e più distanziate.

La **navbar è trasparente e sfocata** (effetto vetro): si vedono, sfocate, le carte dello sfondo che le passano dietro.

Controllato il 27/09/2026 a 360×640, 375×667, 390×844, 412×915, 768×1024, 844×390, 1280×720, 1440×900 e 1920×1080: in tutti i casi il contenuto è alto quanto lo schermo e l'ultima carta-pulsante resta dentro.

## Scelte di interpretazione

- Nel 2v2 "Gioca con un amico" l'amico invitato è il **compagno di squadra**; gli avversari arrivano dal matchmaking. Nel 1v1 l'amico invitato è l'avversario.
- Si invita un amico alla volta; gli amici "In partita" non compaiono tra quelli invitabili.
- Solo tema chiaro: il tema scuro si aggiunge dopo l'ok su questo prototipo.

## Immagini e licenze

| File | Cosa | Fonte | Licenza |
|---|---|---|---|
| `img/seme-denari.svg` | Seme di denari, accanto al nome "Briscola" | Wikimedia Commons, file `Seme_denari_carte_siciliane.svg`, autore Florixc | **Pubblico dominio** |
| `img/cavallo-*.webp`, `img/re-*.webp`, `img/asso-*.webp`, `img/tre-*.webp` (4 semi ciascuno) | Carte dello sfondo, ritagliate dalle scansioni e portate a 200 × 326 px | Wikimedia Commons, file `Carte_da_gioco_siciliane_-_<seme>.jpg`, autore Matsoftware | **CC BY-SA 3.0**: si possono usare citando l'autore e la licenza; i ritagli restano sotto la stessa licenza |

Da ricordare per le pagine vere: le immagini CC BY-SA richiedono una **riga di crediti** visibile nel sito; dove metterla è la domanda D37 di `DA-DECIDERE.md`.

## Risorse esterne

| Risorsa | Da dove | Uso | Licenza |
|---|---|---|---|
| Font **Fredoka** (500, 600, 700) | Google Fonts | Titoli e numeri (vedi tabella sotto) | SIL Open Font License |
| Font **Nunito** (400, 600, 700, 800) | Google Fonts | Tutto il resto del testo | SIL Open Font License |
| Icone **Material Symbols Rounded** | Google Fonts | Icone dell'interfaccia (niente emoji) | Apache 2.0 |

### Dove si usa ogni font

| Font | Dove |
|---|---|
| **Fredoka** | nome "Briscola"; iniziale dell'avatar; "1v1 / 2v2" sulle carte-pulsante; titoli "Partita Veloce" e "Gioca con un amico"; titolo del modal; scelta 150 / 300 / 500; nome nel pannello statistiche; numeri delle statistiche; titolo "Amici" e nome dell'amico in cima alla chat |
| **Nunito** | "giocatori online"; sottotitoli delle carte-pulsante; "Mario" e "Amici" nella navbar (su computer); scritta sopra il titolo del modal; "Punti per vincere"; lista inviti; pulsanti "Gioca", "Invita", "Invia"; etichette delle statistiche; "Impostazioni" ed "Esci"; ricerca, titoletti e nomi nel pannello amici; messaggi della chat; lettere degli avatar piccoli; contatore delle notifiche; messaggi brevi in basso |
| **Material Symbols Rounded** | tutte le icone |

## Cose che le pagine vere NON riprendono

- I parametri `?apri=` e l'accettazione automatica dell'invito dopo 2 secondi.
- Il codice dello sfondo, che nelle pagine vere va nel componente `js/components/CardBackground.js` e le immagini in `app/static/img/cards-bg/` (P22).
- I dati finti (Mario, 24 online, amici, messaggi): nelle pagine vere arrivano dal server.
- Lo script classico: le pagine vere usano moduli ES, che però non partono aprendo un file con un doppio clic.
