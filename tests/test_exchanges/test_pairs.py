import pytest

from jibrel.authentication.factories import VerifiedUser
from tests.test_payments.utils import validate_response_schema


@pytest.fixture()
def verified_user_factory(full_verified_user):
    def create_user(residency):
        user = VerifiedUser.create()
        user.profile.last_basic_kyc.residency = residency
        user.profile.last_basic_kyc.save()
        return user
    return create_user


@pytest.mark.parametrize(
    'currency, country',
    (
        ('AED', 'AE'),
        ('SAR', 'SA'),
        ('BHD', 'BH'),
        ('KWD', 'KW'),
        ('OMR', 'OM'),
        ('USD', 'RU'),
    )
)
@pytest.mark.django_db
def test_pairs_by_country(currency, country, client, verified_user_factory):
    url = '/v1/exchanges/pairs'
    user = verified_user_factory(country)
    client.force_login(user)
    response = client.get(url)
    assert response.status_code == 200
    validate_response_schema(url, 'GET', response)
    for pair in response.data['data']:
        assert pair['quoteAsset'].upper() == currency
