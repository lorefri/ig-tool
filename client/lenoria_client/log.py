"""Logging locale del client. File rotanti per giorno in cartella dati OS."""

import logging
import sys
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler


def _data_dir() -> Path:
    """Cartella dati per OS (Win: %APPDATA%, Mac: ~/Library/App Support, Linux: ~/.local/share)."""
    import os
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or str(Path.home())
        return Path(base) / "Lenoria"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Lenoria"
    return Path.home() / ".local" / "share" / "lenoria"


def get_data_dir() -> Path:
    d = _data_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d


def configure(verbose: bool = False):
    """Configura logging globale: stdout + file rotante in cartella dati OS."""
    log_dir = get_data_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "client.log"

    level = logging.DEBUG if verbose else logging.INFO
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

    root = logging.getLogger()
    root.setLevel(level)
    # Pulisci handler precedenti (in caso di re-configure)
    root.handlers = []

    # Console
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(logging.Formatter(fmt))
    root.addHandler(sh)

    # File con rotation giornaliera, retention 7 giorni
    fh = TimedRotatingFileHandler(log_file, when="midnight", backupCount=7, encoding="utf-8")
    fh.setFormatter(logging.Formatter(fmt))
    root.addHandler(fh)


def get(name: str) -> logging.Logger:
    return logging.getLogger(name)
