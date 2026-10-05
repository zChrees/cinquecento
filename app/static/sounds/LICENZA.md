# Suoni del tavolo: autore e licenza

I suoni del tavolo (P103, rifatti con suoni registrati dal vero in P109, 05/10/2026), usati da `js/core/sounds.js` (l'elenco nome → file è `SOUNDS`).

| File | Momento | Fonte (file originale) | Licenza |
|---|---|---|---|
| `card-place-1.mp3`, `card-place-2.mp3`, `card-place-3.mp3` | una carta si posa sul tavolo (a fine lancio) | Kenney, **Casino Audio**: `card-place-1`, `card-place-2`, `card-place-4` | **CC0** |
| `card-slide-1.mp3` … `card-slide-4.mp3` | pescata | Casino Audio: `card-slide-1` … `card-slide-4` | CC0 |
| `card-shuffle.mp3` | mescolata a inizio mano | Casino Audio: `card-shuffle` (primi 1,1 s, con 0,3 s di dissolvenza) | CC0 |
| `card-fan.mp3` | distribuzione | Casino Audio: `card-fan-1` | CC0 |
| `card-gather.mp3` | presa raccolta | Casino Audio: `card-slide-1` e `card-slide-3` sovrapposti, il secondo 90 ms dopo (P109, al posto di `card-shove-1` e `-2`, che avevano molto rumore di fondo) | CC0 |
| `cards-laid-down.mp3` | "Cala le carte" | Casino Audio: `card-fan-2` | CC0 |
| `chips-stack.mp3` | canto (40 o 20) | Casino Audio: `chips-stack-3` | CC0 |
| `phrase.mp3` | frase al tavolo | Kenney, **Interface Sounds**: `pluck_002` | CC0 |
| `tick.mp3`, `tick-last.mp3` | ultimi 5 secondi del tuo turno | Interface Sounds: `tick_001`, `tick_002` | CC0 |
| `win.mp3`, `lose.mp3`, `tie.mp3` | fine partita: vittoria, sconfitta, pareggio | Interface Sounds: `confirmation_002`, `minimize_005`, `switch_003` | CC0 |

**Fonte**: <https://kenney.nl/assets/casino-audio> e <https://kenney.nl/assets/interface-sounds> (autore Kenney, www.kenney.nl), scaricati il 05/10/2026. **Licenza CC0 1.0** (<https://creativecommons.org/publicdomain/zero/1.0/>): uso libero, anche modificati, senza obbligo di citare l'autore (lo citiamo comunque qui). Il testo della licenza è nel file `License.txt` dei due pacchetti.

**Come sono stati preparati**: dai file `.ogg` dei pacchetti a **MP3 mono, 44,1 kHz, 80 kbit/s** (lo leggono tutti i browser, anche Safari su iPhone, che con l'OGG non sempre funziona), con `ffmpeg` (`-af volume=…dB -ac 1 -ar 44100 -c:a libmp3lame -b:a 80k`). Il volume è stato pareggiato intorno a −27 dB di media: carte quasi invariate (0, +2 o −2/−4 dB), suoni dell'interfaccia abbassati da −6 a −12 dB, perché nei pacchetti sono molto più forti. In tutto circa **120 kB**.

**Presa raccolta** (P109, completato il 05/10/2026): `ffmpeg -i card-slide-1.ogg -i card-slide-3.ogg -filter_complex "[1]adelay=90[b];[0][b]amix=inputs=2:normalize=0,volume=-3dB" -ac 1 -ar 44100 -c:a libmp3lame -b:a 80k card-gather.mp3`. Il suono di "tocca a te" (`glass_001`, un "ding" di vetro) è stato tolto su richiesta di Christian: restano l'anello del tempo e il ticchettio.
