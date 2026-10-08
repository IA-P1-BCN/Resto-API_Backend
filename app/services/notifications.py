"""Envío de emails transaccionales (contrato §5.2: send_email(to, subject, html)).

Se llama desde BackgroundTasks: nunca debe lanzar excepciones, porque la
respuesta HTTP ya se ha enviado. Los errores solo se registran en el log.
"""

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"
BREVO_TIMEOUT_SECONDS = 10


def send_email(to: str, subject: str, html: str) -> None:
    """Envía un email con Brevo. Con EMAIL_ENABLED=false solo lo registra en el log.

    Nunca lanza excepciones: se llama desde BackgroundTasks, después de enviar
    la respuesta HTTP. Si Brevo falla, la reserva ya está guardada y el error
    queda en el log (§4.4 de HU-19).
    """
    try:
        if not settings.EMAIL_ENABLED:
            logger.info(
                "Email simulado (EMAIL_ENABLED=false) a=%s asunto=%r", to, subject
            )
            return

        if not settings.BREVO_API_KEY or not settings.MAIL_FROM:
            logger.warning(
                "EMAIL_ENABLED=true pero falta BREVO_API_KEY o MAIL_FROM; "
                "email no enviado a=%s asunto=%r",
                to,
                subject,
            )
            return

        payload = {
            "sender": {"email": settings.MAIL_FROM},
            "to": [{"email": to}],
            "subject": subject,
            "htmlContent": html,
        }
        headers = {
            "api-key": settings.BREVO_API_KEY,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        response = httpx.post(
            BREVO_API_URL,
            json=payload,
            headers=headers,
            timeout=BREVO_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        logger.info("Email enviado a=%s asunto=%r", to, subject)
    except Exception:
        # Plan §4.4 (HU-19): si el envío falla, la reserva sigue guardada y el
        # error queda en el log.
        logger.exception("Error enviando email a=%s asunto=%r", to, subject)
