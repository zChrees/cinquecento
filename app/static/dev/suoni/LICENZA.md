# Suoni da confrontare (P115): autore e licenza

Suoni **candidati** per i tre avvisi del menu (P115), usati solo dalla pagina di prova `app/static/dev/suoni.html` (elenco in `suoni.json`). Vengono dai candidati di P113 (commit `a9a24fc`). Dopo la scelta di Christian, i file scelti passano in `app/static/sounds/` (con la riga in `app/static/sounds/LICENZA.md`) e questa cartella, con la pagina, si cancella. Non va in `main`.

Tutti i file vengono dai pacchetti di **Kenney** (www.kenney.nl), licenza **CC0 1.0** (<https://creativecommons.org/publicdomain/zero/1.0/>): uso libero, anche modificati, senza obbligo di citare l'autore. Scaricati il 05/10/2026 da:

- **Interface Sounds**: <https://kenney.nl/assets/interface-sounds>
- **Music Jingles**: <https://kenney.nl/assets/music-jingles>
- **Casino Audio**: <https://kenney.nl/assets/casino-audio>

| File | Pacchetto | File originale |
|---|---|---|
| `maximize-3.mp3`, `pluck-1.mp3`, `question-1.mp3` | Interface Sounds | `maximize_003`, `pluck_001`, `question_001` |
| `glass-1.mp3`, `select-3.mp3`, `bong-1.mp3` | Interface Sounds | `glass_001`, `select_003`, `bong_001` |
| `jingle-steel-00.mp3`, `jingle-pizzi-00.mp3` | Music Jingles | `jingles_STEEL00`, `jingles_PIZZI00` |
| `chips-stack-1.mp3` | Casino Audio | `chips-stack-1` |

**Come sono stati preparati**: come quelli di `app/static/sounds/` (P109), dai file `.ogg` a **MP3 mono, 44,1 kHz, 80 kbit/s** con `ffmpeg` e `libmp3lame`, con il volume pareggiato intorno a −27 dB di media e il picco sotto −1 dB.
