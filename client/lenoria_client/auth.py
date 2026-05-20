"""Gestione pairing e storage del token.

Storage: file JSON in cartella dati OS, permessi 0600.
(In F7 si migrerà a OS keychain con il package `keyring` per maggiore sicurezza.)
"""

import json
import os
import secrets
import string
import time
import webbrowser
from pathlib import Path
from typing import Optional

from .api_client import ApiClient
from .log import get, get_data_dir

_log = get("auth")


def _token_file() -> Path:
    return get_data_dir() / "auth.json"


def load_token(server_url: str) -> Optional[str]:
    """Legge il token salvato per QUESTO server. None se manca o se server diverso."""
    f = _token_file()
    if not f.exists():
        return None
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
        if data.get("server_url") != server_url:
            _log.warning(f"Token salvato è per server diverso ({data.get('server_url')}), ignoro.")
            return None
        return data.get("token")
    except Exception as e:
        _log.error(f"Impossibile leggere token file: {e}")
        return None


def save_token(server_url: str, token: str) -> None:
    f = _token_file()
    f.write_text(json.dumps({"server_url": server_url, "token": token,
                             "created_at": time.time()}), encoding="utf-8")
    try:
        os.chmod(f, 0o600)  # solo owner può leggere
    except Exception:
        pass  # Windows non supporta chmod come Unix


def clear_token() -> None:
    f = _token_file()
    if f.exists():
        f.unlink()


def _generate_device_code() -> str:
    """9 caratteri tipo 'X4K7QMPN2' (no I/O/0/1 per leggibilità umana)."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(9))


def run_pairing(api: ApiClient, open_browser: bool = True,
                poll_interval: float = 2.0, timeout_seconds: int = 600) -> str:
    """Esegue il pairing end-to-end. Ritorna il token al successo.

    1. Genera device_code
    2. POST /pair/init → pair_url
    3. Apre il browser sull'URL (utente conferma da web)
    4. Polla /pair/poll finché status=approved (o expired/timeout)
    """
    code = _generate_device_code()
    _log.info(f"Pairing avviato. Device code: {code}")

    resp = api.pair_init(code)
    pair_url = resp["pair_url"]
    _log.info(f"Apri questo URL nel browser per confermare:\n  {pair_url}")
    print(f"\n→ Apri nel browser per confermare il collegamento:")
    print(f"  {pair_url}\n")
    print(f"  Codice device: {code}\n")

    if open_browser:
        try:
            webbrowser.open(pair_url)
        except Exception as e:
            _log.warning(f"Impossibile aprire browser automaticamente: {e}")

    start = time.time()
    while time.time() - start < timeout_seconds:
        r = api.pair_poll(code)
        status = r.get("status")
        if status == "approved":
            token = r["token"]
            _log.info("Pairing riuscito! Token ricevuto.")
            return token
        if status == "expired":
            raise RuntimeError("Pairing scaduto. Riprova.")
        # status == "pending" → continua a pollare
        time.sleep(poll_interval)

    raise RuntimeError(f"Pairing timeout dopo {timeout_seconds}s.")
