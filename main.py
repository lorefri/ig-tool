import time
import random
import json
import requests
from datetime import datetime, date
from pathlib import Path
from rich.console import Console
from rich.panel import Panel

from config import (
    TARGET_PAGES, MAX_DM_PER_DAY, MIN_DELAY_SECONDS, MAX_DELAY_SECONDS,
    MAX_FOLLOWS_PER_DAY, MAX_LIKES_PER_DAY, MAX_STORIES_PER_DAY,
    STRATEGY_TYPE, DAYS_BETWEEN_STEPS,
    CUSTOM_DO_FOLLOW, CUSTOM_DO_LIKE_POST, CUSTOM_DO_LIKE_STORY,
    CUSTOM_DO_DM, CUSTOM_DO_UNFOLLOW, DAYS_BEFORE_UNFOLLOW,
    MAX_DM_FOLLOWUPS, DAYS_BEFORE_FOLLOWUP,
    MIN_FOLLOWERS, MAX_FOLLOWERS, MIN_POSTS, SKIP_VERIFIED, REQUIRE_ITALY,
    BIO_INCLUDE_KEYWORDS, BIO_EXCLUDE_KEYWORDS,
    ACTIVE_HOURS_START, ACTIVE_HOURS_END, ACTIVE_DAYS,
    NOTIFY_ON_REPLY, NOTIFY_WEBHOOK,
)
from instagram import get_client, get_followers, send_dm, load_contacts, save_contact, already_contacted
from ai_agent import analyze_profile, generate_followup
from actions import follow_user, unfollow_user, like_recent_post, like_story

console = Console()
TODAY = date.today().isoformat()
CONTACTS_FILE = Path(__file__).parent / "contacts.json"


# ── Contacts helpers ──────────────────────────────────────────────────────────
def save_contacts(contacts: dict):
    CONTACTS_FILE.write_text(json.dumps(contacts, indent=2, ensure_ascii=False), encoding="utf-8")


def update_contact(username: str, updates: dict):
    contacts = load_contacts()
    entry = contacts.get(username, {})
    entry.update(updates)
    entry["last_action_date"] = TODAY
    contacts[username] = entry
    save_contacts(contacts)


def days_since(date_str: str) -> int:
    if not date_str:
        return 999
    try:
        return (date.today() - datetime.strptime(date_str[:10], "%Y-%m-%d").date()).days
    except Exception:
        return 999


def count_today(contacts: dict, action: str) -> int:
    return sum(1 for d in contacts.values() if d.get(f"{action}_date", "").startswith(TODAY))


# ── Schedule check ────────────────────────────────────────────────────────────
def is_active_now() -> bool:
    now = datetime.now()
    if now.isoweekday() not in ACTIVE_DAYS:
        return False
    if not (ACTIVE_HOURS_START <= now.hour < ACTIVE_HOURS_END):
        return False
    return True


# ── Target filters ────────────────────────────────────────────────────────────
def passes_filters(user, bio: str = "") -> tuple[bool, str]:
    followers = getattr(user, "follower_count", 0) or 0
    posts     = getattr(user, "media_count", 0) or 0
    verified  = getattr(user, "is_verified", False)
    bio_lower = bio.lower()

    # Controlla follower/post solo se disponibili (UserShort li riporta a 0)
    if followers > 0:
        if followers < MIN_FOLLOWERS:
            return False, f"Troppo pochi follower ({followers})"
        if followers > MAX_FOLLOWERS:
            return False, f"Troppi follower ({followers})"
    if posts > 0 and posts < MIN_POSTS:
        return False, f"Troppo pochi post ({posts})"
    if SKIP_VERIFIED and verified:
        return False, "Account verificato"
    if BIO_EXCLUDE_KEYWORDS and any(k in bio_lower for k in BIO_EXCLUDE_KEYWORDS):
        return False, "Keyword esclusa nella bio"
    if BIO_INCLUDE_KEYWORDS and not any(k in bio_lower for k in BIO_INCLUDE_KEYWORDS):
        return False, "Nessuna keyword inclusa trovata"
    return True, ""


# ── Notification ─────────────────────────────────────────────────────────────
def notify(message: str):
    if not NOTIFY_WEBHOOK:
        return
    try:
        requests.post(NOTIFY_WEBHOOK, json={"text": message}, timeout=5)
    except Exception:
        pass


