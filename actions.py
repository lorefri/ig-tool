import time
import random
from rich.console import Console

console = Console()

def _delay(min_s=3, max_s=9):
    time.sleep(random.randint(min_s, max_s))


def follow_user(cl, user_id: int, username: str) -> bool:
    try:
        cl.user_follow(user_id)
        console.print(f"[cyan]👤 Seguito @{username}[/cyan]")
        _delay()
        return True
    except Exception as e:
        console.print(f"[red]Errore follow @{username}: {e}[/red]")
        return False


def unfollow_user(cl, user_id: int, username: str) -> bool:
    try:
        cl.user_unfollow(user_id)
        console.print(f"[dim]🔕 Unfollowed @{username}[/dim]")
        _delay()
        return True
    except Exception as e:
        console.print(f"[red]Errore unfollow @{username}: {e}[/red]")
        return False


def like_recent_post(cl, user_id: int, username: str) -> bool:
    try:
        medias = cl.user_medias(user_id, amount=3)
        if not medias:
            console.print(f"[dim]@{username} — nessun post disponibile[/dim]")
            return False
        cl.media_like(medias[0].id)
        console.print(f"[cyan]❤️  Like post di @{username}[/cyan]")
        _delay()
        return True
    except Exception as e:
        console.print(f"[red]Errore like post @{username}: {e}[/red]")
        return False


def like_story(cl, user_id: int, username: str) -> bool:
    try:
        stories = cl.user_stories(user_id)
        if not stories:
            console.print(f"[dim]@{username} — nessuna storia disponibile[/dim]")
            return False
        cl.story_like(stories[0].pk)
        console.print(f"[cyan]👁️  Like storia di @{username}[/cyan]")
        _delay()
        return True
    except Exception as e:
        console.print(f"[red]Errore like storia @{username}: {e}[/red]")
        return False
