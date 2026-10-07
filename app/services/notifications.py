"""Envío de emails transaccionales (contrato §5.2: send_email(to, subject, html)).

Se llama desde BackgroundTasks: nunca debe lanzar excepciones, porque la
respuesta HTTP ya se ha enviado. Los errores solo se registran en el log.
"""

import logging

from app.config import settings

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, html: str) -> None:
    """Envía un email. Con EMAIL_ENABLED=false solo lo registra en el log."""
    try:
        if not settings.EMAIL_ENABLED:
            logger.info(
                "Email simulado (EMAIL_ENABLED=false) a=%s asunto=%r", to, subject
            )
            return

        # TODO(HU-19): llamar a POST https://api.brevo.com/v3/smtp/email con httpx
        # usando BREVO_API_KEY y MAIL_FROM. Hasta entonces no se envía nada.
        logger.warning(
            "EMAIL_ENABLED=true pero el envío con Brevo aún no está implementado "
            "(HU-19). Email no enviado a=%s asunto=%r",
            to,
            subject,
        )
    except Exception:
        # Plan §4.4 (HU-19): si el envío falla, la reserva sigue guardada y el
        # error queda en el log.
        logger.exception("Error enviando email a=%s asunto=%r", to, subject)
