"""Wrapper HTTP verso il server Lenoria. Aggiunge token + version header automaticamente."""

import requests
from typing import Optional

from . import __version__
from .log import get

_log = get("api_client")


class ApiError(Exception):
    """Errore generico nel parlare col server."""
    def __init__(self, status: int, message: str):
        self.status = status
        self.message = message
        super().__init__(f"[{status}] {message}")


class TokenRevoked(ApiError):
    """Il server ha revocato il token (kill switch). Il worker deve fermarsi."""


class ApiClient:
    def __init__(self, server_url: str, token: Optional[str] = None, timeout: int = 15):
        self.server_url = server_url.rstrip("/")
        self.token = token
        self.timeout = timeout

    # ── helpers privati ──────────────────────────────────────────────────────

    def _headers(self, auth_required: bool = True) -> dict:
        h = {
            "User-Agent": f"lenoria-client/{__version__}",
            "X-Client-Version": __version__,
        }
        if auth_required:
            if not self.token:
                raise ApiError(0, "Nessun token. Esegui 'lenoria pair' prima.")
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def _check_response(self, r: requests.Response):
        if r.status_code == 401:
            try:
                detail = r.json().get("detail", "")
            except Exception:
                detail = r.text[:200]
            if "revoc" in detail.lower():
                raise TokenRevoked(401, detail)
            raise ApiError(401, detail or "Non autorizzato")
        if not r.ok:
            try:
                detail = r.json().get("detail", "")
            except Exception:
                detail = r.text[:200]
            raise ApiError(r.status_code, detail or f"HTTP {r.status_code}")

    # ── endpoint pubblici (no auth) ──────────────────────────────────────────

    def pair_init(self, device_code: str) -> dict:
        r = requests.post(f"{self.server_url}/api/worker/pair/init",
                          json={"device_code": device_code},
                          headers=self._headers(auth_required=False),
                          timeout=self.timeout)
        self._check_response(r)
        return r.json()

    def pair_poll(self, device_code: str) -> dict:
        r = requests.get(f"{self.server_url}/api/worker/pair/poll",
                         params={"code": device_code},
                         headers=self._headers(auth_required=False),
                         timeout=self.timeout)
        self._check_response(r)
        return r.json()

    def latest_version(self) -> dict:
        r = requests.get(f"{self.server_url}/api/worker/latest-version",
                         headers=self._headers(auth_required=False),
                         timeout=self.timeout)
        self._check_response(r)
        return r.json()

    # ── endpoint autenticati ──────────────────────────────────────────────────

    def heartbeat(self, running: bool = True, stats: Optional[dict] = None,
                  last_error: Optional[str] = None) -> dict:
        payload = {"version": __version__, "running": running}
        if stats:
            payload["stats_24h"] = stats
        if last_error:
            payload["last_error"] = last_error
        r = requests.post(f"{self.server_url}/api/worker/heartbeat",
                          json=payload, headers=self._headers(), timeout=self.timeout)
        self._check_response(r)
        return r.json()

    def plan(self) -> dict:
        r = requests.get(f"{self.server_url}/api/worker/plan",
                         headers=self._headers(), timeout=self.timeout)
        self._check_response(r)
        return r.json()

    def result(self, action_id: str, status: str,
               result: Optional[dict] = None, error: Optional[str] = None) -> dict:
        payload = {"action_id": action_id, "status": status}
        if result is not None:
            payload["result"] = result
        if error is not None:
            payload["error"] = error
        r = requests.post(f"{self.server_url}/api/worker/result",
                          json=payload, headers=self._headers(), timeout=self.timeout)
        self._check_response(r)
        return r.json()

    def draft_message(self, contact_username: str, kind: str = "first_dm",
                      user_profile: Optional[dict] = None) -> dict:
        payload = {"contact_username": contact_username, "kind": kind}
        if user_profile:
            payload["user_profile"] = user_profile
        r = requests.post(f"{self.server_url}/api/worker/draft-message",
                          json=payload, headers=self._headers(), timeout=self.timeout)
        self._check_response(r)
        return r.json()

    def ig_credentials(self) -> dict:
        """Recupera la sessionid Instagram del distributore loggato.
        Salvata sul server in distributore_settings, ritornata solo a client autenticato."""
        r = requests.get(f"{self.server_url}/api/worker/ig-credentials",
                         headers=self._headers(), timeout=self.timeout)
        self._check_response(r)
        return r.json()

    def report_error(self, message: str, level: str = "warning",
                     stack: Optional[str] = None) -> None:
        try:
            payload = {"level": level, "message": message}
            if stack:
                payload["stack"] = stack
            requests.post(f"{self.server_url}/api/worker/error",
                          json=payload, headers=self._headers(),
                          timeout=self.timeout)
        except Exception as e:
            # Non vogliamo che report_error scateni altri error report → swallow
            _log.warning(f"Impossibile riportare error al server: {e}")
