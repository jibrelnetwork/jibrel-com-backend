from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from jibrel.campaigns.enum import RoundName
from jibrel.campaigns.models import (
    Company,
    Offering,
    Security
)
from tests.test_banking.factories.dajngo_banking import AssetFactory


@pytest.fixture()
def company_factory(db):
    counter = 1

    def _company_factory(slug='company_{}', name=None):
        nonlocal counter
        slug = slug.format(counter)
        counter += 1
        if name is None:
            name = slug
        return Company.objects.create(
            slug=slug,
            name=name
        )

    return _company_factory


@pytest.fixture()
def company(company_factory):
    return company_factory()


@pytest.fixture()
def security_factory(db, company_factory):
    def _security_factory(type=Security.TYPE_DEFAULT, company=None, asset=None):
        if company is None:
            company = company_factory()
        if asset is None:
            asset = AssetFactory()
        return Security.objects.create(
            type=type,
            company=company,
            asset=asset,
        )

    return _security_factory


@pytest.fixture()
def security(security_factory):
    return security_factory()


@pytest.fixture()
def offering_factory(security_factory):
    def _offering_factory(
        security=None,
        limit_min_amount=None,
        limit_max_amount=None,
        date_start=None,
        date_end=None,
        valuation=Decimal(1_000_000),
        goal=None,
        round=RoundName.A,
        shares=None,
        price=None,
        status=None,
    ):
        if security is None:
            security = security_factory()
        if date_start is None:
            date_start = timezone.now()
        if date_end is None:
            date_end = date_start + timedelta(days=30)
        if goal is None:
            goal = valuation / 2
        data = dict(
            security=security,
            limit_min_amount=limit_min_amount,
            limit_max_amount=limit_max_amount,
            date_start=date_start,
            date_end=date_end,
            valuation=valuation,
            goal=goal,
            round=round,
            shares=shares,
            price=price,
            status=status,
        )
        return Offering.objects.create(
            **{k: v for k, v in data.items() if v is not None}
        )
    return _offering_factory


@pytest.fixture()
def offering(offering_factory):
    return offering_factory()
