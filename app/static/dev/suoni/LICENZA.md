# Suoni da confrontare (P113): autore e licenza

Suoni **candidati** per la scelta dei tre (D47), usati solo dalla pagina di prova `app/static/dev/suoni.html` (elenco in `suoni.json`). Dopo la scelta, i file scelti passano in `app/static/sounds/` (con la riga in `app/static/sounds/LICENZA.md`) e questa cartella si cancella. Non va in `main`.

Tutti i file vengono dai pacchetti di **Kenney** (www.kenney.nl), licenza **CC0 1.0** (<https://creativecommons.org/publicdomain/zero/1.0/>): uso libero, anche modificati, senza obbligo di citare l'autore. Scaricati il 05/10/2026 da:

- **Casino Audio**: <https://kenney.nl/assets/casino-audio>
- **Interface Sounds**: <https://kenney.nl/assets/interface-sounds>
- **UI Audio**: <https://kenney.nl/assets/ui-audio>
- **Impact Sounds**: <https://kenney.nl/assets/impact-sounds>
- **RPG Audio**: <https://kenney.nl/assets/rpg-audio>
- **Music Jingles**: <https://kenney.nl/assets/music-jingles>

| File | Pacchetto | File originale |
|---|---|---|
| `card-place-x3.mp3` | Casino Audio | `card-place-3` |
| `card-place-4.mp3` | Casino Audio | `card-place-4` |
| `card-slide-5.mp3` … `card-slide-8.mp3` | Casino Audio | `card-slide-5` … `card-slide-8` |
| `pack-take-out-1.mp3`, `pack-take-out-2.mp3` | Casino Audio | `cards-pack-take-out-1`, `-2` |
| `pack-open-1.mp3`, `pack-open-2.mp3` | Casino Audio | `cards-pack-open-1`, `-2` |
| `card-shuffle-full.mp3` | Casino Audio | `card-shuffle` (intero) |
| `card-fan-1.mp3`, `card-fan-2.mp3` | Casino Audio | `card-fan-1`, `-2` |
| `card-shove-1.mp3`, `card-shove-3.mp3`, `card-shove-4.mp3` | Casino Audio | `card-shove-1`, `-3`, `-4` |
| `chips-stack-1.mp3`, `chips-stack-5.mp3` | Casino Audio | `chips-stack-1`, `-5` |
| `chips-collide-2.mp3` | Casino Audio | `chips-collide-2` |
| `chips-handle-2.mp3` | Casino Audio | `chips-handle-2` |
| `pluck-1.mp3`, `drop-1.mp3`, `drop-2.mp3`, `bong-1.mp3`, `question-1.mp3` | Interface Sounds | `pluck_001`, `drop_001`, `drop_002`, `bong_001`, `question_001` |
| `tick-4.mp3`, `click-1.mp3`, `click-3.mp3` | Interface Sounds | `tick_004`, `click_001`, `click_003` |
| `glass-1.mp3`, `select-3.mp3` | Interface Sounds | `glass_001`, `select_003` |
| `confirmation-1.mp3`, `confirmation-4.mp3`, `maximize-3.mp3` | Interface Sounds | `confirmation_001`, `confirmation_004`, `maximize_003` |
| `minimize-8.mp3`, `back-2.mp3`, `switch-5.mp3`, `toggle-2.mp3` | Interface Sounds | `minimize_008`, `back_002`, `switch_005`, `toggle_002` |
| `ui-click-1.mp3`, `ui-click-2.mp3` | UI Audio | `click1`, `click2` |
| `impact-light-1.mp3` | Impact Sounds | `impactGeneric_light_001` |
| `book-place-1.mp3`, `book-place-2.mp3`, `book-flip-1.mp3`, `book-flip-2.mp3` | RPG Audio | `bookPlace1`, `bookPlace2`, `bookFlip1`, `bookFlip2` |
| `cloth-1.mp3`, `coins.mp3`, `metal-click.mp3` | RPG Audio | `cloth1`, `handleCoins`, `metalClick` |
| `jingle-pizzi-00.mp3`, `jingle-pizzi-03.mp3`, `jingle-pizzi-07.mp3` | Music Jingles | `jingles_PIZZI00`, `03`, `07` |
| `jingle-steel-00.mp3`, `jingle-steel-03.mp3`, `jingle-sax-00.mp3` | Music Jingles | `jingles_STEEL00`, `jingles_STEEL03`, `jingles_SAX00` |

**Come sono stati preparati**: come quelli di `app/static/sounds/` (P109), dai file `.ogg` a **MP3 mono, 44,1 kHz, 80 kbit/s** con `ffmpeg` e `libmp3lame`, con il volume pareggiato intorno a −27 dB di media e il picco sotto −1 dB (`-af volume=…dB -ac 1 -ar 44100 -c:a libmp3lame -b:a 80k`). In tutto circa 320 kB.
