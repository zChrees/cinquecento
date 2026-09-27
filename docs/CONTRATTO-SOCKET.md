# Contratto tra server e pagine (P8)

> **Stato: approvato da Giuseppe, Antonio e Christian il 28/09/2026.**
> Dopo l'approvazione, un cambiamento a questo file si propone agli altri due e si fa solo con l'accordo di tutti e tre, perché lo usano P15, P21, P22, P23, P24, P25, P28, P29, P30, P40, P44, P45, P46, P47, P48, P55 e P56.

Questo documento fissa **come si parlano il server e le pagine**: i nomi degli eventi in tempo reale (Socket.IO), le richieste HTTP in JSON e la forma dei dati di ciascuno. Serve a lavorare in parallelo: chi scrive le pagine usa i file di esempio in `app/static/dev/`, chi scrive il server produce esattamente quei dati.

File di esempio (rispettano questo contratto):

| File | Cosa contiene | Chi lo usa |
|---|---|---|
| `app/static/dev/vista_1v1.json` | la vista di gioco di un giocatore, 1v1, nel suo turno | P15 (formato), P21, P24 |
| `app/static/dev/vista_2v2.json` | la vista di gioco, 2v2, turno di un altro, un giocatore scollegato | P15 (formato), P21, P24 |
| `app/static/dev/home_esempio.json` | dati della home: utente, stato, coda, partita trovata | P22, P28, P44 |
| `app/static/dev/statistiche_esempio.json` | dati del pannello statistiche | P40, P30 |
| `app/static/dev/amici_esempio.json` | lista amici, chat, inviti, presenza | P45, P46, P47, P48 |

Nei file di esempio la chiave `_nota` è solo un commento: il server non la manda e le pagine la ignorano.

---

## 1. Regole comuni

### 1.1 Nomi e valori

- **Eventi**: `area:azione`, in inglese e minuscolo (`game:play_card`, `queue:join`). Quelli che manda la pagina sono verbi (`game:play_card`); quelli che manda il server descrivono uno stato o un fatto (`game:state`, `invite:received`).
- **Chiavi JSON** in inglese, `snake_case`. I testi da mostrare (messaggi di errore) sono in italiano.
- **Modalità**: `"1v1"` oppure `"2v2"`. **Punti per vincere** (`target_score`): solo `150`, `300` o `500`.
- **Semi**: `"denari"`, `"coppe"`, `"spade"`, `"bastoni"` (sono nomi propri del gioco, come nel regolamento).
- **Carta**: `{"suit": "coppe", "rank": 10}`. `rank` va da 1 a 10: **1 = Asso**, 2–7 le carte numerate, **8 = Fante, 9 = Cavallo, 10 = Re**. È la stessa coppia degli attributi `data-suit` e `data-rank` del componente carta (P20). Il motore può rappresentarla come vuole al suo interno: la conversione la fa la vista (P15).
- **Utenti**: sempre con il numero (`user_id`) e, dove si mostrano, `username` e `avatar`. `avatar` è il codice di un avatar del set (D29) oppure `null`: con `null` la pagina mostra l'iniziale del nome.
- **Date e ore**: testo ISO 8601 in UTC, con i millesimi e la `Z` finale (`"2026-09-28T14:03:12.000Z"`). La pagina le converte nell'ora italiana.
- **Tempi che scorrono** (turno, invito, attesa per rientrare): il server manda i **secondi rimasti** nel momento dell'invio (`seconds_left`, anche con decimali) e la pagina conta alla rovescia da sola. Niente orari assoluti, perché l'orologio del telefono può essere sbagliato.

### 1.2 Risposte ed errori

Ogni evento che la pagina manda al server riceve **una risposta** (in Socket.IO si chiama *ack*: una funzione che il server richiama quando ha finito). Le richieste HTTP rispondono con la stessa forma:

```json
{"ok": true, "data": { ... }}
{"ok": false, "error": {"code": "not_your_turn", "message": "Non è il tuo turno."}}
```

- `data` può mancare quando non c'è niente da restituire.
- `error.code` è uno dei codici della tabella sotto: la pagina decide cosa fare in base al codice; `error.message` è il testo in italiano da mostrare così com'è.
- Gli errori vanno **solo a chi ha mandato la richiesta**, mai agli altri giocatori.
- Nessuna correzione silenziosa: un dato non valido si rifiuta.
- Finché non arriva la risposta, la pagina tiene disattivato il pulsante che ha mandato la richiesta.

