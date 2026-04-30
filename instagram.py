import time
import random
import json
import os
from pathlib import Path
from instagrapi import Client
from instagrapi.exceptions import LoginRequired, UserNotFound, TwoFactorRequired
from rich.console import Console
from config import INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD, INSTAGRAM_SESSION_ID, MIN_DELAY_SECONDS, MAX_DELAY_SECONDS

console = Console()
SESSION_FILE = "session.json"
CONTACTS_FILE = "contacts.json"


def load_contacts() -> dict:
    if Path(CONTACTS_FILE).exists():
        with open(CONTACTS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_contact(username: str, status: str, message_sent: str = "", user_id: int = None, stage: str = "new", pending_message: str = ""):
    contacts = load_contacts()
    contacts[username] = {
        "status": status,
        "stage": stage,
        "user_id": user_id,
        "message": message_sent,
        "pending_message": pending_message,
        "last_action_date": time.strftime("%Y-%m-%d"),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    with open(CONTACTS_FILE, "w", encoding="utf-8") as f:
        json.dump(contacts, f, indent=2, ensure_ascii=False)


def already_contacted(username: str) -> bool:
    return username in load_contacts()


def get_client() -> Client:
    cl = Client()

    if INSTAGRAM_SESSION_ID:
        cl.login_by_sessionid(INSTAGRAM_SESSION_ID)
        cl.dump_settings(SESSION_FILE)
        console.print("[green]✓ Login via Session ID effettuato[/green]")
        return cl

    if Path(SESSION_FILE).exists():
        try:
            cl.load_settings(SESSION_FILE)
            cl.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
            console.print("[green]✓ Sessione ripristinata[/green]")
            return cl
        except TwoFactorRequired:
            pass
        except Exception:
            console.print("[yellow]Sessione scaduta, nuovo login...[/yellow]")

    try:
        cl.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
    except TwoFactorRequired:
        code = input("Inserisci il codice 2FA: ").strip()
        cl.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD, verification_code=code)

    cl.dump_settings(SESSION_FILE)
    console.print("[green]✓ Login effettuato[/green]")
    return cl


def get_followers(cl: Client, page_username: str, amount: int = 100) -> list:
    try:
        user_id = cl.user_id_from_username(page_username)
        followers = cl.user_followers(user_id, amount=amount)
        return list(followers.values())
    except UserNotFound:
        console.print(f"[red]Pagina @{page_username} non trovata[/red]")
        return []
    except Exception as e:
        console.print(f"[red]Errore nel recupero follower di @{page_username}: {e}[/red]")
        return []


def send_dm(cl: Client, user_id: int, username: str, message: str) -> bool:
    try:
        cl.direct_send(message, user_ids=[user_id])
        delay = random.randint(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS)
        console.print(f"[green]✓ DM inviato a @{username}[/green] — prossimo in {delay}s")
        time.sleep(delay)
        return True
    except Exception as e:
        console.print(f"[red]Errore invio DM a @{username}: {e}[/red]")
        return False
