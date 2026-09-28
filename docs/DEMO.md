# Demo di Cinquecento: installazione, backup e giorno della demo

Guida per chi prepara la demo (P38 e P39). Si segue dall'alto in basso, sul PC che ospita la demo; ogni comando si lancia in **PowerShell**.

> **Da decidere (D20)** prima di cominciare:
> - **quale PC ospita la demo**: ____________________
> - **come si collegano gli altri**: stessa rete Wi-Fi (consigliato) oppure un tunnel come ngrok: ____________________
> - **da quale branch si installa**: finché `main` non viene aggiornato si usa `dev` (portare `dev` in `main` lo decide il gruppo).
>
> Finché D20 non è deciso questa guida si può leggere, ma non seguire.

## Perché una cartella separata

La demo ha **account veri** (quelli degli amici che la provano). Per non toccarli mai per sbaglio:

- vive in **una seconda copia del progetto**, diversa da quella in cui si sviluppa;
- quella copia ha il file **`PRODUZIONE`**: lì i test si rifiutano di partire;
- usa il suo **`.env`**, con una `SECRET_KEY` sua e il database **`cinquecento`** (quello di sviluppo è `cinquecento_dev`, quello dei test `cinquecento_test`).

Claude non esplora e non modifica la cartella della demo (`CLAUDE.md`).

## 1. Cosa serve sul PC

- Python **3.14.4**, MySQL **8.0** e Git, alle stesse versioni dello sviluppo (`README.md`).
- Se su questo PC non si è mai sviluppato, prima si lancia **una volta** `scripts/setup_db.sql` come nel `README.md` (crea l'utente MySQL `cinquecento`): la password generata va conservata, serve al passo 5.

## 2. La copia del progetto

Fuori da OneDrive e da cartelle sincronizzate (un file bloccato dalla sincronizzazione può fermare il server o il backup):

```powershell
git clone https://github.com/zChrees/cinquecento.git C:\cinquecento-demo
cd C:\cinquecento-demo
git switch dev
```

## 3. Il file PRODUZIONE

```powershell
New-Item -ItemType File PRODUZIONE
```

Controllo **[T]** (è il primo "Fatto quando" di P38): il runner dei test deve rifiutarsi di partire e uscire con 2.

```powershell
python tests\esegui_tutti.py
# → "trovato il file PRODUZIONE: questa è un'installazione vera, i test non partono."
```

`PRODUZIONE` è in `.gitignore`: non finisce mai su GitHub.

## 4. Python e dipendenze

```powershell
py -3.14 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Nella demo non servono `pytest` e `ruff` (`requirements-dev.txt`).

## 5. Database della demo

Come **root** (chiede la password di root). Crea il database `cinquecento` e dà all'utente del progetto il permesso di usarlo (oggi l'utente può scrivere solo in `cinquecento_dev` e `cinquecento_test`):

```powershell
& "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p -e "CREATE DATABASE IF NOT EXISTS cinquecento CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci; GRANT ALL PRIVILEGES ON cinquecento.* TO 'cinquecento'@'localhost';"
```

## 6. Il file .env della demo

```powershell
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_hex(32))"
```

Poi, nel `.env`:

| Chiave | Valore nella demo |
|---|---|
| `APP_ENV` | `demo` |
| `SECRET_KEY` | la stringa appena generata (**diversa** da quella di sviluppo) |
| `HOST` | `0.0.0.0` se gli altri si collegano dalla rete locale (P39), altrimenti `127.0.0.1` |
| `PORT` | `5000` |
| `DB_USER` / `DB_PASSWORD` | l'utente `cinquecento` e la sua password, tra apici singoli: `DB_PASSWORD='...'` |
| `DB_NAME` | `cinquecento` |
| `DB_NAME_TEST` | `cinquecento_test` |
| `LOG_LEVEL` | `INFO` |

**Tieni una copia del `.env` fuori dal PC** (una chiavetta o un gestore di password): se si perde, la `SECRET_KEY` nuova costringe tutti a rifare il login, e senza `DB_PASSWORD` il server non parte. Il `.env` non va mai su GitHub, né in chat, né in una foto.

## 7. Tabelle e avvio

```powershell
python scripts\migrate.py
python run.py
```

Deve comparire `Cinquecento (demo): http://0.0.0.0:5000` (o `127.0.0.1`). Nella demo la home non usa i dati finti di sviluppo (`/?demo=rientro` risponde 404) e il debug è spento. Per fermarlo: **Ctrl+C** nella finestra di PowerShell.