| Codice | Quando | HTTP |
|---|---|---|
| `invalid_data` | dato mancante, del tipo sbagliato, troppo lungo o fuori elenco | 400 |
| `not_logged_in` | serve il login | 401 |
| `not_allowed` | l'utente non può fare questa azione (es. non è seduto a quel tavolo) | 403 |
| `blocked` | c'è un blocco tra i due utenti (D23) | 403 |
| `not_found` | l'utente, la partita o l'invito non esiste (o non esiste più) | 404 |
| `not_friends` | l'azione richiede che siate amici | 403 |
| `not_your_turn` | mossa fuori turno | — |
| `illegal_move` | mossa non ammessa dalle regole | — |
| `stale_state` | la mossa si riferisce a una vista vecchia (vedi 3.2) | — |
| `busy` | l'utente (o l'amico) è già in partita, in coda o ha un invito in sospeso | 409 |
| `already_exists` | amicizia o richiesta già esistente | 409 |
| `request_from_them` | l'altro ti ha già mandato una richiesta: va accettata | 409 |
| `limit_reached` | superato un limite fisso (es. 100 amici, D26) | 409 |
| `too_fast` | troppe richieste ravvicinate (chat: 1 al secondo, frasi del tavolo: 1 ogni 3 secondi); c'è anche `error.retry_after`, i secondi da aspettare | 429 |
| `expired` | l'invito è scaduto | 410 |
| `offline` | l'amico non è collegato | — |
| `server_error` | errore imprevisto del server (il dettaglio va solo nel log) | 500 |

### 1.3 Richieste che creano qualcosa: `request_id`

Le richieste che **creano** qualcosa portano `request_id`: un testo generato dalla pagina con `crypto.randomUUID()`, **lo stesso per tutti i tentativi della stessa azione** (per esempio se la connessione cade e la pagina rimanda la richiesta). Se il server riceve due volte lo stesso `request_id` dallo stesso utente, non crea un doppione e risponde come la prima volta. Lo portano: `queue:join`, `invite:send`, `chat:send`, `POST /friends/requests`, `POST /friends/blocks`.

Le mosse di gioco non lo usano: le protegge `version` (vedi 3.2).

### 1.4 Collegamento

- Una connessione Socket.IO per scheda, aperta da `core/socket.js` (P23), con riconnessione automatica.
- **Si collega solo chi ha fatto il login**: senza login il server rifiuta la connessione e la pagina riceve l'errore di connessione con il messaggio `not_logged_in`.
- Se la connessione manca, la pagina non manda niente e lo dice all'utente (nessuna azione parte senza connessione).
- Dopo una riconnessione il server rimanda lo stato attuale (`home:status`, oppure `game:state` se la pagina rientra nella partita con `game:join`).

### 1.5 Dati scritti nella pagina dal server

Chi è l'utente la pagina lo sa **senza chiederlo**: `base.html` scrive nel `<body>` gli attributi `data-user-id`, `data-username` e `data-avatar` (vuoti per chi non ha fatto il login), e nell'`<head>` il tag `<meta name="csrf-token" content="...">`. Le richieste HTTP che modificano qualcosa (`POST`, `DELETE`) mandano quel valore nell'intestazione `X-CSRFToken` (protezione CSRF di Flask-WTF).

---

## 2. Richieste HTTP in JSON

Tutte richiedono il login e rispondono nella forma di 1.2.

### 2.1 Statistiche (P30; dati finti per P40)

`GET /stats/me` → `data` come in `statistiche_esempio.json`:

| Campo | Significato |
|---|---|
| `games`, `wins`, `losses`, `draws` | partite giocate, vinte, perse, pareggiate (tutte le modalità e i punteggi; una partita abbandonata è persa) |
| `win_rate` | percentuale di vittorie, intero da 0 a 100; `null` se non ha ancora giocato |
| `ratings["1v1"]`, `ratings["2v2"]` | `value` (intero arrotondato), `games` (partite che contano per il rating in quella modalità), `provisional` (`true` per le prime 10, D9) |

Chi non ha mai giocato in una modalità ha `value: 1500`, `games: 0`, `provisional: true`. Si vedono solo le proprie statistiche.

### 2.2 Amici (P45; dati finti per P46)

