# Suoni del tavolo e del menu: autore e licenza

I suoni del tavolo (P103, rifatti con suoni registrati dal vero in P109, scelti dal gruppo con la pagina di P113 il 05/10/2026, D47) e quelli del menu (P115: proposti da Claude e scelti da Christian il 07/10/2026, D48, scambiando quelli di richiesta di amicizia e invito), usati da `js/core/sounds.js` (l'elenco nome → file è `SOUNDS`).

| File | Momento | Fonte (file originale) | Licenza |
|---|---|---|---|
| `card-place.mp3` | una carta si posa sul tavolo (a fine lancio) | Kenney, **Casino Audio**: `card-place-2` | **CC0** |
| `card-slide-1.mp3` … `card-slide-4.mp3` | pescata (uno a caso per carta) | Casino Audio: `card-slide-1` … `card-slide-4` | CC0 |
| `deck-riffle.mp3` | mescolata a inizio mano | Casino Audio: `card-fan-2` | CC0 |
| `card-deal.mp3` | ogni carta distribuita, quando arriva | Casino Audio: `card-place-4` | CC0 |
| `card-gather.mp3` | presa raccolta | Casino Audio: `card-slide-1` e `card-slide-3` sovrapposti, il secondo 90 ms dopo (P109, al posto di `card-shove-1` e `-2`, che avevano molto rumore di fondo) | CC0 |
| `cards-laid-down.mp3` | "Cala le carte" | Casino Audio: `card-shove-1` | CC0 |
| `sing.mp3` | canto (40 o 20) | Kenney, **Music Jingles**: `jingles_SAX06` | CC0 |
| `phrase.mp3` | frase al tavolo | Kenney, **Interface Sounds**: `drop_002` | CC0 |
| `tick.mp3`, `tick-last.mp3` | ultimi 5 secondi del tuo turno | Interface Sounds: `tick_001`, `tick_002` | CC0 |
| `win.mp3`, `lose.mp3` | fine partita: vittoria, sconfitta | Music Jingles: `jingles_HIT01`, `jingles_PIZZI07` | CC0 |
| `tie.mp3` | fine partita: pareggio | Kenney, **Digital Audio**: `threeTone1` | CC0 |
| `friend-request.mp3` | P115: richiesta di amicizia ricevuta | Interface Sounds: `confirmation_004` | CC0 |
| `chat-message.mp3` | P115: messaggio di un amico | Interface Sounds: `drop_001` | CC0 |
| `invite.mp3` | P115: invito a una partita | Interface Sounds: `confirmation_001` | CC0 |

**Fonte**: <https://kenney.nl/assets/casino-audio>, <https://kenney.nl/assets/interface-sounds>, <https://kenney.nl/assets/music-jingles> e <https://kenney.nl/assets/digital-audio> (autore Kenney, www.kenney.nl), scaricati il 05/10/2026. **Licenza CC0 1.0** (<https://creativecommons.org/publicdomain/zero/1.0/>): uso libero, anche modificati, senza obbligo di citare l'autore (lo citiamo comunque qui). Il testo della licenza è nel file `License.txt` dei pacchetti.

**Come sono stati preparati**: dai file `.ogg` dei pacchetti a **MP3 mono, 44,1 kHz, 80 kbit/s** (lo leggono tutti i browser, anche Safari su iPhone, che con l'OGG non sempre funziona), con `ffmpeg` (`-af volume=…dB -ac 1 -ar 44100 -c:a libmp3lame -b:a 80k`). Il volume è stato pareggiato intorno a −27 dB di media, con il picco sotto −1 dB: carte quasi invariate, suoni dell'interfaccia e jingle abbassati, perché nei pacchetti sono molto più forti. In tutto circa **110 kB**.

**Presa raccolta** (P109, completato il 05/10/2026): `ffmpeg -i card-slide-1.ogg -i card-slide-3.ogg -filter_complex "[1]adelay=90[b];[0][b]amix=inputs=2:normalize=0,volume=-3dB" -ac 1 -ar 44100 -c:a libmp3lame -b:a 80k card-gather.mp3`. Il suono di "tocca a te" (`glass_001`, un "ding" di vetro) è stato tolto su richiesta di Christian: restano l'anello del tempo e il ticchettio. Con la scelta del 05/10 (D47) "tocca a te" e la fine della mano restano senza suono.
