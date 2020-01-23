import pytest

from jibrel.campaigns.models import Offering
from jibrel.investment.enum import InvestmentApplicationStatus


@pytest.mark.django_db
def test_single_offering(offering, application_factory):
    application_factory(amount=100, status=InvestmentApplicationStatus.PENDING, offering=offering)
    o = Offering.objects.with_application_statistics().with_money_statistics().get(pk=offering.pk)
    assert o.pending_applications_count == 1
    assert o.pending_money_sum == 100
    assert o.total_applications_count == 1
    assert o.total_money_sum == 100

    application_factory(amount=100, status=InvestmentApplicationStatus.HOLD, offering=offering)
    o = Offering.objects.with_application_statistics().with_money_statistics().get(pk=offering.pk)
    assert o.pending_applications_count == 1
    assert o.pending_money_sum == 100
    assert o.hold_applications_count == 1
    assert o.hold_money_sum == 100
    assert o.total_applications_count == 2
    assert o.total_money_sum == 200

    application_factory(amount=100, status=InvestmentApplicationStatus.COMPLETED, offering=offering)
    o = Offering.objects.with_application_statistics().with_money_statistics().get(pk=offering.pk)
    assert o.pending_applications_count == 1
    assert o.pending_money_sum == 100
    assert o.hold_applications_count == 1
    assert o.hold_money_sum == 100
    assert o.completed_applications_count == 1
    assert o.completed_money_sum == 100
    assert o.total_applications_count == 3
    assert o.total_money_sum == 300

    application_factory(amount=100, status=InvestmentApplicationStatus.CANCELED, offering=offering)
    o = Offering.objects.with_application_statistics().with_money_statistics().get(pk=offering.pk)
    assert o.pending_applications_count == 1
    assert o.pending_money_sum == 100
    assert o.hold_applications_count == 1
    assert o.hold_money_sum == 100
    assert o.completed_applications_count == 1
    assert o.completed_money_sum == 100
    assert o.canceled_applications_count == 1
    assert o.canceled_money_sum == 100
    assert o.total_applications_count == 4
    assert o.total_money_sum == 400


@pytest.mark.django_db
def test_many_offerings(offering_factory, application_factory):
    offering1 = offering_factory()
    application_factory(amount=100, status=InvestmentApplicationStatus.PENDING, offering=offering1)
    application_factory(amount=100, status=InvestmentApplicationStatus.PENDING, offering=offering1)
    o1 = Offering.objects.with_application_statistics().with_money_statistics().get(pk=offering1.pk)
    assert o1.pending_applications_count == 2
    assert o1.pending_money_sum == 200

    offering2 = offering_factory()
    application_factory(amount=100, status=InvestmentApplicationStatus.PENDING, offering=offering2)
    application_factory(amount=100, status=InvestmentApplicationStatus.PENDING, offering=offering2)
    o1 = Offering.objects.with_application_statistics().with_money_statistics().get(pk=offering1.pk)
    o2 = Offering.objects.with_application_statistics().with_money_statistics().get(pk=offering2.pk)
    assert o1.pending_applications_count == 2
    assert o1.pending_money_sum == 200
    assert o2.pending_applications_count == 2
    assert o2.pending_money_sum == 200