| Richiesta | Corpo | Cosa fa |
|---|---|---|
| `GET /friends/` | — | lista amici, richieste e contatori (`data` come `"GET /friends/"` in `amici_esempio.json`) |
| `POST /friends/requests` | `{"request_id", "username"}` | manda una richiesta a chi ha **esattamente** quello username (D33, maiuscole comprese) |
| `POST /friends/requests/<user_id>/accept` | — | accetta la richiesta ricevuta da `user_id` |
| `POST /friends/requests/<user_id>/decline` | — | rifiuta (la richiesta si cancella: si potrà rimandare) |
| `DELETE /friends/requests/<user_id>` | — | annulla una richiesta mandata |
| `DELETE /friends/<user_id>` | — | toglie l'amicizia, per tutti e due |
| `POST /friends/blocks` | `{"request_id", "user_id"}` | blocca l'utente e toglie l'amicizia (D23) |
| `DELETE /friends/blocks/<user_id>` | — | toglie il blocco |

Accettare, rifiutare o togliere una seconda volta la stessa cosa risponde `ok` senza fare niente.

Nella lista, `presence` di un amico è `"online"`, `"in_game"` oppure `"offline"`. Non c'è "visto 2 ore fa" del prototipo: il database non salva l'ultimo accesso. `unread` è il numero di messaggi non letti da quell'amico. `counters.requests_in` e `counters.unread_messages` servono al contatore sull'icona degli amici, che ne mostra la somma. Per privacy, un utente che ti ha bloccato risponde come uno inesistente (`not_found`).

---

## 3. Partita

### 3.1 Posti al tavolo

I posti (`seat`) sono numerati da 0 **nell'ordine di gioco** (verso destra, D11): dopo il posto 0 gioca l'1, poi il 2… Nel 1v1 i posti sono 0 e 1, e ognuno è una squadra (`team` 0 e 1). Nel 2v2 i posti sono 0–3, con **squadra 0 = posti 0 e 2** e **squadra 1 = posti 1 e 3**, i compagni uno di fronte all'altro. Sono gli stessi numeri di `giocatori_partita.posto` e `squadra` nel database. La pagina disegna sempre te in basso e gli altri attorno, nell'ordine dei posti.

### 3.2 Eventi

| Evento | Chi → chi | Dati | Risposta |
|---|---|---|---|
| `game:join` | pagina → server | `{"game_id"}` | `ok`, poi arrivano `game:phrases` e `game:state` |
| `game:play_card` | pagina → server | `{"game_id", "version", "card"}` | `ok` o errore |
| `game:sing` | pagina → server | `{"game_id", "version", "suit"}` | `ok` o errore |
| `game:send_phrase` | pagina → server | `{"game_id", "code"}` | `ok` o errore (`too_fast` con `retry_after`) |
| `game:leave` | pagina → server | `{"game_id"}` | `ok`: la partita è persa per abbandono, subito |
| `game:state` | server → ogni giocatore | la **sua** vista (3.3) | — |
| `game:sang` | server → tutti al tavolo | `{"seat", "suit", "points", "cards", "show_seconds"}` | — |
| `game:phrases` | server → chi entra | `{"phrases": [{"code", "text"}]}` | — |
| `game:phrase` | server → tutti al tavolo | `{"seat", "code"}` | — |
| `game:replaced` | server → la scheda sostituita | `{"game_id"}` | — |
| `game:start` | server → i giocatori della nuova partita | `{"game_id", "url"}` | — |

- **`game:start`** arriva quando la coda o un invito creano la partita: la pagina va all'indirizzo `url` (`/game/<game_id>`). `game_id` è il codice della stanza in memoria, un testo; non è il numero della partita nel database, che esiste solo a fine partita.
- **`game:join`** lo manda la pagina del tavolo appena collegata; serve anche per rientrare dopo una disconnessione (entro 60 secondi). Se lo stesso utente fa `game:join` da un'altra scheda o dispositivo, **l'ultima prende il posto** della precedente, che riceve `game:replaced` e mostra "partita aperta altrove" (D14).
- **`version`**: ogni vista ha un numero che sale a ogni cambiamento della partita. `game:play_card` e `game:sing` mandano il numero della vista su cui l'utente ha deciso; se nel frattempo la partita è cambiata, il server risponde `stale_state` e rimanda la vista attuale. Così il doppio clic e le due schede non giocano due carte.
- **Dopo ogni mossa accettata** il server manda a ogni giocatore la sua nuova vista (`game:state`). Anche il turno scaduto (mossa automatica, D12) e i cambi di connessione di un giocatore producono una nuova vista.
- **Canto** (D15): `game:sang` porta le due carte mostrate (`cards`: Re e Cavallo del seme); la pagina le mostra per `show_seconds` secondi (3). Nella vista resta l'elenco dei canti della mano (`sings`), per l'icona fissa accanto a chi ha cantato.
- **Frasi del tavolo** (D24, P55–P56): l'elenco arriva con `game:phrases` a ogni ingresso nella stanza, e la pagina non ne tiene una copia sua. `game:phrase` porta solo il codice: il testo si prende dall'elenco. Le frasi non si salvano e chi rientra non vede quelle arrivate nel frattempo.
- **`game:leave`**: il pulsante "esci" del tavolo, dopo la conferma nella pagina. Vale come abbandono (nel 2v2 perde tutta la squadra, D13).

