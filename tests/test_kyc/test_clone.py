import pytest


@pytest.mark.django_db
def test_clone_kyc(
    full_verified_user,
):
    last_kyc = full_verified_user.profile.last_kyc.details
    new_kyc = last_kyc.clone()
    assert new_kyc.pk != last_kyc.pk
    assert new_kyc.base_kyc.pk != last_kyc.base_kyc.pk
    assert new_kyc.profile.pk == last_kyc.profile.pk


@pytest.mark.django_db
def test_clone_organisational_kyc(
    full_verified_organisational_user,
):
    last_kyc = full_verified_organisational_user.profile.last_kyc.details
    new_kyc = last_kyc.clone()
    assert new_kyc.pk != last_kyc.pk
    assert new_kyc.base_kyc.pk != last_kyc.base_kyc.pk
    assert new_kyc.profile.pk == last_kyc.profile.pk

    assert new_kyc.commercial_register.pk != last_kyc.commercial_register.pk
    assert new_kyc.shareholder_register.pk != last_kyc.shareholder_register.pk
    assert new_kyc.articles_of_incorporation.pk != last_kyc.articles_of_incorporation.pk

    assert new_kyc.company_address_registered.pk != last_kyc.company_address_registered.pk
    assert new_kyc.company_address_principal.pk != last_kyc.company_address_principal.pk

    compare_instances = lambda att, sub: len(
        set(getattr(last_kyc, att).values_list(sub, flat=True)) &
        set(getattr(new_kyc, att).values_list(sub, flat=True))
    ) == 0

    assert compare_instances('directors', 'pk')
    assert compare_instances('directors', 'pk')
    assert compare_instances('beneficiaries', 'proof_of_address_document_id')
    assert compare_instances('beneficiaries', 'passport_document_id')
