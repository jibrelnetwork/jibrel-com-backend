import pytest


@pytest.fixture()
def verified_individual_user_kyc(db, full_verified_user):
    return full_verified_user.profile.last_kyc.details


@pytest.fixture()
def verified_organisational_user_kyc(db, full_verified_organisational_user):
    return full_verified_organisational_user.profile.last_kyc.details
