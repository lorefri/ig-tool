"""Tray icon nel menubar (Mac) / system tray (Win). F7.

L'icona è generata al volo con Pillow (mini cerchio gradient con "L" bianca).
Menu: stato corrente, apri dashboard nel browser, quit.

Il worker gira in un thread daemon; il main thread blocca su Icon.run().
"""

import threading
import webbrowser
from typing import Optional

from PIL import Image, ImageDraw, ImageFont
import pystray

from .log import get

_log = get("tray")


def _make_icon_image(running: bool = True) -> Image.Image:
    """Genera al volo l'icona: cerchio gradient indaco con 'L' bianca.
    Versione 'stopped' è più tenue."""
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Cerchio principale
    if running:
        fill = (99, 102, 241, 255)     # indaco vivo
    else:
        fill = (139, 143, 168, 255)    # grigio
    draw.ellipse((4, 4, size - 4, size - 4), fill=fill)
    # Lettera "L"
    # Cascata: font Mac → Windows → Linux → fallback
    font = None
    for candidate in (
        "/System/Library/Fonts/HelveticaNeue.ttc",
        "arial.ttf",
        "arialbd.ttf",
        "DejaVuSans-Bold.ttf",
    ):
        try:
            font = ImageFont.truetype(candidate, 38)
            break
        except Exception:
            continue
    if font is None:
        font = ImageFont.load_default()
    # bbox per centratura
    try:
        bbox = draw.textbbox((0, 0), "L", font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        tx = (size - tw) // 2 - bbox[0]
        ty = (size - th) // 2 - bbox[1] - 2
    except Exception:
        tx, ty = 20, 12
    draw.text((tx, ty), "L", fill=(255, 255, 255, 255), font=font)
    return img


class TrayApp:
    """Avvolge il worker in un thread daemon e mostra una tray icon col menu."""

    def __init__(self, worker, server_url: str):
        self.worker = worker
        self.server_url = server_url
        self._worker_thread: Optional[threading.Thread] = None
        self.icon: Optional[pystray.Icon] = None

    def _menu(self):
        running = self._worker_thread is not None and self._worker_thread.is_alive()
        state_label = "✓ In esecuzione" if running else "✗ Fermato"
        return pystray.Menu(
            pystray.MenuItem(state_label, None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Apri dashboard…", self._on_open_dashboard),
            pystray.MenuItem("Stato sul server", self._on_open_status),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Esci", self._on_quit),
        )

    def _on_open_dashboard(self, icon, item):
        webbrowser.open(self.server_url)

    def _on_open_status(self, icon, item):
        webbrowser.open(f"{self.server_url}/api/health")

    def _on_quit(self, icon, item):
        _log.info("Quit dal menu tray → stop worker + tray")
        try:
            self.worker.stop()
        except Exception:
            pass
        icon.stop()

    def _run_worker(self):
        try:
            self.worker.run()
        except Exception as e:
            _log.exception(f"Worker terminato con eccezione: {e}")
        finally:
            # Quando il worker si ferma da solo (token revocato etc.),
            # cambio icona a "stopped"
            if self.icon:
                self.icon.icon = _make_icon_image(running=False)
                self.icon.title = "Lenoria — fermato"

    def run(self):
        # Worker in thread daemon
        self._worker_thread = threading.Thread(target=self._run_worker, daemon=True)
        self._worker_thread.start()
        # Icona tray nel main thread (blocca)
        self.icon = pystray.Icon(
            name="lenoria",
            icon=_make_icon_image(running=True),
            title="Lenoria — in esecuzione",
            menu=self._menu(),
        )
        self.icon.run()
