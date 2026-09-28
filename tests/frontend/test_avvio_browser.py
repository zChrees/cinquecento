"""Avvio del browser dei test (tests/browser.py).

Chrome scrive il numero della porta in DevToolsActivePort; su Windows, mentre lo scrive,
il file è bloccato e leggerlo dà PermissionError. Prima questo faceva fallire a caso un
test su qualche decina (visto in test_momenti_tavolo.py): ora vale come "non ancora pronto".
"""

from pathlib import Path

from tests.browser import read_devtools_port


def test_file_che_non_c_e_ancora(tmp_path):
    assert read_devtools_port(tmp_path / "DevToolsActivePort") is None


def test_file_ancora_vuoto(tmp_path):
    port_file = tmp_path / "DevToolsActivePort"
    port_file.write_text("")
    assert read_devtools_port(port_file) is None


def test_file_scritto_a_meta(tmp_path):
    port_file = tmp_path / "DevToolsActivePort"
    port_file.write_text("92")  # manca ancora il resto della porta e la seconda riga
    assert read_devtools_port(port_file) is None


def test_file_bloccato_mentre_chrome_lo_scrive(tmp_path, monkeypatch):
    port_file = tmp_path / "DevToolsActivePort"
    port_file.write_text("9222\n/devtools/browser/x\n")

    def locked(self, *args, **kwargs):
        raise PermissionError(13, "Permission denied", str(self))

    monkeypatch.setattr(Path, "read_text", locked)
    assert read_devtools_port(port_file) is None


def test_porta_letta_dalla_prima_riga(tmp_path):
    port_file = tmp_path / "DevToolsActivePort"
    port_file.write_text("9222\n/devtools/browser/x\n")
    assert read_devtools_port(port_file) == "9222"
