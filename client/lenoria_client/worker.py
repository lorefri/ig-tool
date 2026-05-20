"""Worker loop: polla il server, esegue le azioni IG, riporta risultati.

F4: executor reali tramite instagrapi. Flag `dry_run` per testare il flusso
senza chiamare Instagram (utile per QA del routing/queue).
"""

import random
import threading
import time
from datetime import datetime, timezone
from typing import Optional

from .api_client import ApiClient, ApiError, TokenRevoked
from .ig_session import IgSession
from .log import get

_log = get("worker")


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Esecutori delle azioni ───────────────────────────────────────────────────


def _stub_execute(kind: str, payload: dict, ig: IgSession) -> tuple[bool, dict, Optional[str]]:
    """Simulazione (per --dry-run): attendi 1-3s, 95% successo. Niente call IG."""
    _log.info(f"  [DRY-RUN] {kind} payload={payload}")
    time.sleep(random.uniform(1.0, 3.0))
    if random.random() < 0.95:
        return True, {"stub": True, "kind": kind, "executed_at": _iso_now()}, None
    return False, {}, f"Stub-error simulato per {kind}"


def _resolve_user_id(ig: IgSession, payload: dict) -> tuple[Optional[int], Optional[str]]:
    """Estrae user_id dal payload o lo risolve via username. Ritorna (user_id, username)."""
    user_id = payload.get("user_id")
    username = payload.get("target_username") or payload.get("username") or payload.get("contact_username") or ""
    if user_id:
        return int(user_id), username
    if not username:
        return None, ""
    cl = ig.get_client()
    from .ig.actions import resolve_user_id
    return resolve_user_id(cl, username), username


def _exec_like_post(payload, ig):
    from .ig.actions import like_recent_post
    user_id, username = _resolve_user_id(ig, payload)
    if not user_id:
        return False, {}, "user_id/username mancante nel payload"
    cl = ig.get_client()
    ok, msg = like_recent_post(cl, user_id, username)
    return ok, {"username": username, "user_id": user_id, "msg": msg}, None if ok else msg


def _exec_like_story(payload, ig):
    from .ig.actions import like_story
    user_id, username = _resolve_user_id(ig, payload)
    if not user_id:
        return False, {}, "user_id/username mancante nel payload"
    cl = ig.get_client()
    ok, msg = like_story(cl, user_id, username)
    return ok, {"username": username, "user_id": user_id, "msg": msg}, None if ok else msg


def _exec_follow(payload, ig):
    from .ig.actions import follow_user
    user_id, username = _resolve_user_id(ig, payload)
    if not user_id:
        return False, {}, "user_id/username mancante"
    cl = ig.get_client()
    ok, msg = follow_user(cl, user_id, username)
    return ok, {"username": username, "user_id": user_id, "msg": msg}, None if ok else msg


def _exec_unfollow(payload, ig):
    from .ig.actions import unfollow_user
    user_id, username = _resolve_user_id(ig, payload)
    if not user_id:
        return False, {}, "user_id/username mancante"
    cl = ig.get_client()
    ok, msg = unfollow_user(cl, user_id, username)
    return ok, {"username": username, "user_id": user_id, "msg": msg}, None if ok else msg


def _exec_dm(payload, ig):
    """Per il DM il `message` deve essere nel payload (già richiesto via draft-message)."""
    from .ig.actions import send_dm
    message = payload.get("message", "")
    if not message:
        return False, {}, "message vuoto"
    user_id, username = _resolve_user_id(ig, payload)
    if not user_id:
        return False, {}, "user_id/username mancante"
    cl = ig.get_client()
    ok, msg = send_dm(cl, user_id, username, message)
    return ok, {"username": username, "user_id": user_id, "msg": msg}, None if ok else msg


