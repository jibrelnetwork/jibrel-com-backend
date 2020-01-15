from django.utils.functional import cached_property
from rest_framework.generics import (
    CreateAPIView,
    get_object_or_404
)

from django_banking.models import (
    Asset,
    UserAccount
)
from jibrel.campaigns.models import Offering
from jibrel.core.permissions import IsKYCVerifiedUser
from jibrel.investment.models import InvestmentApplication
from jibrel.investment.serializer import InvestmentApplicationSerializer


class InvestmentApplicationAPIView(CreateAPIView):
    permission_classes = [IsKYCVerifiedUser]
    serializer_class = InvestmentApplicationSerializer
    queryset = InvestmentApplication.objects.all()
    offering_queryset = Offering.objects.all()  # TODO exclude inactive/closed/etc.

    @cached_property
    def offering(self):
        return get_object_or_404(self.offering_queryset, pk=self.kwargs.get('offering_id'))

    def post(self, request, *args, **kwargs):
        self.offering  # raises 404 if offering doesn't exist
        return super(InvestmentApplicationAPIView, self).post(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(
            offering=self.offering,
            user=self.request.user,
            account=UserAccount.objects.for_customer(
                user=self.request.user,
                asset=Asset.objects.main_fiat_for_customer(self.request.user)
            )
        )
