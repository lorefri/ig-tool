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


def cmd_run(args):
    log = get("main")
    server = _resolve_server(args)
    token = load_token(server)
    if not token:
        log.error("Nessun token. Esegui 'lenoria pair' prima.")
        return 1
    api = ApiClient(server, token=token)
    if args.dry_run:
        log.warning("DRY-RUN attivo: le azioni NON verranno eseguite su Instagram.")
    worker = Worker(api, dry_run=args.dry_run)

    # Gestione SIGINT/SIGTERM pulita (utile in dev da terminale)
    def _shutdown(signum, frame):
        log.info(f"Ricevuto segnale {signum}, fermo il worker...")
        worker.stop()
    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    # Modalità headless (--no-tray): solo worker loop, niente UI. Utile per
    # eseguire l'app in background su CI / VPS / dev terminal.
    if args.no_tray:
        try:
            worker.run()
        except Exception as e:
            log.exception(f"Errore inatteso nel worker: {e}")
            try:
                api.report_error(message=str(e), level="critical")
            except Exception:
                pass
            return 3
        return 0

    # Modalità app: worker in thread daemon + finestra pywebview nel main thread
    # (su macOS pywebview richiede il main thread per il loop Cocoa).
    import threading
    worker_thread = threading.Thread(target=_worker_safe_run,
                                     args=(worker, api, log),
                                     name="lenoria-worker", daemon=True)
    worker_thread.start()

    try:
        from .webui import launch as launch_webui
        launch_webui(api, server, worker=worker)
        return 0
    except Exception as e:
        log.warning(f"WebUI non disponibile ({e}), fallback al tray classico.")
        try:
            from .tray import TrayApp
            TrayApp(worker, server).run()
            return 0
        except Exception as e2:
            log.warning(f"Anche tray non disponibile ({e2}), eseguo in foreground.")
            try:
                worker_thread.join()
            except KeyboardInterrupt:
                worker.stop()
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

    # Default smart quando lanciato senza subcommand (es. doppio-click su .app):
    # se c'è già un token → run (con tray); altrimenti → pair (con browser).
    if not getattr(args, "cmd", None):
        server = _resolve_server(args)
        if load_token(server):
            args.dry_run = False
            args.no_tray = False
            sys.exit(cmd_run(args))
        else:
            args.no_browser = False
            args.force = False
            sys.exit(cmd_pair(args))

    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