def _exec_discovery(payload, ig):
    """Esegue discovery: trova nuovi user da una fonte.
    Payload: {source_type: 'hashtag'|'page', source: 'X', amount: N}
    - hashtag: ultimi post recenti del tag, estraggo gli autori
    - page: followers dell'utente
    Ritorna lista user trovati come result.
    """
    src_type = payload.get("source_type", "")
    source = str(payload.get("source", "")).strip().lstrip("#").lstrip("@")
    amount = int(payload.get("amount", 10))
    if not source:
        return False, {}, "source vuota nel payload"
    cl = ig.get_client()

    seen = set()
    users = []

    try:
        if src_type == "hashtag":
            medias = cl.hashtag_medias_recent(source, amount=amount)
            for m in medias:
                u = getattr(m, "user", None)
                if u is None: continue
                pk = getattr(u, "pk", None)
                if not pk or pk in seen: continue
                seen.add(pk)
                users.append({
                    "user_id": int(pk),
                    "username": u.username,
                    "full_name": u.full_name or "",
                    "is_private": bool(getattr(u, "is_private", False)),
                    "is_verified": bool(getattr(u, "is_verified", False)),
                })
        elif src_type == "page":
            page_user_id = cl.user_id_from_username(source)
            followers = cl.user_followers(int(page_user_id), amount=amount)
            # user_followers ritorna dict {user_id: User}
            items = followers.values() if isinstance(followers, dict) else followers
            for u in items:
                pk = getattr(u, "pk", None)
                if not pk or pk in seen: continue
                seen.add(pk)
                users.append({
                    "user_id": int(pk),
                    "username": u.username,
                    "full_name": u.full_name or "",
                    "is_private": bool(getattr(u, "is_private", False)),
                    "is_verified": bool(getattr(u, "is_verified", False)),
                })
        else:
            return False, {}, f"source_type '{src_type}' non supportato (atteso hashtag|page)"
    except Exception as e:
        return False, {}, f"discovery {src_type}/{source}: {e}"

    return True, {
        "source_type": src_type, "source": source,
        "users_count": len(users), "users": users,
    }, None


def _exec_check_replies(payload, ig):
    """Scarica i thread DM 1:1 recenti e ritorna l'ultimo msg di testo del lead per ognuno.
    Il server filtra/applica gli effetti su ig_contacts (stage='replied', reply_text)."""
    cl = ig.get_client()
    amount = int(payload.get("amount") or 200)
    try:
        threads = cl.direct_threads(amount=amount)
    except Exception as e:
        return False, {}, f"direct_threads: {e}"
    my_user_id = cl.user_id
    replies = []
    for t in threads:
        users = getattr(t, "users", []) or []
        # Solo thread 1:1 (skip gruppi)
        if len(users) != 1:
            continue
        u = users[0]
        username = getattr(u, "username", "") or ""
        if not username:
            continue
        # I messaggi sono ordinati dal più recente al più vecchio.
        # Cerca il primo (più recente) messaggio testuale del lead (non mio).
        last_text = None
        last_ts = None
        for msg in getattr(t, "messages", []) or []:
            if getattr(msg, "user_id", None) == my_user_id:
                continue
            if getattr(msg, "item_type", "") != "text":
                continue
            text = (getattr(msg, "text", "") or "").strip()
            if not text:
                continue
            last_text = text
            ts = getattr(msg, "timestamp", None)
            last_ts = ts.isoformat() if ts else None
            break
        if last_text:
            replies.append({
                "username": username,
                "user_id": int(getattr(u, "pk", 0) or 0) or None,
                "last_lead_text": last_text,
                "last_lead_timestamp": last_ts,
            })
    return True, {"replies_count": len(replies), "replies": replies}, None


def _exec_score(payload, ig):
    """Fetch profilo completo via instagrapi, ritorna campi che il server usa
    per chiamare ai_agent.analyze_profile() (scoring + DM draft).
    Payload: {target_username, user_id?}"""
    user_id, username = _resolve_user_id(ig, payload)
    if not username:
        return False, {}, "username mancante nel payload"
    cl = ig.get_client()
    try:
        if user_id:
            info = cl.user_info(int(user_id))
        else:
            info = cl.user_info_by_username(username)
    except Exception as e:
        return False, {}, f"user_info({username}): {e}"
    return True, {
        "username": info.username,
        "user_id": int(info.pk),
        "full_name": info.full_name or "",
        "bio": getattr(info, "biography", "") or "",
        "followers": int(getattr(info, "follower_count", 0) or 0),
        "following": int(getattr(info, "following_count", 0) or 0),
        "media_count": int(getattr(info, "media_count", 0) or 0),
        "is_private": bool(getattr(info, "is_private", False)),
        "is_verified": bool(getattr(info, "is_verified", False)),
        "external_url": getattr(info, "external_url", "") or "",
    }, None


# Dispatch table per executor reali (modalità production).
EXECUTORS = {
    "dm":            _exec_dm,
    "follow":        _exec_follow,
    "unfollow":      _exec_unfollow,
    "like_post":     _exec_like_post,
    "like_story":    _exec_like_story,
    "discovery":     _exec_discovery,
    "check_replies": _exec_check_replies,
    "score":         _exec_score,
}


def _parse_execute_at(s: str) -> datetime:
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return datetime.now(timezone.utc)


# ── Worker loop principale ───────────────────────────────────────────────────


