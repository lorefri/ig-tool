"""Azioni atomiche su Instagram. Adattamento di `actions.py` server-side senza
dipendenze da rich. Ogni funzione ritorna (success: bool, message: str).
"""

import random
import time

from ..log import get

_log = get("ig.actions")


def _delay(min_s: int = 3, max_s: int = 9):
    time.sleep(random.randint(min_s, max_s))


def follow_user(cl, user_id: int, username: str) -> tuple[bool, str]:
    try:
        cl.user_follow(user_id)
        _log.info(f"  👤 seguito @{username}")
        _delay()
        return True, f"Seguito @{username}"
    except Exception as e:
        _log.error(f"  follow @{username}: {e}")
        return False, str(e)


def unfollow_user(cl, user_id: int, username: str) -> tuple[bool, str]:
    try:
        cl.user_unfollow(user_id)
        _log.info(f"  🔕 unfollowed @{username}")
        _delay()
        return True, f"Unfollowed @{username}"
    except Exception as e:
        _log.error(f"  unfollow @{username}: {e}")
        return False, str(e)


def like_recent_post(cl, user_id: int, username: str) -> tuple[bool, str]:
    try:
        medias = cl.user_medias(user_id, amount=3)
        if not medias:
            return False, f"Nessun post per @{username}"
        cl.media_like(medias[0].id)
        _log.info(f"  ❤️  like post di @{username} (media_id={medias[0].id})")
        _delay()
        return True, f"Like post di @{username} (media={medias[0].id})"
    except Exception as e:
        _log.error(f"  like_post @{username}: {e}")
        return False, str(e)


def like_story(cl, user_id: int, username: str) -> tuple[bool, str]:
    try:
        stories = cl.user_stories(user_id)
        if not stories:
            return False, f"Nessuna storia per @{username}"
        cl.story_like(stories[0].pk)
        _log.info(f"  👁️  like storia di @{username} (pk={stories[0].pk})")
        _delay()
        return True, f"Like storia di @{username} (story={stories[0].pk})"
    except Exception as e:
        _log.error(f"  like_story @{username}: {e}")
        return False, str(e)


def send_dm(cl, user_id: int, username: str, message: str) -> tuple[bool, str]:
    try:
        thread = cl.direct_send(message, user_ids=[user_id])
        _log.info(f"  📩 DM a @{username}")
        _delay()
        return True, f"DM inviato a @{username} (thread={thread.id})"
    except Exception as e:
        _log.error(f"  send_dm @{username}: {e}")
        return False, str(e)


def resolve_user_id(cl, username: str) -> int:
    """Cerca l'id Instagram a partire dallo username (usato quando il server
    ci passa solo lo username e non l'user_id)."""
    info = cl.user_info_by_username(username)
    return int(info.pk)
