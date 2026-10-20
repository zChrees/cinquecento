/**
 * Gli indirizzi della SPA: indirizzo → pagina (React Router).
 *
 * Cosa contiene:
 *   router   l'oggetto che main.tsx passa a <RouterProvider>
 *
 * Una pagina nuova della SPA si aggiunge qui, in SPA_PATHS di vite.config.ts e
 * in SPA_PATHS di app/blueprints/spa/routes.py (lo controlla test_spa.py).
 * Le pagine non ancora migrate (home, tavolo, ...) restano pagine Jinja di
 * Flask: dalla SPA ci si arriva con un normale <a href>, che ricarica la pagina.
 * La home React, finché non è finita, sta su /prova-home (passo 7: solo in
 * sviluppo e nei test, lo decide Flask); al lotto 7d prende il posto di /.
 *
 * DA DOVE ARRIVANO I DATI: React Router legge l'indirizzo della barra del
 * browser (window.location) e sceglie la voce di routes con lo stesso path.
 */

import { createBrowserRouter } from 'react-router';
import type { DataRouter, RouteObject } from 'react-router';
import { HomePage } from './pages/HomePage';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { SettingsPage } from './pages/SettingsPage';

// routes: l'elenco delle pagine. path è l'indirizzo, element il componente da
// disegnare (<LoginPage /> vuol dire "il componente LoginPage, senza dati").
const routes: RouteObject[] = [
  { path: '/auth/login', element: <LoginPage /> },
  { path: '/auth/register', element: <RegisterPage /> },
  { path: '/profile/settings', element: <SettingsPage /> },
  { path: '/prova-home', element: <HomePage /> },
];

// router: chi segue la barra degli indirizzi e cambia pagina senza ricaricare
// ("Browser" perché usa gli indirizzi veri, /auth/login, e la cronologia del
// browser, quindi anche il tasto "indietro")
export const router: DataRouter = createBrowserRouter(routes);
