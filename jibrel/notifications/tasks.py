from anymail.exceptions import AnymailRequestsAPIError
from django.core.mail import get_connection

from jibrel.celery import app
from jibrel.notifications.email import EmailMessage
from jibrel.notifications.logging import LoggedCallTask
from jibrel.notifications.models import ExternalServiceCallLog


@app.task(bind=True, base=LoggedCallTask)
def send_mail(
    self: LoggedCallTask,
    subject: str,
    txt_content: str,
    html_content: str,
    recipient: str,
    from_email: str,
    task_context: dict = None
) -> None:
    def log_email(response, status=ExternalServiceCallLog.SUCCESS):
        self.log_request_and_response(response.request.body, response.text, status)

    _task_context = task_context or {}  # NOQA
    message = EmailMessage(
        subject=subject,
        body=txt_content,
        from_email=from_email,
        to=[recipient],
        connection=get_connection(),
        postprocess=log_email
    )
    message.attach_alternative(html_content, 'text/html')
    try:
        message.send()
    except AnymailRequestsAPIError as e:
        log_email(e.response, ExternalServiceCallLog.ERROR)
