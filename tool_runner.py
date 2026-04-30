import subprocess
import os
import sys
import signal
from pathlib import Path

PID_FILE = Path(__file__).parent / "tool.pid"
LOG_FILE = Path(__file__).parent / "tool.log"
BASE_DIR = Path(__file__).parent


def start_tool():
    if is_running():
        return False
    log = open(LOG_FILE, "w", encoding="utf-8")
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.Popen(
        [sys.executable, "main.py"],
        stdout=log,
        stderr=subprocess.STDOUT,
        cwd=str(BASE_DIR),
        env=env,
    )
    PID_FILE.write_text(str(proc.pid))
    return True


def stop_tool():
    pid = get_pid()
    if not pid:
        return False
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    PID_FILE.unlink(missing_ok=True)
    return True


def is_running():
    pid = get_pid()
    if not pid:
        return False
    try:
        if sys.platform == "win32":
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                capture_output=True, text=True
            )
            if str(pid) in result.stdout:
                return True
            PID_FILE.unlink(missing_ok=True)
            return False
        else:
            os.kill(pid, 0)
            return True
    except ProcessLookupError:
        PID_FILE.unlink(missing_ok=True)
        return False
    except Exception:
        PID_FILE.unlink(missing_ok=True)
        return False


def get_pid():
    if not PID_FILE.exists():
        return None
    try:
        return int(PID_FILE.read_text().strip())
    except Exception:
        return None


def get_logs(last_n=80):
    if not LOG_FILE.exists():
        return ""
    lines = LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()
    clean = [l for l in lines if "NotOpenSSLWarning" not in l and "warnings.warn" not in l and "urllib3" not in l]
    return "\n".join(clean[-last_n:])
