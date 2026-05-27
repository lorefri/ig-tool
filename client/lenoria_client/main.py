"""Entry point CLI del client Lenoria.

Comandi:
  lenoria pair                 → fa pairing col server, salva token in locale
  lenoria run                  → avvia il worker loop (richiede pairing già fatto)
  lenoria status               → stato locale: token presente? versione? ultimo error?
  lenoria logout               → cancella token locale (richiederà nuovo pairing)

Flags globali:
  --server URL                 → override server URL (default: production)
  --verbose                    → debug logging
"""

import argparse
import os
import signal
import sys

from . import __version__, DEFAULT_SERVER_URL
from .api_client import ApiClient, ApiError
from .auth import run_pairing, load_token, save_token, clear_token
from .log import configure, get, get_data_dir
from .worker import Worker


def _resolve_server(args) -> str:
    if args.server:
        return args.server
    return os.environ.get("LENORIA_SERVER_URL", DEFAULT_SERVER_URL)


def cmd_pair(args):
    log = get("main")
    server = _resolve_server(args)
    log.info(f"Pairing contro server: {server}")
    if load_token(server):
        log.warning("Hai già un token salvato per questo server.")
        if not args.force:
            print("Esegui 'lenoria logout' prima per ri-fare pairing, o usa --force.")
            return 1
    api = ApiClient(server)
    try:
        token = run_pairing(api, open_browser=not args.no_browser)
    except RuntimeError as e:
        log.error(f"Pairing fallito: {e}")
        return 2
    save_token(server, token)
    log.info(f"Token salvato in {get_data_dir() / 'auth.json'}")
    print("\n✓ Pairing completato. Esegui 'lenoria run' per avviare il worker.")
    return 0


class _WorkerController:
    """Gestisce il ciclo di vita del worker in un thread daemon, avviabile e
    fermabile a runtime. Il bridge della webview lo usa per partire al login
    (quando arriva il client_token) e fermarsi al logout."""

    def __init__(self, api, log, dry_run=False):
        self.api = api
        self.log = log
        self.dry_run = dry_run
        self._worker = None
        self._thread = None

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        if not self.api.token:
            self.log.warning("WorkerController.start() senza token — ignoro")
            return
        import threading
        self._worker = Worker(self.api, dry_run=self.dry_run)
        self._thread = threading.Thread(target=_worker_safe_run,
                                        args=(self._worker, self.api, self.log),
                                        name="lenoria-worker", daemon=True)
        self._thread.start()
        self.log.info("Worker avviato")

    def start_blocking(self):
        self._worker = Worker(self.api, dry_run=self.dry_run)
        self._worker.run()

    def stop(self):
        if self._worker:
            try:
                self._worker.stop()
            except Exception as e:
                self.log.warning(f"Errore fermando worker: {e}")

    @property
    def worker(self):
        return self._worker


def cmd_run(args):
    log = get("main")
    server = _resolve_server(args)
    token = load_token(server)
    api = ApiClient(server, token=token)  # token può essere None: login dalla webview
    if args.dry_run:
        log.warning("DRY-RUN attivo: le azioni NON verranno eseguite su Instagram.")

    controller = _WorkerController(api, log, dry_run=args.dry_run)

    # Modalità headless (--no-tray): solo worker loop, niente UI. Richiede un token
    # già presente (non c'è modo di fare login interattivo). Utile su CI / VPS / dev.
    if args.no_tray:
        if not token:
            log.error("Nessun token in --no-tray: fai prima il login dall'app o 'lenoria pair'.")
            return 1
        def _shutdown(signum, frame):
            log.info(f"Ricevuto segnale {signum}, fermo il worker...")
            controller.stop()
        signal.signal(signal.SIGINT, _shutdown)
        signal.signal(signal.SIGTERM, _shutdown)
        try:
            controller.start_blocking()
        except Exception as e:
            log.exception(f"Errore inatteso nel worker: {e}")
            try:
                api.report_error(message=str(e), level="critical")
            except Exception:
                pass
            return 3
        return 0

    # Modalità app: la finestra pywebview è SEMPRE aperta. Se c'è già un token avviamo
    # subito il worker; altrimenti l'utente fa login nella webview e il bridge
    # (save_client_token) avvia il worker. Il logout lo ferma.
    if token:
        controller.start()

    def _shutdown(signum, frame):
        log.info(f"Ricevuto segnale {signum}, fermo il worker...")
        controller.stop()
    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    try:
        from .webui import launch as launch_webui
        launch_webui(api, server, controller=controller)
        return 0
    except Exception as e:
        log.warning(f"WebUI non disponibile ({e}), fallback al tray classico.")
        # Senza webview non c'è modo di fare login: serve un token già presente.
        if not load_token(server):
            log.error("Nessun token e WebUI non disponibile: esegui 'lenoria pair'.")
            return 1
        try:
            from .tray import TrayApp
            TrayApp(controller.worker, server).run()
            return 0
        except Exception as e2:
            log.warning(f"Anche tray non disponibile ({e2}), eseguo in foreground.")
            if controller._thread:
                try:
                    controller._thread.join()
                except KeyboardInterrupt:
                    controller.stop()
            return 0