# ── Reply detection ───────────────────────────────────────────────────────────
def check_replies(cl):
    console.print("[bold]— Controllo risposte ai DM —[/bold]")
    contacts = load_contacts()
    dm_sent = {u: d for u, d in contacts.items() if d.get("status") == "dm_sent" and d.get("reply_received") != True}

    if not dm_sent:
        return

    try:
        threads = cl.direct_threads(amount=30)
    except Exception as e:
        console.print(f"[red]Errore controllo inbox: {e}[/red]")
        return

    for thread in threads:
        if not thread.users:
            continue
        other_user = thread.users[0].username
        if other_user not in dm_sent:
            continue

        # Check if last message is from them (not us)
        if thread.messages and thread.messages[0].user_id != cl.user_id:
            console.print(f"[green]💬 Risposta ricevuta da @{other_user}![/green]")
            update_contact(other_user, {
                "reply_received": True,
                "reply_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "status": "replied"
            })
            if NOTIFY_ON_REPLY:
                notify(f"✅ @{other_user} ha risposto al DM su Instagram!")


# ── Follow-up DMs ─────────────────────────────────────────────────────────────
def process_followups(cl, contacts):
    if MAX_DM_FOLLOWUPS == 0:
        return

    dms_today = count_today(contacts, "dm_sent")
    console.print("[bold]— Follow-up DM —[/bold]")

    for username, data in list(contacts.items()):
        if dms_today >= MAX_DM_PER_DAY:
            break
        if data.get("status") not in ("dm_sent",):
            continue
        if data.get("reply_received"):
            continue

        followups_done = data.get("followups_done", 0)
        if followups_done >= MAX_DM_FOLLOWUPS:
            continue

        last_dm = data.get("dm_sent_date") or data.get("last_action_date", "")
        if days_since(last_dm) < DAYS_BEFORE_FOLLOWUP:
            continue

        user_id = data.get("user_id")
        if not user_id:
            continue

        console.print(f"Follow-up #{followups_done + 1} per @{username}...")
        msg = generate_followup(
            username=username,
            full_name="",
            original_message=data.get("message", ""),
            attempt=followups_done + 1
        )

        success = send_dm(cl, user_id, username, msg)
        if success:
            dms_today += 1
            update_contact(username, {
                "followups_done": followups_done + 1,
                "last_followup_message": msg,
                f"followup_{followups_done + 1}_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "dm_sent_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })


# ── Unfollow non-reciprocal ───────────────────────────────────────────────────
def process_unfollow(cl, contacts):
    console.print("[bold]— Unfollow automatico —[/bold]")
    for username, data in list(contacts.items()):
        stage = data.get("stage", "")
        if stage in ("dm_sent", "unfollowed", "not_target", "skipped_private"):
            continue

        followed_date = data.get("followed_date") or data.get("followed_date", "")
        if not followed_date or days_since(followed_date) < DAYS_BEFORE_UNFOLLOW:
            continue

        user_id = data.get("user_id")
        if not user_id:
            continue

        # Check if they follow back
        try:
            friendship = cl.user_friendship_v1(user_id)
            follows_back = getattr(friendship, "followed_by", False)
        except Exception:
            follows_back = False

        if not follows_back:
            console.print(f"[dim]🔕 @{username} non ha ricambiato dopo {DAYS_BEFORE_UNFOLLOW}gg → unfollow[/dim]")
            unfollow_user(cl, user_id, username)
            update_contact(username, {"stage": "unfollowed", "status": "unfollowed"})


