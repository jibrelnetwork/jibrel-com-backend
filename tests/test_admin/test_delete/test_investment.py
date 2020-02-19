import pytest
from django.urls import reverse

from jibrel.investment.enum import InvestmentApplicationStatus


@pytest.mark.parametrize(
    'allow_all,deposit,expected_status',
    [
        (False, False, 302),
        (False, True, 403),
        (True, False, 302),
        (True, True, 302),
    ]
)
@pytest.mark.django_db
def test_deletion(settings, admin_client,
                  allow_all, deposit, expected_status,
                  application_factory, deposit_operation):
    settings.ALLOW_INVESTMENT_APPLICATION_DELETION = allow_all
    obj = application_factory(status=InvestmentApplicationStatus.COMPLETED)
    if deposit:
        obj.deposit = deposit_operation
        obj.save()

    model = obj.__class__
    url = reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_delete', args=(obj.pk,))
    response = admin_client.post(url, {'post': 'yes'})
    assert response.status_code == expected_status
    assert model.objects.filter(pk=obj.pk).exists() is (expected_status != 302)
