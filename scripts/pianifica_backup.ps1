<#
Backup pianificato della demo (P38): crea (o aggiorna) l'attivita' di Windows che ogni
giorno lancia "python scripts\backup.py" nella cartella della demo.

Si lancia UNA VOLTA, in PowerShell, dalla cartella della demo (quella con il file
PRODUZIONE), senza bisogno di amministratore:

    powershell -ExecutionPolicy Bypass -File scripts\pianifica_backup.ps1
    powershell -ExecutionPolicy Bypass -File scripts\pianifica_backup.ps1 -Ora 21:30

- Parte solo nella cartella della demo: senza il file PRODUZIONE si rifiuta (la
  cartella di sviluppo non ha dati veri da salvare).
- L'attivita' si chiama "Cinquecento - backup della demo"; rilanciato, lo script la
  aggiorna invece di crearne un'altra.
- Se all'ora scelta il PC e' spento, il backup parte appena il PC si riaccende
  (StartWhenAvailable). Gira con l'utente che lancia lo script, quando e' collegato.
- Il risultato di ogni backup si aggiunge a logs\backup.log (mai la password: backup.py
  non la stampa). I backup vanno in backups\; quelli piu' vecchi di
  BACKUP_RETENTION_DAYS giorni (config.py, D10) li cancella backup.py.
- Per toglierla: Unregister-ScheduledTask -TaskName "Cinquecento - backup della demo"
#>

param(
    [ValidatePattern('^([01]\d|2[0-3]):[0-5]\d$')]
    [string]$Ora = "03:00"
)

$ErrorActionPreference = "Stop"
$NomeAttivita = "Cinquecento - backup della demo"
$Cartella = Split-Path -Parent $PSScriptRoot

if (-not (Test-Path -LiteralPath (Join-Path $Cartella "PRODUZIONE"))) {
    Write-Host "Backup pianificato NON creato: in $Cartella manca il file PRODUZIONE." -ForegroundColor Red
    Write-Host "Lancia lo script dalla cartella della demo (docs\DEMO.md)."
    exit 1
}

$Python = Join-Path $Cartella ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Python)) {
    Write-Host "Backup pianificato NON creato: manca $Python." -ForegroundColor Red
    Write-Host "Prima crea l'ambiente .venv e installa le dipendenze (docs\DEMO.md)."
    exit 1
}

New-Item -ItemType Directory -Force -Path (Join-Path $Cartella "logs") | Out-Null

$Comando = "/c `"`"$Python`" scripts\backup.py >> logs\backup.log 2>&1`""
$Azione = New-ScheduledTaskAction -Execute "cmd.exe" -Argument $Comando -WorkingDirectory $Cartella
$Quando = New-ScheduledTaskTrigger -Daily -At $Ora
$Impostazioni = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 30)

Register-ScheduledTask -TaskName $NomeAttivita -Action $Azione -Trigger $Quando -Settings $Impostazioni `
    -Description "Backup giornaliero del database della demo di Cinquecento (scripts\backup.py)." -Force | Out-Null

Write-Host "Backup pianificato ogni giorno alle $Ora ($NomeAttivita)." -ForegroundColor Green
Write-Host "Per provarlo subito: Start-ScheduledTask -TaskName `"$NomeAttivita`", poi guarda logs\backup.log e backups\."
