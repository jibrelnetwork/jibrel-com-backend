import pytest
from django.urls import reverse

from jibrel.authentication.models import User


@pytest.mark.django_db
def test_kyc_force_onfido_routine(admin_client, full_verified_user, mocker):
    mock = mocker.patch('jibrel.authentication.services.send_mail.delay')
    model = full_verified_user.__class__
    url = reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_actions', kwargs={
        'pk': full_verified_user.pk,
        'tool': 'send_password_reset_mail'
    })
    response = admin_client.get(url)
    assert response.status_code == 302
    mock.assert_called()