# ── Sequence processors ───────────────────────────────────────────────────────
def process_sequence(cl, contacts):
    follows_today = count_today(contacts, "followed")
    likes_today   = count_today(contacts, "liked_post")
    stories_today = count_today(contacts, "liked_story")
    dms_today     = count_today(contacts, "dm_sent")

    if STRATEGY_TYPE == "recommended":
        sequence = ["followed", "liked_story", "dm_sent"]
    else:
        sequence = []
        if CUSTOM_DO_FOLLOW:     sequence.append("followed")
        if CUSTOM_DO_LIKE_POST:  sequence.append("liked_post")
        if CUSTOM_DO_LIKE_STORY: sequence.append("liked_story")
        if CUSTOM_DO_DM:         sequence.append("dm_sent")

    if not sequence:
        return

    console.print(f"[bold]— Avanzamento sequenza ({STRATEGY_TYPE}) —[/bold]")

    for username, data in list(contacts.items()):
        status = data.get("status", "")
        if status in ("not_target", "skipped_private", "dm_sent", "unfollowed", "replied"):
            continue

        stage = data.get("stage", "new")
        last  = data.get("last_action_date", "")
        uid   = data.get("user_id")
        if not uid:
            continue

        # Con days=0 eseguiamo tutta la sequenza in un colpo solo
        steps_to_do = []
        if stage == "new":
            if DAYS_BETWEEN_STEPS == 0:
                steps_to_do = sequence[:]   # tutta la sequenza subito
            else:
                steps_to_do = [sequence[0]]
        elif stage in sequence:
            idx = sequence.index(stage)
            if idx + 1 >= len(sequence):
                continue
            if days_since(last) < DAYS_BETWEEN_STEPS:
                continue
            steps_to_do = [sequence[idx + 1]]
        else:
            continue

        for next_step in steps_to_do:
            if next_step == "followed":
                if follows_today >= MAX_FOLLOWS_PER_DAY: break
                if follow_user(cl, uid, username):
                    follows_today += 1
                    update_contact(username, {"stage": "followed", "followed_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})

            elif next_step == "liked_post":
                if likes_today >= MAX_LIKES_PER_DAY: break
                if like_recent_post(cl, uid, username):
                    likes_today += 1
                    update_contact(username, {"stage": "liked_post", "liked_post_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})

            elif next_step == "liked_story":
                if stories_today >= MAX_STORIES_PER_DAY: break
                like_story(cl, uid, username)
                stories_today += 1
                update_contact(username, {"stage": "liked_story", "liked_story_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})

            elif next_step == "dm_sent":
                if dms_today >= MAX_DM_PER_DAY: break
                msg = data.get("pending_message", "")
                if not msg: break
                if send_dm(cl, uid, username, msg):
                    dms_today += 1
                    update_contact(username, {
                        "stage": "dm_sent", "status": "dm_sent",
                        "message": msg,
                        "dm_sent_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "followups_done": 0,
                    })


# ── Discovery ─────────────────────────────────────────────────────────────────
def discover_new_contacts(cl):
    console.print("[bold]— Ricerca nuovi profili in target —[/bold]")

    for page in TARGET_PAGES:
        console.print(f"\nScansione @{page}...")
        followers = get_followers(cl, page, amount=200)
        console.print(f"Trovati {len(followers)} follower")
        random.shuffle(followers)

        for user in followers:
            username = user.username
            if already_contacted(username):
                continue
            if getattr(user, "is_private", False):
                save_contact(username, "skipped_private", user_id=user.pk, stage="skipped_private")
                continue

            # Pre-filter without full profile call
            bio_short = getattr(user, "biography", "") or ""
            ok, reason = passes_filters(user, bio_short)
            if not ok:
                console.print(f"[dim]@{username} filtrato — {reason}[/dim]")
                save_contact(username, "filtered", user_id=user.pk, stage="filtered")
                continue

            console.print(f"Analisi @{username}...")
            try:
                full = cl.user_info(user.pk)
                bio  = getattr(full, "biography", "") or ""
                loc  = getattr(full, "location", "") or ""

                ok, reason = passes_filters(full, bio)
                if not ok:
                    console.print(f"[dim]@{username} filtrato — {reason}[/dim]")
                    save_contact(username, "filtered", user_id=user.pk, stage="filtered")
                    continue

                result = analyze_profile(
                    username=username,
                    full_name=getattr(full, "full_name", "") or "",
                    bio=bio,
                    followers=getattr(full, "follower_count", 0) or 0,
                    following=getattr(full, "following_count", 0) or 0,
                    posts=getattr(full, "media_count", 0) or 0,
                    location=loc,
                )
            except Exception as e:
                console.print(f"[red]Errore @{username}: {e}[/red]")
                continue

            if not result.get("in_target"):
                console.print(f"[dim]@{username} non in target — {result.get('motivo','')}[/dim]")
                save_contact(username, "not_target", user_id=user.pk, stage="not_target")
                continue

            console.print(f"[cyan]✓ In target! {result.get('motivo','')}[/cyan]")
            save_contact(username, "queued", user_id=user.pk, stage="new",
                         pending_message=result.get("messaggio", ""))


# ── Main ──────────────────────────────────────────────────────────────────────
def run():
    console.print(Panel.fit("[bold blue]Progetto ADS WD[/bold blue]\nInstagram AI Outreach Tool", border_style="blue"))

    if not is_active_now():
        now = datetime.now()
        console.print(f"[yellow]Fuori orario o giorno non attivo ({now.strftime('%A %H:%M')}). Controllare impostazioni schedule.[/yellow]")
        return

    cl = get_client()
    contacts = load_contacts()

    console.print(f"\n[bold]Strategia: [cyan]{STRATEGY_TYPE.upper()}[/cyan][/bold]")

    check_replies(cl)
    process_followups(cl, contacts)

    if CUSTOM_DO_UNFOLLOW or STRATEGY_TYPE == "recommended":
        process_unfollow(cl, contacts)

    # Discovery prima → poi sequenza (così i nuovi contatti vengono processati subito se days=0)
    discover_new_contacts(cl)
    contacts = load_contacts()
    process_sequence(cl, contacts)

    console.print("\n[bold green]✓ Sessione completata.[/bold green]")


if __name__ == "__main__":
    run()
