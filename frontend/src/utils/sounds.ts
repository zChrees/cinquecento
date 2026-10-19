/**
 * I suoni (P103, P109, P113, P115, P118): la versione TypeScript di
 * app/static/js/core/sounds.js (passo 5c della migrazione), con gli stessi file, la
 * stessa scelta acceso/spento e lo stesso evento per i test. File dei pacchetti
 * Kenney, licenza CC0: dettagli in app/static/sounds/LICENZA.md.
 *
 * Cosa contiene:
 *   preloadSounds(true)        scarica i file e crea subito il contesto audio (una volta per pagina)
 *   playSound('message', 0)    suona subito; playSound('draw', 500) tra 500 ms
 *   soundsEnabled()            true se i suoni sono accesi
 *   setSoundsEnabled(false)    li spegne (l'interruttore delle impostazioni, passo 6)
 *   SOUNDS                     nome del suono → file (lo stesso elenco di sounds.js:
 *                              lo confronta tests/frontend2/test_spa_amici.py)
 *
 * I file si scaricano con fetch, senza bloccare la pagina. Il contesto audio (il
 * "mixer" del browser) si crea al primo tocco o tasto, oppure subito con
 * preloadSounds(true): mai durante un ridisegno, che bloccava la pagina per più di
 * 100 ms (P109). I browser fanno suonare una pagina solo dopo un gesto: Chrome conta
 * anche il clic nella pagina di prima dello stesso sito, Safari su iPhone no (il
 * contesto resta sospeso fino al primo tocco). Prima di allora, o senza Web Audio,
 * non suona niente e la pagina funziona lo stesso.
 *
 * La scelta acceso/spento si ricorda nel browser (localStorage, chiave SOUNDS_KEY,
 * la stessa di sounds.js): la cambia l'interruttore "Suoni" delle impostazioni e vale
 * per tutti i suoni. Per i test: ogni suono che parte manda sul documento l'evento
 * "cinquecento:sound" con { name }, anche quando il browser non lo fa sentire.
 *
 * DA DOVE ARRIVANO I DATI: i file MP3 di app/static/sounds/, serviti da Flask.
 */

// SOUNDS_KEY: la chiave della scelta acceso/spento nel browser
export const SOUNDS_KEY = 'cinquecento.sounds';
// BASE: dove stanno i file dei suoni
const BASE = '/static/sounds/';
// VOLUME: il volume di tutti i suoni, da 0 a 1
const VOLUME = 0.8;

// SoundName: i nomi dei suoni. La | vuol dire "uno di questi valori" (come un enum del C)
export type SoundName =
  | 'card'
  | 'draw'
  | 'shuffle'
  | 'deal'
  | 'trick'
  | 'lay_down'
  | 'sing'
  | 'phrase'
  | 'tick'
  | 'last_tick'
  | 'win'
  | 'lose'
  | 'tie'
  | 'friend_request'
  | 'message'
  | 'invite';

// SOUNDS: nome del suono → file (senza .mp3). Con più di un file se ne sceglie uno a
// caso, così non sembra un disco. Record<SoundName, string[]>: un elenco per ogni nome
export const SOUNDS: Record<SoundName, string[]> = {
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
  // P115, suoni del menu (scelti da Christian il 07/10/2026, D48)
  friend_request: ['friend-request'], // richiesta di amicizia ricevuta
  message: ['chat-message'], // messaggio di un amico
  invite: ['invite'], // invito a una partita
};

// context: il contesto audio, creato al primo gesto (null prima, o senza Web Audio)
let context: AudioContext | null = null;
// master: il volume generale, a cui si collegano tutti i suoni
let master: GainNode | null = null;
// raw: i file scaricati e non ancora decodificati (nome del file → byte)
const raw: Map<string, ArrayBuffer> = new Map();
// decoded: i file pronti da suonare (nome del file → suono decodificato)
const decoded: Map<string, AudioBuffer> = new Map();
// preloading: true dopo la prima chiamata di preloadSounds (lavora una volta per pagina)
let preloading = false;

/**
 * Dice se i suoni sono accesi.
 *
 * In parole semplici:
 *   soundsEnabled()  →  false solo se nel browser c'è la scelta 'off'. Se il browser
 *   non permette di leggerla (memoria bloccata) i suoni restano accesi.
 */
export function soundsEnabled(): boolean {
  try {
    return localStorage.getItem(SOUNDS_KEY) !== 'off';
  } catch {
    return true;
  }
}

/**
 * Accende o spegne i suoni (l'interruttore "Suoni" delle impostazioni).
 *
 * @param {boolean} on true per accenderli
 *
 * In parole semplici:
 *   setSoundsEnabled(false)
 *   Salva la scelta nel browser; se il browser non lo permette resta quella di prima.
 */
export function setSoundsEnabled(on: boolean): void {
  let value = 'off';
  if (on) {
    value = 'on';
  }
  try {
    localStorage.setItem(SOUNDS_KEY, value);
  } catch {
    // Scelta non salvata (memoria del browser bloccata): resta quella di prima
  }
}

/**
 * Decodifica un file scaricato, se c'è già il contesto audio.
 *
 * In parole semplici:
 *   decode('chat-message')
 *   decodeAudioData "consuma" i byte, per questo si tolgono da raw prima.
 */
