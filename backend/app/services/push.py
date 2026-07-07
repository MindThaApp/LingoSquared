import json
import logging

from pywebpush import WebPushException, webpush
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import PushSubscription

logger = logging.getLogger(__name__)


def push_configured() -> bool:
    settings = get_settings()
    return bool(settings.vapid_public_key and settings.vapid_private_key)


def send_push_to_user(db: Session, user_id: str, title: str, body: str, url: str = "/") -> int:
    """Sends a push notification to every subscription registered for
    a user. Returns the number of subscriptions successfully notified.
    Dead subscriptions (expired/unsubscribed — pywebpush raises with a
    404/410 response from the push service) are pruned automatically,
    same "honest fallback, never silently dead" convention the rest of
    this project's optional-provider integrations follow.
    """
    if not push_configured():
        return 0
    settings = get_settings()
    subscriptions = db.scalars(
        select(PushSubscription).where(PushSubscription.user_id == user_id)
    ).all()
    payload = json.dumps({"title": title, "body": body, "url": url})
    sent = 0
    for sub in subscriptions:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
                },
                data=payload,
                vapid_private_key=settings.vapid_private_key,
                vapid_claims={"sub": settings.vapid_subject},
            )
            sent += 1
        except WebPushException as exc:
            status_code = getattr(exc.response, "status_code", None)
            if status_code in (404, 410):
                db.delete(sub)
            else:
                logger.warning("web push failed for subscription %s: %s", sub.id, exc)
    db.commit()
    return sent
