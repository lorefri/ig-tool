# Lenoria Desktop Client

Eseguibile installato sul PC del distributore. Esegue le call Instagram dal suo IP residenziale.
Vedi [`../CLIENT_DESKTOP_DESIGN.md`](../CLIENT_DESKTOP_DESIGN.md) per il design completo.

## Dev mode (no packaging)

```bash
# Dalla cartella ig-tool-github/
pip install -r client/requirements.txt
cd client
python -m lenoria_client.main --server http://localhost:8000 pair
python -m lenoria_client.main --server http://localhost:8000 run
```

## Comandi

- `lenoria pair` — pairing iniziale con server (genera token)
- `lenoria run` — avvia worker loop
- `lenoria status` — verifica token + ping server
- `lenoria logout` — cancella token

## Stato moduli

| File | Stato |
|---|---|
| `__init__.py` | versione + costanti |
| `log.py` | logging file + console |
| `api_client.py` | wrapper HTTP verso server |
| `auth.py` | pairing flow + token storage (JSON, F7 → keychain) |
| `worker.py` | loop principale + heartbeat thread + executor (STUB in F3) |
| `main.py` | CLI argparse |
| `instagram.py` | NON ANCORA IMPORTATO — F4 collegherà i moduli reali |
| `actions.py` | NON ANCORA IMPORTATO — F4 |
| `tray.py` | NON ANCORA SCRITTO — F7 |
| `updater.py` | NON ANCORA SCRITTO — F6 |

## Cartella dati locale

- macOS: `~/Library/Application Support/Lenoria/`
- Windows: `%APPDATA%\Lenoria\`
- Linux: `~/.local/share/lenoria/`

Contiene: `auth.json` (token), `logs/client-YYYY-MM-DD.log`.