def _worker_safe_run(worker, api, log):
    """Esegue il loop worker in un thread daemon catturando le eccezioni."""
    try:
        worker.run()
    except Exception as e:
        log.exception(f"Errore inatteso nel worker thread: {e}")
        try:
            api.report_error(message=str(e), level="critical")
        except Exception:
            pass


def cmd_status(args):
    server = _resolve_server(args)
    print(f"Lenoria Client v{__version__}")
    print(f"Server: {server}")
    print(f"Cartella dati: {get_data_dir()}")
    token = load_token(server)
    if not token:
        print("Token: ✗ non presente — esegui 'lenoria pair'")
        return 1
    print(f"Token: ✓ presente (prefisso {token[:10]}...)")
    # Smoke test heartbeat
    api = ApiClient(server, token=token)
    try:
        r = api.heartbeat(running=False)
        print(f"Heartbeat: ✓ OK — server v{r.get('server_version', '?')}")
        if r.get("force_update_to"):
            print(f"  ⚠ Server richiede aggiornamento a v{r['force_update_to']}")
    except ApiError as e:
        print(f"Heartbeat: ✗ {e}")
        return 2
    return 0


def cmd_logout(args):
    clear_token()
    print("✓ Token cancellato. Prossimo avvio richiederà pairing.")
    return 0


def main():
    p = argparse.ArgumentParser(prog="lenoria",
                                description=f"Lenoria desktop client v{__version__}")
    p.add_argument("--server", help="URL del server (override env LENORIA_SERVER_URL)")
    p.add_argument("--verbose", "-v", action="store_true", help="Debug logging")

    sub = p.add_subparsers(dest="cmd", required=False)

    pp = sub.add_parser("pair", help="Esegui pairing col server")
    pp.add_argument("--no-browser", action="store_true",
                    help="Non aprire il browser automaticamente (mostra solo l'URL)")
    pp.add_argument("--force", action="store_true",
                    help="Sovrascrivi token esistente")
    pp.set_defaults(func=cmd_pair)

    pr = sub.add_parser("run", help="Avvia worker loop (con tray icon)")
    pr.add_argument("--dry-run", action="store_true",
                    help="Non chiama Instagram realmente — usa executor stub")
    pr.add_argument("--no-tray", action="store_true",
                    help="Esegui in foreground senza icona menubar (utile in dev)")
    pr.set_defaults(func=cmd_run)

    ps = sub.add_parser("status", help="Stato locale + smoke test connessione")
    ps.set_defaults(func=cmd_status)

    pl = sub.add_parser("logout", help="Cancella token locale")
    pl.set_defaults(func=cmd_logout)

    args = p.parse_args()
    configure(verbose=args.verbose)

    # Default quando lanciato senza subcommand (es. doppio-click su .app):
    # apre sempre l'app (webview). Con token → worker parte subito; senza token
    # → l'utente fa login email+password nella finestra e il worker parte dopo.
    # (Il vecchio pairing a codice resta come comando CLI 'lenoria pair' di fallback.)
    if not getattr(args, "cmd", None):
        args.dry_run = False
        args.no_tray = False
        sys.exit(cmd_run(args))

    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
