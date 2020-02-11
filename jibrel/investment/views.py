import logging

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import (
    Q,
    Sum,
    Value
)
from django.db.models.functions import Coalesce
from django.http import (
    HttpResponseNotFound,
    HttpResponseRedirect
)
from django.utils.functional import cached_property
from rest_framework import mixins
from rest_framework.decorators import action
from rest_framework.generics import (
    CreateAPIView,
    GenericAPIView,
    get_object_or_404
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from django_banking.contrib.wire_transfer.models import ColdBankAccount
from django_banking.core.api.pagination import CustomCursorPagination
from django_banking.models import (
    Asset,
    UserAccount
)
from jibrel.campaigns.enum import OfferingStatus
from jibrel.campaigns.models import Offering
from jibrel.core.errors import (
    ConflictException,
    ServiceUnavailableException
)
from jibrel.core.permissions import IsKYCVerifiedUser
from jibrel.core.rest_framework import WrapDataAPIViewMixin
from jibrel.investment.enum import InvestmentApplicationStatus
from jibrel.investment.models import (
    InvestmentApplication,
    PersonalAgreement
)
from jibrel.investment.serializer import (
    CreateInvestmentSubscriptionSerializer,
    InvestmentApplicationSerializer
)
from jibrel.investment.tasks import docu_sign_start_task

logger = logging.getLogger(__name__)


class InvestmentSubscriptionAPIView(CreateAPIView):
    permission_classes = [IsAuthenticated, IsKYCVerifiedUser]
    serializer_class = CreateInvestmentSubscriptionSerializer
    offering_queryset = Offering.objects.filter(status=OfferingStatus.WAITLIST)

    @cached_property
    def offering(self):
        offering = get_object_or_404(
            self.offering_queryset,
            pk=self.kwargs.get('offering_id')
        )
        if offering.subscribes.filter(user=self.request.user).exists():
            raise ConflictException()
        return offering

    def perform_create(self, serializer):
        return serializer.save(
            user=self.request.user,
            offering=self.offering
        )


class InvestmentApplicationViewSet(
    # mixins.CreateModelMixin, # TODO add offering in payload
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    permission_classes = [IsAuthenticated, IsKYCVerifiedUser]
    serializer_class = InvestmentApplicationSerializer
    pagination_class = CustomCursorPagination

    def get_queryset(self):
        qs = InvestmentApplication.objects.with_draft().filter(
            user=self.request.user,
            offering__status__in=[OfferingStatus.ACTIVE, ]  # todo
        )
        if self.action == 'list':
            return qs.exclude_draft()
        return qs

    @action(methods=['POST'], detail=True, url_path='finish-signing')
    def finish_signing(self):
        pass


class CreateInvestmentApplicationAPIView(WrapDataAPIViewMixin, CreateAPIView):
    permission_classes = [IsKYCVerifiedUser]
    serializer_class = InvestmentApplicationSerializer
    queryset = InvestmentApplication.objects.all()
    offering_queryset = Offering.objects.active()

    @cached_property
    def offering(self):
        return get_object_or_404(self.offering_queryset, pk=self.kwargs.get('offering_id'))

    def create(self, request, *args, **kwargs):
        if self.offering.applications.filter(user=request.user).exists():
            raise ConflictException()  # user already applied to invest in this offering
        return super().create(request, *args, **kwargs)

    @transaction.atomic()
    def perform_create(self, serializer):
        try:
            bank_account = ColdBankAccount.objects.for_customer(self.request.user)
        except ColdBankAccount.DoesNotExist:
            logger.exception('Bank Account for accepting payment wasn\'t created in Admin')
            raise ServiceUnavailableException()
        instance = serializer.save(
            user=self.request.user,
            offering=self.offering,
            account=UserAccount.objects.for_customer(
                user=self.request.user,
                asset=Asset.objects.main_fiat_for_customer(self.request.user)
            ),
            status=InvestmentApplicationStatus.DRAFT,
            bank_account=bank_account,
        )
        PersonalAgreement.objects.filter(
            offering=instance.offering,
            user=self.request.user,
        ).select_for_update().update(is_agreed=True)
        docu_sign_start_task.delay(application_id=str(instance.pk))


class InvestmentApplicationsSummaryAPIView(GenericAPIView):
    def get_queryset(self):
        return InvestmentApplication.objects.filter(user=self.request.user)

    def get(self, request, *args, **kwargs):
        qs = self.get_queryset()
        total_investment = qs.aggregate(total_investment=Coalesce(
            Sum('amount', filter=Q(
                status__in=[
                    InvestmentApplicationStatus.HOLD,
                    InvestmentApplicationStatus.COMPLETED
                ])),
            Value(0))
        )['total_investment']
        return Response({
            'total_investment': "{0:.2f}".format(total_investment)
        })


class PersonalAgreementAPIView(GenericAPIView):
    permission_classes = [IsAuthenticated, IsKYCVerifiedUser]

    def get(self, request, *args, **kwargs):
        try:
            url = PersonalAgreement.objects.get(
                user=self.request.user,
                offering=self.kwargs.get('offering_id')
            ).file.url
        except PersonalAgreement.DoesNotExist:
            url = f'http://{settings.DOMAIN_NAME.rstrip("/")}/docs/en/subscription-agreement-template.pdf'
        except ValidationError:
            return HttpResponseNotFound()
        return HttpResponseRedirect(url)
