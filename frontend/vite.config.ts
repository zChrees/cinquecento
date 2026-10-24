/**
 * Configurazione di Vite.
 *
 * Vite fa due lavori:
 *
 *   npm run dev    accende il server di sviluppo su http://localhost:5173. Le
 *                  pagine della SPA le serve lui, e le aggiorna a ogni salvataggio
 *                  senza ricaricare; i dati (/api/), i file statici (/static/) e
 *                  Socket.IO li gira a Flask su http://localhost:5000
 *                  (FLASK_PATHS). Questo "girare" si chiama proxy: il
 *                  browser vede un solo indirizzo, quindi il cookie del login e il
 *                  CSRF funzionano come in produzione.
 *   npm run build  traduce TypeScript e React in JavaScript normale e scrive il
 *                  risultato in app/static/dist/, che Flask serve come ogni file
 *                  statico (D54: la cartella non va nel repository).
 *
 * DA DOVE ARRIVANO I DATI: Vite legge questo file quando parte (npm run dev o
 * npm run build, comandi scritti in package.json).
 */

import { defineConfig } from 'vite';
import type { ConfigEnv, UserConfig } from 'vite';
import react from '@vitejs/plugin-react';

// FLASK: l'indirizzo del server Flask acceso con python run.py
const FLASK = 'http://localhost:5000';

// FLASK_PATHS: l'inizio degli indirizzi che Vite gira a Flask (lotto 9d della
// migrazione, regola unica): i dati (/api/), i file statici (/static/: CSS,
// immagini, font, suoni) e il tempo reale (/socket.io). Tutto il resto è una pagina
// della SPA e lo serve Vite, anche un indirizzo che non esiste (React disegna
// "Pagina non trovata"), come fa Flask in produzione. Deve restare uguale a NOT_SPA
// di app/blueprints/spa/routes.py (lo controlla tests/frontend/test_frontend_servito.py).
// La / dopo api e static serve perché Vite confronta solo l'inizio: senza,
// anche /apice andrebbe a Flask.
const FLASK_PATHS: string[] = ['/api/', '/static/', '/socket.io'];

/**
 * La configurazione vera e propria.
 *
 * @param {ConfigEnv} env cosa sta facendo Vite: env.command è 'serve' (npm run dev) o 'build'
 * @returns {UserConfig}
 *
 * In parole semplici:
 *   viteConfig(env)
 *   Restituisce le impostazioni. L'unica che cambia tra sviluppo e build è base,
 *   il pezzo di indirizzo davanti ai file: in sviluppo i file li serve Vite dalla
 *   radice (/src/main.tsx); dopo il build li serve Flask da /static/dist/.
 */
function viteConfig(env: ConfigEnv): UserConfig {
  // base: davanti a ogni file prodotto, per esempio /static/dist/assets/index-3f9a1c.js
  let base = '/';
  if (env.command === 'build') {
    base = '/static/dist/';
  }

  // proxy: inizio dell'indirizzo → dove girarlo. Solo Socket.IO vuole anche il
  // WebSocket (ws: true, il collegamento sempre aperto del tempo reale); le altre
  // voci senza, così non toccano quello che Vite usa per aggiornare la pagina
  // mentre si sviluppa.
  const proxy: Record<string, { target: string; ws: boolean }> = {};
  for (let i = 0; i < FLASK_PATHS.length; i++) {
    // path: l'inizio di un indirizzo, per esempio '/api/'
    const path = FLASK_PATHS[i];
    proxy[path] = { target: FLASK, ws: path === '/socket.io' };
  }

  return {
    base: base,
    plugins: [react()],
    server: {
      port: 5173,
      // se la porta è occupata Vite si ferma, invece di sceglierne un'altra
      strictPort: true,
      proxy: proxy,
    },
    build: {
      // la cartella che Flask serve come /static/dist/ (fuori da frontend/, quindi
      // va detto esplicitamente che si può svuotare prima di ogni build)
      outDir: '../app/static/dist',
      emptyOutDir: true,
    },
  };
}

export default defineConfig(viteConfig);
