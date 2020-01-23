import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_company_view(admin_client, company_factory):
    obj = company_factory(slug='blabla')
    model = obj.__class__
    url = reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_change', args=(obj.pk,))
    response = admin_client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_security_view(admin_client, security_factory):
    obj = security_factory()
    model = obj.__class__
    url = reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_change', args=(obj.pk,))
    response = admin_client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_offering_view(admin_client, offering_factory):
    obj = offering_factory()
    model = obj.__class__
    url = reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_change', args=(obj.pk,))
    response = admin_client.get(url)
    assert response.status_code == 200
