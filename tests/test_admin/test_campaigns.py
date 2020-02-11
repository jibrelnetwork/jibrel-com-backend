import pytest
from django.urls import reverse

from jibrel.investment.models import InvestmentSubscription


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


@pytest.mark.django_db
def test_offering_subscriptions_xlsx(admin_client, full_verified_user, offering_waitlist):
    InvestmentSubscription.objects.create(
        email='asdf@gmail.com',
        amount=233,
        user=full_verified_user,
        offering=offering_waitlist,
    )
    model = offering_waitlist.__class__
    url = reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_actions', kwargs={
        'pk': offering_waitlist.pk,
        'tool': 'waitlist'
    })
    response = admin_client.get(url)
    assert response.status_code == 200
    assert response._headers['content-disposition'][1].startswith('attachment')
