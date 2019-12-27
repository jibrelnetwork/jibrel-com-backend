from jibrel.celery import app


def email_message_send(email_message, recipient, language, kwargs):
    rendered = email_message.render(kwargs, language=language)
    app.send_task(
        'jibrel.notifications.tasks.send_mail',
        kwargs=dict(
            recipient=recipient,
            **rendered.serialize()
        )
    )
