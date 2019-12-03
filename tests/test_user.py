import phonenumbers
import pytest

from jibrel.core.exceptions import NonSupportedCountryException


@pytest.mark.django_db
def test_get_residency_country_code_user_without_any(
    user_not_confirmed,
    user_confirmed_email,
):
    with pytest.raises(NonSupportedCountryException):
        assert user_not_confirmed.get_residency_country_code()
    with pytest.raises(NonSupportedCountryException):
        assert user_confirmed_email.get_residency_country_code()


@pytest.mark.parametrize(
    'code,number,country',
    (
        ('971', '545559508', 'AE'),
        ('971', '565556185', 'AE'),
        ('966', '515559304', 'SA'),
        ('966', '505555154', 'SA'),
        ('973', '37755588', 'BH'),
        ('973', '38355596', 'BH'),
        ('965', '55551427', 'KW'),
        ('965', '55559305', 'KW'),
        ('968', '91555817', 'OM'),
        ('968', '96555647', 'OM'),
        ('7', '9502216578', None),
        ('1', '5417543010', None),
        ('44', '7155584977', None),
    )
)
@pytest.mark.django_db
def test_get_residency_country_code_by_phone(
    code,
    number,
    country,
    user_with_phone,
    user_with_confirmed_phone,
    full_verified_user,
):
    phone_obj = phonenumbers.parse(f'+{code}{number}')
    assert phonenumbers.is_valid_number(phone_obj)

    phone = user_with_phone.profile.phone
    phone.code = code
    phone.number = number
    phone.save()

    try:
        returned_country = user_with_phone.get_residency_country_code()
    except NonSupportedCountryException:
        returned_country = None

    assert returned_country == country

    phone = user_with_confirmed_phone.profile.phone
    phone.code = code
    phone.number = number
    phone.save()

    try:
        returned_country = user_with_confirmed_phone.get_residency_country_code()
    except NonSupportedCountryException:
        returned_country = None

    assert returned_country == country

    phone = full_verified_user.profile.phone
    phone.code = code
    phone.number = number
    phone.save()

    full_verified_user.profile.last_basic_kyc.residency = 'N'
    full_verified_user.profile.last_basic_kyc.save()

    try:
        returned_country = full_verified_user.get_residency_country_code()
    except NonSupportedCountryException:
        returned_country = None

    if country is not None:
        assert returned_country != country


@pytest.mark.parametrize(
    'country',
    ('AE', 'SA', 'BH', 'KW', 'OM',)
)
@pytest.mark.django_db
def test_get_residency_country_code_with_kyc(
    country,
    full_verified_user,
):
    full_verified_user.profile.last_basic_kyc.residency = country
    full_verified_user.profile.last_basic_kyc.save()

    assert full_verified_user.get_residency_country_code() == country
