from uuid import uuid4

import pytest
from django.urls import reverse

from jibrel.notifications.models import ExternalServiceCallLog


@pytest.mark.django_db
def test_externalservicecalllog_view(admin_client, full_verified_user):
    obj = ExternalServiceCallLog.objects.create(
        uuid=uuid4(),
        action_type=ExternalServiceCallLog.SEND_MAIL,
        initiator_type=ExternalServiceCallLog.SYSTEM_INITIATOR,
        initiator_id=full_verified_user.pk,
        initiator_ip='192.168.1.1',
        kwargs={},
    )
    model = ExternalServiceCallLog
    url = reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_change', args=(obj.pk,))
    response = admin_client.get(url)
    assert response.status_code == 200
