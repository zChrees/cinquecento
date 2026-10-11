-- =====================================================================
-- Cinquecento: preparazione di MySQL sul proprio PC (P5)
-- =====================================================================
-- Si lancia UNA VOLTA SOLA, come root, dalla cartella del progetto:
--
--   & "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p --table -e "source scripts/setup_db.sql"
--
-- (il comando chiede la password di root; "--table" mostra il risultato
-- come tabella). Crea:
--   - il database di sviluppo cinquecento_dev e quello dei test
--     cinquecento_test, in utf8mb4;
--   - l'utente MySQL "cinquecento", che può usare solo questi due database.
--
-- La password dell'utente la inventa MySQL (RANDOM PASSWORD) e la mostra
-- UNA SOLA VOLTA, nella colonna "generated password": copiala subito nel
-- file .env, tra apici singoli:  DB_PASSWORD='...'
-- Non va mai scritta in questo file né in nessun altro file del repository.
--
-- Rilanciato, lo script non cambia niente: database e utente esistono già,
-- e la password resta quella di prima (MySQL avvisa con un "warning").
-- Se hai perso la password, rimettila dalla copia del tuo .env; se non ce
-- l'hai più, generane una nuova (poi aggiorna il .env):
--
--   ALTER USER 'cinquecento'@'localhost' IDENTIFIED BY RANDOM PASSWORD;
--
-- Le tabelle non le crea questo file: dopo, lancia  python scripts/migrate.py
-- =====================================================================

CREATE DATABASE IF NOT EXISTS cinquecento_dev
    CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;

-- Il nome dei database di test finisce sempre con _test: i test si
-- rifiutano di usarne uno diverso.
CREATE DATABASE IF NOT EXISTS cinquecento_test
    CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;

-- 'localhost' vale anche per le connessioni a 127.0.0.1 (DB_HOST del .env).
CREATE USER IF NOT EXISTS 'cinquecento'@'localhost' IDENTIFIED BY RANDOM PASSWORD;

GRANT ALL PRIVILEGES ON cinquecento_dev.* TO 'cinquecento'@'localhost';
GRANT ALL PRIVILEGES ON cinquecento_test.* TO 'cinquecento'@'localhost';