class Worker:
    """Loop principale. Esegue in foreground (chiama run()).
    Heartbeat in thread separato (non blocca il worker).
    """

    def __init__(self, api: ApiClient, heartbeat_interval: int = 300, dry_run: bool = False):
        self.api = api
        self.heartbeat_interval = heartbeat_interval
        self.dry_run = dry_run
        self._stop = threading.Event()
        self._heartbeat_thread: Optional[threading.Thread] = None
        self.ig = IgSession(api) if not dry_run else None
        # Stats aggregate per heartbeat
        self.actions_done = 0
        self.actions_failed = 0

    def stop(self):
        self._stop.set()

    def _heartbeat_loop(self):
        """Manda heartbeat ogni N secondi finché _stop non viene settato."""
        # Primo heartbeat immediato
        while not self._stop.is_set():
            try:
                resp = self.api.heartbeat(running=True, stats={
                    "actions_done": self.actions_done,
                    "actions_failed": self.actions_failed,
                })
                if resp.get("force_update_to"):
                    _log.warning(f"Server segnala aggiornamento richiesto: "
                                 f"v{resp['force_update_to']} (sei su questa versione vecchia)")
                # NB: il "kill_switch" effettivo arriva via 401 TokenRevoked sui prossimi call autenticati.
            except TokenRevoked:
                _log.error("Token revocato dal server. Mi spengo.")
                self._stop.set()
                return
            except ApiError as e:
                _log.warning(f"Heartbeat fallito: {e}")
            except Exception as e:
                _log.warning(f"Heartbeat eccezione: {e}")
            # Sleep frazionato per rispondere subito a stop
            for _ in range(self.heartbeat_interval):
                if self._stop.is_set():
                    return
                time.sleep(1)

    def _execute_action(self, action: dict):
        """Esegue una singola azione e riporta l'esito."""
        kind = action.get("kind", "")
        payload = action.get("payload", {}) or {}
        action_id = action["id"]
        executor = EXECUTORS.get(kind)
        if not executor:
            _log.error(f"Action kind sconosciuto: {kind} (id={action_id})")
            self.api.result(action_id, "failed", error=f"Kind sconosciuto: {kind}")
            self.actions_failed += 1
            return

        # Per i DM, il messaggio lo chiede al server just-in-time
        if kind == "dm" and "message" not in payload:
            try:
                draft = self.api.draft_message(
                    contact_username=payload.get("contact_username", "") or payload.get("target_username", ""),
                    kind=payload.get("dm_kind", "first_dm"),
                )
                payload = {**payload, "message": draft.get("message", "")}
            except Exception as e:
                _log.error(f"Impossibile ottenere draft message: {e}")
                self.api.result(action_id, "failed", error=f"draft_message: {e}")
                self.actions_failed += 1
                return

        # Esegui (dry-run = stub; production = executor reale tramite IgSession)
        try:
            if self.dry_run:
                ok, result, err = _stub_execute(kind, payload, self.ig)
            else:
                ok, result, err = executor(payload, self.ig)
        except Exception as e:
            _log.exception(f"Eccezione executor {kind}: {e}")
            # Se è LoginRequired, invalido la sessione per re-login prossima volta
            if "LoginRequired" in type(e).__name__:
                if self.ig:
                    self.ig.invalidate()
            self.api.result(action_id, "failed", error=f"Eccezione: {e}")
            self.actions_failed += 1
            return

        if ok:
            self.api.result(action_id, "done", result=result)
            self.actions_done += 1
        else:
            self.api.result(action_id, "failed", error=err)
            self.actions_failed += 1

    def run(self):
        """Loop principale. Esegue finché stop() o token revocato."""
        _log.info("Worker avviato.")
        # Heartbeat thread in background
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()

        next_poll_in = 60
        while not self._stop.is_set():
            try:
                resp = self.api.plan()
                actions = resp.get("actions", [])
                next_poll_in = int(resp.get("next_poll_in", 60))
            except TokenRevoked:
                _log.error("Token revocato dal server. Mi spengo.")
                break
            except ApiError as e:
                _log.warning(f"Plan fetch fallito: {e}. Riprovo in {next_poll_in}s.")
                actions = []
            except Exception as e:
                _log.error(f"Eccezione su plan(): {e}")
                actions = []

            if actions:
                _log.info(f"Ricevute {len(actions)} azioni dal server.")
                for action in actions:
                    if self._stop.is_set():
                        break
                    execute_at = _parse_execute_at(action.get("execute_at", _iso_now()))
                    delay = (execute_at - datetime.now(timezone.utc)).total_seconds()
                    if delay > 0:
                        # Aspetta il momento giusto (interrompibile da stop)
                        if self._stop.wait(timeout=delay):
                            break
                    self._execute_action(action)
            else:
                # Nessuna azione → aspetta next_poll_in (interrompibile)
                if self._stop.wait(timeout=next_poll_in):
                    break

        _log.info(f"Worker fermato. Stats: {self.actions_done} done, {self.actions_failed} failed.")
