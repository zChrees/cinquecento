/**
 * Suoni al tavolo (P103, rifatti in P109 con suoni veri, scelti dal gruppo in P113) e,
 * da P115, quelli del menu (richiesta di amicizia, messaggio, invito):
 * file dei pacchetti Kenney "Casino Audio" (carte), "Interface Sounds" (frasi,
 * ticchettio), "Music Jingles" e "Digital Audio" (canto, fine partita), licenza CC0;
 * dettagli in sounds/LICENZA.md.
 *
 *   preloadSounds({ now: true }) // la pagina del tavolo, una volta, appena si apre
 *   playSound('card')           // subito
 *   playSound('draw', 500)      // tra 500 ms (in fila con le animazioni)
 *   soundsEnabled() / setSoundsEnabled(false)
 *
 * I file si scaricano con fetch, senza bloccare la pagina. Il contesto audio si crea al
 * primo tocco o tasto, oppure (P118, `now`) subito, all'apertura del tavolo, prima del
 * primo ridisegno: mai durante un ridisegno, che bloccava per più di 100 ms (P109).
 * I browser fanno suonare la pagina solo dopo un gesto: Chrome conta anche il clic
 * nella pagina di prima dello stesso sito ("Gioca" nella home), così si sente la
 * distribuzione della prima mano; Safari no, e il contesto resta sospeso fino al primo
 * tocco. Prima di allora, o se il browser non ha Web Audio, non suona niente e la
 * pagina funziona lo stesso.
 *
 * La scelta acceso/spento si ricorda nel browser (localStorage, chiave SOUNDS_KEY);
 * all'inizio i suoni sono accesi. La cambia l'interruttore "Suoni" della pagina delle
 * impostazioni, e vale per tutti i suoni (P115: anche quelli del menu).
 *
 * Per i test: ogni suono che parte manda sul documento l'evento "cinquecento:sound"
 * con { name }, anche quando il browser non lo fa sentire; con i suoni spenti niente.
 */

export const SOUNDS_KEY = 'cinquecento.sounds';
const BASE = new URL('../../sounds/', import.meta.url).href;
const VOLUME = 0.8;

// Nome del suono → file (più di uno: se ne sceglie uno a caso, così non sembra un disco)
export const SOUNDS = {
  card: ['card-place'], // una carta si posa sul tavolo
  draw: ['card-slide-1', 'card-slide-2', 'card-slide-3', 'card-slide-4'], // pescata
  shuffle: ['deck-riffle'], // mescolata a inizio mano
  deal: ['card-deal'], // ogni carta distribuita, quando arriva (D47)
  trick: ['card-gather'], // presa raccolta
  lay_down: ['cards-laid-down'], // calata
  sing: ['sing'], // canto
  phrase: ['phrase'], // frase al tavolo
  tick: ['tick'], // ultimi secondi del tuo turno (nessun suono quando comincia: P109)
  last_tick: ['tick-last'],
  win: ['win'],
  lose: ['lose'],
  tie: ['tie'],
  // P115, suoni del menu (provvisori: li sceglie Christian con app/static/dev/suoni.html)
  friend_request: ['friend-request'], // richiesta di amicizia ricevuta
  message: ['chat-message'], // messaggio di un amico
  invite: ['invite'], // invito a una partita
};

let context = null;
let master = null;
const raw = new Map(); // file → ArrayBuffer scaricato
const decoded = new Map(); // file → AudioBuffer pronto
let preloading = false;

/** true se i suoni sono accesi (anche quando il browser non permette di leggere la scelta). */
export function soundsEnabled() {
  try {
    return localStorage.getItem(SOUNDS_KEY) !== 'off';
  } catch {
    return true;
  }
}

export function setSoundsEnabled(on) {
  try {
    localStorage.setItem(SOUNDS_KEY, on ? 'on' : 'off');
  } catch {
    // Scelta non salvata (memoria del browser bloccata): resta quella di prima
  }
}

function decode(file) {
  const data = raw.get(file);
  if (!context || !data || decoded.has(file)) return;
  raw.delete(file); // decodeAudioData consuma il buffer
  context.decodeAudioData(data).then((buffer) => decoded.set(file, buffer), () => {});
}

/** Al primo gesto dell'utente: crea (o fa ripartire) il contesto audio e prepara i suoni. */
function unlock() {
  if (!context) {
    const Context = window.AudioContext || window.webkitAudioContext;
    if (!Context) return;
    try {
      context = new Context();
      master = context.createGain();
      master.gain.value = VOLUME;
      master.connect(context.destination);
    } catch {
      context = null;
      return;
    }
    for (const file of raw.keys()) decode(file);
  }
  if (context.state === 'suspended') context.resume().catch(() => {});
}

/**
 * Scarica i file dei suoni (una volta) e prepara lo sblocco dell'audio al primo gesto.
 * @param {{now?: boolean}} [options] now: crea subito il contesto audio (P118)
 */
export function preloadSounds({ now = false } = {}) {
  if (preloading) return;
  preloading = true;
  if (now) unlock();
  for (const type of ['pointerup', 'touchend', 'click', 'keydown']) {
    window.addEventListener(type, unlock, { capture: true, passive: true });
  }
  const files = [...new Set(Object.values(SOUNDS).flat())];
  for (const file of files) {
    fetch(`${BASE}${file}.mp3`)
      .then((response) => (response.ok ? response.arrayBuffer() : null))
      .then((data) => {
        if (!data) return;
        raw.set(file, data);
        decode(file);
      })
      .catch(() => {});
  }
}

/**
 * Suona `name` tra `delay` millisecondi (subito con 0). Con i suoni spenti non fa niente.
 * @param {string} name una delle chiavi di SOUNDS
 * @param {number} [delay]
 */
export function playSound(name, delay = 0) {
  const files = SOUNDS[name];
  if (!files) throw new Error(`Suono sconosciuto: ${name}`);
  if (delay > 0) {
    setTimeout(() => playSound(name, 0), delay);
    return;
  }
  if (!soundsEnabled()) return;
  document.dispatchEvent(new CustomEvent('cinquecento:sound', { detail: { name } }));
  const buffer = decoded.get(files[Math.floor(Math.random() * files.length)]);
  if (!context || context.state !== 'running' || !buffer) return;
  try {
    const source = context.createBufferSource();
    source.buffer = buffer;
    source.connect(master);
    source.start();
  } catch {
    // L'audio non è disponibile adesso: la pagina va avanti senza suono
  }
}
