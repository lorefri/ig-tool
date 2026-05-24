"""Build script PyInstaller per Lenoria desktop client.

Su Mac: produce dist/Lenoria.app (bundle).
Su Win: produce dist/Lenoria.exe (one-file).

Uso:
    cd client/
    .venv/bin/python build.py

Output:
    dist/Lenoria.app  (Mac)  oppure  dist/Lenoria.exe  (Win)
"""
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent.resolve()
ENTRY = HERE / "run_lenoria.py"
APP_NAME = "Lenoria"
BUNDLE_ID = "it.lenoria.client"

# Cleanup precedenti build
for d in ("build", "dist"):
    p = HERE / d
    if p.exists():
        shutil.rmtree(p)
spec = HERE / f"{APP_NAME}.spec"
if spec.exists():
    spec.unlink()

cmd = [
    sys.executable, "-m", "PyInstaller",
    "--noconfirm",
    "--name", APP_NAME,
    "--windowed",                         # no console window
    "--paths", str(HERE),                 # trova il package lenoria_client
    "--collect-all", "instagrapi",        # include risorse non-Python
    "--collect-all", "pystray",           # backend menubar Mac/Win
    "--collect-all", "PIL",               # icona tray generata con Pillow
    # pywebview: collect SOLO i moduli Python (no bundle gtk/qt/cef che non
    # usiamo). Hidden-import del backend specifico viene aggiunto sotto in
    # base alla piattaforma — su Mac WebKit nativo via Cocoa, su Win WebView2.
    "--collect-submodules", "webview",
    "--collect-submodules", "lenoria_client",
    "--hidden-import", "lenoria_client.ig.actions",
    "--hidden-import", "lenoria_client.ig.client",
    "--hidden-import", "lenoria_client.tray",
    "--hidden-import", "lenoria_client.webui",
    # Esclude moduli pesanti che non usiamo (riduce drasticamente il bundle).
    # pandas/pyarrow/streamlit sono tirati transitivamente ma il client non li
    # usa (giravano sull'app.py legacy Streamlit lato server). Da soli pesano ~150MB.
    "--exclude-module", "pandas",
    "--exclude-module", "pyarrow",
    "--exclude-module", "streamlit",
    "--exclude-module", "altair",
    "--exclude-module", "tornado",
    # imageio_ffmpeg = ffmpeg binary (73MB!), serve solo per upload video.
    # Il client Lenoria invia solo DM testuali, niente media → si elimina.
    "--exclude-module", "imageio",
    "--exclude-module", "imageio_ffmpeg",
    "--exclude-module", "moviepy",
    "--exclude-module", "tkinter",
    "--exclude-module", "matplotlib",
    "--exclude-module", "scipy",
    "--exclude-module", "numpy.tests",
    "--exclude-module", "PyQt5",
    "--exclude-module", "PyQt6",
    "--exclude-module", "PySide2",
    "--exclude-module", "PySide6",
    "--exclude-module", "webview.platforms.gtk",
    "--exclude-module", "webview.platforms.qt",
    "--exclude-module", "webview.platforms.cef",
]

if sys.platform == "darwin":
    cmd += [
        "--osx-bundle-identifier", BUNDLE_ID,
        "--hidden-import", "webview.platforms.cocoa",
        "--strip",                        # rimuove symbols Mach-O (-30/40%)
    ]
elif sys.platform == "win32":
    cmd += [
        "--hidden-import", "webview.platforms.edgechromium",
    ]

cmd.append(str(ENTRY))

print(">>> Eseguo PyInstaller:")
print("    " + " ".join(cmd))
print()
result = subprocess.run(cmd, cwd=HERE)
if result.returncode != 0:
    print(f"\n[FAIL] Build fallito (exit {result.returncode})")
    sys.exit(result.returncode)

# Esito
dist = HERE / "dist"
out = None
if sys.platform == "darwin":
    candidate = dist / f"{APP_NAME}.app"
    if candidate.exists():
        out = candidate
elif sys.platform == "win32":
    # PyInstaller (no --onefile) mette tutto in dist/<APP_NAME>/<APP_NAME>.exe
    candidate = dist / APP_NAME / f"{APP_NAME}.exe"
    if candidate.exists():
        out = candidate.parent

if out:
    size_mb = sum(f.stat().st_size for f in out.rglob("*") if f.is_file()) / (1024 * 1024) \
              if out.is_dir() else out.stat().st_size / (1024 * 1024)
    print(f"\n[OK] Build OK: {out}  ({size_mb:.1f} MB)")
else:
    print(f"\n[WARN] Build completato ma output non trovato in {dist}")
    sys.exit(1)