### 3.3 Vista di gioco (`game:state`)

Esempi completi: `vista_1v1.json` e `vista_2v2.json`. La vista contiene **solo quello che quel giocatore può vedere**: mai le carte in mano agli altri, mai l'ordine o il contenuto del mazzo, mai le carte già prese nella mano in corso.

| Campo | Significato |
|---|---|
| `game_id`, `version` | codice della stanza e numero della vista (3.2) |
| `mode`, `target_score` | modalità e punti per vincere |
| `rated` | `false` solo nel 1v1 contro un amico (D36) |
| `status` | `"playing"` oppure `"finished"` |
| `hand_number` | numero della mano, da 1 |
| `dealer_seat` | posto del mazziere (D11) |
| `you` | `{"seat"}`: il tuo posto |
| `players` | per ogni posto: `seat`, `team`, `user_id`, `username`, `avatar`, `cards_in_hand` (solo il numero), `connected`, `reconnect_seconds_left` (secondi che restano per rientrare se è scollegato, altrimenti `null`) |
| `hand` | le **tue** carte |
| `trick` | la presa in corso: `leader_seat` (chi l'ha aperta) e `cards`, un elenco di `{"seat", "card"}` nell'ordine in cui sono state giocate |
| `last_trick` | l'ultima presa chiusa: `winner_seat` e `cards`; `null` a inizio mano. Serve a mostrare per un momento com'è finita |
| `trump` | seme di briscola, oppure `null` finché nessuno ha cantato 40 (carte franche) |
| `deck_count` | carte rimaste nel mazzo |
| `sings` | canti della mano in corso: `{"seat", "suit", "points"}` (40 o 20), in ordine |
| `scores` | per ogni squadra: `{"team", "total"}`, i punti delle mani **già finite** |
| `last_hand` | riepilogo dell'ultima mano finita: `hand_number` e, per ogni squadra, `card_points`, `sing_points`, `hand_total`; `null` nella prima mano |
| `turn` | `{"seat", "seconds_total", "seconds_left"}`: di chi è il turno e quanto tempo gli resta (30 secondi); `null` a partita finita |
| `legal` | le tue mosse ammesse adesso: `play` (carte giocabili) e `sing` (semi che puoi cantare); **liste vuote quando non è il tuo turno** |
| `result` | `null` durante la partita; a partita finita: `reason` (`"score"` o `"abandon"`), `winner_team` (0, 1, oppure `null` per il pareggio), `abandoned_seats` (posti di chi ha abbandonato) e `scores` finali |

La pagina **non calcola regole**: attiva solo le carte di `legal.play` e i pulsanti "Canta" dei semi in `legal.sing`. Il punto "40 o 20" lo decide il server. I punti delle carte prese si vedono solo a fine mano, in `last_hand` (come al tavolo vero, dove le prese stanno coperte).

---

## 4. Code di matchmaking (P28, P29)

| Evento | Chi → chi | Dati | Risposta |
|---|---|---|---|
| `queue:join` | pagina → server | `{"request_id", "mode", "target_score"}` | `ok` con `data` = stato della coda, o errore (`busy`) |
| `queue:leave` | pagina → server | `{}` | `ok` (anche se non era in coda) |
| `queue:status` | server → chi è in coda | stato della coda | — |
| `queue:left` | server → chi era in coda | `{"reason"}`: `"cancelled"` (ha annullato, anche da un'altra scheda) o `"partner_left"` (nel 2v2 il compagno è uscito) | — |

Stato della coda (esempio `"queue:status"` in `home_esempio.json`): `mode`, `target_score`, `seconds_waiting` (da quanto è in coda), `rating_range` (`{"min", "max"}` dell'intervallo di rating accettato adesso, oppure `null` quando si accetta qualunque avversario) e `partner` (`{"user_id", "username", "avatar"}` dell'amico compagno nel 2v2, altrimenti `null`). Il server lo rimanda ogni volta che l'intervallo si allarga (ogni 10 secondi, D16); tra un invio e l'altro la pagina conta i secondi da sola. Le code sono separate per modalità e punteggio. Quando la partita è pronta arriva `game:start` (3.2).

Il 2v2 con un amico non passa da `queue:join`: la coppia entra in coda con `invite:start` (5.3).

---

## 5. Home, amici online, inviti e chat

### 5.1 Home (P44)

| Evento | Chi → chi | Dati |
|---|---|---|
| `home:status` | server → pagina, appena collegata e poi a ogni cambiamento | `{"online_count", "resume"}` |

`online_count` conta gli utenti collegati (lo stesso utente con due schede conta una volta). `resume` è `null`, oppure `{"game_id", "url", "mode", "target_score"}` quando l'utente ha una partita in corso da cui rientrare: la home mostra "Hai una partita in corso: rientra".

### 5.2 Amici online (P47)

| Evento | Chi → chi | Dati |
|---|---|---|
| `friends:presence` | server → gli amici di chi cambia stato | `{"user_id", "presence"}` (`"online"`, `"in_game"`, `"offline"`) |
| `friends:changed` | server → l'utente | `{"reason"}`: `"request_received"`, `"request_accepted"`, `"request_declined"`, `"friend_removed"`, `"blocked"` |

Con `friends:changed` la pagina ricarica la lista con `GET /friends/`: così la forma della lista resta una sola.

### 5.3 Inviti a partita (P47, D27)

| Evento | Chi → chi | Dati | Risposta |
|---|---|---|---|
| `invite:send` | chi invita → server | `{"request_id", "user_id", "mode", "target_score"}` | `ok` con `data` = l'invito, o errore (`not_friends`, `offline`, `busy`) |
| `invite:received` | server → l'invitato | l'invito | — |
| `invite:accept` | l'invitato → server | `{"invite_id"}` | `ok` o errore (`expired`, `not_found`, `busy`) |
| `invite:decline` | l'invitato → server | `{"invite_id"}` | `ok` |
| `invite:cancel` | chi invita → server | `{"invite_id"}` | `ok` |
| `invite:start` | chi invita → server, dopo l'accettazione ("Gioca") | `{"invite_id"}` | `ok` o errore |
| `invite:update` | server → tutti e due | `{"invite_id", "status"}` | — |

- **Invito** (esempio in `amici_esempio.json`): `invite_id`, `from` e `to` (`{"user_id", "username", "avatar"}`), `mode`, `target_score`, `status`, `seconds_left`.
- `status`: `"pending"` (in attesa), `"accepted"`, `"declined"`, `"expired"` (60 secondi senza risposta), `"cancelled"` (chi invita ha chiuso il modal o si è scollegato), `"started"`.
- Si invita **un amico alla volta**: un secondo `invite:send` mentre un invito è `pending` o `accepted` risponde `busy`. Dopo un rifiuto o una scadenza chi invita vede un avviso e può invitare un altro amico (D27).
- **"Gioca" si attiva solo quando lo stato è `accepted`**. Con `invite:start`: nel **1v1** il server crea la partita e manda `game:start` a tutti e due (non conta per il rating); nel **2v2** i due entrano insieme nella coda come coppia e ricevono `queue:status` con `partner` (conta per il rating).

### 5.4 Chat tra amici (P48)

| Evento | Chi → chi | Dati | Risposta |
|---|---|---|---|
| `chat:history` | pagina → server | `{"user_id", "before_id"}` | `ok` con `data` = `{"messages", "has_more", "can_write"}` |
| `chat:send` | pagina → server | `{"request_id", "user_id", "text"}` | `ok` con `data` = `{"message"}`, o errore |
| `chat:read` | pagina → server | `{"user_id"}` | `ok` |
| `chat:message` | server → destinatario (e alle altre schede di chi scrive) | `{"message"}` | — |

- **Messaggio**: `{"id", "from_user_id", "to_user_id", "text", "sent_at"}`.
- `chat:history` restituisce al massimo 50 messaggi, **dal più vecchio al più nuovo**; `before_id` è `null` per gli ultimi, oppure l'`id` del messaggio più vecchio già caricato per quelli prima. Aprire la chat segna come letti i messaggi ricevuti; con la chat aperta, `chat:read` segna quelli appena arrivati.
- `can_write` è `false` se l'amicizia è finita o c'è un blocco: la conversazione si legge ma non si scrive (D24), e `chat:send` risponde `not_friends` o `blocked`.
- `text`: al massimo 1000 caratteri (D26) e non vuoto né fatto solo di spazi, altrimenti `invalid_data`; si salva così com'è, senza correzioni; più di 1 messaggio al secondo → `too_fast`. Il testo si mostra **sempre con `textContent`**, mai come HTML, e non va mai nei log.
