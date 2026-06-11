import logging
from datetime import datetime, timezone

from flask import request as flask_request
from flask_login import current_user

from app import db
from app.models import AuditLog

logger = logging.getLogger(__name__)


def log_event(
    accion,
    nivel=AuditLog.INFO,
    actor=None,
    target_tipo=None,
    target_id=None,
    target_label=None,
    detalle=None,
    req=None,
):
    """Persiste un AuditLog. Nunca lanza excepción — los fallos van al logger de aplicación."""
    try:
        req = req or flask_request._get_current_object()

        actor_id = None
        actor_username = ""

        if isinstance(actor, str):
            # Login fallido: username intentado, sin objeto User válido
            actor_username = actor
        elif actor is not None:
            actor_id = actor.id
            actor_username = actor.username
        else:
            try:
                if current_user.is_authenticated:
                    actor_id = current_user.id
                    actor_username = current_user.username
            except Exception:
                pass

        if req:
            forwarded = req.headers.get("X-Forwarded-For")
            ip = forwarded.split(",")[0].strip() if forwarded else req.remote_addr
            ua = (req.headers.get("User-Agent") or "")[:300]
        else:
            ip = None
            ua = ""

        entry = AuditLog(
            timestamp=datetime.now(timezone.utc),
            actor_id=actor_id,
            actor_username=actor_username,
            accion=accion,
            nivel=nivel,
            ip=ip,
            user_agent=ua,
            target_tipo=target_tipo,
            target_id=target_id,
            target_label=target_label,
            detalle=detalle,
        )
        db.session.add(entry)
        db.session.commit()

    except Exception as exc:
        try:
            db.session.rollback()
        except Exception:
            pass
        logger.error("log_event falló [accion=%s]: %s", accion, exc, exc_info=True)
