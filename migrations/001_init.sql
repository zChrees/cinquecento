-- =====================================================================
-- Cinquecento: migrazione 001, tutte le tabelle della prima versione (P5)
-- =====================================================================
-- Sono le tabelle approvate dal gruppo il 27/09/2026 (D38), prima in
-- docs/proposta-tabelle.sql. La lancia solo scripts/migrate.py, che la
-- registra in versione_schema: non modificarla dopo che è stata applicata.
-- Una modifica alle tabelle si fa con una migrazione nuova (002_...sql),
-- da concordare nel gruppo (SCALETTA.md, P5).
--
-- Decisioni di cui tiene conto (dettagli in DECISIONI.md):
--   D6  account cancellato: le partite restano, con "utente eliminato"
--   D7  nome utente da 3 a 20 caratteri (lettere, numeri, _),
--       maiuscole e minuscole DIVERSE ("Mario" e "mario" sono due utenti)
--   D23 blocco degli utenti: sì
--   D24 chat tra amici a testo libero, mai cancellata (solo con l'account);
--       le frasi pronte del tavolo NON si salvano: il server le inoltra e basta
--   D26 messaggi tra amici lunghi al massimo 1000 caratteri
--   D35 rating uguale per 150, 300 e 500 punti
--   D36 il 1v1 con un amico non conta per il rating, il 2v2 sì
--   D38 nomi di tabelle, colonne e valori in italiano
--
-- Regole comuni:
--   - MySQL 8.0, motore InnoDB (transazioni e chiavi esterne).
--   - Testo in utf8mb4 (anche emoji e lettere accentate), confronti
--     senza distinguere maiuscole e minuscole (utf8mb4_0900_ai_ci),
--     tranne il nome utente (D7).
--   - Date e ore sempre in UTC: la conversione all'ora italiana la fa
--     la pagina.
--   - Una partita si salva TUTTA INSIEME A FINE PARTITA (P26): la riga in
--     partite, i giocatori e le mosse, in una sola transazione. Le partite
--     in corso stanno solo in memoria (app/realtime/): nel database non
--     esiste mai una partita "a metà" (28/09/2026).
--   - Niente contatori duplicati: statistiche (partite, vinte, perse)
--     e numero di partite giocate si calcolano da giocatori_partita.
--   - I valori iniziali del rating (1500, 350, 0,06) stanno in
--     config.py, non qui.
--   - Colonne con un elenco fisso di valori: testo esatto (utf8mb4_0900_bin,
--     distingue maiuscole, accenti e spazi finali) con un CHECK sui valori
--     ammessi, non ENUM.
--     Un ENUM NOT NULL scritto senza valore prende in silenzio il primo
--     dell'elenco (es. risultato 'vittoria'); così invece MySQL rifiuta
--     la riga (P5, 28/09/2026). Fa eccezione amicizie.stato, che ha un
--     valore predefinito voluto ('in_attesa').
--   - "Chiave esterna" = collegamento a una riga di un'altra tabella;
--     ON DELETE dice cosa succede a questa riga se l'altra si cancella.
-- =====================================================================


-- ---------------------------------------------------------------------
-- 1. utenti: gli account. Un utente = una riga.
-- ---------------------------------------------------------------------
CREATE TABLE utenti (
    id              INT UNSIGNED NOT NULL AUTO_INCREMENT,  -- numero dell'utente, usato da tutte le altre tabelle
    nome_utente     VARCHAR(20)                            -- unico; "Mario" e "mario" sono due utenti diversi (D7)
                    CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_as_cs NOT NULL,
    email           VARCHAR(254) NOT NULL,                 -- unica; qui "Mario@x.it" = "mario@x.it"; mai mostrata agli altri
    hash_password   VARCHAR(255) NOT NULL,                 -- mai la password vera: solo la sua versione cifrata
    avatar          VARCHAR(30) NULL,                      -- codice di un avatar predefinito (D29); vuoto = iniziale del nome
    creato_il       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_utenti_nome (nome_utente),
    UNIQUE KEY uq_utenti_email (email),
    CONSTRAINT ck_utenti_nome CHECK (REGEXP_LIKE(nome_utente, '^[A-Za-z0-9_]{3,20}$', 'c'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- ---------------------------------------------------------------------
-- 2. rating: il punteggio di bravura (Glicko-2). Al massimo due righe
--    per utente: una per il 1v1 e una per il 2v2. Si crea alla prima
--    partita che conta per il rating.
-- ---------------------------------------------------------------------
CREATE TABLE rating (
    utente_id       INT UNSIGNED NOT NULL,
    modalita        VARCHAR(3) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_bin NOT NULL,  -- '1v1' o '2v2'
    valore         DOUBLE NOT NULL,                       -- il rating: parte da 1500
    deviazione      DOUBLE NOT NULL,                       -- quanto il sistema è incerto: parte da 350 e scende giocando
    volatilita      DOUBLE NOT NULL,                       -- quanto il rating oscilla: parte da 0,06
    aggiornato_il   DATETIME NOT NULL,                     -- ultima partita che l'ha cambiato
    PRIMARY KEY (utente_id, modalita),
    CONSTRAINT ck_rating_modalita CHECK (modalita IN ('1v1', '2v2')),
    CONSTRAINT fk_rating_utente FOREIGN KEY (utente_id)
        REFERENCES utenti (id) ON DELETE CASCADE          -- account cancellato: il suo rating sparisce
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- ---------------------------------------------------------------------
-- 3. partite: una riga per partita, scritta a fine partita (P26).
-- ---------------------------------------------------------------------
CREATE TABLE partite (
    id                  INT UNSIGNED NOT NULL AUTO_INCREMENT,
    modalita            VARCHAR(3) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_bin NOT NULL,  -- '1v1' o '2v2'
    punti_per_vincere   SMALLINT UNSIGNED NOT NULL,        -- solo 150, 300 o 500
    conta_per_rating    BOOLEAN NOT NULL,                  -- no per il 1v1 contro un amico (D36)
    iniziata_il         DATETIME NOT NULL,
    finita_il           DATETIME NOT NULL,
    motivo_fine         VARCHAR(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_bin NOT NULL,  -- 'punteggio' o 'abbandono'
    squadra_vincente    TINYINT UNSIGNED NULL,             -- 0 o 1; vuota = pareggio
    punti_squadra_0     SMALLINT UNSIGNED NOT NULL,        -- punti finali della squadra 0
    punti_squadra_1     SMALLINT UNSIGNED NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT ck_partite_modalita CHECK (modalita IN ('1v1', '2v2')),
    CONSTRAINT ck_partite_motivo CHECK (motivo_fine IN ('punteggio', 'abbandono')),
    CONSTRAINT ck_partite_punti CHECK (punti_per_vincere IN (150, 300, 500)),
    CONSTRAINT ck_partite_vincente CHECK (squadra_vincente IS NULL OR squadra_vincente IN (0, 1)),
    CONSTRAINT ck_partite_date CHECK (finita_il >= iniziata_il)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- ---------------------------------------------------------------------
-- 4. giocatori_partita: chi ha giocato in quale partita.
--    Due righe nel 1v1, quattro nel 2v2. Nel 1v1 ogni giocatore è una
--    "squadra" da uno.
-- ---------------------------------------------------------------------
CREATE TABLE giocatori_partita (
    partita_id      INT UNSIGNED NOT NULL,
    posto           TINYINT UNSIGNED NOT NULL,             -- 0-1 nel 1v1, 0-3 nel 2v2 (i compagni uno di fronte all'altro)
    squadra         TINYINT UNSIGNED NOT NULL,             -- 0 o 1
    utente_id       INT UNSIGNED NULL,                     -- vuoto = "utente eliminato" (D6)
    risultato       VARCHAR(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_bin NOT NULL,  -- 'vittoria', 'sconfitta' o 'pareggio'
    ha_abbandonato  BOOLEAN NOT NULL DEFAULT FALSE,        -- non è rientrato entro 60 secondi
    PRIMARY KEY (partita_id, posto),
    UNIQUE KEY uq_giocatori_utente (partita_id, utente_id),  -- lo stesso utente non siede due volte (i vuoti non contano)
    KEY ix_giocatori_utente (utente_id),                   -- per le statistiche di un utente
    CONSTRAINT ck_giocatori_risultato CHECK (risultato IN ('vittoria', 'sconfitta', 'pareggio')),
    CONSTRAINT ck_giocatori_posto CHECK (posto <= 3),
    CONSTRAINT ck_giocatori_squadra CHECK (squadra IN (0, 1)),
    CONSTRAINT fk_giocatori_partita FOREIGN KEY (partita_id)
        REFERENCES partite (id) ON DELETE CASCADE,
    CONSTRAINT fk_giocatori_utente FOREIGN KEY (utente_id)
        REFERENCES utenti (id) ON DELETE SET NULL         -- account cancellato: la partita resta, il nome no (D6)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- ---------------------------------------------------------------------
-- 5. mosse_partita: il diario della partita, mossa per mossa.
--    Contiene solo i posti al tavolo, non gli utenti: resta anche se
--    un giocatore cancella l'account.
-- ---------------------------------------------------------------------
CREATE TABLE mosse_partita (
    partita_id      INT UNSIGNED NOT NULL,
    numero          INT UNSIGNED NOT NULL,                 -- 1, 2, 3... nell'ordine in cui succedono le cose
    mano            SMALLINT UNSIGNED NOT NULL,            -- in quale mano della partita
    posto           TINYINT UNSIGNED NULL,                 -- chi ha fatto la mossa; vuoto per gli eventi del server
    tipo            VARCHAR(20) NOT NULL,                  -- es. 'gioca_carta', 'canta', 'mossa_automatica' (elenco in P24)
    dettagli        JSON NOT NULL,                         -- es. {"seme": "coppe", "punti": 40}
    creata_il       DATETIME(3) NOT NULL,                  -- con i millesimi di secondo
    PRIMARY KEY (partita_id, numero),
    CONSTRAINT fk_mosse_partita FOREIGN KEY (partita_id)
        REFERENCES partite (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- ---------------------------------------------------------------------
-- 6. amicizie: richieste (in attesa) e amicizie (accettate).
--    Una sola riga per coppia, in qualunque direzione: se Totò ha
--    chiesto l'amicizia a Nina, Nina non può crearne un'altra verso
--    Totò. Una richiesta rifiutata si cancella, così si può rimandare.
-- ---------------------------------------------------------------------
CREATE TABLE amicizie (
    richiedente_id  INT UNSIGNED NOT NULL,
    destinatario_id INT UNSIGNED NOT NULL,
    stato           ENUM('in_attesa', 'accettata') NOT NULL DEFAULT 'in_attesa',
    richiesta_il    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    risposta_il     DATETIME NULL,                         -- vuota finché è in attesa
    -- La coppia in ordine (il numero più piccolo prima): serve solo a
    -- garantire "una riga per coppia". Verificato in P5 (28/09/2026):
    -- MySQL 8.0 accetta queste colonne insieme alle chiavi esterne qui
    -- sotto e rifiuta la seconda riga della stessa coppia, anche al contrario.
    utente_minore   INT UNSIGNED AS (LEAST(richiedente_id, destinatario_id)) VIRTUAL,
    utente_maggiore INT UNSIGNED AS (GREATEST(richiedente_id, destinatario_id)) VIRTUAL,
    PRIMARY KEY (richiedente_id, destinatario_id),
    UNIQUE KEY uq_amicizie_coppia (utente_minore, utente_maggiore),
    KEY ix_amicizie_destinatario (destinatario_id, stato), -- per le richieste ricevute
    CONSTRAINT fk_amicizie_richiedente FOREIGN KEY (richiedente_id)
        REFERENCES utenti (id) ON DELETE CASCADE,
    CONSTRAINT fk_amicizie_destinatario FOREIGN KEY (destinatario_id)
        REFERENCES utenti (id) ON DELETE CASCADE
    -- "Non si chiede l'amicizia a se stessi" lo controlla il servizio:
    -- MySQL non ammette un CHECK su colonne con ON DELETE CASCADE.
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- ---------------------------------------------------------------------
-- 7. blocchi: chi ha bloccato chi (D23). Un utente bloccato non può
--    mandare richieste né messaggi; il blocco toglie l'amicizia.
-- ---------------------------------------------------------------------
CREATE TABLE blocchi (
    bloccante_id    INT UNSIGNED NOT NULL,                 -- chi blocca
    bloccato_id     INT UNSIGNED NOT NULL,                 -- chi è bloccato (mai uguale: lo controlla il servizio)
    bloccato_il     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (bloccante_id, bloccato_id),
    KEY ix_blocchi_bloccato (bloccato_id),
    CONSTRAINT fk_blocchi_bloccante FOREIGN KEY (bloccante_id)
        REFERENCES utenti (id) ON DELETE CASCADE,
    CONSTRAINT fk_blocchi_bloccato FOREIGN KEY (bloccato_id)
        REFERENCES utenti (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- ---------------------------------------------------------------------
-- 8. messaggi: la chat tra amici, a testo libero (D24).
--    Non si cancellano mai, tranne quando uno dei due cancella
--    l'account: allora sparisce tutta la conversazione con lui.
--    Se l'amicizia finisce o c'è un blocco, la conversazione resta
--    visibile ma non si può più scrivere (lo controlla il servizio).
-- ---------------------------------------------------------------------
CREATE TABLE messaggi (
    id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    mittente_id     INT UNSIGNED NOT NULL,
    destinatario_id INT UNSIGNED NOT NULL,
    testo           VARCHAR(1000) NOT NULL,                -- max 1000 caratteri (D26); mostrato sempre come testo, mai come HTML; mai nei log
    inviato_il      DATETIME(3) NOT NULL,
    letto_il        DATETIME NULL,                         -- vuota finché il destinatario non lo apre
    PRIMARY KEY (id),
    KEY ix_messaggi_conversazione (mittente_id, destinatario_id, inviato_il),
    KEY ix_messaggi_non_letti (destinatario_id, letto_il),
    CONSTRAINT fk_messaggi_mittente FOREIGN KEY (mittente_id)
        REFERENCES utenti (id) ON DELETE CASCADE,
    CONSTRAINT fk_messaggi_destinatario FOREIGN KEY (destinatario_id)
        REFERENCES utenti (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- ---------------------------------------------------------------------
-- 9. versione_schema: quali file di migrations/ sono già stati
--    applicati. La usa solo scripts/migrate.py.
-- ---------------------------------------------------------------------
CREATE TABLE versione_schema (
    versione        INT UNSIGNED NOT NULL,
    nome_file       VARCHAR(100) NOT NULL,                 -- es. '001_init.sql'
    applicata_il    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (versione)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
