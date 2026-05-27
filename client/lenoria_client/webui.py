"""Finestra principale del client Lenoria (pywebview).

Renderizza `app.lenoria.it` autenticato dentro una webview nativa
(WebKit su Mac, Edge WebView2 su Windows). L'utente vede l'app come
un'applicazione desktop nativa — niente più "vai al browser per fare
le cose". Il `target="_blank"` (es. apri Stripe Portal per gestione
abbonamento) viene intercettato e aperto nel browser di sistema.

Flow:
1. Client scambia client_token → JWT Supabase via /api/worker/web-session
2. Apre webview su app.lenoria.it/?desktop_token=<jwt>
3. UA custom "LenoriaDesktop/x.y" → frontend nasconde voci billing/scarica
4. Bridge JS expose `lenoriaOpen(url)` → webbrowser.open() di Python
"""

import platform
import threading
import webbrowser

import webview  # pywebview

from . import __version__
from .api_client import ApiClient, ApiError
from .log import get

_log = get("webui")


class _JsBridge:
    """API Python esposta al JS frontend.

    Oltre ad aprire URL nel browser di sistema, gestisce il nuovo modello di
    autenticazione: il sito (dentro la webview) fa login email+password e poi
    consegna qui un client_token coniato dal server (`save_client_token`), che
    salviamo in locale e usiamo per avviare il worker. Il logout (`logout`) ferma
    il worker e cancella il token. Niente più pairing a codice device."""

    def __init__(self, server_url: str, api: ApiClient, controller=None):
        self.server_url = server_url
        self.api = api
        self.controller = controller  # WorkerController con .start()/.stop()

    def open_external(self, url: str) -> bool:
        try:
            webbrowser.open(url, new=2)
            return True
        except Exception as e:
            _log.warning(f"open_external fallito per {url}: {e}")
            return False

    def has_client_token(self) -> bool:
        """True se il client ha già un token salvato per questo server."""
        try:
            from .auth import load_token
            return bool(load_token(self.server_url))
        except Exception:
            return False

    def save_client_token(self, token: str) -> bool:
        """Salva il client_token coniato dal server dopo il login e avvia il worker."""
        try:
            from .auth import save_token
            if not token or not str(token).startswith("lt_"):
                _log.warning("save_client_token: token mancante o formato invalido")
                return False
            save_token(self.server_url, token)
            self.api.token = token
            if self.controller:
                self.controller.start()
            _log.info("client_token salvato, worker avviato")
            return True
        except Exception as e:
            _log.warning(f"save_client_token fallito: {e}")
            return False

    def logout(self) -> bool:
        """Logout in-app: ferma il worker e cancella il token locale."""
        try:
            from .auth import clear_token
            if self.controller:
                self.controller.stop()
            clear_token()
            self.api.token = None
            _log.info("logout: worker fermato e token locale cancellato")
            return True
        except Exception as e:
            _log.warning(f"logout fallito: {e}")
            return False


def _platform_name() -> str:
    s = platform.system().lower()
    if "darwin" in s:
        return "macOS"
    if "windows" in s:
        return "Windows"
    return "Linux"


def _build_window_url(api: ApiClient, server_url: str) -> str:
    """Ritorna l'URL iniziale per la webview.
    - Con client_token: tentiamo il pre-login (web_session → ?desktop_token=) così
      l'utente atterra già loggato.
    - Senza token: apriamo la schermata di login normale del sito (?desktop_link=1
      segnala al frontend di coniare il client_token dopo il login)."""
    base = server_url.rstrip("/")
    if not api.token:
        return f"{base}/?desktop_link=1"
    try:
        sess = api.web_session()
        token = sess.get("access_token")
        if token:
            return f"{base}/?desktop_token={token}"
    except ApiError as e:
        _log.warning(f"web-session fallita ({e}); apro alla login")
    except Exception as e:
        _log.warning(f"web-session errore inatteso: {e}; apro alla login")
    return f"{base}/?desktop_link=1"


def launch(api: ApiClient, server_url: str, worker=None, controller=None) -> None:
    """Apre la finestra principale. Blocca finché non viene chiusa.
    `controller` (WorkerController) permette al bridge di avviare/fermare il worker
    su login/logout. Alla chiusura della finestra fermiamo worker/controller."""
    url = _build_window_url(api, server_url)
    ua = f"LenoriaDesktop/{__version__} ({_platform_name()})"
    _log.info(f"Apertura webview verso {url[:80]}... (UA: {ua})")

    bridge = _JsBridge(server_url, api, controller)
    window = webview.create_window(
        title="Lenoria",
        url=url,
        width=1280, height=820,
        min_size=(960, 620),
        text_select=True,
        confirm_close=False,
        js_api=bridge,
    )

    # Quando l'utente chiude la finestra, fermiamo il worker in background
    # (così l'app esce davvero invece di restare zombie con il loop attivo).
    def _on_closing():
        if controller is not None:
            try:
                controller.stop()
            except Exception as e:
                _log.warning(f"Errore fermando controller alla chiusura: {e}")
        if worker is not None:
            try:
                worker.stop()
            except Exception as e:
                _log.warning(f"Errore fermando worker alla chiusura: {e}")

    try:
        window.events.closing += _on_closing
    except Exception:
        pass

    webview.start(user_agent=ua, debug=False)
