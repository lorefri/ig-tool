"""Sessione Instagram lazy + cache.

Recupera la sessionid dal server alla prima richiesta, fa login con instagrapi,
mantiene il client vivo per le chiamate successive. Se la sessione scade
(LoginRequired), prova a recuperare una nuova sessionid dal server.
"""

from typing import Optional

from .api_client import ApiClient, ApiError
from .log import get

_log = get("ig_session")


class IgSession:
    """Singleton per worker: una sessione IG riusabile per tutte le azioni."""

    def __init__(self, api: ApiClient):
        self._api = api
        self._client = None
        self._username = None  # ig_username del distributore

    def _fetch_credentials(self) -> dict:
        """GET /api/worker/ig-credentials → {sessionid, ig_username, proxy?}"""
        creds = self._api.ig_credentials()
        if not creds.get("sessionid"):
            raise RuntimeError("Il server non ha la tua sessionid Instagram. "
                               "Inseriscila in Profilo IG → Impostazioni dal sito.")
        return creds

    def get_client(self):
        """Ritorna il Client instagrapi loggato. Login lazy al primo accesso."""
        if self._client is not None:
            return self._client
        creds = self._fetch_credentials()
        from .ig.client import login_by_sessionid
        self._client = login_by_sessionid(
            sessionid=creds["sessionid"],
            ig_username=creds.get("ig_username"),
            proxy=creds.get("proxy"),
        )
        self._username = creds.get("ig_username")
        _log.info(f"Sessione IG attiva per @{self._username or '?'}")
        return self._client

    def invalidate(self):
        """Forza re-login al prossimo get_client (es. dopo LoginRequired)."""
        _log.warning("Sessione IG invalidata, prossima azione farà re-login.")
        self._client = None
