from django.core.mail import get_connection

from jibrel.celery import app
from jibrel.notifications.email import EmailMessage
from jibrel.notifications.logging import LoggedCallTask


@app.task(bind=True, base=LoggedCallTask)
def send_mail(
    self: LoggedCallTask,
    subject: str,
    txt_content: str,
    html_content: str,
    recipient: str,
    from_email: str,
    task_context: dict
) -> None:
    def log_email(response):
        self.log_request_and_response(response.request.body, response.text)

    message = EmailMessage(
        subject=subject,
        body=txt_content,
        from_email=from_email,
        to=[recipient],
        connection=get_connection(),
        postprocess=log_email
    )
    message.attach_alternative(html_content, 'text/html')
    message.send()
