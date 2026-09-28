"""P38: backup pianificato della demo (scripts/pianifica_backup.ps1) e guida docs/DEMO.md.

Lo script si prova senza creare niente: qui non c'è il file PRODUZIONE (i test non
partono dove c'è), quindi deve rifiutarsi prima di toccare l'Utilità di pianificazione.
Si controllano anche la sintassi (parser di PowerShell), l'ora non valida e che il file
sia solo ASCII: Windows PowerShell 5.1 legge un .ps1 senza BOM con la codifica di
sistema, e le lettere accentate diventerebbero caratteri sbagliati.
I controlli con PowerShell si saltano se PowerShell non c'è.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "pianifica_backup.ps1"
GUIDE = ROOT / "docs" / "DEMO.md"
POWERSHELL = shutil.which("powershell") or shutil.which("pwsh")

needs_powershell = pytest.mark.skipif(POWERSHELL is None, reason="PowerShell non trovato")


def _run(*args):
    return subprocess.run(
        [POWERSHELL, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(SCRIPT), *args],
        capture_output=True, text=True, timeout=60, cwd=ROOT, check=False,
    )


def test_script_solo_ascii_e_crlf():
    data = SCRIPT.read_bytes()
    assert data.isascii(), "pianifica_backup.ps1 deve restare ASCII (Windows PowerShell 5.1)"
    assert data.count(b"\n") == data.count(b"\r\n")


@needs_powershell
def test_sintassi_dello_script():
    command = (
        "$e = $null; [System.Management.Automation.Language.Parser]::ParseFile("
        f"'{SCRIPT}', [ref]$null, [ref]$e) | Out-Null; $e.Count"
    )
    result = subprocess.run([POWERSHELL, "-NoProfile", "-NonInteractive", "-Command", command],
                            capture_output=True, text=True, timeout=60, check=False)
    assert result.stdout.strip() == "0", result.stdout + result.stderr


@needs_powershell
def test_senza_produzione_si_rifiuta():
    assert not (ROOT / "PRODUZIONE").exists()
    result = _run()
    assert result.returncode == 1
    assert "manca il file PRODUZIONE" in result.stdout


@needs_powershell
def test_ora_non_valida():
    result = _run("-Ora", "25:00")
    assert result.returncode != 0
    assert "Backup pianificato ogni giorno" not in result.stdout


def test_guida_con_i_passi_della_demo():
    text = GUIDE.read_text(encoding="utf-8")
    for needed in ("PRODUZIONE", "APP_ENV", "GRANT ALL PRIVILEGES ON cinquecento.*", "pianifica_backup.ps1",
                   "ripristina.py", "cinquecento_test", "New-NetFirewallRule", "-Profile Private", "D20"):
        assert needed in text, needed
    # Nessun segreto d'esempio che qualcuno potrebbe copiare così com'è
    assert "SECRET_KEY=" not in text and "DB_PASSWORD='" not in text.replace("DB_PASSWORD='...'", "")
