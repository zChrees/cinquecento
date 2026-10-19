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
 *
 * DA DOVE ARRIVANO I DATI: React Router legge l'indirizzo della barra del
 * browser (window.location) e sceglie la voce di routes con lo stesso path.
 */

import { createBrowserRouter } from 'react-router';
import type { DataRouter, RouteObject } from 'react-router';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { TestPage } from './pages/TestPage';

// routes: l'elenco delle pagine. path è l'indirizzo, element il componente da
// disegnare (<TestPage /> vuol dire "il componente TestPage, senza dati").
const routes: RouteObject[] = [
  { path: '/prova-react', element: <TestPage /> },
  { path: '/auth/login', element: <LoginPage /> },
  { path: '/auth/register', element: <RegisterPage /> },
];

// router: chi segue la barra degli indirizzi e cambia pagina senza ricaricare
// ("Browser" perché usa gli indirizzi veri, /prova-react, e la cronologia del
// browser, quindi anche il tasto "indietro")
export const router: DataRouter = createBrowserRouter(routes);