function decode(file: string): void {
  const data = raw.get(file);
  if (context === null || data === undefined || decoded.has(file)) {
    return;
  }
  raw.delete(file);

  /** Il suono è pronto. */
  function keep(buffer: AudioBuffer): void {
    decoded.set(file, buffer);
  }

  /** Il file non si decodifica: quel suono non si sentirà, la pagina va avanti. */
  function ignore(): void {
    // niente da fare
  }

  context.decodeAudioData(data).then(keep, ignore);
}

/**
 * La "classe" del contesto audio del browser, oppure null se non c'è.
 *
 * In parole semplici:
 *   audioContextClass()  →  AudioContext, oppure webkitAudioContext nei Safari
 *   vecchi. webkitAudioContext non è nei tipi di TypeScript: si legge con
 *   Reflect.get (che restituisce un valore senza tipo, unknown), si controlla che
 *   sia una funzione e solo allora si usa con "as": è lo stesso oggetto di
 *   AudioContext con un altro nome.
 */
function audioContextClass(): typeof AudioContext | null {
  if (typeof window.AudioContext === 'function') {
    return window.AudioContext;
  }
  const legacy: unknown = Reflect.get(window, 'webkitAudioContext');
  if (typeof legacy === 'function') {
    return legacy as typeof AudioContext;
  }
  return null;
}

/**
 * Al primo gesto dell'utente: crea (o fa ripartire) il contesto audio e prepara i suoni.
 */
function unlock(): void {
  if (context === null) {
    const ContextClass = audioContextClass();
    if (ContextClass === null) {
      return;
    }
    try {
      context = new ContextClass();
      master = context.createGain();
      master.gain.value = VOLUME;
      master.connect(context.destination);
    } catch {
      context = null;
      master = null;
      return;
    }
    // I file arrivati prima del contesto si decodificano adesso
    const files = Array.from(raw.keys());
    for (let i = 0; i < files.length; i++) {
      decode(files[i]);
    }
  }
  if (context.state === 'suspended') {
    /** Il browser non lo fa ripartire (nessun gesto ancora): si riprova al prossimo. */
    function stillSuspended(): void {
      // niente da fare
    }
    context.resume().catch(stillSuspended);
  }
}

/**
 * Scarica un file e lo decodifica appena c'è il contesto.
 *
 * In parole semplici:
 *   download('chat-message')  →  GET /static/sounds/chat-message.mp3
 *   Se il file non arriva, quel suono semplicemente non si sentirà.
 */
async function download(file: string): Promise<void> {
  try {
    const response = await fetch(`${BASE}${file}.mp3`);
    if (!response.ok) {
      return;
    }
    const data = await response.arrayBuffer();
    raw.set(file, data);
    decode(file);
  } catch {
    // niente rete: il suono non si sentirà
  }
}

/**
 * Scarica i file dei suoni (una volta per pagina) e prepara lo sblocco dell'audio.
 *
 * @param {boolean} now true: crea subito il contesto audio (P118), senza aspettare un gesto
 * @returns {void}
 *
 * In parole semplici:
 *   preloadSounds(true);   (pannello amici, all'apertura della pagina)
 *   Le volte dopo la prima non fa niente. Il contesto si crea (o riparte) anche al
 *   primo tocco, clic o tasto: si ascoltano in "capture", cioè prima di tutti gli altri.
 */
export function preloadSounds(now: boolean): void {
  if (preloading) {
    return;
  }
  preloading = true;
  if (now) {
    unlock();
  }
  const gestures = ['pointerup', 'touchend', 'click', 'keydown'];
  for (let i = 0; i < gestures.length; i++) {
    window.addEventListener(gestures[i], unlock, { capture: true, passive: true });
  }

  // files: tutti i file di SOUNDS, ognuno una volta sola
  const files: string[] = [];
  // lists: gli elenchi di file di SOUNDS, uno per suono (Object.values: i valori dell'oggetto)
  const lists: string[][] = Object.values(SOUNDS);
  for (let i = 0; i < lists.length; i++) {
    const list = lists[i];
    for (let j = 0; j < list.length; j++) {
      if (!files.includes(list[j])) {
        files.push(list[j]);
      }
    }
  }
  for (let i = 0; i < files.length; i++) {
    download(files[i]);
  }
}

/**
 * Suona un suono, subito o dopo un po'. Con i suoni spenti non fa niente.
 *
 * @param {SoundName} name il nome, per esempio 'message'
 * @param {number} delay i millisecondi da aspettare; 0 per subito
 * @returns {void}
 *
 * In parole semplici:
 *   playSound('message', 0);
 *   Manda prima l'evento "cinquecento:sound" (per i test), poi suona uno dei file a
 *   caso, se il browser lo permette.
 */
export function playSound(name: SoundName, delay: number): void {
  if (delay > 0) {
    /** Il momento è arrivato. */
    function playNow(): void {
      playSound(name, 0);
    }
    window.setTimeout(playNow, delay);
    return;
  }
  if (!soundsEnabled()) {
    return;
  }
  document.dispatchEvent(new CustomEvent('cinquecento:sound', { detail: { name: name } }));

  const files = SOUNDS[name];
  const buffer = decoded.get(files[Math.floor(Math.random() * files.length)]);
  if (context === null || master === null || context.state !== 'running' || buffer === undefined) {
    return;
  }
  try {
    const source = context.createBufferSource();
    source.buffer = buffer;
    source.connect(master);
    source.start();
  } catch {
    // L'audio non è disponibile adesso: la pagina va avanti senza suono
  }
}
