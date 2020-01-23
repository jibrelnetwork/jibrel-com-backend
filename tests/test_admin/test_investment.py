import pytest
from django.urls import reverse

from jibrel.investment.models import InvestmentApplication


@pytest.mark.django_db
def test_investment_application_view(admin_client, application_factory):
    application = application_factory()
    model = InvestmentApplication
    url = reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_change', args=(application.pk,))
    response = admin_client.get(url)
    assert response.status_code == 200
