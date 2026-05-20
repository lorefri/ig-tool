"""Factory per `instagrapi.Client`: login via sessionid bypassando il check
`user_short_gql` rotto da Instagram nel 2026.

Adattamento di `instagram.py::_login_by_sessionid_safe` dell'app server,
ma senza dipendenze da config.py: tutto passa come parametri.

IMPORTANTE: instagrapi mantiene un "device fingerprint" (UUID, device_id, user_agent, ecc.)
che Instagram traccia. Se cambia ad ogni esecuzione, IG marca l'account come sospetto e
fa shadow ban (azioni accettate ma silenziosamente scartate = like fantasma).
Per questo carichiamo/salviamo i settings da disco — l'identità "device" resta stabile
tra avvii del client.
"""

import re
from pathlib import Path
from typing import Optional

from ..log import get, get_data_dir

_log = get("ig.client")


def _settings_path() -> Path:
    """Dove salviamo il device fingerprint di instagrapi. Stabile tra avvii."""
    return get_data_dir() / "ig_settings.json"


def login_by_sessionid(sessionid: str, ig_username: Optional[str] = None,
                       proxy: Optional[str] = None):
    """Crea un nuovo Client instagrapi e lo logga via sessionid.

    Args:
        sessionid: la sessionid Instagram (formato '12345%3AABC...').
        ig_username: username del proprietario (usato per validare via web_profile_info).
        proxy: opzionale proxy HTTP/SOCKS (formato 'http://user:pass@host:port').

    Returns:
        instagrapi.Client logged-in, oppure solleva RuntimeError.
    """
    from instagrapi import Client

    cl = Client()
    if proxy:
        cl.set_proxy(proxy)

    # PRIMA carico il device fingerprint persistito (se esiste).
    # Cosi' instagrapi riusa UUID/device_id/user_agent del primo avvio.
    settings_file = _settings_path()
    if settings_file.exists():
        try:
            cl.load_settings(settings_file)
            _log.info(f"Device fingerprint caricato da {settings_file.name}")
        except Exception as e:
            _log.warning(f"load_settings fallito ({e}), genero device nuovo")

    m = re.search(r"^\d+", sessionid)
    if not m:
        raise RuntimeError("Sessionid malformato: deve iniziare con user_id numerico")
    user_id = int(m.group())

    cl.private.cookies.set("sessionid", sessionid)
    cl.public.cookies.set("sessionid", sessionid)
    cl.authorization_data = {"sessionid": sessionid, "ds_user_id": str(user_id)}

    # Validazione: se ho username, faccio una call web_profile_info per verificare la sessione.
    if ig_username:
        try:
            info = cl.public.get(
                "https://i.instagram.com/api/v1/users/web_profile_info/",
                params={"username": ig_username},
                headers={"x-ig-app-id": "936619743392459"},
                timeout=15,
            )
            if not info.ok:
                raise RuntimeError(f"Validazione sessione fallita (HTTP {info.status_code}) — "
                                   f"sessione probabilmente scaduta")
            data = info.json().get("data", {}).get("user")
            if not data:
                raise RuntimeError("Validazione sessione: payload vuoto da Instagram")
            try:
                cl.username = data.get("username", ig_username)
            except AttributeError:
                pass
        except RuntimeError:
            raise
        except Exception as e:
            _log.warning(f"Validazione sessione web_profile_info ha sollevato eccezione: {e}. "
                         f"Procedo comunque (sessione potrebbe non funzionare).")
    else:
        _log.warning("Nessun ig_username: non valido la sessione, procedo a fiducia.")

    # Salva i settings (device fingerprint) per i prossimi avvii.
    try:
        cl.dump_settings(settings_file)
        _log.info(f"Device fingerprint salvato in {settings_file.name}")
    except Exception as e:
        _log.warning(f"dump_settings fallito: {e}")

    _log.info(f"Login via Session ID OK (user_id={user_id})")
    return cl
