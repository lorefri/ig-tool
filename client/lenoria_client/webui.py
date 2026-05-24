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
    """API Python esposta al JS frontend per delegare azioni native (es. aprire
    URL nel browser di sistema invece che nella webview)."""

    def open_external(self, url: str) -> bool:
        try:
            webbrowser.open(url, new=2)
            return True
        except Exception as e:
            _log.warning(f"open_external fallito per {url}: {e}")
            return False


def _platform_name() -> str:
    s = platform.system().lower()
    if "darwin" in s:
        return "macOS"
    if "windows" in s:
        return "Windows"
    return "Linux"


def _build_window_url(api: ApiClient, server_url: str) -> str:
    """Ritorna l'URL iniziale per la webview. Se otteniamo lo scambio JWT,
    il frontend atterra già loggato. Se fallisce (es. token revocato), il
    fallback è la home — l'utente vedrà la schermata di login."""
    base = server_url.rstrip("/")
    try:
        sess = api.web_session()
        token = sess.get("access_token")
        if token:
            return f"{base}/?desktop_token={token}"
    except ApiError as e:
        _log.warning(f"web-session fallita ({e}); apro senza pre-login")
    except Exception as e:
        _log.warning(f"web-session errore inatteso: {e}; apro senza pre-login")
    return f"{base}/"


def launch(api: ApiClient, server_url: str, worker=None) -> None:
    """Apre la finestra principale. Blocca finché non viene chiusa.
    Se `worker` è passato, viene fermato alla chiusura della finestra."""
    url = _build_window_url(api, server_url)
    ua = f"LenoriaDesktop/{__version__} ({_platform_name()})"
    _log.info(f"Apertura webview verso {url[:80]}... (UA: {ua})")

    bridge = _JsBridge()
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
