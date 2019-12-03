from jibrel.authentication.models import User
from jibrel.authentication.services import request_password_reset
from jibrel.celery import app


@app.task(expires=60 * 30)
def send_password_reset_mail(user_ip: str, user_pk: str):
    user = User.objects.get(pk=user_pk)
    request_password_reset(user_ip, user.email)