## 8. Backup pianificato

Una volta sola, dalla cartella della demo (non serve essere amministratore):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\pianifica_backup.ps1
# oppure a un'altra ora:  ... -File scripts\pianifica_backup.ps1 -Ora 21:30
```

Crea l'attività di Windows **"Cinquecento - backup della demo"**: ogni giorno (alle 3:00 se non indichi un'ora) lancia `python scripts\backup.py`, che salva il database in `backups\` e cancella i backup più vecchi di 14 giorni (`BACKUP_RETENTION_DAYS`, provvisorio: D10). Se a quell'ora il PC è spento, il backup parte appena si riaccende. Lo script si rifiuta di partire senza il file `PRODUZIONE`.

Controllo **[T]** (secondo "Fatto quando" di P38): prova subito l'attività e guarda che il file ci sia.

```powershell
Start-ScheduledTask -TaskName "Cinquecento - backup della demo"
Get-Content logs\backup.log -Tail 3
Get-ChildItem backups
```

**Copia i backup anche fuori dal PC** ogni tanto (chiavetta o disco): se si rompe il PC, `backups\` si perde con lui.

## 9. Ripristino di prova

Controllo **[T]** (terzo "Fatto quando" di P38): un backup si ricarica **nel database dei test**, mai in quello della demo.

```powershell
python scripts\ripristina.py backups\cinquecento_AAAA-MM-GG_HHMMSS.sql.gz cinquecento_test
```

Ricaricare un backup in `cinquecento` (per esempio dopo un guasto) sostituisce i dati di adesso: lo script chiede di scrivere il nome del database per confermare. Prima di farlo, un backup nuovo.

## 10. Aggiornare la demo

Quando arriva codice nuovo in `dev` (o in `main`):

```powershell
# 1. ferma il server (Ctrl+C), poi un backup
python scripts\backup.py
# 2. codice e dipendenze
git pull
pip install -r requirements.txt
# 3. tabelle nuove, se ci sono (rilanciato non fa niente)
python scripts\migrate.py
# 4. di nuovo acceso
python run.py
```

Nella cartella della demo **non si modifica mai il codice**: si cambia nella cartella di sviluppo, passa da `dev`, e qui si fa solo `git pull`.

## 11. Accesso dagli altri dispositivi (P39)

Solo se D20 sceglie la **stessa rete Wi-Fi**:

1. Nel `.env` della demo `HOST=0.0.0.0` (passo 6), poi riavvia il server.
2. La rete Wi-Fi del PC deve essere **privata** (Impostazioni → Rete e Internet → Wi-Fi → la rete → Tipo di profilo di rete: Privata).
3. Apri la porta 5000 **solo per le reti private**, in una PowerShell **come amministratore**:

   ```powershell
   New-NetFirewallRule -DisplayName "Cinquecento demo" -Direction Inbound -Protocol TCP -LocalPort 5000 -Profile Private -Action Allow
   ```

   Per toglierla dopo la demo: `Remove-NetFirewallRule -DisplayName "Cinquecento demo"`.
4. L'indirizzo del PC: `ipconfig`, riga "Indirizzo IPv4" della scheda Wi-Fi (per esempio `192.168.1.23`).
5. Dai telefoni: `http://192.168.1.23:5000` (con l'indirizzo vero). È `http`, non `https`: va bene sulla rete di casa o della scuola.

Se D20 sceglie un tunnel (ngrok), questo passo va riscritto.

## 12. Lista di controllo del giorno della demo (P39)

Prima (almeno il giorno prima):

- [ ] demo aggiornata all'ultima versione (passo 10) e tutte le suite PASS **nella cartella di sviluppo**
- [ ] backup fatto e copiato fuori dal PC
- [ ] PC in carica, sospensione e aggiornamenti di Windows rimandati per la durata della demo
- [ ] copia del `.env` a portata di mano

Il giorno della demo:

- [ ] MySQL acceso, `python run.py` avviato, nessun errore nella finestra
- [ ] dal PC stesso la home si apre e il login funziona
- [ ] da un telefono sulla stessa rete la home si apre (passo 11)
- [ ] prova generale (fatto quando di P39): **tre telefoni e un PC** si registrano, diventano amici, si invitano e giocano **una partita 2v2 completa**
- [ ] dopo la demo: un backup (passo 8, `Start-ScheduledTask ...`) e, se non serve più, la regola del firewall tolta

Se qualcosa non va: guarda `logs\cinquecento.log` (errori del server) e `logs\backup.log` (backup).
